"""Call the deployed Databricks App's REST API end to end and record the responses as text evidence
(evidence/app_api_smoke_test.md). Exercises every integration: Lakebase reads/writes, SQL warehouse,
Model Serving what-if, UC model service (LLM) and Genie.

usage: python scripts/smoke_test_app.py --profile Azure-ytcy-east2 [--account ACC-1004] [--skip-llm]
"""
import argparse, datetime, json, subprocess, time, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True)
ap.add_argument("--app", default="crm-help-desk-demo")
ap.add_argument("--account", default="ACC-1004")
ap.add_argument("--skip-llm", action="store_true")
a = ap.parse_args()
CLI = "/opt/homebrew/bin/databricks"
url = json.loads(subprocess.run([CLI, "apps", "get", a.app, "--profile", a.profile, "-o", "json"], capture_output=True, text=True).stdout)["url"]
tok = json.loads(subprocess.run([CLI, "auth", "token", "--profile", a.profile], capture_output=True, text=True).stdout)["access_token"]
md = [f"# App API smoke test — {url}\n", f"Run {datetime.datetime.now():%Y-%m-%d %H:%M:%S} by `scripts/smoke_test_app.py` against the deployed Databricks App.\n"]


def call(method, path, body=None, keep=1800):
    t0 = time.perf_counter()
    req = urllib.request.Request(url + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            status, data = r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        status, data = e.code, {"error": e.read().decode()[:500]}
    ms = round((time.perf_counter() - t0) * 1000)
    txt = json.dumps(data, ensure_ascii=False, indent=1, default=str)
    md.append(f"\n## `{method} {path}` → HTTP {status} ({ms} ms end-to-end)\n")
    if body is not None:
        md.append(f"request: `{json.dumps(body, ensure_ascii=False)}`\n")
    md.append("```json\n" + (txt[:keep] + ("\n... (truncated)" if len(txt) > keep else "")) + "\n```")
    print(method, path, status, ms, "ms")
    return data


call("GET", "/api/health")
call("GET", "/api/meta")
call("GET", "/api/dashboard/kpis")
call("GET", "/api/churn/summary")
acc = call("GET", "/api/accounts?band=%E9%AB%98", keep=2500)
call("GET", f"/api/accounts/{a.account}", keep=2500)
call("POST", f"/api/accounts/{a.account}/whatif", {"overrides": {"attendance_detect_rate_4w": 0.85, "login_rate_4w": 0.8, "avg_csat_12w": 4.2, "open_tickets": 0}})
if not a.skip_llm:
    rec = call("POST", f"/api/accounts/{a.account}/recommend", keep=4000)
    acts = (rec.get("recommendation") or {}).get("recommended_actions") or []
    if acts:
        call("POST", f"/api/accounts/{a.account}/actions", {"action": acts[0]["action"], "priority": acts[0].get("priority", "高"),
                                                          "rationale": acts[0].get("rationale"), "due_in_days": acts[0].get("due_in_days", 7),
                                                          "add_to_schedule": True})
call("GET", "/api/actions", keep=1500)
call("GET", "/api/model/summary", keep=2500)
call("GET", "/api/tickets?company=%E3%83%86%E3%83%83%E3%82%AF%E3%83%96%E3%83%AA%E3%83%83%E3%82%B8", keep=1500)
call("GET", "/api/schedule", keep=1500)
call("POST", "/api/genie/ask", {"message": "CSMが未フラグの高リスク顧客は何社？期待損失ARRの合計も"}, keep=2500)
open("evidence/app_api_smoke_test.md", "w").write("\n".join(md) + "\n")
