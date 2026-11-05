-- =====================================================================
-- SILVER: cleaned, conformed, de-duplicated entities with data-quality
-- expectations. Keys are conformed to the CRM account_id (ACC-xxxx):
--   GA4 tenant_id 'acc-1001' -> 'ACC-1001', Zendesk organization.external_id.
-- =====================================================================

-- Contact PII is masked at the source of truth with a Unity Catalog column mask
-- (function created by notebook 01; members of `officepulse-cs-leads` see clear values).
CREATE OR REFRESH MATERIALIZED VIEW silver_accounts (
  account_id STRING, company_name STRING, industry STRING, plan STRING, status STRING, csm_owner STRING,
  seats INT, arr_jpy BIGINT, region STRING, created_at DATE,
  contact_name STRING,
  contact_email STRING MASK ${mask_function},
  contact_phone STRING MASK ${mask_function},
  CONSTRAINT valid_account_id EXPECT (account_id RLIKE '^ACC-[0-9]+$') ON VIOLATION DROP ROW,
  CONSTRAINT valid_plan EXPECT (plan IN ('Starter', 'Standard', 'Premium', 'Enterprise')),
  CONSTRAINT positive_seats EXPECT (seats > 0)
)
COMMENT "One row per customer account (latest CRM export wins). contact_* columns are PII."
TBLPROPERTIES ("quality" = "silver")
AS SELECT
  account_id, company_name, industry, plan, status, csm_owner,
  CAST(seats AS INT) AS seats, CAST(arr_jpy AS BIGINT) AS arr_jpy, region,
  CAST(created_at AS DATE) AS created_at,
  contact_name, contact_email, contact_phone
FROM (
  SELECT *, row_number() OVER (PARTITION BY account_id ORDER BY exported_at DESC, _ingested_at DESC) AS rn
  FROM bronze_crm_accounts
)
WHERE rn = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_contracts (
  CONSTRAINT valid_account_id EXPECT (account_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT end_after_start EXPECT (end_date IS NULL OR end_date > start_date)
)
COMMENT "Annual subscription contracts. end_date is NULL while the customer is live; renewal_date is the next renewal (or the churn date)."
TBLPROPERTIES ("quality" = "silver")
AS SELECT
  contract_id, account_id, plan,
  CAST(start_date AS DATE) AS start_date,
  CAST(nullif(end_date, '') AS DATE) AS end_date,
  CAST(renewal_date AS DATE) AS renewal_date,
  CAST(term_months AS INT) AS term_months,
  loaned_devices, used_services,
  nullif(churn_reason, '') AS churn_reason,
  CAST(mrr_jpy AS BIGINT) AS mrr_jpy,
  auto_renew = 'Y' AS auto_renew
FROM bronze_crm_contracts;

CREATE OR REFRESH MATERIALIZED VIEW silver_usage_weekly (
  CONSTRAINT valid_tenant EXPECT (account_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT plausible_login_rate EXPECT (login_rate BETWEEN 0 AND 1) ON VIOLATION DROP ROW,
  CONSTRAINT plausible_detect_rate EXPECT (attendance_detect_rate BETWEEN 0 AND 1) ON VIOLATION DROP ROW
)
COMMENT "Weekly product-usage KPIs per account derived from GA4 counts. Rates are 0-1 ratios (multiply by 100 for %)."
TBLPROPERTIES ("quality" = "silver")
AS
WITH dedup AS (
  SELECT *, row_number() OVER (PARTITION BY tenant_id, report_week ORDER BY exported_at DESC) AS rn
  FROM bronze_ga4_usage
)
SELECT
  upper(tenant_id) AS account_id,
  CAST(report_week AS DATE) AS week_start,
  metrics.licensed_seats AS seats,
  round(metrics.active_users / metrics.licensed_seats, 4) AS login_rate,
  round(metrics.registered_users / metrics.licensed_seats, 4) AS signup_rate,
  round(metrics.attendance_detect_events / metrics.expected_detect_events, 4) AS attendance_detect_rate,
  round(metrics.app_installs / metrics.licensed_seats, 4) AS install_rate,
  round(metrics.devices_config_ok / metrics.devices_total, 4) AS app_config_ok_rate,
  CAST(metrics.active_users AS INT) AS dau,
  CAST(metrics.sessions AS INT) AS sessions,
  round(metrics.avg_session_sec / 60, 1) AS avg_session_min
FROM dedup
WHERE rn = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_tickets (
  CONSTRAINT valid_account_id EXPECT (account_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_csat EXPECT (csat IS NULL OR csat BETWEEN 1 AND 5)
)
COMMENT "Support tickets (Zendesk). Timestamps are JST wall-clock. csat 1-5, first_response_min in minutes."
TBLPROPERTIES ("quality" = "silver")
AS SELECT
  concat('ZD-', CAST(id AS STRING)) AS ticket_id,
  organization.external_id AS account_id,
  subject,
  tags[0] AS category,
  priority,
  status,
  via.channel AS channel,
  assignee.name AS assignee,
  to_timestamp(substr(created_at, 1, 19)) AS created_at,
  to_timestamp(substr(updated_at, 1, 19)) AS updated_at,
  CAST(metric_set.reply_time_in_minutes.calendar AS INT) AS first_response_min,
  round(metric_set.full_resolution_time_in_minutes.calendar / 60.0, 1) AS resolution_hours,
  CAST(satisfaction_rating.score AS INT) AS csat,
  description,
  to_timestamp(substr(created_at, 1, 19))
    + make_interval(0, 0, 0, 0, 0, CAST(coalesce(metric_set.full_resolution_time_in_minutes.calendar, 0) AS INT), 0) AS solved_at,
  (subject LIKE '%解約%' OR subject LIKE '%見送%') AS is_cancellation_intent
FROM bronze_zendesk_tickets;

CREATE OR REFRESH MATERIALIZED VIEW silver_ticket_events
COMMENT "Ticket conversation timeline (one row per Zendesk comment)."
TBLPROPERTIES ("quality" = "silver")
AS SELECT
  concat('EV-', CAST(c.id AS STRING)) AS event_id,
  concat('ZD-', CAST(t.id AS STRING)) AS ticket_id,
  t.organization.external_id AS account_id,
  to_timestamp(substr(c.created_at, 1, 19)) AS event_at,
  CASE WHEN c.author_role = 'end-user' THEN 'customer' ELSE 'agent' END AS author_type,
  c.author_name AS author,
  c.body
FROM bronze_zendesk_tickets t
LATERAL VIEW explode(t.comments) AS c;
