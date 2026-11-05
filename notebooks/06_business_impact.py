# Databricks notebook source
# MAGIC %md
# MAGIC # 06 — Business impact in the buyer's KPIs (GRR, churned ARR, CSM capacity)
# MAGIC
# MAGIC Converts the out-of-time model evaluation (`gold_model_metrics`, T-90 checkpoint) into the KPIs
# MAGIC the VP Customer Success and the CFO track. All inputs are read from tables produced earlier in the
# MAGIC job; assumptions are explicit parameters so the business can challenge them.
# MAGIC
# MAGIC **Save-rate assumptions (conservative, adjustable):**
# MAGIC * A save play started ≥ 90 days before renewal (exec sponsor call, adoption workshop, sensor
# MAGIC   re-provisioning, right-sizing) retains **30%** of at-risk ARR.
# MAGIC * A save play started only when the customer sends a cancellation ticket (median 31 days before
# MAGIC   renewal, status quo) retains **10%**.

# COMMAND ----------

import json
import pandas as pd

dbutils.widgets.text("catalog", "ytcy_azure_east2classic_stable")
dbutils.widgets.text("schema", "officepulse_churn")
dbutils.widgets.text("save_rate_early", "0.30")
dbutils.widgets.text("save_rate_late", "0.10")
FQ = f"{dbutils.widgets.get('catalog')}.{dbutils.widgets.get('schema')}"
SAVE_EARLY = float(dbutils.widgets.get("save_rate_early"))
SAVE_LATE = float(dbutils.widgets.get("save_rate_late"))

m = {r["metric"]: r["value"] for r in spark.table(f"{FQ}.gold_model_metrics").collect()}
display(spark.table(f"{FQ}.gold_model_metrics").orderBy("metric_group", "metric"))

# COMMAND ----------

# MAGIC %md ## Trailing-12-month churn, ARR base and today's risk book

# COMMAND ----------

# Trailing-12-month churn and ARR base from the Lakeflow gold tables
t12 = spark.sql(f"""
SELECT sum(churned_accounts) AS churned_logos_12m, sum(churned_arr_jpy) AS churned_arr_12m
FROM {FQ}.gold_churn_monthly WHERE month >= add_months(DATE'2026-11-01', -12) AND month < DATE'2026-11-01'
""").first()
base = spark.sql(f"""
SELECT sum(CASE WHEN c.start_date <= add_months(DATE'2026-11-01', -12)
                 AND (c.end_date IS NULL OR c.end_date > add_months(DATE'2026-11-01', -12)) THEN a.arr_jpy END) AS arr_start_12m,
       sum(CASE WHEN c.end_date IS NULL THEN a.arr_jpy END) AS arr_live_now
FROM {FQ}.silver_contracts c JOIN {FQ}.silver_accounts a USING (account_id)
""").first()
now = spark.sql(f"""
SELECT count(*) AS scored, sum(CASE WHEN risk_band = '高' THEN 1 ELSE 0 END) AS high,
       sum(CASE WHEN risk_band = '高' THEN arr_jpy ELSE 0 END) AS high_arr,
       sum(CASE WHEN hidden_risk THEN 1 ELSE 0 END) AS hidden, sum(CASE WHEN hidden_risk THEN arr_jpy ELSE 0 END) AS hidden_arr,
       sum(arr_at_risk_jpy) AS expected_arr_at_risk,
       sum(CASE WHEN risk_band = '高' AND datediff(renewal_date, DATE'2026-11-02') BETWEEN 0 AND 180 THEN arr_jpy ELSE 0 END) AS high_arr_renewing_180d
FROM {FQ}.gold_account_360 WHERE churn_probability IS NOT NULL
""").first()

print(t12, base, now, sep="\n")

# COMMAND ----------

# MAGIC %md ## Business case

# COMMAND ----------

churned_arr = float(t12.churned_arr_12m)
arr_start = float(base.arr_start_12m)
ml_cov = m["ml_arr_recall_at_t90"]
rules_cov = m["rules_arr_recall_at_t90"]
ticket_cov = m["cancel_ticket_share_of_churners"]

saved_status_quo = churned_arr * ticket_cov * SAVE_LATE
saved_rules = churned_arr * rules_cov * SAVE_EARLY
saved_ml = churned_arr * ml_cov * SAVE_EARLY
grr_now = 1 - churned_arr / arr_start
impact = {
    "arr_live_now_jpy": float(base.arr_live_now),
    "arr_start_12m_jpy": arr_start,
    "churned_logos_12m": float(t12.churned_logos_12m),
    "churned_arr_12m_jpy": churned_arr,
    "gross_revenue_retention_12m": grr_now,
    "ml_arr_coverage_t90": ml_cov,
    "rules_arr_coverage_t90": rules_cov,
    "cancel_ticket_coverage_any_time": ticket_cov,
    "arr_saved_status_quo_jpy": saved_status_quo,
    "arr_saved_with_ml_jpy": saved_ml,
    "incremental_arr_saved_vs_status_quo_jpy": saved_ml - saved_status_quo,
    "incremental_arr_saved_vs_rules_jpy": saved_ml - saved_rules,
    # observed churn already includes the status-quo saves, so only the increment improves GRR
    "grr_with_ml": 1 - (churned_arr - (saved_ml - saved_status_quo)) / arr_start,
    "grr_uplift_pts": (saved_ml - saved_status_quo) / arr_start * 100,
    "alerts_per_quarter_t90": m["ml_alerts_at_t90"] / 2,   # test window covers ~6 months of renewals
    "alert_precision_t90": m["ml_precision_at_t90"],
    "accounts_scored_now": float(now.scored),
    "high_risk_accounts_now": float(now.high),
    "high_risk_arr_now_jpy": float(now.high_arr),
    "high_risk_arr_renewing_180d_jpy": float(now.high_arr_renewing_180d),
    "hidden_risk_accounts_now": float(now.hidden),
    "hidden_risk_arr_now_jpy": float(now.hidden_arr),
    "expected_arr_at_risk_now_jpy": float(now.expected_arr_at_risk),
    "save_rate_early": SAVE_EARLY,
    "save_rate_late": SAVE_LATE,
}
pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
display(pd.DataFrame(impact.items(), columns=["kpi", "value"]))

# COMMAND ----------

spark.createDataFrame(pd.DataFrame([(k, float(v)) for k, v in impact.items()], columns=["kpi", "value"])) \
    .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.gold_business_impact")
spark.sql(f"COMMENT ON TABLE {FQ}.gold_business_impact IS 'Business case KPIs (JPY) derived from out-of-time model evaluation and trailing-12-month churn. Save-rate assumptions are rows save_rate_early / save_rate_late.'")

print(f"""
Trailing 12 months: {t12.churned_logos_12m} logos churned, ¥{churned_arr/1e6:,.0f}M ARR lost, GRR {grr_now:.1%}
Status quo (react to cancellation ticket): saves ¥{saved_status_quo/1e6:,.1f}M/yr
With ML early warning at T-90:            saves ¥{saved_ml/1e6:,.1f}M/yr  (+¥{(saved_ml-saved_status_quo)/1e6:,.1f}M, GRR +{impact['grr_uplift_pts']:.1f} pts)
Today: {now.high} high-risk accounts, ¥{now.high_arr/1e6:,.0f}M ARR; {now.hidden} of them NOT flagged by CSMs (¥{now.hidden_arr/1e6:,.0f}M)
""")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({k: round(v, 4) for k, v in impact.items()}))
