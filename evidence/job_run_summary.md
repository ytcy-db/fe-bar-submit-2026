# Job run evidence — `officepulse-churn-e2e` run 184435700181273

- Run page: https://adb-7405605463330453.13.azuredatabricks.net/?o=7405605463330453#job/920636648124867/run/184435700181273
- Result: **SUCCESS** (TERMINATED)
- Started: 2026-11-05 13:11:20 — Ended: 2026-11-05 13:18:58

| task | type | result | duration (s) | evidence |
|---|---|---|---|---|
| generate_raw_data | notebook | SUCCESS | 47 | `evidence/notebook_runs/generate_raw_data.ipynb` (8 outputs) |
| lakeflow_pipeline | pipeline | SUCCESS | 93 | `evidence/pipeline_data_quality.md` |
| train_register_serve | notebook | SUCCESS | 155 | `evidence/notebook_runs/train_register_serve.ipynb` (12 outputs) |
| uc_governance | notebook | SUCCESS | 64 | `evidence/notebook_runs/uc_governance.ipynb` (8 outputs) |
| batch_score | notebook | SUCCESS | 139 | `evidence/notebook_runs/batch_score.ipynb` (9 outputs) |
| business_impact | notebook | SUCCESS | 16 | `evidence/notebook_runs/business_impact.ipynb` (5 outputs) |
| publish_lakebase | notebook | SUCCESS | 22 | `evidence/notebook_runs/publish_lakebase.ipynb` (5 outputs) |

## Notebook exit values (dbutils.notebook.exit)

### generate_raw_data

```json
{
  "accounts": 612,
  "crm_status": {
    "active": 428,
    "onboarding": 31,
    "churn_risk": 15,
    "churned": 124,
    "prospect": 14
  },
  "churned_in_window": 124,
  "future_churners_hidden_in_data": 46,
  "ga4_rows": 36176,
  "ga4_files": 78,
  "zendesk_tickets": 4420,
  "zendesk_files": 19,
  "crm_account_rows": 627,
  "contracts": 598,
  "total_arr_jpy": 2190690000
}
```

### train_register_serve

```json
{
  "model": "ytcy_azure_east2classic_stable.officepulse_churn.churn_model",
  "version": "5",
  "run_id": "28ad734ce3a8442a8f22b138817e1525",
  "test_auc": 0.8469,
  "test_pr_auc": 0.6207,
  "test_brier": 0.1071,
  "rules_auc": 0.7716,
  "rules_pr_auc": 0.393,
  "base_rate": 0.1905,
  "precision_at_top5pct": 0.812,
  "recall_at_top5pct": 0.2126,
  "rules_precision_at_top5pct": 0.406,
  "rules_recall_at_top5pct": 0.1063,
  "precision_at_top10pct": 0.7632,
  "recall_at_top10pct": 0.3996,
  "rules_precision_at_top10pct": 0.4023,
  "rules_recall_at_top10pct": 0.2106,
  "precision_at_top20pct": 0.576,
  "recall_at_top20pct": 0.6043,
  "rules_precision_at_top20pct": 0.4071,
  "rules_recall_at_top20pct": 0.4272,
  "lift_at_top10pct": 4.0051,
  "renewals_at_checkpoint": 247.0,
  "churned_renewals": 47.0,
  "churned_arr_jpy": 124990000.0,
  "ml_recall_at_t90": 0.5532,
  "ml_arr_recall_at_t90": 0.606,
  "ml_alerts_at_t90": 41.0,
  "ml_precision_at_t90": 0.6341,
  "rules_recall_at_t90": 0.5106,
  "rules_arr_recall_at_t90": 0.5385,
  "rules_alerts_at_t90": 41.0,
  "rules_precision_at_t90": 0.5854,
  "cancel_ticket_recall_at_t90": 0.0,
  "cancel_ticket_arr_recall_at_t90": 0.0,
  "cancel_ticket_alerts_at_t90": 3.0,
  "cancel_ticket_precision_at_t90": 0.0,
  "cancel_ticket_share_of_churners": 0.4681,
  "cancel_ticket_median_days_before_renewal": 31.5
}
```

### batch_score

```json
{
  "scored_accounts": 448,
  "latest_week": "2026-11-02",
  "by_band": {
    "中": {
      "accounts": 62.0,
      "arr_jpy": 234910000.0,
      "arr_at_risk_jpy": 81046591.0,
      "csm_flagged": 0.0,
      "hidden_risk": 0.0
    },
    "低": {
      "accounts": 345.0,
      "arr_jpy": 1751050000.0,
      "arr_at_risk_jpy": 119433567.0,
      "csm_flagged": 10.0,
      "hidden_risk": 0.0
    },
    "高": {
      "accounts": 41.0,
      "arr_jpy": 119810000.0,
      "arr_at_risk_jpy": 79558257.0,
      "csm_flagged": 5.0,
      "hidden_risk": 36.0
    }
  }
}
```

### business_impact

```json
{
  "arr_live_now_jpy": 2190690000.0,
  "arr_start_12m_jpy": 2144320000.0,
  "churned_logos_12m": 93.0,
  "churned_arr_12m_jpy": 329910000.0,
  "gross_revenue_retention_12m": 0.8461,
  "ml_arr_coverage_t90": 0.606,
  "rules_arr_coverage_t90": 0.5385,
  "cancel_ticket_coverage_any_time": 0.4681,
  "arr_saved_status_quo_jpy": 15442595.7447,
  "arr_saved_with_ml_jpy": 59974518.1214,
  "incremental_arr_saved_vs_status_quo_jpy": 44531922.3768,
  "incremental_arr_saved_vs_rules_jpy": 6675273.1419,
  "grr_with_ml": 0.8669,
  "grr_uplift_pts": 2.0767,
  "alerts_per_quarter_t90": 20.5,
  "alert_precision_t90": 0.6341,
  "accounts_scored_now": 448.0,
  "high_risk_accounts_now": 41.0,
  "high_risk_arr_now_jpy": 119810000.0,
  "high_risk_arr_renewing_180d_jpy": 96200000.0,
  "hidden_risk_accounts_now": 36.0,
  "hidden_risk_arr_now_jpy": 101870000.0,
  "expected_arr_at_risk_now_jpy": 280038415.0,
  "save_rate_early": 0.3,
  "save_rate_late": 0.1
}
```

### publish_lakebase

```json
{
  "account_360": {
    "rows": 612,
    "seconds": 0.05,
    "rows_in_lakebase": 612
  },
  "tickets": {
    "rows": 4420,
    "seconds": 0.09,
    "rows_in_lakebase": 4420
  },
  "ticket_events": {
    "rows": 15433,
    "seconds": 0.11,
    "rows_in_lakebase": 15433
  },
  "usage_weekly": {
    "rows": 35835,
    "seconds": 0.24,
    "rows_in_lakebase": 35835
  },
  "lakebase_point_lookup_ms": {
    "p50": 1.3,
    "p95": 1.9
  }
}
```

