"""Build the business deck (HTML -> PDF via headless Chrome, plus a Markdown export).

Numbers come from the committed job run (evidence/job_run_summary.md, notebooks 03 and 06).
usage: python deck/build_deck.py   (Japanese version: python deck/build_deck_ja.py)
"""
import html
import subprocess

N = dict(
    arr="¥2.19B", arr_start="¥2.14B", arr_usd="≈ $14.6M", churn_arr="¥330M", churn_logos="93", grr="84.6%", grr_ml="86.7%", grr_pts="+2.1 pts",
    saved_sq="¥15.4M", saved_ml="¥60.0M", saved_inc="+¥44.5M", saved_inc_usd="≈ $300k",
    cov_ml="60.6%", cov_rules="53.9%", cov_sq="0%", prec_ml="63%", prec_rules="59%",
    auc_ml="0.847", auc_rules="0.772", pr_ml="0.621", pr_rules="0.393", top10_ml="76%", top10_rules="40%",
    ticket_share="47%", ticket_days="31", high_n="41", high_arr="¥120M", hidden_n="36", hidden_arr="¥102M",
    renew180="¥96M", exp_risk="¥280M", alerts_q="≈ 20", lake_ms="≈ 2 ms",
)

# (title, kicker, body_html, markdown)
SLIDES = []


def slide(title, kicker, body, md):
    SLIDES.append((title, kicker, body, md))


def kpis(items):
    cells = "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l in items)
    return f'<div class="kpis">{cells}</div>'


def table(head, rows, hl_col=None):
    th = "".join(f"<th>{h}</th>" for h in head)
    trs = "".join("<tr>" + "".join(f'<td class="{"hl" if i == hl_col else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def md_table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(r) + " |" for r in rows])


def bullets(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def md_bullets(items):
    return "\n".join(f"- {html.unescape(i).replace('<b>', '**').replace('</b>', '**')}" for i in items)


# 1 ---------------------------------------------------------------- title
slide("See churn 90 days before the customer says goodbye",
      "OfficePulse Churn-Prevention CRM — built on Databricks",
      '<div class="sub">For the executive sponsor (CEO / CFO) and the domain owner (VP Customer Success)<br>'
      'Working prototype · synthetic data · fictional names (CloudNest / OfficePulse)</div>',
      "For the executive sponsor (CEO / CFO) and the domain owner (VP Customer Success). Working prototype, synthetic data, fictional names.")

# 2 ---------------------------------------------------------------- exec summary
items = [f"<b>{N['saved_inc']} ARR retained per year</b> ({N['saved_inc_usd']}) — save plays start 90 days before renewal instead of after the cancellation e-mail",
         f"<b>Gross Revenue Retention {N['grr']} → {N['grr_ml']}</b> ({N['grr_pts']}) on a {N['arr']} ARR base",
         f"<b>{N['hidden_n']} high-risk accounts ({N['hidden_arr']} ARR) are not on any CSM's radar today</b> — the cockpit surfaces them with the reasons and a playbook",
         "<b>Ask:</b> approve a 90-day pilot with two CSM pods (A/B on flagged accounts) to confirm the save rate before scale-out"]
slide("Executive summary", "The outcome",
      kpis([(N["saved_inc"], "ARR retained / year"), (N["grr_pts"], "GRR uplift"), (N["cov_ml"], "of churning ARR flagged at T-90 days (today: 0%)")]) + bullets(items),
      md_bullets(items))

# 3 ---------------------------------------------------------------- problem
items = [f"<b>{N['churn_arr']} ARR and {N['churn_logos']} logos lost in the last 12 months</b> — GRR {N['grr']}",
         f"Only <b>{N['ticket_share']}</b> of churners ever tell us; the cancellation ticket arrives a median <b>{N['ticket_days']} days</b> before renewal — too late for a save play",
         "The warning signs exist but live in three silos: product usage (GA4), support (Zendesk), contracts (CRM)",
         "The current rule-based health score is hand-tuned, not explainable per account, and misses half of the churners"]
slide("The problem, in your KPIs", "Why churn is a board-level issue",
      kpis([(N["churn_arr"], "ARR churned (12 m)"), (N["grr"], "Gross Revenue Retention"), (f"{N['ticket_days']} days", "median warning before renewal today")]) + bullets(items),
      md_bullets(items))

# 4 ---------------------------------------------------------------- today's book
items = [f"<b>{N['high_n']}</b> accounts with ≥ 50% probability of not renewing — <b>{N['high_arr']}</b> ARR; <b>{N['renew180']}</b> of it renews within 180 days",
         f"<b>{N['hidden_n']} of the {N['high_n']}</b> are still marked <i>active</i> by their CSM — <b>{N['hidden_arr']}</b> ARR at risk is invisible today",
         f"Expected ARR at risk (Σ probability × ARR) = <b>{N['exp_risk']}</b> — a number Finance can forecast against",
         "Example — Asuka Construction (Enterprise, ¥13.3M ARR, renews 25 Dec): CRM status <i>active</i>, model 67%. Drivers: sensor detection rate 61%, CSAT 3.0, logins 57%"]
slide("What the model sees in the book today", "Risk you can act on now",
      kpis([(N["high_n"], "high-risk accounts"), (N["hidden_n"], "not flagged by CSMs"), (N["exp_risk"], "expected ARR at risk")]) + bullets(items),
      md_bullets(items))

# 5 ---------------------------------------------------------------- proof
head = ["Out-of-time test (renewals after 1 May 2026)", "Status quo<br>(customer's ticket)", "Old rule score", "ML model"]
rows = [["Churning ARR flagged 90 days before renewal", N["cov_sq"], N["cov_rules"], f"<b>{N['cov_ml']}</b>"],
        ["Alert precision at T-90 (same alert volume)", "—", N["prec_rules"], f"<b>{N['prec_ml']}</b>"],
        ["Precision in top-10% riskiest snapshots", "—", N["top10_rules"], f"<b>{N['top10_ml']}</b>"],
        ["ROC AUC / PR AUC", "—", f"{N['auc_rules']} / {N['pr_rules']}", f"<b>{N['auc_ml']} / {N['pr_ml']}</b>"]]
slide("Proof: earlier and more precise than today", "Model results, validated out of time",
      table(head, rows, 3) + '<div class="note">Trained only on renewals whose outcome was known before 1 May 2026, tested on the 247 renewals after it (47 churned). '
      'Rules compared at the same number of alerts. Full outputs: evidence/notebook_runs/train_register_serve.ipynb</div>',
      md_table([h.replace("<br>", " ") for h in head], [[c.replace("<b>", "**").replace("</b>", "**") for c in r] for r in rows]))

# 6 ---------------------------------------------------------------- domain owner
items = ["<b>Monday morning:</b> the CS cockpit lists renewals by probability, with a <i>missed-risk</i> filter (high risk, not flagged)",
         "<b>Why:</b> top-3 drivers per account (SHAP) — e.g. sensor detection rate, CSAT, urgent tickets, auto-renew off",
         "<b>What if:</b> move the levers (re-provision sensors → detection 85%, resolve tickets) and re-score live on Model Serving",
         "<b>What to do:</b> a generated playbook — prioritized actions, owner, due date, talk track, success metric — one click to save as an action or meeting",
         f"<b>Workload:</b> {N['alerts_q']} T-90 alerts per quarter at {N['prec_ml']} precision — a short, explained list instead of the whole book",
         "<b>Ask anything:</b> Genie answers ad-hoc questions in Japanese over the same governed data (e.g. ‘high-risk accounts renewing in 90 days by industry’)"]
slide("For the VP Customer Success: a different Monday", "Value for the domain owner", bullets(items), md_bullets(items))

# 7 ---------------------------------------------------------------- exec sponsor
items = [f"<b>Retention:</b> {N['saved_inc']} ARR per year retained, GRR {N['grr_pts']} — compounding into NRR and valuation",
         f"<b>Predictability:</b> expected ARR at risk ({N['exp_risk']}) is refreshed weekly per account — renewal forecast stops being a surprise",
         "<b>Root causes for Product:</b> detection-rate drops (sensor health) are the #1 churn driver — a fixable product/ops issue, not just a CS issue",
         "<b>Leverage:</b> same CS headcount covers the at-risk book 90 days earlier; no new tooling licences — one governed platform",
         "<b>Low risk to start:</b> runs on serverless (scale-to-zero serving, autoscaling Lakebase); pilot uses existing GA4 / Zendesk / CRM exports"]
slide("For the CEO / CFO: retention you can forecast", "Value for the executive sponsor", bullets(items), md_bullets(items))

# 8 ---------------------------------------------------------------- business case
head = ["Save rate when a play starts ≥ 90 days before renewal", "ARR retained / year", "Increment vs today", "GRR"]
rows = [["20%", "¥40.0M", "+¥24.5M", "85.8%"], ["30% (base case)", N["saved_ml"], f"<b>{N['saved_inc']}</b>", f"<b>{N['grr_ml']}</b>"], ["40%", "¥80.0M", "+¥64.5M", "87.6%"]]
slide("Business case and assumptions", "Conservative, transparent, adjustable",
      table(head, rows, 2) + bullets([
          f"Base: trailing-12-month churned ARR {N['churn_arr']} on a {N['arr_start']} starting ARR (Lakeflow gold tables)",
          f"Early coverage = {N['cov_ml']} of churning ARR flagged at T-90 (out-of-time test)",
          f"Today: plays start only after a cancellation ticket ({N['ticket_share']} of churners), save rate 10% → {N['saved_sq']}/year",
          "Assumptions are parameters of the business-impact notebook — the pilot replaces them with measured save rates"]),
      md_table(head, [[c.replace("<b>", "**").replace("</b>", "**") for c in r] for r in rows]))

# 9 ---------------------------------------------------------------- architecture
arch = '''<div class="flow">
<div class="box">Raw exports<br><small>CRM CSV · GA4 JSON · Zendesk JSON<br>UC Volume</small></div><div class="arr">→</div>
<div class="box">Lakeflow<br><small>Auto Loader bronze → silver (8 DQ expectations) → gold features</small></div><div class="arr">→</div>
<div class="box">ML<br><small>MLflow · UC model @champion · Model Serving · SHAP</small></div><div class="arr">→</div>
<div class="box">Lakebase<br><small>Postgres serving (≈2 ms) + app writes</small></div><div class="arr">→</div>
<div class="box">Databricks App<br><small>CS cockpit · Gen AI playbook · Genie agent</small></div>
</div><div class="gov">Unity Catalog — one governed namespace: tags · certified gold · PII masks · grants · lineage · model registry · AI Gateway model service</div>'''
items = ["One Lakeflow Job runs the whole journey (generate → pipeline → govern → train/register/serve → score → publish → business case)",
         "Gen AI is grounded on the model's probability and drivers, called through a Unity Catalog model service (governed, permissioned)",
         "Genie space over certified gold tables, with instructions, sample questions and SQL benchmarks; embedded in the app"]
slide("How it works: one integrated data journey", "Architecture", arch + bullets(items),
      "Raw exports (CRM/GA4/Zendesk) → Lakeflow (bronze/silver/gold, expectations) → ML (MLflow, UC registry, Model Serving, SHAP) → Lakebase (serving + app writes) → Databricks App (cockpit, Gen AI playbook, Genie). Governed end-to-end by Unity Catalog.\n\n" + md_bullets(items))

# 10 --------------------------------------------------------------- governance
items = ["<b>Unity Catalog</b>: raw volume, 12 pipeline tables, ML tables, model, LLM service and mask function in one schema; gold tables tagged <i>certified</i>",
         "<b>PII</b>: contact e-mail/phone classified (class.* tags) and masked by a UC column mask declared in the pipeline",
         "<b>Least privilege</b>: the app's service principal gets read on the schema, EXECUTE on the model service, CAN_QUERY on the endpoint, its own Postgres role",
         "<b>Lineage & audit</b>: raw → bronze → silver → gold → scores captured automatically; MLflow run + model version on every score",
         "<b>Data quality</b>: 130 defective GA4 rows (duplicates, missing tenant, impossible counts) dropped by expectations and reported in the event log",
         "<b>Responsible AI</b>: the model scores, the LLM explains; every recommendation cites the drivers it is based on"]
slide("Trust: governed from raw file to recommendation", "Governance & security", bullets(items), md_bullets(items))

# 11 --------------------------------------------------------------- insights
head = ["Driver (feature importance rank)", "What it means", "Owner of the fix"]
rows = [["1. Sensor detection rate (4 weeks)", "Devices offline / mis-configured → product feels broken", "Support + Field Ops"],
        ["2. Average CSAT (12 weeks)", "Poor support experience precedes churn", "Support leadership"],
        ["3. Auto-renew switched off", "Procurement already reviewing the contract", "Account Executive"],
        ["4. Urgent tickets (12 weeks)", "Escalations accumulate before a decision", "Support"],
        ["5. Login trend (8 weeks)", "Adoption fading after rollout", "CSM (enablement)"]]
slide("What drives churn — and who can fix it", "Insights for the whole company", table(head, rows),
      md_table(head, rows))

# 12 --------------------------------------------------------------- next steps
items = ["<b>Weeks 0–2</b>: connect live GA4, Zendesk and CRM via Lakeflow Connect; switch publish to Lakebase Synced Tables",
         "<b>Weeks 2–10</b>: pilot with two CSM pods — half of flagged renewals get the playbook (A/B); log every action in the cockpit",
         "<b>Week 12</b>: read-out on measured save rate, GRR and CSM time; retrain monthly with the new outcomes",
         "<b>Success criteria</b>: ≥ 25% save rate on early-flagged ARR; ≥ 55% of churning ARR flagged at T-90; CSM adoption ≥ 80% weekly",
         "<b>Decision needed today</b>: executive sponsor + VP CS nominate pilot pods and agree success criteria"]
slide("Next steps: a 90-day pilot", "From prototype to measured value", bullets(items), md_bullets(items))

# 13 --------------------------------------------------------------- appendix
items = ["Label: account does not renew at its next annual renewal; scored weekly; evaluated 30–180 days before renewal",
         "Features (20, no look-ahead): usage rates and trends, sessions, tickets/urgent/technical/cancellation, slow responses, CSAT, open tickets, auto-renew, plan",
         "Excluded on purpose: seats/ARR (identity leakage), days-to-renewal/tenure (not actionable); accounts with < 12 weeks of history are not scored",
         "Model: GradientBoosting (depth 2, 250 trees) wrapped as an MLflow pyfunc returning probability + SHAP top-3 drivers",
         "Data: 612 synthetic accounts, 78 weeks of GA4, 4.4k Zendesk tickets with 15k comments, 18 months of CRM contracts",
         "Evidence (text): notebooks with outputs, pipeline event log, Genie Q&A, live app API calls — see repository /evidence"]
slide("Appendix: model and data details", "For the technical reviewer", bullets(items), md_bullets(items))

CSS = """
@page { size: 13.333in 7.5in; margin: 0 }
* { box-sizing: border-box }
body { margin: 0; font-family: -apple-system, 'Helvetica Neue', 'Hiragino Sans', Arial, sans-serif; color: #1b3139 }
.slide { width: 13.333in; height: 7.5in; padding: .55in .7in .45in; position: relative; page-break-after: always; overflow: hidden; background: #fff }
.slide:before { content: ''; position: absolute; left: 0; top: 0; width: .16in; height: 100%; background: #ff3621 }
.kicker { color: #ff3621; font-weight: 700; font-size: 15pt; letter-spacing: .3px; text-transform: uppercase }
h1 { font-size: 30pt; margin: .06in 0 .22in; line-height: 1.15 }
.title h1 { font-size: 42pt; margin-top: 1.6in }
.title { background: linear-gradient(135deg, #1b3139 0%, #0b2026 100%); color: #fff }
.title .sub { font-size: 17pt; color: #cfd8dc; line-height: 1.6 }
ul { margin: .1in 0 0; padding-left: .3in } li { font-size: 16pt; line-height: 1.42; margin-bottom: .09in }
.kpis { display: flex; gap: .25in; margin-bottom: .2in }
.kpi { flex: 1; background: #f5f7f8; border-top: 5px solid #ff3621; border-radius: 6px; padding: .16in .2in }
.kpi .v { font-size: 30pt; font-weight: 800; color: #1b3139 } .kpi .l { font-size: 13pt; color: #5a6f77; margin-top: .03in }
table { width: 100%; border-collapse: collapse; font-size: 15pt; margin-bottom: .15in }
th { background: #1b3139; color: #fff; text-align: left; padding: .1in .14in; font-weight: 600 }
td { border-bottom: 1px solid #dfe5e8; padding: .1in .14in } td.hl { background: #fff1ef }
.note { font-size: 12.5pt; color: #5a6f77; margin-top: .05in }
.flow { display: flex; align-items: stretch; gap: .08in; margin: .1in 0 .15in }
.box { flex: 1; background: #1b3139; color: #fff; border-radius: 8px; padding: .14in; font-weight: 700; font-size: 15pt; text-align: center }
.box small { display: block; font-weight: 400; font-size: 11.5pt; color: #cfd8dc; margin-top: .06in; line-height: 1.35 }
.arr { align-self: center; font-size: 24pt; color: #ff3621; font-weight: 800 }
.gov { background: #fff1ef; border: 2px solid #ff3621; border-radius: 8px; padding: .1in .16in; font-size: 14pt; font-weight: 600; margin-bottom: .1in }
.foot { position: absolute; bottom: .22in; right: .7in; font-size: 10pt; color: #8a9aa1 }
"""

def render(slides, base, title, footer, lang="en", css_extra=""):
    """Write deck/<base>.html, .md and .pdf for the given slides."""
    import os
    parts = []
    for i, (t, k, b, _) in enumerate(slides, start=1):
        cls = "slide title" if i == 1 else "slide"
        parts.append(f'<section class="{cls}"><div class="kicker">{k}</div><h1>{t}</h1>{b}'
                     f'<div class="foot">{footer} · {i}/{len(slides)}</div></section>')
    html_path = f"deck/{base}.html"
    open(html_path, "w").write(
        f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><title>{footer}</title>"
        f"<style>{CSS}{css_extra}</style></head><body>{''.join(parts)}</body></html>")
    md = [f"# {title}\n"]
    for i, (t, k, _, m) in enumerate(slides, start=1):
        md.append(f"\n---\n\n## {i}. {t}\n*{k}*\n\n{m}\n")
    open(f"deck/{base}.md", "w").write("\n".join(md))
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--user-data-dir=/tmp/chdeck",
                    f"--print-to-pdf=deck/{base}.pdf", "file://" + os.path.abspath(html_path)], capture_output=True)
    print(f"built deck/{base}.{{html,md,pdf}}")


if __name__ == "__main__":
    render(SLIDES, "OfficePulse_Churn_Prevention_Deck",
           "See churn 90 days before the customer says goodbye — OfficePulse Churn-Prevention CRM on Databricks",
           "OfficePulse churn prevention")
