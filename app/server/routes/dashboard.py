"""Dashboard + model/impact endpoints.

Analytical aggregates (weekly KPI trend, churn history, model evaluation, business case) are read
from Unity Catalog gold tables through the serverless SQL warehouse; operational counters come
from Lakebase. Both paths report their latency so the UI can show OLAP vs OLTP.
"""
import time
from fastapi import APIRouter
from ..db import query
from ..config import fqtn
from ..pg import timed_query

router = APIRouter()


def _timed_sql(sql: str):
    t0 = time.perf_counter()
    rows = query(sql)
    return rows, round((time.perf_counter() - t0) * 1000, 1)


@router.get("/dashboard/kpis")
def dashboard_kpis():
    trend, ms_wh = _timed_sql(f"""
        SELECT week_start, login_rate_pct AS login_rate, signup_rate_pct AS signup_rate,
               attendance_detect_rate_pct AS attendance_detect_rate, install_rate_pct AS install_rate,
               app_config_ok_rate_pct AS app_config_ok_rate
        FROM {fqtn('gold_kpi_weekly')} ORDER BY week_start DESC LIMIT 2""")
    counts, ms_pg = timed_query("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE status = 'active') AS active,
               count(*) FILTER (WHERE status = 'onboarding') AS onboarding,
               count(*) FILTER (WHERE status = 'churn_risk') AS churn_risk,
               count(*) FILTER (WHERE status = 'churned') AS churned,
               count(*) FILTER (WHERE status = 'prospect') AS prospect,
               count(*) FILTER (WHERE risk_band = '高') AS ml_high,
               count(*) FILTER (WHERE hidden_risk) AS ml_hidden,
               coalesce(sum(arr_jpy) FILTER (WHERE end_date IS NULL AND status <> 'prospect'), 0) AS live_arr_jpy,
               coalesce(round(sum(arr_at_risk_jpy)), 0) AS expected_arr_at_risk_jpy,
               coalesce(sum(arr_jpy) FILTER (WHERE risk_band = '高'), 0) AS high_risk_arr_jpy
        FROM serving.account_360""")
    open_tickets, _ = timed_query("""
        SELECT count(*) AS c FROM serving.tickets t
        LEFT JOIN (SELECT DISTINCT ON (ticket_id) ticket_id, status FROM crm_ops.ticket_updates
                   ORDER BY ticket_id, updated_at DESC) u USING (ticket_id)
        WHERE coalesce(u.status, t.status) IN ('new','open','pending')""")
    return {
        "kpis": trend[0] if trend else {},
        "kpis_prev": trend[1] if len(trend) > 1 else {},
        "counts": counts[0] if counts else {},
        "open_tickets": open_tickets[0]["c"] if open_tickets else 0,
        "latency": {"sql_warehouse_ms": ms_wh, "lakebase_ms": ms_pg},
    }


@router.get("/dashboard/kpi-trend")
def kpi_trend():
    rows = query(f"""
        SELECT cast(week_start AS STRING) AS week, login_rate_pct AS login_rate, signup_rate_pct AS signup_rate,
               attendance_detect_rate_pct AS attendance_detect_rate, install_rate_pct AS install_rate,
               app_config_ok_rate_pct AS app_config_ok_rate
        FROM {fqtn('gold_kpi_weekly')} WHERE week_start >= DATE'2026-11-02' - INTERVAL 26 WEEKS ORDER BY week_start""")
    return {"trend": rows}


@router.get("/dashboard/churn-history")
def churn_history():
    rows = query(f"""
        SELECT cast(month AS STRING) AS month, churned_accounts, new_accounts, churned_arr_jpy
        FROM {fqtn('gold_churn_monthly')} ORDER BY month""")
    return {"history": rows}


@router.get("/model/summary")
def model_summary():
    """Model evaluation (out-of-time), feature importance and business case for the 'ML/効果' page."""
    metrics = {r["metric"]: r["value"] for r in query(f"SELECT metric, value FROM {fqtn('gold_model_metrics')}")}
    impact = {r["kpi"]: r["value"] for r in query(f"SELECT kpi, value FROM {fqtn('gold_business_impact')}")}
    importance = query(f"""SELECT feature, label_ja, round(importance, 4) AS importance
                           FROM {fqtn('gold_feature_importance')} ORDER BY importance DESC LIMIT 12""")
    return {"metrics": metrics, "impact": impact, "importance": importance,
            "model": f"{fqtn('churn_model')}@champion"}
