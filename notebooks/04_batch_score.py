# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — Batch-score every live account and build the Account 360 serving table
# MAGIC
# MAGIC * Loads `officepulse_churn.churn_model@champion` from Unity Catalog.
# MAGIC * Scores the **latest week** for every live account (renewal risk + top-3 SHAP drivers).
# MAGIC * Writes `gold_churn_scores` (history, appended per run) and `gold_account_360`
# MAGIC   (one row per account: CRM + contract + latest KPIs + features + score).
# MAGIC * `gold_account_360`, `silver_tickets`, `silver_ticket_events` and `silver_usage_weekly` have
# MAGIC   Change Data Feed enabled and are synced to **Lakebase** (see `05_publish_lakebase.py`) where the
# MAGIC   CS app reads them with millisecond latency.

# COMMAND ----------

# MAGIC %pip install -q "mlflow>=2.21,<4" "scikit-learn==1.5.2" "shap==0.46.0" "numpy<2.2"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import json
import mlflow
import numpy as np
import pandas as pd
from pyspark.sql import functions as F

from churn_features import FEATURES, build_features, rule_score

dbutils.widgets.text("catalog", "ytcy_azure_east2classic_stable")
dbutils.widgets.text("schema", "officepulse_churn")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
MODEL_URI = f"models:/{FQ}.churn_model@champion"
mlflow.set_registry_uri("databricks-uc")

model = mlflow.pyfunc.load_model(MODEL_URI)
version = mlflow.MlflowClient().get_model_version_by_alias(f"{FQ}.churn_model", "champion").version
print("loaded", MODEL_URI, "version", version)

# COMMAND ----------

weekly = spark.table(f"{FQ}.gold_account_weekly").toPandas()
contracts = spark.table(f"{FQ}.silver_contracts").toPandas()
accounts = spark.table(f"{FQ}.silver_accounts").toPandas()
latest_week = pd.to_datetime(weekly.week_start).max()

feat = build_features(weekly, contracts, accounts, with_label=False)
live_ids = set(contracts[contracts.end_date.isna()].account_id)
cur = feat[(feat.snapshot_week == latest_week) & feat.account_id.isin(live_ids)]
# accounts with < 12 weeks of usage are still onboarding: their ramp-up looks like a decline and the
# model was not trained on them -> they are handled by the onboarding playbook, not scored
n_onb = int((cur.weeks_observed < 12).sum())
cur = cur[cur.weeks_observed >= 12].reset_index(drop=True)
print("latest week:", latest_week.date(), " live accounts scored:", len(cur), " onboarding (not scored):", n_onb)

pred = model.predict(cur[FEATURES])
cur["churn_probability"] = pred["churn_probability"].values
cur["top_drivers"] = pred["top_drivers"].values
cur["rule_score"] = rule_score(cur).round(1)
cur["risk_score"] = (cur.churn_probability * 100).round(1)
cur["risk_band"] = np.select([cur.churn_probability >= 0.5, cur.churn_probability >= 0.25], ["高", "中"], "低")

status = accounts.set_index("account_id").status
cur["csm_flagged"] = cur.account_id.map(status).eq("churn_risk")
cur["hidden_risk"] = (cur.risk_band == "高") & ~cur.csm_flagged
cur["model_version"] = int(version)
cur["scored_at"] = pd.Timestamp.utcnow().tz_localize(None)

display(cur.sort_values("churn_probability", ascending=False)
        [["account_id", "churn_probability", "risk_band", "rule_score", "csm_flagged", "hidden_risk", "days_to_renewal", "top_drivers"]].head(25))

# COMMAND ----------

score_cols = ["account_id", "snapshot_week", "churn_probability", "risk_score", "risk_band", "rule_score",
              "top_drivers", "csm_flagged", "hidden_risk", "model_version", "scored_at"]
scores_sdf = spark.createDataFrame(cur[score_cols]).withColumn("snapshot_week", F.to_date("snapshot_week"))
scores_sdf.write.mode("append").option("mergeSchema", "true").saveAsTable(f"{FQ}.gold_churn_scores")
spark.sql(f"COMMENT ON TABLE {FQ}.gold_churn_scores IS 'Renewal-risk scores per account per scoring run (model officepulse_churn.churn_model@champion). top_drivers = JSON array of SHAP drivers.'")

# COMMAND ----------

# MAGIC %md ## Account 360 (one row per account) — the table the app serves from Lakebase

# COMMAND ----------

scores_sdf.createOrReplaceTempView("latest_scores")
spark.createDataFrame(cur[["account_id"] + FEATURES]).createOrReplaceTempView("latest_features")
spark.sql(f"""
CREATE OR REPLACE TABLE {FQ}.gold_account_360
COMMENT 'Account 360 for the CS app: CRM + contract + latest usage KPIs + ML renewal-risk score and drivers. Synced to Lakebase.'
TBLPROPERTIES (delta.enableChangeDataFeed = true)
AS
WITH last_usage AS (
  SELECT * FROM {FQ}.silver_usage_weekly
  QUALIFY row_number() OVER (PARTITION BY account_id ORDER BY week_start DESC) = 1
), tk AS (
  SELECT account_id,
         count(*) AS tickets_total,
         sum(CASE WHEN status IN ('new','open','pending') THEN 1 ELSE 0 END) AS open_tickets_now,
         round(avg(csat), 2) AS avg_csat,
         max(is_cancellation_intent) AS has_cancellation_ticket
  FROM {FQ}.silver_tickets GROUP BY account_id
)
SELECT
  a.account_id, a.company_name, a.industry, a.plan, a.status, a.csm_owner, a.seats, a.arr_jpy, a.region,
  c.contract_id, c.start_date, c.end_date, c.renewal_date, c.loaned_devices, c.used_services,
  c.churn_reason, c.mrr_jpy, c.auto_renew,
  u.week_start AS last_usage_week, u.login_rate, u.signup_rate, u.attendance_detect_rate, u.install_rate,
  u.app_config_ok_rate,
  coalesce(tk.tickets_total, 0) AS tickets_total, coalesce(tk.open_tickets_now, 0) AS open_tickets_now,
  tk.avg_csat, coalesce(tk.has_cancellation_ticket, false) AS has_cancellation_ticket,
  s.churn_probability, s.risk_score, s.risk_band, s.rule_score, s.top_drivers, s.csm_flagged, s.hidden_risk,
  s.model_version, s.scored_at,
  CASE WHEN s.churn_probability IS NOT NULL THEN round(s.churn_probability * a.arr_jpy) END AS arr_at_risk_jpy,
  to_json(named_struct({", ".join(f"'{f}', f.{f}" for f in FEATURES)})) AS features_json
FROM {FQ}.silver_accounts a
LEFT JOIN {FQ}.silver_contracts c ON c.account_id = a.account_id
LEFT JOIN last_usage u ON u.account_id = a.account_id
LEFT JOIN tk ON tk.account_id = a.account_id
LEFT JOIN latest_scores s ON s.account_id = a.account_id
LEFT JOIN latest_features f ON f.account_id = a.account_id
""")
spark.sql(f"ALTER TABLE {FQ}.gold_account_360 SET TAGS ('cs_domain' = 'customer_success', 'medallion_layer' = 'gold', 'serving_layer' = 'lakebase')")

# Source tables synced to Lakebase need Change Data Feed for TRIGGERED sync
for t in ["silver_tickets", "silver_ticket_events", "silver_usage_weekly"]:
    try:
        spark.sql(f"ALTER MATERIALIZED VIEW {FQ}.{t} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    except Exception as e:
        print(t, "CDF via ALTER not supported on MV (synced in SNAPSHOT mode):", str(e)[:120])

# COMMAND ----------

summary = spark.sql(f"""
SELECT risk_band, count(*) AS accounts, sum(arr_jpy) AS arr_jpy, round(sum(arr_at_risk_jpy)) AS arr_at_risk_jpy,
       sum(CASE WHEN csm_flagged THEN 1 ELSE 0 END) AS csm_flagged, sum(CASE WHEN hidden_risk THEN 1 ELSE 0 END) AS hidden_risk
FROM {FQ}.gold_account_360 WHERE churn_probability IS NOT NULL GROUP BY risk_band ORDER BY risk_band
""")
display(summary)
out = {r["risk_band"]: {k: (float(v) if v is not None else None) for k, v in r.asDict().items() if k != "risk_band"} for r in summary.collect()}

# COMMAND ----------

dbutils.notebook.exit(json.dumps({"scored_accounts": len(cur), "latest_week": str(latest_week.date()), "by_band": out}, ensure_ascii=False))
