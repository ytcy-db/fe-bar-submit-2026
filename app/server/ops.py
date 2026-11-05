"""Bootstraps the app-owned Lakebase schema `crm_ops` (runs at app startup, idempotent).

The service principal creates and therefore owns this schema (Lakebase permission model), so no
human-owned objects block the app. Seed rows make the demo usable on first start: recommended
retention meetings are generated from the *current ML scores* in `serving.account_360` and linked
to the account's most severe open ticket.
"""
import logging
from .pg import pg_execute, pg_query

log = logging.getLogger("ops")

DDL = [
    "CREATE SCHEMA IF NOT EXISTS crm_ops",
    """CREATE TABLE IF NOT EXISTS crm_ops.retention_actions (
        action_id BIGSERIAL PRIMARY KEY,
        account_id TEXT NOT NULL,
        action TEXT NOT NULL,
        priority TEXT DEFAULT '中',
        rationale TEXT,
        owner TEXT,
        status TEXT DEFAULT 'planned',          -- planned | in_progress | done | dropped
        outcome TEXT,
        due_date DATE,
        source TEXT DEFAULT 'manual',           -- ai_recommendation | manual
        churn_probability_at_creation DOUBLE PRECISION,
        model_version INT,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now())""",
    "CREATE INDEX IF NOT EXISTS ix_actions_account ON crm_ops.retention_actions (account_id)",
    """CREATE TABLE IF NOT EXISTS crm_ops.schedule (
        schedule_id TEXT PRIMARY KEY, account_id TEXT, owner TEXT, date DATE, title TEXT,
        kind TEXT, ticket_id TEXT, start_time TEXT, duration_min INT, action_id BIGINT,
        created_at TIMESTAMPTZ DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS crm_ops.feedback (
        feedback_id TEXT PRIMARY KEY, title TEXT, detail TEXT, priority TEXT, status TEXT,
        created_at DATE, submitted_by TEXT)""",
    """CREATE TABLE IF NOT EXISTS crm_ops.tickets_new (
        ticket_id TEXT PRIMARY KEY, account_id TEXT, subject TEXT, category TEXT, priority TEXT,
        status TEXT, channel TEXT, assignee TEXT, created_at TIMESTAMP, updated_at TIMESTAMP,
        first_response_min INT, resolution_hours DOUBLE PRECISION, csat INT, description TEXT)""",
    """CREATE TABLE IF NOT EXISTS crm_ops.ticket_updates (
        id BIGSERIAL PRIMARY KEY, ticket_id TEXT NOT NULL, status TEXT, assignee TEXT,
        updated_by TEXT, updated_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Tokyo'))""",
    "CREATE INDEX IF NOT EXISTS ix_ticket_updates ON crm_ops.ticket_updates (ticket_id, updated_at DESC)",
    """CREATE TABLE IF NOT EXISTS crm_ops.ticket_replies (
        id BIGSERIAL PRIMARY KEY, ticket_id TEXT NOT NULL, account_id TEXT, event_at TIMESTAMP,
        author_type TEXT DEFAULT 'agent', author TEXT, body TEXT)""",
    """CREATE TABLE IF NOT EXISTS crm_ops.genie_history (
        history_id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, query TEXT,
        created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Tokyo'))""",
]

FEEDBACK = [
    ("FB-201", "CSVエクスポート項目のカスタマイズ", "CSVエクスポート時に出力項目を選択できるようにしてほしい。", "低", "完了"),
    ("FB-202", "出社検知の判定感度を調整したい", "フロアごとに検知感度をチューニングしたい。", "高", "対応中"),
    ("FB-203", "センサーのオフライン通知", "センサーが落ちたら管理者にすぐ通知してほしい（検知率低下の主要因）。", "高", "未対応"),
    ("FB-204", "モバイルアプリのウィジェット対応", "ホーム画面ウィジェットで出社状況を確認したい。", "中", "未対応"),
    ("FB-205", "Slack通知のテンプレート機能", "よく使う通知文をテンプレート化したい。", "低", "未対応"),
    ("FB-206", "APIレート制限の緩和", "大量データ連携時にレート制限に達する。", "高", "対応中"),
]
WEEK = ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]
TIMES = ["10:00", "11:00", "13:00", "14:00", "15:30", "16:00"]


def bootstrap() -> None:
    # Only the owner (the app service principal) runs DDL; a developer running locally against an
    # SP-owned schema skips straight to the data checks.
    exists = pg_query("SELECT to_regclass('crm_ops.genie_history') IS NOT NULL AS ok")[0]["ok"]
    if not exists:
        for stmt in DDL:
            pg_execute(stmt)
    if not pg_query("SELECT 1 FROM crm_ops.feedback LIMIT 1"):
        for fid, title, detail, pri, status in FEEDBACK:
            pg_execute("INSERT INTO crm_ops.feedback VALUES (%s,%s,%s,%s,%s,DATE '2026-10-20' + (random()*14)::int,'CS運用チーム')",
                       (fid, title, detail, pri, status))
    if not pg_query("SELECT 1 FROM crm_ops.schedule LIMIT 1"):
        _seed_schedule()
    log.info("crm_ops bootstrap complete")


def _seed_schedule() -> None:
    risky = pg_query("""
        SELECT a.account_id, a.company_name, a.csm_owner, a.churn_probability,
               (SELECT t.ticket_id FROM serving.tickets t
                 WHERE t.account_id = a.account_id
                 ORDER BY (t.subject LIKE '%%解約%%' OR t.subject LIKE '%%見送%%') DESC,
                          (t.status IN ('new','open','pending')) DESC,
                          (t.priority IN ('urgent','high')) DESC, t.created_at DESC
                 LIMIT 1) AS ticket_id
        FROM serving.account_360 a
        WHERE a.risk_band = '高' AND a.end_date IS NULL
        ORDER BY a.churn_probability DESC LIMIT 10""")
    healthy = pg_query("""
        SELECT account_id, company_name, csm_owner FROM serving.account_360
        WHERE risk_band = '低' AND end_date IS NULL ORDER BY md5(account_id) LIMIT 12""")
    n = 100
    for i, r in enumerate(risky):
        n += 1
        title = ["解約リスクヒアリング", "エグゼクティブ訪問", "利用改善提案", "契約更新交渉"][i % 4]
        pg_execute("INSERT INTO crm_ops.schedule VALUES (%s,%s,%s,%s,%s,'recommended',%s,%s,%s,NULL,now())",
                   (f"SC-{n}", r["account_id"], r["csm_owner"], WEEK[i % 5], f"{r['company_name']} {title}",
                    r["ticket_id"], TIMES[i % 6], 45))
    for i, r in enumerate(healthy):
        n += 1
        title = ["定例フォローアップ", "利用状況レビュー", "拡大提案", "契約更新相談"][i % 4]
        pg_execute("INSERT INTO crm_ops.schedule VALUES (%s,%s,%s,%s,%s,'confirmed',NULL,%s,%s,NULL,now())",
                   (f"SC-{n}", r["account_id"], r["csm_owner"], WEEK[(i + 2) % 5], f"{r['company_name']} {title}",
                    TIMES[(i + 3) % 6], 30))
