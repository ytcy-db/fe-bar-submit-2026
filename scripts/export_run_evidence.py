"""Export execution evidence of a job run as TEXT (the reviewer cannot see screenshots).

For job `officepulse-churn-e2e` run <run_id>:
  * evidence/notebook_runs/<task>.ipynb   — every notebook task WITH its cell outputs (converted from the run export)
  * evidence/job_run_summary.md           — task states, durations, notebook exit values
  * evidence/pipeline_data_quality.md     — Lakeflow event log: rows written + expectation pass/fail per dataset

usage: python scripts/export_run_evidence.py --profile Azure-ytcy-east2 --run-id <job_run_id>
"""
import argparse, base64, datetime, json, os, re, subprocess, urllib.parse

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True)
ap.add_argument("--run-id", required=True)
ap.add_argument("--warehouse", default="9c8fac7a0b250221")
a = ap.parse_args()
CLI = "/opt/homebrew/bin/databricks"
os.makedirs("evidence/notebook_runs", exist_ok=True)


def cli(*args):
    out = subprocess.run([CLI, *args, "--profile", a.profile, "-o", "json"], capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr[:400])
    return json.loads(out.stdout)


def sql(stmt):
    r = cli("api", "post", "/api/2.0/sql/statements", "--json",
            json.dumps({"warehouse_id": a.warehouse, "statement": stmt, "wait_timeout": "50s"}))
    cols = [c["name"] for c in r["manifest"]["schema"]["columns"]]
    return cols, r.get("result", {}).get("data_array", []) or []


# ---------------------------------------------------------------- notebook -> ipynb
def table_text(data, schema, limit=40):
    cols = [c.get("name") for c in schema or []]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in (data or [])[:limit]:
        lines.append("| " + " | ".join("" if v is None else str(v)[:120] for v in row) + " |")
    if data and len(data) > limit:
        lines.append(f"... ({len(data)} rows, first {limit} shown)")
    return "\n".join(lines) + "\n"


def outputs_from(results):
    if not results:
        return []
    t, d = results.get("type"), results.get("data")
    if t in ("raw", "text", "ansi"):
        return [{"output_type": "stream", "name": "stdout", "text": str(d)}] if d else []
    if t == "table":
        return [{"output_type": "execute_result", "execution_count": None, "metadata": {},
                 "data": {"text/plain": table_text(d, results.get("schema"))}}]
    if t in ("html", "htmlSandbox"):
        txt = re.sub(r"<[^>]+>", " ", str(d))
        return [{"output_type": "display_data", "metadata": {}, "data": {"text/html": str(d)[:20000], "text/plain": txt[:4000]}}]
    if t == "error":
        return [{"output_type": "error", "ename": "Error", "evalue": str(results.get("summary") or d)[:2000], "traceback": []}]
    if t == "listResults":
        out = []
        for sub in d or []:
            out += outputs_from(sub)
        return out
    return [{"output_type": "stream", "name": "stdout", "text": json.dumps(results)[:4000]}]


def export_notebook(task_run_id, name):
    exp = cli("jobs", "export-run", str(task_run_id), "--views-to-export", "CODE")
    html = exp["views"][0]["content"]
    m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", html)
    model = json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode()))
    cells = []
    for i, c in enumerate(sorted(model["commands"], key=lambda c: c.get("position", 0))):
        src = c.get("command", "")
        if src.lstrip().startswith("%md"):
            cells.append({"cell_type": "markdown", "metadata": {}, "source": src.lstrip()[3:].lstrip("\n")})
            continue
        outs = outputs_from(c.get("results"))
        if c.get("errorSummary") and not any(o["output_type"] == "error" for o in outs):
            outs.append({"output_type": "error", "ename": "Error", "evalue": c["errorSummary"][:2000], "traceback": []})
        cells.append({"cell_type": "code", "metadata": {"databricks_run_cell": i}, "execution_count": i + 1,
                      "source": src, "outputs": outs})
    nb = {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
          "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                       "databricks": {"job_run_task_id": task_run_id, "exported_at": datetime.datetime.now().isoformat()}}}
    path = f"evidence/notebook_runs/{name}.ipynb"
    json.dump(nb, open(path, "w"), ensure_ascii=False, indent=1)
    return path, sum(len(c.get("outputs", [])) for c in cells)


# ---------------------------------------------------------------- job summary
run = cli("jobs", "get-run", a.run_id)
md = [f"# Job run evidence — `{run['run_name']}` run {a.run_id}\n",
      f"- Run page: {run.get('run_page_url')}",
      f"- Result: **{run['state'].get('result_state')}** ({run['state'].get('life_cycle_state')})",
      f"- Started: {datetime.datetime.fromtimestamp(run['start_time']/1000):%Y-%m-%d %H:%M:%S} — Ended: "
      f"{datetime.datetime.fromtimestamp(run.get('end_time', 0)/1000):%Y-%m-%d %H:%M:%S}\n",
      "| task | type | result | duration (s) | evidence |", "|---|---|---|---|---|"]
outputs = []
pipeline_update = None
for t in sorted(run["tasks"], key=lambda t: t.get("start_time", 0)):
    dur = round((t.get("end_time", 0) - t.get("start_time", 0)) / 1000)
    kind = "notebook" if "notebook_task" in t else "pipeline" if "pipeline_task" in t else "other"
    ev = ""
    if kind == "notebook":
        path, n = export_notebook(t["run_id"], t["task_key"])
        ev = f"`{path}` ({n} outputs)"
        try:
            o = cli("jobs", "get-run-output", str(t["run_id"]))
            if (o.get("notebook_output") or {}).get("result"):
                outputs.append((t["task_key"], o["notebook_output"]["result"]))
        except Exception:
            pass
    if kind == "pipeline":
        pipeline_update = t["pipeline_task"]["pipeline_id"]
        ev = "`evidence/pipeline_data_quality.md`"
    md.append(f"| {t['task_key']} | {kind} | {t['state'].get('result_state')} | {dur} | {ev} |")
md.append("\n## Notebook exit values (dbutils.notebook.exit)\n")
for k, v in outputs:
    try:
        v = json.dumps(json.loads(v), ensure_ascii=False, indent=2)
    except Exception:
        pass
    md += [f"### {k}\n", "```json", v, "```\n"]
open("evidence/job_run_summary.md", "w").write("\n".join(md) + "\n")
print("wrote evidence/job_run_summary.md")

# ---------------------------------------------------------------- pipeline DQ
if pipeline_update:
    cols, rows = sql(f"""
      SELECT origin.flow_name AS dataset,
             max(CAST(details:flow_progress.metrics.num_output_rows AS BIGINT)) AS rows_written,
             max(details:flow_progress.data_quality.dropped_records) AS dropped_records,
             max(CAST(details:flow_progress.data_quality.expectations AS STRING)) AS expectations
      FROM event_log('{pipeline_update}')
      WHERE event_type = 'flow_progress' AND details:flow_progress.status = 'COMPLETED'
        AND timestamp >= (SELECT max(timestamp) - INTERVAL 1 HOUR FROM event_log('{pipeline_update}') WHERE event_type = 'create_update')
      GROUP BY origin.flow_name ORDER BY dataset""")
    md = [f"# Lakeflow pipeline data quality — pipeline `{pipeline_update}`\n",
          "Source: `event_log()` table-valued function (latest update). Expectations are declared in `pipelines/officepulse_churn/transformations/*.sql`.\n",
          "| dataset | rows written | dropped records | expectations (name / passed / failed) |", "|---|---|---|---|"]
    for ds, n, dropped, exps in rows:
        e = ""
        if exps:
            e = "; ".join(f"{x['name']}: {x['passed_records']} passed / {x['failed_records']} failed" for x in json.loads(exps))
        md.append(f"| {ds} | {n} | {dropped or 0} | {e} |")
    md += ["\n## Row counts of every table in the governed schema (after the run)\n", "| table | rows |", "|---|---|"]
    _, tables = sql("SHOW TABLES IN ytcy_azure_east2classic_stable.officepulse_churn")
    for _db, tname, _tmp in sorted(tables, key=lambda r: r[1]):
        try:
            _, cnt = sql(f"SELECT count(*) FROM ytcy_azure_east2classic_stable.officepulse_churn.{tname}")
            md.append(f"| {tname} | {cnt[0][0]} |")
        except Exception as e:
            md.append(f"| {tname} | n/a ({str(e)[:60]}) |")
    open("evidence/pipeline_data_quality.md", "w").write("\n".join(md) + "\n")
    print("wrote evidence/pipeline_data_quality.md")
