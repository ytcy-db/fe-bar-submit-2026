-- =====================================================================
-- BRONZE: incremental ingestion of raw source exports with Auto Loader
-- (read_files in STREAM mode = Lakeflow Auto Loader). Files land in the
-- UC Volume `raw` from three systems: CRM (CSV), GA4 (JSON), Zendesk (JSON).
-- Bronze keeps the source shape and adds lineage columns only.
-- =====================================================================

CREATE OR REFRESH STREAMING TABLE bronze_crm_accounts
COMMENT "Raw CRM account export (CSV, one file per daily export). Contains contact PII."
TBLPROPERTIES ("quality" = "bronze", "source_system" = "crm")
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${raw_path}/crm/accounts',
  format => 'csv',
  header => true,
  schemaHints => 'seats INT, arr_jpy BIGINT, contact_phone STRING'
);

CREATE OR REFRESH STREAMING TABLE bronze_crm_contracts
COMMENT "Raw CRM contract export (CSV)."
TBLPROPERTIES ("quality" = "bronze", "source_system" = "crm")
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${raw_path}/crm/contracts',
  format => 'csv',
  header => true,
  schemaHints => 'end_date STRING, churn_reason STRING, mrr_jpy BIGINT, term_months INT'
);

CREATE OR REFRESH STREAMING TABLE bronze_ga4_usage
COMMENT "Raw GA4 weekly tenant report (JSON lines, one file per ISO week). Contains duplicates and defects by design."
TBLPROPERTIES ("quality" = "bronze", "source_system" = "ga4")
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${raw_path}/ga4',
  format => 'json',
  schemaHints => 'report_week STRING, exported_at STRING, tenant_id STRING'
);

CREATE OR REFRESH STREAMING TABLE bronze_zendesk_tickets
COMMENT "Raw Zendesk ticket export (JSON lines per month) with nested comments array."
TBLPROPERTIES ("quality" = "bronze", "source_system" = "zendesk")
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '${raw_path}/zendesk',
  format => 'json',
  schemaHints => 'created_at STRING, updated_at STRING'
);
