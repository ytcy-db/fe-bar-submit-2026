# Databricks notebook source
# MAGIC %md
# MAGIC # 05 — Publish gold tables to Lakebase (operational serving layer)
# MAGIC
# MAGIC The CS app needs **millisecond point lookups and transactional writes** (CSM actions, meetings,
# MAGIC ticket replies) — an OLTP workload. Lakebase (serverless Postgres) is that layer:
# MAGIC
# MAGIC | Lakebase schema | Owner | Content |
# MAGIC |---|---|---|
# MAGIC | `serving` | this job (read-only for the app) | `account_360`, `tickets`, `ticket_events`, `usage_weekly`, published from UC gold/silver |
# MAGIC | `crm_ops` | the app service principal | app writes: `retention_actions`, `schedule`, `feedback`, `ticket_updates`, `ticket_replies`, `genie_history` |
# MAGIC
# MAGIC **Why a job-based publish instead of Synced Tables?** Lakebase Synced Tables are the managed
# MAGIC option, but they require registering the Lakebase database as a UC catalog (`CREATE CATALOG` on
# MAGIC the metastore), which this sandbox workspace does not grant. This task performs the same
# MAGIC Delta→Postgres reverse-ETL as an idempotent, transactional full reload after every scoring run
# MAGIC (≈40k rows in a few seconds). Switching to Synced Tables is a configuration change; the app is unaffected.

# COMMAND ----------

# MAGIC %pip install -q psycopg2-binary==2.9.10

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import io
import json
import time
import psycopg2
from databricks.sdk import WorkspaceClient

dbutils.widgets.text("catalog", "ytcy_azure_east2classic_stable")
dbutils.widgets.text("schema", "officepulse_churn")
dbutils.widgets.text("lakebase_project", "officepulse-crm")
dbutils.widgets.text("app_sp", "bbf9c5aa-04e7-48e6-8cc2-0ca1ad4ff6b6")
CATALOG, SCHEMA = dbutils.widgets.get("catalog"), dbutils.widgets.get("schema")
PROJECT, APP_SP = dbutils.widgets.get("lakebase_project"), dbutils.widgets.get("app_sp")
FQ = f"{CATALOG}.{SCHEMA}"
ENDPOINT = f"projects/{PROJECT}/branches/production/endpoints/primary"

w = WorkspaceClient()
ep = w.api_client.do("GET", f"/api/2.0/postgres/{ENDPOINT}")
HOST = ep["status"]["hosts"]["host"]
USER = w.current_user.me().user_name


def connect():
    token = w.api_client.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": ENDPOINT})["token"]
    return psycopg2.connect(host=HOST, port=5432, dbname="databricks_postgres", user=USER, password=token, sslmode="require")


print("Lakebase endpoint:", HOST, "as", USER)

# COMMAND ----------

PG_TYPES = {"string": "text", "int": "integer", "bigint": "bigint", "smallint": "smallint", "double": "double precision",
            "float": "real", "boolean": "boolean", "date": "date", "timestamp": "timestamp", "timestamp_ntz": "timestamp"}

TABLES = {
    # lakebase table: (UC source, primary key, extra indexes)
    "account_360": (f"{FQ}.gold_account_360", ["account_id"], ["risk_band", "csm_owner", "status"]),
    "tickets": (f"{FQ}.silver_tickets", ["ticket_id"], ["account_id", "status"]),
    "ticket_events": (f"{FQ}.silver_ticket_events", ["event_id"], ["ticket_id"]),
    "usage_weekly": (f"{FQ}.silver_usage_weekly", ["account_id", "week_start"], []),
}


def pg_type(spark_type: str) -> str:
    t = spark_type.lower()
    if t.startswith("decimal"):
        return "numeric"
    return PG_TYPES.get(t, "text")


def publish(conn, name, source, pk, indexes):
    sdf = spark.table(source)
    cols = [(f.name, pg_type(f.dataType.simpleString())) for f in sdf.schema.fields]
    pdf = sdf.toPandas()
    for c, t in cols:  # nullable integers arrive as float64 from Arrow ("4.0" would not load into integer)
        if t in ("integer", "bigint", "smallint"):
            pdf[c] = pdf[c].astype("Int64")
    buf = io.StringIO()
    pdf.to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)
    t0 = time.time()
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS serving")
        cur.execute(f"DROP TABLE IF EXISTS serving.{name}")
        cur.execute(f"CREATE TABLE serving.{name} ({', '.join(f'{c} {t}' for c, t in cols)}, PRIMARY KEY ({', '.join(pk)}))")
        cur.copy_expert(f"COPY serving.{name} FROM STDIN WITH (FORMAT csv, NULL '\\N')", buf)
        for ix in indexes:
            cur.execute(f"CREATE INDEX ON serving.{name} ({ix})")
        cur.execute(f"COMMENT ON TABLE serving.{name} IS 'Published from {source} by job officepulse-churn-e2e'")
        if app_role_exists:
            cur.execute(f'GRANT SELECT ON serving.{name} TO "{APP_SP}"')
    conn.commit()  # drop + create + load is one transaction: readers never see a half-loaded table
    return len(pdf), round(time.time() - t0, 2)


conn = connect()
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_SP,))
    app_role_exists = cur.fetchone() is not None
    cur.execute("CREATE SCHEMA IF NOT EXISTS serving")
    if app_role_exists:
        cur.execute(f'GRANT USAGE ON SCHEMA serving TO "{APP_SP}"')
conn.commit()
print("app service principal role present in Lakebase:", app_role_exists)

results = {}
for name, (src, pk, ix) in TABLES.items():
    n, sec = publish(conn, name, src, pk, ix)
    results[name] = {"rows": n, "seconds": sec}
    print(f"published {src} -> serving.{name}: {n} rows in {sec}s")

# COMMAND ----------

# MAGIC %md ## Verify: row counts and point-lookup latency (Lakebase vs. SQL warehouse)

# COMMAND ----------

with conn.cursor() as cur:
    for name in TABLES:
        cur.execute(f"SELECT count(*) FROM serving.{name}")
        results[name]["rows_in_lakebase"] = cur.fetchone()[0]
    cur.execute("""SELECT account_id, company_name, risk_band, round(churn_probability::numeric, 3), csm_flagged, hidden_risk
                   FROM serving.account_360 WHERE churn_probability IS NOT NULL
                   ORDER BY churn_probability DESC LIMIT 10""")
    top10 = cur.fetchall()
    ids = [r[0] for r in top10]
    lat = []
    for i in range(50):
        t0 = time.perf_counter()
        cur.execute("SELECT * FROM serving.account_360 WHERE account_id = %s", (ids[i % len(ids)],))
        cur.fetchall()
        lat.append((time.perf_counter() - t0) * 1000)
lat.sort()
results["lakebase_point_lookup_ms"] = {"p50": round(lat[len(lat) // 2], 1), "p95": round(lat[int(len(lat) * 0.95)], 1)}
for r in top10:
    print(r)
print(json.dumps(results, indent=2, ensure_ascii=False))
conn.close()

# COMMAND ----------

dbutils.notebook.exit(json.dumps(results, ensure_ascii=False))
