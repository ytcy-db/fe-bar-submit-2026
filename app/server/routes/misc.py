"""Schedule (CRUD) and product feedback — app-owned operational tables in Lakebase (crm_ops)."""
from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..pg import pg_query, pg_execute

router = APIRouter()


@router.get("/schedule")
def get_schedule():
    """Meetings; recommended ones carry the ticket (or retention action) that triggered them."""
    rows = pg_query("""
        SELECT s.schedule_id, s.account_id, a.company_name, s.owner, s.date, s.title, s.kind, s.ticket_id,
               s.start_time, s.duration_min, s.action_id,
               t.subject AS ticket_subject, t.priority AS ticket_priority, t.status AS ticket_status,
               t.category AS ticket_category, a.risk_band, a.churn_probability
        FROM crm_ops.schedule s
        LEFT JOIN serving.account_360 a ON a.account_id = s.account_id
        LEFT JOIN serving.tickets t ON t.ticket_id = s.ticket_id
        ORDER BY s.date, s.start_time""")
    return {"schedule": rows}


class ScheduleUpsert(BaseModel):
    account_id: str | None = None
    owner: str
    date: str
    title: str
    kind: str = "confirmed"
    ticket_id: str | None = None
    start_time: str = "10:00"
    duration_min: int = 30


@router.post("/schedule")
def create_schedule(body: ScheduleUpsert):
    last = pg_query("SELECT max(substring(schedule_id from 4)::int) AS m FROM crm_ops.schedule")
    sid = f"SC-{(last[0]['m'] or 100) + 1}"
    pg_execute("""INSERT INTO crm_ops.schedule (schedule_id, account_id, owner, date, title, kind, ticket_id, start_time, duration_min)
                  VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
               (sid, body.account_id, body.owner, body.date, body.title, body.kind, body.ticket_id or None,
                body.start_time, body.duration_min))
    return {"ok": True, "schedule_id": sid}


@router.patch("/schedule/{schedule_id}")
def update_schedule(schedule_id: str, body: ScheduleUpsert):
    n = pg_execute("""UPDATE crm_ops.schedule SET account_id=%s, owner=%s, date=%s, title=%s, kind=%s,
                      ticket_id=%s, start_time=%s, duration_min=%s WHERE schedule_id=%s""",
                   (body.account_id, body.owner, body.date, body.title, body.kind, body.ticket_id or None,
                    body.start_time, body.duration_min, schedule_id))
    if not n:
        raise HTTPException(404, "schedule not found")
    return {"ok": True}


@router.delete("/schedule/{schedule_id}")
def delete_schedule(schedule_id: str):
    pg_execute("DELETE FROM crm_ops.schedule WHERE schedule_id=%s", (schedule_id,))
    return {"ok": True}


@router.get("/feedback")
def list_feedback():
    return {"feedback": pg_query("""SELECT feedback_id, title, detail, priority, status, created_at, submitted_by
                                    FROM crm_ops.feedback ORDER BY created_at DESC, feedback_id DESC""")}


class NewFeedback(BaseModel):
    title: str
    detail: str = ""
    priority: str = "中"
    submitted_by: str = "CS運用チーム"


@router.post("/feedback")
def add_feedback(body: NewFeedback):
    last = pg_query("SELECT max(substring(feedback_id from 4)::int) AS m FROM crm_ops.feedback")
    fid = f"FB-{(last[0]['m'] or 200) + 1}"
    pg_execute("INSERT INTO crm_ops.feedback VALUES (%s,%s,%s,%s,'未対応',%s,%s)",
               (fid, body.title, body.detail, body.priority, date.today().isoformat(), body.submitted_by))
    return {"ok": True, "feedback_id": fid}


class FeedbackStatus(BaseModel):
    status: str


@router.patch("/feedback/{feedback_id}")
def update_feedback(feedback_id: str, body: FeedbackStatus):
    pg_execute("UPDATE crm_ops.feedback SET status=%s WHERE feedback_id=%s", (body.status, feedback_id))
    return {"ok": True}
