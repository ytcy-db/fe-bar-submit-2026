# Lakeflow pipeline data quality — pipeline `7ae3982c-4d3a-4d0b-ad42-b0e4cfc359c8`

Source: `event_log()` table-valued function (latest update). Expectations are declared in `pipelines/officepulse_churn/transformations/*.sql`.

| dataset | rows written | dropped records | expectations (name / passed / failed) |
|---|---|---|---|
| ytcy_azure_east2classic_stable.officepulse_churn.bronze_crm_accounts | None | 0 |  |
| ytcy_azure_east2classic_stable.officepulse_churn.bronze_crm_contracts | None | 0 |  |
| ytcy_azure_east2classic_stable.officepulse_churn.bronze_ga4_usage | None | 0 |  |
| ytcy_azure_east2classic_stable.officepulse_churn.bronze_zendesk_tickets | None | 0 |  |
| ytcy_azure_east2classic_stable.officepulse_churn.gold_account_weekly | 35924 | 0 |  |
| ytcy_azure_east2classic_stable.officepulse_churn.gold_churn_monthly | 19 | 0 |  |
| ytcy_azure_east2classic_stable.officepulse_churn.gold_kpi_weekly | 78 | 0 |  |
| ytcy_azure_east2classic_stable.officepulse_churn.silver_accounts | 612 | 0 | valid_account_id: 612 passed / 0 failed; positive_seats: 612 passed / 0 failed; valid_plan: 612 passed / 0 failed |
| ytcy_azure_east2classic_stable.officepulse_churn.silver_contracts | 598 | 0 | end_after_start: 598 passed / 0 failed; valid_account_id: 598 passed / 0 failed |
| ytcy_azure_east2classic_stable.officepulse_churn.silver_ticket_events | 15433 | 0 |  |
| ytcy_azure_east2classic_stable.officepulse_churn.silver_tickets | 4420 | 0 | valid_csat: 4420 passed / 0 failed; valid_account_id: 4420 passed / 0 failed |
| ytcy_azure_east2classic_stable.officepulse_churn.silver_usage_weekly | 35924 | 130 | plausible_detect_rate: 36051 passed / 0 failed; plausible_login_rate: 35979 passed / 72 failed; valid_tenant: 35996 passed / 55 failed |

## Row counts of every table in the governed schema (after the run)

| table | rows |
|---|---|
| bronze_crm_accounts | 627 |
| bronze_crm_contracts | 598 |
| bronze_ga4_usage | 36176 |
| bronze_zendesk_tickets | 4420 |
| gold_account_360 | 612 |
| gold_account_weekly | 35835 |
| gold_business_impact | 25 |
| gold_churn_lead_time | 247 |
| gold_churn_monthly | 19 |
| gold_churn_scores | 1369 |
| gold_feature_importance | 20 |
| gold_kpi_weekly | 78 |
| gold_model_metrics | 39 |
| ml_churn_training_set | 20133 |
| silver_accounts | 612 |
| silver_contracts | 598 |
| silver_ticket_events | 15433 |
| silver_tickets | 4420 |
| silver_usage_weekly | 35835 |
