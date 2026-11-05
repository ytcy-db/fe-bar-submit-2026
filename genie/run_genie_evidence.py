"""Ask the Genie space real questions and commit the answers (question -> generated SQL -> result rows)
as text evidence: evidence/genie_conversations.md

usage: python genie/run_genie_evidence.py --profile Azure-ytcy-east2
"""
import argparse, json, subprocess, time, datetime

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True)
a = ap.parse_args()
SID = open("genie/space_id.txt").read().strip()
CLI = "/opt/homebrew/bin/databricks"


def api(method, path, body=None):
    cmd = [CLI, "api", method, path, "--profile", a.profile]
    if body is not None:
        cmd += ["--json", json.dumps(body, ensure_ascii=False)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(out.stderr[:500])
    return json.loads(out.stdout or "{}")


QUESTIONS = [
    "CSMがまだフラグしていない高リスク顧客をARRの大きい順に10社教えて",
    "今後90日以内に更新日を迎える高リスク顧客と期待損失ARRの合計は？",
    "業界別の平均解約確率と期待損失ARRを教えて",
    "直近12ヶ月の月別解約件数と解約ARRの推移を見せて",
    "MLモデルとルールベースの精度（AUC）を比較して",
]
md = [f"# Genie evidence — space `{SID}` (OfficePulse Churn Agent)\n",
      f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M} by `genie/run_genie_evidence.py` via the Genie Conversation API.\n"]
for q in QUESTIONS:
    r = api("post", f"/api/2.0/genie/spaces/{SID}/start-conversation", {"content": q})
    cid, mid = r["conversation_id"], r["message_id"]
    for _ in range(90):
        m = api("get", f"/api/2.0/genie/spaces/{SID}/conversations/{cid}/messages/{mid}")
        if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(3)
    md.append(f"\n## Q: {q}\n\nstatus: `{m.get('status')}`\n")
    for att in m.get("attachments", []) or []:
        if att.get("text"):
            md.append(f"**Answer:** {att['text'].get('content','')}\n")
        if att.get("query"):
            qq = att["query"]
            md.append(f"**Generated SQL** ({qq.get('description','')}):\n\n```sql\n{qq.get('query','').strip()}\n```\n")
            res = api("get", f"/api/2.0/genie/spaces/{SID}/conversations/{cid}/messages/{mid}/attachments/{att['attachment_id']}/query-result")
            sr = res.get("statement_response", {})
            cols = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
            rows = (sr.get("result", {}) or {}).get("data_array", []) or []
            if cols:
                md.append("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
                for row in rows[:12]:
                    md.append("| " + " | ".join("" if v is None else str(v) for v in row) + " |")
                md.append(f"\n_{len(rows)} row(s)_\n")
    print("done:", q, m.get("status"))
open("evidence/genie_conversations.md", "w").write("\n".join(md) + "\n")
