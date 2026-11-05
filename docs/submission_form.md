# FE Bar submission — form answers (English)

**Customer name:** (entered in the form only). The repository and deck use the fictional names *CloudNest / OfficePulse*; all data is synthetic and no customer-identifying content is committed.

**Industry / vertical:** B2B SaaS — workplace technology / PropTech (office attendance detection: loaned sensors + mobile app, annual subscriptions)

---

### What is the business challenge you are solving?

The customer sells an office attendance-detection SaaS (sensors + app) on annual contracts and is losing about 15% of ARR every year. In the trailing 12 months, 93 logos and ¥330M ARR churned, for a Gross Revenue Retention of 84.6%. Customer Success learns about churn too late. Only 47% of churning customers ever send a cancellation ticket, and the median ticket arrives 31 days before renewal, too late for a save play. The early signals do exist (sensor detection rates falling, logins declining, urgent tickets, low CSAT, auto-renew switched off), but they are spread across GA4 product analytics, Zendesk and the CRM, and the existing rule-based health score is neither accurate nor explainable enough for CSMs to act on. The VP of CS needs a ranked, explained list of at-risk renewals at least 90 days ahead, plus a way to act on it and track the result. The CEO/CFO needs GRR to improve and ARR at risk to be forecastable.

### How does your Databricks solution address this challenge?

One integrated data journey, deployed as a Databricks Asset Bundle and run as a single Lakeflow Job (7 tasks, all green in the committed run):

1. **Lakeflow (ingest and transform):** synthetic raw exports (CRM CSV, GA4 weekly JSON, Zendesk JSON with nested comments) land in a UC Volume. A serverless Lakeflow Spark Declarative Pipeline ingests them with Auto Loader into bronze streaming tables, then builds silver materialized views (dedup, key conformance, 8 data-quality expectations that dropped 130 defective rows) and gold tables (`gold_account_weekly` feature backbone, KPI and churn aggregates).
2. **Unity Catalog (govern):** one governed schema holds the volume, tables, model, LLM model service and functions. It has tags, the governed `system.certification_status=certified` tag on gold tables, `class.*` PII tags, and a column-mask function on contact e-mail and phone declared in the pipeline. The app service principal gets least-privilege grants, and lineage from raw to bronze, silver, gold and the scores is visible in `system.access.table_lineage`.
3. **ML:** label = "will not renew at the next annual renewal", evaluated 30–180 days before renewal. A GradientBoosting model is tracked in MLflow, registered in UC as `churn_model@champion` and served on a scale-to-zero Model Serving endpoint. A pyfunc returns the probability plus the top-3 SHAP drivers. Out-of-time evaluation: ROC AUC 0.847 vs 0.772 for the previous rule score; at T-90 days it catches 60.6% of churning ARR vs 53.9% for rules at the same alert volume, and 0% for the status quo.
4. **Gen AI:** a retention playbook (summary, prioritized actions with owner and due date, talk track, success metric), grounded on the model's probability and SHAP drivers. It is called through a Unity Catalog model service (Unity AI Gateway → Claude Sonnet), with `EXECUTE` granted to the app.
5. **Lakebase (operational serving):** Account 360 with scores, tickets, events and weekly usage are published transactionally to Lakebase Postgres (point lookups p50 ≈ 2 ms). The app writes retention actions, meetings, ticket updates/replies and Genie history to its own `crm_ops` schema.
6. **Genie Agent:** the space "OfficePulse Churn Agent" covers the certified gold tables, with instructions, sample questions and SQL benchmarks. It is embedded in the app in chat and agent modes, and its answers are recorded in the repo.
7. **Databricks App (FastAPI + React):** the CS cockpit. It provides a risk list ranked by ML with a "missed risk" filter (high risk but not flagged by the CSM), SHAP drivers, what-if re-scoring on Model Serving, an AI playbook whose actions can be saved and scheduled into Lakebase, an action tracker, the help desk, Genie, and an ML / business-impact page.

### What AI tools did you use, and what was your workflow? What decisions and trade-offs did you have to make?

Tool: Claude Code (Claude Opus) with the Databricks plugin skills (CLI, Asset Bundles, Lakeflow pipelines, Lakebase, Model Serving, Genie). I extended an existing CRM help-desk app of mine, which had only a rule-based score and UC tables, into the full journey. Workflow: (1) prototype the synthetic data generator and features locally with pandas/sklearn and check that the signal was realistic but not trivial; (2) write the pipeline, notebooks and bundle, then deploy and run them on serverless; (3) refactor the app onto Lakebase, Model Serving, the UC model service and Genie; (4) record execution evidence as text (notebooks with outputs, pipeline event log, Genie Q&A, live app API calls).

Main decisions and trade-offs:
- **Label design.** "Churn in the next 90 days" was dominated by the renewal date (renewal timing alone scored AUC 0.91). I reframed the task as "non-renewal at the next renewal, scored 30–180 days out".
- **Leakage.** A snapshot-date split put the same renewal on both sides of the split. Switching to a split by renewal event and dropping identity-like features (seats, ARR) and non-actionable ones (days-to-renewal, tenure) cost about 0.01 AUC, and in return the drivers became actionable.
- **Fair baseline.** ML is compared with the old rule score at the same alert volume, and with the status quo.
- **Onboarding accounts** (fewer than 12 weeks of history) are not scored, because their ramp-up looks like a decline.
- **Lakebase Synced Tables** need `CREATE CATALOG` on the metastore, which my sandbox does not grant, so a job task performs a transactional Delta→Postgres reload. The app writes only to its own schema, so republishing never overwrites operational writes.
- **Governed tag policies** blocked common keys, so I used custom keys plus the governed certification and `class.*` tags. The PII mask had to be declared inside the pipeline, because managed materialized views reject `ALTER ... SET MASK`.
- **The LLM explains and plans; it does not score.** It is called through a UC model service rather than a raw endpoint, for governance.

### What are the business outcomes and impact?

Measured on out-of-time renewals, with conservative save rates (30% when a save play starts at least 90 days before renewal, 10% when it starts after a cancellation ticket):
- **+¥44.5M ARR retained per year** (¥60.0M vs ¥15.4M today), about $300k on a ¥2.19B ($14.6M) ARR base.
- **GRR 84.6% → 86.7% (+2.1 pts).**
- **Early warning:** 60.6% of churning ARR is flagged 90 days before renewal (0% today; the old rule score catches 53.9% at the same alert volume), with 63% alert precision (rules: 59%). Precision in the top 10% of scores is 76% vs 40% for rules.
- **Visible today:** 41 high-risk accounts (¥120M ARR), 36 of them not yet flagged by CSMs (¥102M ARR); ¥96M of high-risk ARR renews within 180 days. Expected ARR at risk is ¥280M, which gives Finance a forecastable figure.
- **CSM capacity:** about 20 alerts per quarter at the T-90 checkpoint, each with drivers, a what-if and a generated playbook, so the team works a short, explained list instead of the whole book.
- Next step: a 90-day pilot with two CSM pods. Half of the flagged accounts get the playbook (A/B), measured on save rate and GRR. Live GA4/Zendesk feeds would then come in via Lakeflow Connect.

**GitHub repo link:** https://github.com/ytcy-db/fe-bar-submit-2026

**Presentation deck:** `deck/OfficePulse_Churn_Prevention_Deck.pdf` (also `deck/OfficePulse_Churn_Prevention_Deck.md`)

**Conversation ID (optional):** the Claude Code session ID of this build (shown by `/status` in Claude Code).
