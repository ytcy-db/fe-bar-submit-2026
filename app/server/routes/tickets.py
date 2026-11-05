"""Help desk on Lakebase.

Ticket history comes from Zendesk via Lakeflow (`serving.tickets` / `serving.ticket_events`,
read-only). Agent work done in this app is written to app-owned tables (`crm_ops.ticket_updates`,
`crm_ops.ticket_replies`, `crm_ops.tickets_new`) and overlaid at read time, so a re-publish of the
serving tables never overwrites operational writes.
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..pg import pg_query, pg_execute

router = APIRouter()

TICKETS_CTE = """
WITH base AS (
  SELECT ticket_id, account_id, subject, category, priority, status, channel, assignee, created_at, updated_at,
         first_response_min, resolution_hours, csat, description FROM serving.tickets
  UNION ALL
  SELECT ticket_id, account_id, subject, category, priority, status, channel, assignee, created_at, updated_at,
         first_response_min, resolution_hours, csat, description FROM crm_ops.tickets_new),
upd AS (SELECT DISTINCT ON (ticket_id) ticket_id, status, assignee, updated_at
        FROM crm_ops.ticket_updates ORDER BY ticket_id, updated_at DESC),
rep AS (SELECT ticket_id, max(event_at) AS last_reply FROM crm_ops.ticket_replies GROUP BY ticket_id),
t AS (
  SELECT b.ticket_id, b.account_id, b.subject, b.category, b.priority,
         coalesce(u.status, b.status) AS status, b.channel, coalesce(u.assignee, b.assignee) AS assignee,
         b.created_at, greatest(b.updated_at, u.updated_at, r.last_reply) AS updated_at,
         b.first_response_min, b.resolution_hours, b.csat, b.description
  FROM base b LEFT JOIN upd u USING (ticket_id) LEFT JOIN rep r USING (ticket_id))
"""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@router.get("/tickets")
def list_tickets(status: str | None = None, priority: str | None = None,
                 account_id: str | None = None, q: str | None = None, company: str | None = None):
    where, params = [], []
    if status:
        where.append("t.status = %s"); params.append(status)
    if priority:
        where.append("t.priority = %s"); params.append(priority)
    if account_id:
        where.append("t.account_id = %s"); params.append(account_id)
    if q:
        where.append("t.subject ILIKE %s"); params.append(f"%{q}%")
    if company:
        where.append("a.company_name ILIKE %s"); params.append(f"%{company}%")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = pg_query(TICKETS_CTE + f"""
        SELECT t.ticket_id, t.account_id, a.company_name, t.subject, t.category, t.priority, t.status,
               t.channel, t.assignee, t.created_at, t.updated_at, t.first_response_min, t.resolution_hours, t.csat,
               a.risk_band, a.churn_probability
        FROM t LEFT JOIN serving.account_360 a USING (account_id)
        {clause}
        ORDER BY t.created_at DESC LIMIT 500""", params)
    return {"tickets": rows}


@router.get("/tickets/stats")
def ticket_stats():
    rows = pg_query(TICKETS_CTE + """
        SELECT count(*) AS total,
               count(*) FILTER (WHERE status IN ('new','open','pending')) AS open,
               count(*) FILTER (WHERE status = 'solved') AS solved,
               count(*) FILTER (WHERE priority IN ('high','urgent') AND status IN ('new','open','pending')) AS high_priority,
               round(avg(csat)::numeric, 2) AS avg_csat,
               round(avg(first_response_min)::numeric, 0) AS avg_first_response_min
        FROM t WHERE created_at >= DATE '2026-11-02' - 90""")
    by_status = pg_query(TICKETS_CTE + "SELECT status, count(*) AS c FROM t GROUP BY status")
    return {"stats": rows[0] if rows else {}, "by_status": by_status}


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str):
    rows = pg_query(TICKETS_CTE + """
        SELECT t.*, a.company_name, a.risk_band, a.churn_probability
        FROM t LEFT JOIN serving.account_360 a USING (account_id) WHERE t.ticket_id = %s""", (ticket_id,))
    if not rows:
        raise HTTPException(404, "ticket not found")
    events = pg_query("""
        SELECT event_at, author_type, author, body FROM serving.ticket_events WHERE ticket_id = %s
        UNION ALL
        SELECT event_at, author_type, author, body FROM crm_ops.ticket_replies WHERE ticket_id = %s
        ORDER BY event_at""", (ticket_id, ticket_id))
    return {"ticket": rows[0], "events": events}


class StatusUpdate(BaseModel):
    status: str
    assignee: str | None = None


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: str, body: StatusUpdate):
    pg_execute("INSERT INTO crm_ops.ticket_updates (ticket_id, status, assignee, updated_by, updated_at) VALUES (%s,%s,%s,%s,%s)",
               (ticket_id, body.status, body.assignee, "crm-app", _now()))
    return {"ok": True}


class NewReply(BaseModel):
    author: str
    body: str


@router.post("/tickets/{ticket_id}/reply")
def add_reply(ticket_id: str, body: NewReply):
    rows = pg_query(TICKETS_CTE + "SELECT account_id FROM t WHERE ticket_id = %s", (ticket_id,))
    if not rows:
        raise HTTPException(404, "ticket not found")
    pg_execute("INSERT INTO crm_ops.ticket_replies (ticket_id, account_id, event_at, author_type, author, body) VALUES (%s,%s,%s,'agent',%s,%s)",
               (ticket_id, rows[0]["account_id"], _now(), body.author, body.body))
    return {"ok": True}


class NewTicket(BaseModel):
    account_id: str
    subject: str
    category: str = "その他"
    priority: str = "normal"
    channel: str = "web_form"
    assignee: str = "未割当"
    description: str = ""


@router.post("/tickets")
def create_ticket(body: NewTicket):
    last = pg_query(TICKETS_CTE + "SELECT max(substring(ticket_id from 4)::int) AS m FROM t")
    tid = f"ZD-{(last[0]['m'] or 10000) + 1}"
    now = _now()
    pg_execute("""INSERT INTO crm_ops.tickets_new
        (ticket_id, account_id, subject, category, priority, status, channel, assignee, created_at, updated_at, description)
        VALUES (%s,%s,%s,%s,%s,'new',%s,%s,%s,%s,%s)""",
        (tid, body.account_id, body.subject, body.category, body.priority, body.channel, body.assignee, now, now, body.description))
    return {"ok": True, "ticket_id": tid}
