"""CloudNest OfficePulse — churn-prevention CRM (Databricks Apps entry point).

Data paths:
  * Lakebase (Postgres)  : account_360 + ML scores, tickets, operational writes (crm_ops)
  * SQL warehouse (UC)   : gold aggregates, model evaluation, business case
  * Model Serving        : officepulse-churn-model (real-time what-if)
  * UC model service     : churn_advisor_llm (GenAI retention playbook)
  * Genie space          : natural-language analytics over the governed gold tables
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from server import ops
from server.routes import dashboard, accounts, tickets, misc, genie

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        ops.bootstrap()  # create/seed the app-owned Lakebase schema crm_ops
    except Exception as e:  # keep serving read paths even if bootstrap fails
        log.exception("crm_ops bootstrap failed: %s", e)
    yield


app = FastAPI(title="OfficePulse Churn-Prevention CRM", lifespan=lifespan)

for r in (dashboard, accounts, tickets, misc, genie):
    app.include_router(r.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    from server.config import CATALOG, SCHEMA, LLM_MODEL_SERVICE, CHURN_MODEL_ENDPOINT, GENIE_SPACE_ID
    from server.pg import LAKEBASE_ENDPOINT
    return {
        "product": "OfficePulse",
        "vendor": "CloudNest 株式会社",
        "catalog": CATALOG,
        "schema": SCHEMA,
        "llm_model_service": LLM_MODEL_SERVICE,
        "churn_model_endpoint": CHURN_MODEL_ENDPOINT,
        "lakebase_endpoint": LAKEBASE_ENDPOINT,
        "genie_enabled": bool(GENIE_SPACE_ID),
    }


# --- static frontend ---
_frontend = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_frontend):
    _assets = os.path.join(_frontend, "assets")
    if os.path.isdir(_assets):
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "not found"}, status_code=404)
        index = os.path.join(_frontend, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"detail": "frontend not built"}, status_code=404)
