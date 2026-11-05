# See churn 90 days before the customer says goodbye — OfficePulse Churn-Prevention CRM on Databricks


---

## 1. See churn 90 days before the customer says goodbye
*OfficePulse Churn-Prevention CRM — built on Databricks*

For the executive sponsor (CEO / CFO) and the domain owner (VP Customer Success). Working prototype, synthetic data, fictional names.


---

## 2. Executive summary
*The outcome*

- **+¥44.5M ARR retained per year** (≈ $300k) — save plays start 90 days before renewal instead of after the cancellation e-mail
- **Gross Revenue Retention 84.6% → 86.7%** (+2.1 pts) on a ¥2.19B ARR base
- **36 high-risk accounts (¥102M ARR) are not on any CSM's radar today** — the cockpit surfaces them with the reasons and a playbook
- **Ask:** approve a 90-day pilot with two CSM pods (A/B on flagged accounts) to confirm the save rate before scale-out


---

## 3. The problem, in your KPIs
*Why churn is a board-level issue*

- **¥330M ARR and 93 logos lost in the last 12 months** — GRR 84.6%
- Only **47%** of churners ever tell us; the cancellation ticket arrives a median **31 days** before renewal — too late for a save play
- The warning signs exist but live in three silos: product usage (GA4), support (Zendesk), contracts (CRM)
- The current rule-based health score is hand-tuned, not explainable per account, and misses half of the churners


---

## 4. What the model sees in the book today
*Risk you can act on now*

- **41** accounts with ≥ 50% probability of not renewing — **¥120M** ARR; **¥96M** of it renews within 180 days
- **36 of the 41** are still marked <i>active</i> by their CSM — **¥102M** ARR at risk is invisible today
- Expected ARR at risk (Σ probability × ARR) = **¥280M** — a number Finance can forecast against
- Example — Asuka Construction (Enterprise, ¥13.3M ARR, renews 25 Dec): CRM status <i>active</i>, model 67%. Drivers: sensor detection rate 61%, CSAT 3.0, logins 57%


---

## 5. Proof: earlier and more precise than today
*Model results, validated out of time*

| Out-of-time test (renewals after 1 May 2026) | Status quo (customer's ticket) | Old rule score | ML model |
|---|---|---|---|
| Churning ARR flagged 90 days before renewal | 0% | 53.9% | **60.6%** |
| Alert precision at T-90 (same alert volume) | — | 59% | **63%** |
| Precision in top-10% riskiest snapshots | — | 40% | **76%** |
| ROC AUC / PR AUC | — | 0.772 / 0.393 | **0.847 / 0.621** |


---

## 6. For the VP Customer Success: a different Monday
*Value for the domain owner*

- **Monday morning:** the CS cockpit lists renewals by probability, with a <i>missed-risk</i> filter (high risk, not flagged)
- **Why:** top-3 drivers per account (SHAP) — e.g. sensor detection rate, CSAT, urgent tickets, auto-renew off
- **What if:** move the levers (re-provision sensors → detection 85%, resolve tickets) and re-score live on Model Serving
- **What to do:** a generated playbook — prioritized actions, owner, due date, talk track, success metric — one click to save as an action or meeting
- **Workload:** ≈ 20 T-90 alerts per quarter at 63% precision — a short, explained list instead of the whole book
- **Ask anything:** Genie answers ad-hoc questions in Japanese over the same governed data (e.g. ‘high-risk accounts renewing in 90 days by industry’)


---

## 7. For the CEO / CFO: retention you can forecast
*Value for the executive sponsor*

- **Retention:** +¥44.5M ARR per year retained, GRR +2.1 pts — compounding into NRR and valuation
- **Predictability:** expected ARR at risk (¥280M) is refreshed weekly per account — renewal forecast stops being a surprise
- **Root causes for Product:** detection-rate drops (sensor health) are the #1 churn driver — a fixable product/ops issue, not just a CS issue
- **Leverage:** same CS headcount covers the at-risk book 90 days earlier; no new tooling licences — one governed platform
- **Low risk to start:** runs on serverless (scale-to-zero serving, autoscaling Lakebase); pilot uses existing GA4 / Zendesk / CRM exports


---

## 8. Business case and assumptions
*Conservative, transparent, adjustable*

| Save rate when a play starts ≥ 90 days before renewal | ARR retained / year | Increment vs today | GRR |
|---|---|---|---|
| 20% | ¥40.0M | +¥24.5M | 85.8% |
| 30% (base case) | ¥60.0M | **+¥44.5M** | **86.7%** |
| 40% | ¥80.0M | +¥64.5M | 87.6% |


---

## 9. How it works: one integrated data journey
*Architecture*

Raw exports (CRM/GA4/Zendesk) → Lakeflow (bronze/silver/gold, expectations) → ML (MLflow, UC registry, Model Serving, SHAP) → Lakebase (serving + app writes) → Databricks App (cockpit, Gen AI playbook, Genie). Governed end-to-end by Unity Catalog.

- One Lakeflow Job runs the whole journey (generate → pipeline → govern → train/register/serve → score → publish → business case)
- Gen AI is grounded on the model's probability and drivers, called through a Unity Catalog model service (governed, permissioned)
- Genie space over certified gold tables, with instructions, sample questions and SQL benchmarks; embedded in the app


---

## 10. Trust: governed from raw file to recommendation
*Governance & security*

- **Unity Catalog**: raw volume, 12 pipeline tables, ML tables, model, LLM service and mask function in one schema; gold tables tagged <i>certified</i>
- **PII**: contact e-mail/phone classified (class.* tags) and masked by a UC column mask declared in the pipeline
- **Least privilege**: the app's service principal gets read on the schema, EXECUTE on the model service, CAN_QUERY on the endpoint, its own Postgres role
- **Lineage & audit**: raw → bronze → silver → gold → scores captured automatically; MLflow run + model version on every score
- **Data quality**: 130 defective GA4 rows (duplicates, missing tenant, impossible counts) dropped by expectations and reported in the event log
- **Responsible AI**: the model scores, the LLM explains; every recommendation cites the drivers it is based on


---

## 11. What drives churn — and who can fix it
*Insights for the whole company*

| Driver (feature importance rank) | What it means | Owner of the fix |
|---|---|---|
| 1. Sensor detection rate (4 weeks) | Devices offline / mis-configured → product feels broken | Support + Field Ops |
| 2. Average CSAT (12 weeks) | Poor support experience precedes churn | Support leadership |
| 3. Auto-renew switched off | Procurement already reviewing the contract | Account Executive |
| 4. Urgent tickets (12 weeks) | Escalations accumulate before a decision | Support |
| 5. Login trend (8 weeks) | Adoption fading after rollout | CSM (enablement) |


---

## 12. Next steps: a 90-day pilot
*From prototype to measured value*

- **Weeks 0–2**: connect live GA4, Zendesk and CRM via Lakeflow Connect; switch publish to Lakebase Synced Tables
- **Weeks 2–10**: pilot with two CSM pods — half of flagged renewals get the playbook (A/B); log every action in the cockpit
- **Week 12**: read-out on measured save rate, GRR and CSM time; retrain monthly with the new outcomes
- **Success criteria**: ≥ 25% save rate on early-flagged ARR; ≥ 55% of churning ARR flagged at T-90; CSM adoption ≥ 80% weekly
- **Decision needed today**: executive sponsor + VP CS nominate pilot pods and agree success criteria


---

## 13. Appendix: model and data details
*For the technical reviewer*

- Label: account does not renew at its next annual renewal; scored weekly; evaluated 30–180 days before renewal
- Features (20, no look-ahead): usage rates and trends, sessions, tickets/urgent/technical/cancellation, slow responses, CSAT, open tickets, auto-renew, plan
- Excluded on purpose: seats/ARR (identity leakage), days-to-renewal/tenure (not actionable); accounts with < 12 weeks of history are not scored
- Model: GradientBoosting (depth 2, 250 trees) wrapped as an MLflow pyfunc returning probability + SHAP top-3 drivers
- Data: 612 synthetic accounts, 78 weeks of GA4, 4.4k Zendesk tickets with 15k comments, 18 months of CRM contracts
- Evidence (text): notebooks with outputs, pipeline event log, Genie Q&A, live app API calls — see repository /evidence
