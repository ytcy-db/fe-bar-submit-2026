-- =====================================================================
-- GOLD: business-level aggregates consumed by ML, Genie, dashboards
-- and the app. gold_account_weekly is the ML feature backbone.
-- =====================================================================

CREATE OR REFRESH MATERIALIZED VIEW gold_account_weekly
COMMENT "One row per account per week: product usage KPIs + support activity in that week + tickets still open at week end. Feature backbone for the churn model."
TBLPROPERTIES ("quality" = "gold")
AS
WITH tk AS (
  SELECT
    account_id,
    date_trunc('WEEK', created_at) AS week_start,
    count(*) AS tickets_created,
    sum(CASE WHEN priority IN ('high', 'urgent') THEN 1 ELSE 0 END) AS urgent_tickets,
    sum(CASE WHEN category = '技術' THEN 1 ELSE 0 END) AS technical_tickets,
    sum(CASE WHEN is_cancellation_intent THEN 1 ELSE 0 END) AS cancellation_tickets,
    sum(CASE WHEN first_response_min > 480 THEN 1 ELSE 0 END) AS slow_first_responses,
    sum(csat) AS csat_sum,
    count(csat) AS csat_n,
    sum(CASE WHEN csat <= 2 THEN 1 ELSE 0 END) AS low_csat_tickets
  FROM silver_tickets
  GROUP BY ALL
),
open_at_week_end AS (
  SELECT u.account_id, u.week_start, count(t.ticket_id) AS open_tickets
  FROM silver_usage_weekly u
  JOIN silver_tickets t
    ON t.account_id = u.account_id
   AND t.created_at < u.week_start + INTERVAL 7 DAYS
   AND (t.status NOT IN ('solved', 'closed') OR t.solved_at >= u.week_start + INTERVAL 7 DAYS)
   AND t.created_at >= u.week_start - INTERVAL 60 DAYS
  GROUP BY ALL
)
SELECT
  u.account_id,
  u.week_start,
  u.seats,
  u.login_rate, u.signup_rate, u.attendance_detect_rate, u.install_rate, u.app_config_ok_rate,
  u.dau, u.sessions, u.avg_session_min,
  coalesce(tk.tickets_created, 0) AS tickets_created,
  coalesce(tk.urgent_tickets, 0) AS urgent_tickets,
  coalesce(tk.technical_tickets, 0) AS technical_tickets,
  coalesce(tk.cancellation_tickets, 0) AS cancellation_tickets,
  coalesce(tk.slow_first_responses, 0) AS slow_first_responses,
  coalesce(tk.csat_sum, 0) AS csat_sum,
  coalesce(tk.csat_n, 0) AS csat_n,
  coalesce(tk.low_csat_tickets, 0) AS low_csat_tickets,
  coalesce(o.open_tickets, 0) AS open_tickets
FROM silver_usage_weekly u
LEFT JOIN tk ON tk.account_id = u.account_id AND CAST(tk.week_start AS DATE) = u.week_start
LEFT JOIN open_at_week_end o ON o.account_id = u.account_id AND o.week_start = u.week_start;

CREATE OR REFRESH MATERIALIZED VIEW gold_kpi_weekly
COMMENT "Company-wide weekly product KPIs (average over live accounts), in percent."
TBLPROPERTIES ("quality" = "gold")
AS SELECT
  week_start,
  count(DISTINCT account_id) AS live_accounts,
  round(avg(login_rate) * 100, 1) AS login_rate_pct,
  round(avg(signup_rate) * 100, 1) AS signup_rate_pct,
  round(avg(attendance_detect_rate) * 100, 1) AS attendance_detect_rate_pct,
  round(avg(install_rate) * 100, 1) AS install_rate_pct,
  round(avg(app_config_ok_rate) * 100, 1) AS app_config_ok_rate_pct
FROM silver_usage_weekly
GROUP BY week_start;

CREATE OR REFRESH MATERIALIZED VIEW gold_churn_monthly
COMMENT "Monthly logo churn, new logos and churned ARR (JPY) from CRM contracts."
TBLPROPERTIES ("quality" = "gold")
AS
WITH months AS (
  SELECT explode(sequence(DATE'2025-05-01', DATE'2026-11-01', INTERVAL 1 MONTH)) AS month
)
SELECT
  m.month,
  count(DISTINCT CASE WHEN date_trunc('MONTH', c.end_date) = m.month THEN c.account_id END) AS churned_accounts,
  count(DISTINCT CASE WHEN date_trunc('MONTH', c.start_date) = m.month THEN c.account_id END) AS new_accounts,
  coalesce(sum(CASE WHEN date_trunc('MONTH', c.end_date) = m.month THEN a.arr_jpy END), 0) AS churned_arr_jpy
FROM months m
CROSS JOIN silver_contracts c
LEFT JOIN silver_accounts a ON a.account_id = c.account_id
GROUP BY m.month;
