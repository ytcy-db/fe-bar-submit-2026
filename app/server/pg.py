"""Lakebase (serverless Postgres) access layer — the app's operational store.

* `serving.*`  : read-only tables published from Unity Catalog gold/silver by the job
                 (account_360 with ML scores, tickets, ticket_events, usage_weekly).
* `crm_ops.*`  : tables owned by the app service principal for transactional writes
                 (retention actions, schedule, feedback, ticket updates/replies, Genie history).

Authentication is Lakebase OAuth: a short-lived database credential is minted with the
workspace identity (app service principal on Databricks Apps, the developer locally) via
`POST /api/2.0/postgres/credentials` and used as the Postgres password. Credentials last ~1h,
so connections are re-created after 45 minutes.
"""
import os
import threading
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

from .config import get_workspace_client, IS_DATABRICKS_APP

LAKEBASE_ENDPOINT = os.environ.get("LAKEBASE_ENDPOINT", "projects/officepulse-crm/branches/production/endpoints/primary")
PGDATABASE = os.environ.get("PGDATABASE", "databricks_postgres")
_TTL = 45 * 60

_lock = threading.Lock()
_pool: ThreadedConnectionPool | None = None
_pool_born = 0.0


def _pg_user() -> str:
    if IS_DATABRICKS_APP:
        return os.environ["DATABRICKS_CLIENT_ID"]  # Postgres role = app service principal client id
    return os.environ.get("PGUSER") or get_workspace_client().current_user.me().user_name


def _new_pool() -> ThreadedConnectionPool:
    w = get_workspace_client()
    host = os.environ.get("PGHOST") or w.api_client.do("GET", f"/api/2.0/postgres/{LAKEBASE_ENDPOINT}")["status"]["hosts"]["host"]
    token = w.api_client.do("POST", "/api/2.0/postgres/credentials", body={"endpoint": LAKEBASE_ENDPOINT})["token"]
    return ThreadedConnectionPool(1, 8, host=host, port=5432, dbname=PGDATABASE, user=_pg_user(),
                                  password=token, sslmode="require", connect_timeout=15,
                                  application_name="officepulse-crm-app")


def _get_pool() -> ThreadedConnectionPool:
    global _pool, _pool_born
    with _lock:
        if _pool is None or time.time() - _pool_born > _TTL:
            old = _pool
            _pool, _pool_born = _new_pool(), time.time()
            if old is not None:
                try:
                    old.closeall()
                except Exception:
                    pass
        return _pool


@contextmanager
def _conn():
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def _jsonable(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            v = v.isoformat(sep=" ") if hasattr(v, "hour") else v.isoformat()
        elif v.__class__.__name__ == "Decimal":
            v = float(v)
        out[k] = v
    return out


def pg_query(sql: str, params: list | tuple | None = None) -> list[dict]:
    """Run a SELECT and return rows as JSON-friendly dicts (%s placeholders)."""
    for attempt in range(2):
        try:
            with _conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                return [_jsonable(dict(r)) for r in cur.fetchall()]
        except psycopg2.OperationalError:
            # compute may have scaled to zero or the credential expired: rebuild the pool once
            global _pool
            _pool = None
            if attempt:
                raise
    return []


def pg_execute(sql: str, params: list | tuple | None = None) -> int:
    with _conn() as c, c.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount


def timed_query(sql: str, params=None) -> tuple[list[dict], float]:
    t0 = time.perf_counter()
    rows = pg_query(sql, params)
    return rows, round((time.perf_counter() - t0) * 1000, 1)
