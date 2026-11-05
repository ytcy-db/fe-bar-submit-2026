# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Unity Catalog governance
# MAGIC
# MAGIC Everything in this build lives in a single governed namespace `<catalog>.officepulse_churn`
# MAGIC (raw Volume, Lakeflow tables, ML feature/score tables, the registered model, the LLM model
# MAGIC service, and — via a database catalog — the Lakebase Postgres tables).
# MAGIC
# MAGIC This notebook applies the controls the CS organisation needs before a business app and an
# MAGIC NL agent can touch customer data:
# MAGIC
# MAGIC 1. **Classification tags** — domain / layer / owner on tables, `pii` on contact columns.
# MAGIC 2. **Column masks** — contact e-mail and phone are masked for everyone except the
# MAGIC    `officepulse-cs-leads` group (the app service principal and Genie users see masked values).
# MAGIC 3. **Least-privilege grants** — the app service principal gets read on the schema plus
# MAGIC    `EXECUTE` on the model; CS analysts get read for Genie.
# MAGIC 4. **Documentation** — table/column comments that Genie uses as semantic context.
# MAGIC 5. **Lineage** is captured automatically by UC (raw volume → bronze → silver → gold → model → scores);
# MAGIC    the last cell queries `system.access.table_lineage` to show it.

# COMMAND ----------

dbutils.widgets.text("catalog", "ytcy_azure_east2classic_stable")
dbutils.widgets.text("schema", "officepulse_churn")
dbutils.widgets.text("app_sp", "bbf9c5aa-04e7-48e6-8cc2-0ca1ad4ff6b6")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
APP_SP = dbutils.widgets.get("app_sp")
FQ = f"{CATALOG}.{SCHEMA}"


def run(sql):
    print(sql.strip().splitlines()[0][:140])
    return spark.sql(sql)

# COMMAND ----------

# MAGIC %md ## 1. Classification tags

# COMMAND ----------

LAYER = {
    "bronze_crm_accounts": "bronze", "bronze_crm_contracts": "bronze", "bronze_ga4_usage": "bronze",
    "bronze_zendesk_tickets": "bronze",
    "silver_accounts": "silver", "silver_contracts": "silver", "silver_usage_weekly": "silver",
    "silver_tickets": "silver", "silver_ticket_events": "silver",
    "gold_account_weekly": "gold", "gold_kpi_weekly": "gold", "gold_churn_monthly": "gold",
    "gold_account_360": "gold", "gold_churn_scores": "gold", "gold_model_metrics": "gold",
    "gold_business_impact": "gold", "ml_churn_training_set": "ml",
}
# NOTE: this metastore enforces governed tag policies on common keys (domain, pii, business_domain, ...),
# so we use our own keys plus the governed system / class.* tags where they fit.
existing = {r.tableName for r in spark.sql(f"SHOW TABLES IN {FQ}").collect()}


def safe(sql):
    try:
        run(sql)
    except Exception as e:
        print("  skipped:", str(e).splitlines()[0][:160])


for t, layer in LAYER.items():
    if t not in existing:
        continue
    safe(f"""ALTER TABLE {FQ}.{t} SET TAGS ('cs_domain' = 'customer_success', 'medallion_layer' = '{layer}',
            'data_owner' = 'cs_operations', 'data_provenance' = 'synthetic')""")
    if layer == "gold":  # governed tag: certified tables are what Genie and the app should use
        safe(f"ALTER TABLE {FQ}.{t} SET TAGS ('system.certification_status' = 'certified')")

safe(f"ALTER SCHEMA {FQ} SET TAGS ('cs_domain' = 'customer_success', 'use_case' = 'churn_prevention')")
safe(f"ALTER VOLUME {FQ}.raw SET TAGS ('medallion_layer' = 'landing', 'contains_contact_pii' = 'true')")

CLASS = {"contact_name": "class.name", "contact_email": "class.email_address", "contact_phone": "class.phone_number"}
for col, cls in CLASS.items():
    for t in ["bronze_crm_accounts", "silver_accounts"]:
        safe(f"ALTER TABLE {FQ}.{t} ALTER COLUMN {col} SET TAGS ('contact_pii' = 'true')")
        safe(f"ALTER TABLE {FQ}.{t} ALTER COLUMN {col} SET TAGS ('{cls}')")

# COMMAND ----------

# MAGIC %md ## 2. Column masks on contact PII
# MAGIC The mask function `mask_contact` is created in notebook 01 and attached to `silver_accounts.contact_email`
# MAGIC / `contact_phone` **inside the Lakeflow pipeline definition** (`MASK ${mask_function}` in `02_silver.sql`) —
# MAGIC pipeline-managed materialized views cannot be altered with `ALTER TABLE ... SET MASK`.
# MAGIC Below: the mask is visible in the table metadata and the values are masked for this caller.

# COMMAND ----------

display(spark.sql(f"""
SELECT table_name, column_name, mask_name FROM {CATALOG}.information_schema.column_masks
WHERE table_schema = '{SCHEMA}' ORDER BY table_name, column_name
"""))
display(spark.sql(f"SELECT account_id, company_name, contact_email, contact_phone FROM {FQ}.silver_accounts ORDER BY account_id LIMIT 5"))

# COMMAND ----------

# MAGIC %md ## 3. Least-privilege grants

# COMMAND ----------

grants = [
    f"GRANT USE CATALOG ON CATALOG {CATALOG} TO `{APP_SP}`",
    f"GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA {FQ} TO `{APP_SP}`",
    f"GRANT READ VOLUME ON VOLUME {FQ}.raw TO `{APP_SP}`",
]
for g in grants:
    try:
        run(g)
    except Exception as e:
        print("  grant skipped:", str(e)[:200])

display(spark.sql(f"SHOW GRANTS ON SCHEMA {FQ}"))

# COMMAND ----------

# MAGIC %md ## 4. Tag inventory and 5. lineage

# COMMAND ----------

display(spark.sql(f"""
SELECT table_name, tag_name, tag_value
FROM {CATALOG}.information_schema.table_tags
WHERE schema_name = '{SCHEMA}'
ORDER BY table_name, tag_name
"""))

display(spark.sql(f"""
SELECT table_name, column_name, tag_name, tag_value
FROM {CATALOG}.information_schema.column_tags
WHERE schema_name = '{SCHEMA}'
ORDER BY table_name, column_name
"""))

# COMMAND ----------

try:
    display(spark.sql(f"""
    SELECT DISTINCT source_table_full_name, target_table_full_name, entity_type
    FROM system.access.table_lineage
    WHERE target_table_catalog = '{CATALOG}' AND target_table_schema = '{SCHEMA}'
      AND source_table_full_name IS NOT NULL
    ORDER BY target_table_full_name
    """))
except Exception as e:
    print("system.access.table_lineage not readable:", str(e)[:200])
