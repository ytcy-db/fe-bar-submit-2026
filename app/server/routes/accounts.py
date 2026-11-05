"""Accounts / churn: ML scores from Lakebase, real-time what-if via Model Serving,
GenAI retention playbook, and CSM retention actions written back to Lakebase."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import llm
from ..config import get_workspace_client, CHURN_MODEL_ENDPOINT
from ..pg import pg_query, pg_execute, timed_query

router = APIRouter()

LIST_COLS = """account_id, company_name, industry, plan, status, csm_owner, seats, arr_jpy, region,
               auto_renew, used_services, start_date, renewal_date, end_date,
               churn_probability, risk_score, risk_band, rule_score, csm_flagged, hidden_risk,
               arr_at_risk_jpy, top_drivers, login_rate, attendance_detect_rate, open_tickets_now"""


def _drivers(v) -> list:
    if not v:
        return []
    try:
        return json.loads(v) if isinstance(v, str) else v
    except Exception:
        return []


def _account(account_id: str) -> dict:
    rows = pg_query("SELECT * FROM serving.account_360 WHERE account_id = %s", (account_id,))
    if not rows:
        raise HTTPException(404, "account not found")
    a = rows[0]
    a["top_drivers"] = _drivers(a.get("top_drivers"))
    a["features"] = json.loads(a["features_json"]) if a.get("features_json") else None
    a.pop("features_json", None)
    return a


@router.get("/accounts")
def list_accounts(q: str | None = None, industry: str | None = None, status: str | None = None,
                  band: str | None = None, hidden: bool | None = None):
    where, params = [], []
    if q:
        where.append("company_name ILIKE %s"); params.append(f"%{q}%")
    if industry:
        where.append("industry = %s"); params.append(industry)
    if status:
        where.append("status = %s"); params.append(status)
    if band:
        where.append("risk_band = %s"); params.append(band)
    if hidden:
        where.append("hidden_risk")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows, ms = timed_query(f"""SELECT {LIST_COLS} FROM serving.account_360 {clause}
                               ORDER BY churn_probability DESC NULLS LAST, arr_jpy DESC""", params)
    for r in rows:
        r["top_drivers"] = _drivers(r.get("top_drivers"))
    return {"accounts": rows, "latency_ms": ms, "source": "lakebase:serving.account_360"}


@router.get("/churn/at-risk")
def at_risk():
    return list_accounts()


@router.get("/churn/summary")
def churn_summary():
    rows, ms = timed_query("""
        SELECT count(*) FILTER (WHERE churn_probability IS NOT NULL) AS scored,
               count(*) FILTER (WHERE risk_band = '高') AS high,
               count(*) FILTER (WHERE risk_band = '中') AS mid,
               count(*) FILTER (WHERE hidden_risk) AS hidden,
               count(*) FILTER (WHERE csm_flagged) AS csm_flagged,
               coalesce(sum(arr_jpy) FILTER (WHERE risk_band = '高'), 0) AS high_arr_jpy,
               coalesce(sum(arr_jpy) FILTER (WHERE hidden_risk), 0) AS hidden_arr_jpy,
               coalesce(round(sum(arr_at_risk_jpy)), 0) AS expected_arr_at_risk_jpy,
               max(model_version) AS model_version, max(scored_at) AS scored_at
        FROM serving.account_360""")
    out = rows[0] if rows else {}
    out["latency_ms"] = ms
    return out


@router.get("/accounts/{account_id}")
def account_detail(account_id: str):
    account = _account(account_id)
    metrics, ms = timed_query("""
        SELECT week_start, login_rate, signup_rate, attendance_detect_rate, install_rate, app_config_ok_rate,
               dau, sessions, avg_session_min
        FROM serving.usage_weekly WHERE account_id = %s ORDER BY week_start DESC LIMIT 26""", (account_id,))
    metrics.reverse()
    tickets = pg_query("""
        WITH base AS (
          SELECT ticket_id, account_id, subject, category, priority, status, channel, assignee,
                 created_at, first_response_min, resolution_hours, csat FROM serving.tickets WHERE account_id = %s
          UNION ALL
          SELECT ticket_id, account_id, subject, category, priority, status, channel, assignee,
                 created_at, first_response_min, resolution_hours, csat FROM crm_ops.tickets_new WHERE account_id = %s),
        upd AS (SELECT DISTINCT ON (ticket_id) ticket_id, status FROM crm_ops.ticket_updates ORDER BY ticket_id, updated_at DESC)
        SELECT b.ticket_id, b.subject, b.category, b.priority, coalesce(u.status, b.status) AS status, b.channel,
               b.assignee, b.created_at, b.first_response_min, b.resolution_hours, b.csat
        FROM base b LEFT JOIN upd u USING (ticket_id) ORDER BY b.created_at DESC LIMIT 30""", (account_id, account_id))
    actions = pg_query("SELECT * FROM crm_ops.retention_actions WHERE account_id = %s ORDER BY created_at DESC", (account_id,))
    score = {"risk_score": account.get("risk_score"), "risk_band": account.get("risk_band"),
             "churn_probability": account.get("churn_probability"), "rule_score": account.get("rule_score"),
             "drivers": account.get("top_drivers"), "model_version": account.get("model_version"),
             "reasons": [d.get("label") for d in account.get("top_drivers") or []]}
    return {"account": account, "metrics": metrics, "tickets": tickets, "score": score,
            "actions": actions, "latency_ms": ms}


# ---------------------------------------------------------------------------
# Real-time what-if scoring on the served model
# ---------------------------------------------------------------------------
class WhatIf(BaseModel):
    overrides: dict[str, float] = {}


@router.post("/accounts/{account_id}/whatif")
def what_if(account_id: str, body: WhatIf):
    account = _account(account_id)
    feats = account.get("features")
    if not feats:
        raise HTTPException(400, "この顧客は現在スコア対象外です（契約終了・見込み客）")
    scenario = {**feats, **body.overrides}
    w = get_workspace_client()
    try:
        base, new = w.serving_endpoints.query(name=CHURN_MODEL_ENDPOINT, dataframe_records=[feats, scenario]).predictions
    except Exception as e:
        raise HTTPException(503, f"モデルサービングの呼び出しに失敗しました（スケールゼロからの起動中の可能性）: {e}")
    return {
        "baseline": {"churn_probability": base["churn_probability"], "drivers": _drivers(base.get("top_drivers"))},
        "scenario": {"churn_probability": new["churn_probability"], "drivers": _drivers(new.get("top_drivers"))},
        "overrides": body.overrides, "endpoint": CHURN_MODEL_ENDPOINT,
    }


# ---------------------------------------------------------------------------
# GenAI retention playbook (grounded on ML drivers)
# ---------------------------------------------------------------------------
@router.post("/accounts/{account_id}/recommend")
def recommend(account_id: str):
    d = account_detail(account_id)
    account, metrics, tickets = d["account"], d["metrics"], d["tickets"]
    latest, first = (metrics[-1] if metrics else {}), (metrics[0] if metrics else {})
    ml = {
        "解約確率(次回更新)": account.get("churn_probability"),
        "リスク帯": account.get("risk_band"),
        "主要因(SHAP)": account.get("top_drivers"),
        "特徴量": account.get("features"),
        "CSMの手動フラグ": account.get("csm_flagged"),
    }
    metrics_summary = {
        "最新_ログイン率": latest.get("login_rate"), "最新_出社検知率": latest.get("attendance_detect_rate"),
        "最新_設定良好率": latest.get("app_config_ok_rate"),
        "26週前_ログイン率": first.get("login_rate"), "26週前_出社検知率": first.get("attendance_detect_rate"),
    }
    tickets_summary = {
        "総チケット数": len(tickets),
        "未解決数": sum(1 for t in tickets if t["status"] in ("new", "open", "pending")),
        "高優先度数": sum(1 for t in tickets if t["priority"] in ("high", "urgent")),
        "平均CSAT": account.get("avg_csat"),
        "解約検討あり": bool(account.get("has_cancellation_ticket")),
        "直近の件名": [t["subject"] for t in tickets[:6]],
    }
    try:
        result = llm.recommend_actions(account, ml, metrics_summary, tickets_summary)
    except Exception as e:
        raise HTTPException(500, f"LLM 呼び出しに失敗しました: {e}")
    return {"score": d["score"], "recommendation": result}


# ---------------------------------------------------------------------------
# Retention actions (OLTP writes to Lakebase)
# ---------------------------------------------------------------------------
class NewAction(BaseModel):
    action: str
    priority: str = "中"
    rationale: str | None = None
    owner: str | None = None
    due_in_days: int | None = 7
    source: str = "ai_recommendation"
    add_to_schedule: bool = False


@router.post("/accounts/{account_id}/actions")
def create_action(account_id: str, body: NewAction):
    a = _account(account_id)
    rows = pg_query("""
        INSERT INTO crm_ops.retention_actions
          (account_id, action, priority, rationale, owner, due_date, source, churn_probability_at_creation, model_version)
        VALUES (%s, %s, %s, %s, %s, DATE '2026-11-02' + %s::int, %s, %s, %s)
        RETURNING action_id, due_date""",
        (account_id, body.action, body.priority, body.rationale, body.owner or a.get("csm_owner"),
         body.due_in_days or 7, body.source, a.get("churn_probability"), a.get("model_version")))
    action_id = rows[0]["action_id"]
    if body.add_to_schedule:
        last = pg_query("SELECT max(substring(schedule_id from 4)::int) AS m FROM crm_ops.schedule")
        sid = f"SC-{(last[0]['m'] or 100) + 1}"
        pg_execute("""INSERT INTO crm_ops.schedule (schedule_id, account_id, owner, date, title, kind, ticket_id,
                        start_time, duration_min, action_id)
                      VALUES (%s, %s, %s, %s, %s, 'recommended', NULL, '14:00', 45, %s)""",
                   (sid, account_id, a.get("csm_owner"), rows[0]["due_date"], f"{a['company_name']} {body.action[:40]}", action_id))
    return {"ok": True, "action_id": action_id}


class ActionUpdate(BaseModel):
    status: str
    outcome: str | None = None


@router.patch("/actions/{action_id}")
def update_action(action_id: int, body: ActionUpdate):
    n = pg_execute("UPDATE crm_ops.retention_actions SET status=%s, outcome=coalesce(%s, outcome), updated_at=now() WHERE action_id=%s",
                   (body.status, body.outcome, action_id))
    if not n:
        raise HTTPException(404, "action not found")
    return {"ok": True}


@router.get("/actions")
def list_actions():
    rows = pg_query("""
        SELECT r.*, a.company_name, a.risk_band, a.churn_probability AS churn_probability_now
        FROM crm_ops.retention_actions r LEFT JOIN serving.account_360 a USING (account_id)
        ORDER BY r.created_at DESC LIMIT 200""")
    return {"actions": rows}
