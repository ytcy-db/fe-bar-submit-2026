# App API smoke test — https://crm-help-desk-demo-7405605463330453.13.azure.databricksapps.com

Run 2026-11-05 13:24:37 by `scripts/smoke_test_app.py` against the deployed Databricks App.


## `GET /api/health` → HTTP 200 (738 ms end-to-end)

```json
{
 "status": "ok"
}
```

## `GET /api/meta` → HTTP 200 (780 ms end-to-end)

```json
{
 "product": "OfficePulse",
 "vendor": "CloudNest 株式会社",
 "catalog": "ytcy_azure_east2classic_stable",
 "schema": "officepulse_churn",
 "llm_model_service": "ytcy_azure_east2classic_stable.officepulse_churn.churn_advisor_llm",
 "churn_model_endpoint": "officepulse-churn-model",
 "lakebase_endpoint": "projects/officepulse-crm/branches/production/endpoints/primary",
 "genie_enabled": true
}
```

## `GET /api/dashboard/kpis` → HTTP 200 (1355 ms end-to-end)

```json
{
 "kpis": {
  "week_start": "2026-11-02",
  "login_rate": 69.6,
  "signup_rate": 78.4,
  "attendance_detect_rate": 76.9,
  "install_rate": 83.8,
  "app_config_ok_rate": 89.5
 },
 "kpis_prev": {
  "week_start": "2026-10-26",
  "login_rate": 69.2,
  "signup_rate": 78.3,
  "attendance_detect_rate": 76.5,
  "install_rate": 84.1,
  "app_config_ok_rate": 89.3
 },
 "counts": {
  "total": 612,
  "active": 428,
  "onboarding": 31,
  "churn_risk": 15,
  "churned": 124,
  "prospect": 14,
  "ml_high": 41,
  "ml_hidden": 36,
  "live_arr_jpy": 2190690000.0,
  "expected_arr_at_risk_jpy": 280038415.0,
  "high_risk_arr_jpy": 119810000.0
 },
 "open_tickets": 308,
 "latency": {
  "sql_warehouse_ms": 625.6,
  "lakebase_ms": 6.5
 }
}
```

## `GET /api/churn/summary` → HTTP 200 (803 ms end-to-end)

```json
{
 "scored": 448,
 "high": 41,
 "mid": 62,
 "hidden": 36,
 "csm_flagged": 15,
 "high_arr_jpy": 119810000.0,
 "hidden_arr_jpy": 101870000.0,
 "expected_arr_at_risk_jpy": 280038415.0,
 "model_version": 5,
 "scored_at": "2026-11-05 04:18:12.123233",
 "latency_ms": 4.6
}
```

## `GET /api/accounts?band=%E9%AB%98` → HTTP 200 (1084 ms end-to-end)

```json
{
 "accounts": [
  {
   "account_id": "ACC-1259",
   "company_name": "奥州建設株式会社",
   "industry": "建設",
   "plan": "Starter",
   "status": "active",
   "csm_owner": "田中 健一",
   "seats": 28,
   "arr_jpy": 480000,
   "region": "札幌",
   "auto_renew": false,
   "used_services": "Slack連携, モバイルアプリ",
   "start_date": "2025-11-16",
   "renewal_date": "2026-11-16",
   "end_date": null,
   "churn_probability": 0.9625906679084834,
   "risk_score": 96.3,
   "risk_band": "高",
   "rule_score": 24.7,
   "csm_flagged": false,
   "hidden_risk": true,
   "arr_at_risk_jpy": 462044.0,
   "top_drivers": [
    {
     "feature": "attendance_detect_rate_4w",
     "label": "出社検知率(直近4週)",
     "value": 0.5785750000000001,
     "impact": 1.5199
    },
    {
     "feature": "avg_csat_12w",
     "label": "平均CSAT(12週)",
     "value": 1.0,
     "impact": 1.5171
    },
    {
     "feature": "auto_renew",
     "label": "自動更新",
     "value": 0.0,
     "impact": 0.7587
    }
   ],
   "login_rate": 0.5,
   "attendance_detect_rate": 0.5429,
   "open_tickets_now": 0
  },
  {
   "account_id": "ACC-1008",
   "company_name": "関西フードサービス株式会社",
   "industry": "外食",
   "plan": "Standard",
   "status": "churn_risk",
   "csm_owner": "佐藤 美咲",
   "seats": 111,
   "arr_jpy": 1850000,
   "region": "広島",
   "auto_renew": false,
   "used_services": "出社検知, 座席管理, 利用分析ダッシュボード, API連携",
   "start_date": "2024-11-30",
   "renewal_date": "2026-11-30",
   "end_date": null,
   "churn_probability": 0.938054351824144,
   "risk_score": 93.8,
   "risk_band": "高",
   "rule_score": 62.3,
   "csm_flagged": true,
   "hidden_risk": false,
   "arr_at_risk_jpy": 1735401.0,
   "top_drivers": [
    {
     "feature": "attendance_detect_rate_4w",
     "label": "出社検知率(直近4週)",
     "value": 0.45754999999999996,
     "impact": 1.885
    },
    {
     "feature": "urgent_tickets_12w",
     "label": "高優先度の問い合わせ(12週)",
     "value": 4.0,
     "impact": 1.7792
    },
    {
     "feature": "avg_csat_12w",
     "label": "平均CSAT(12週)",
     "value": 3.0,
     "impact": 0.8364
    }
   ],
   "login_rate": 0.2793,
   "attendance_detect_rate": 0.5126,
   "open_tickets_now": 3
  },
  {
   "account_id": "ACC-1420",
   "company_name": "日向コンサルティング株式会社",
   "industry": "コンサル",
   "plan": "Premium",
   "status": "churn_risk",
   "csm_owner": "鈴木 彩子",
   "seats": 663,
   "arr_jpy": 7810000,
   "region": "東京",
   "auto_renew": true,
   "used_services": "入退室ログ, Slack連携, 利用分析ダッシュボード, モバイルアプリ, SSO/SAML, 出社検知",
   "start_date": "2024-11-17",
   "renewal_date"
... (truncated)
```

## `GET /api/accounts/ACC-1120` → HTTP 200 (770 ms end-to-end)

```json
{
 "account": {
  "account_id": "ACC-1120",
  "company_name": "飛鳥建設株式会社",
  "industry": "建設",
  "plan": "Enterprise",
  "status": "active",
  "csm_owner": "鈴木 彩子",
  "seats": 1279,
  "arr_jpy": 13260000,
  "region": "広島",
  "contract_id": "CT-20261120",
  "start_date": "2023-12-25",
  "end_date": null,
  "renewal_date": "2026-12-25",
  "loaned_devices": "OfficePulse Sensor G2×14, OfficePulse Beacon Lite×9",
  "used_services": "利用分析ダッシュボード, API連携, 入退室ログ, モバイルアプリ, 出社検知, 座席管理, SSO/SAML, Slack連携",
  "churn_reason": null,
  "mrr_jpy": 1105000,
  "auto_renew": true,
  "last_usage_week": "2026-11-02",
  "login_rate": 0.5559,
  "signup_rate": 0.7099,
  "attendance_detect_rate": 0.6281,
  "install_rate": 0.8124,
  "app_config_ok_rate": 0.7451,
  "tickets_total": 12,
  "open_tickets_now": 2,
  "avg_csat": 4.13,
  "has_cancellation_ticket": false,
  "churn_probability": 0.6715909783732332,
  "risk_score": 67.2,
  "risk_band": "高",
  "rule_score": 20.8,
  "top_drivers": [
   {
    "feature": "attendance_detect_rate_4w",
    "label": "出社検知率(直近4週)",
    "value": 0.610725,
    "impact": 1.3249
   },
   {
    "feature": "avg_csat_12w",
    "label": "平均CSAT(12週)",
    "value": 3.0,
    "impact": 0.7839
   },
   {
    "feature": "login_rate_4w",
    "label": "ログイン率(直近4週)",
    "value": 0.574075,
    "impact": 0.3754
   }
  ],
  "csm_flagged": false,
  "hidden_risk": true,
  "model_version": 5,
  "scored_at": "2026-11-05 04:18:12.123233",
  "arr_at_risk_jpy": 8905296.0,
  "features": {
   "login_rate_4w": 0.574075,
   "signup_rate_4w": 0.73885,
   "attendance_detect_rate_4w": 0.610725,
   "install_rate_4w": 0.7875249999999999,
   "app_config_ok_rate_4w": 0.7745,
   "login_trend_8w": -0.10009999999999997,
   "detect_trend_8w": -0.12902500000000006,
   "config_trend_8w": -0.004925000000000068,
   "avg_session_min_4w": 11.400000000000002,
   "sessions_per_user_4w": 3.5386448757235276,
   "tickets_12w": 2.0,
   "urgent_tickets_12w": 1.0,
   "technical_tickets_12w": 1.0,
   "cancellation_tickets_12w": 0.0,
   "slow_first_responses_12w": 0.0,
   "low_csat_tickets_12w": 0.0,
   "avg_csat_12w": 3.0,
   "open_tickets": 0,
   "auto_renew": 1,
   "plan_ordinal": 3
  }
 },
 "metrics": [
  {
   "week_start": "2026-05-04",
   "login_rate": 0.6755,
   "signup_rate": 0.767,
   "attendance_detect_rate": 0.767,
   "install_rate": 0.8671,
   "app_config_ok_rate": 0.8627,
   "dau": 864,
   "sessions": 2380,
   "avg_session_min": 16.7
  },
  {
   "week_start": "2026-05-11",
   "login_rate": 0.72
... (truncated)
```

## `POST /api/accounts/ACC-1120/whatif` → HTTP 200 (901 ms end-to-end)

request: `{"overrides": {"attendance_detect_rate_4w": 0.85, "login_rate_4w": 0.8, "avg_csat_12w": 4.2, "open_tickets": 0}}`

```json
{
 "baseline": {
  "churn_probability": 0.6715909783732332,
  "drivers": [
   {
    "feature": "attendance_detect_rate_4w",
    "label": "出社検知率(直近4週)",
    "value": 0.610725,
    "impact": 1.3249
   },
   {
    "feature": "avg_csat_12w",
    "label": "平均CSAT(12週)",
    "value": 3.0,
    "impact": 0.7839
   },
   {
    "feature": "login_rate_4w",
    "label": "ログイン率(直近4週)",
    "value": 0.574075,
    "impact": 0.3754
   }
  ]
 },
 "scenario": {
  "churn_probability": 0.027378729186936353,
  "drivers": [
   {
    "feature": "urgent_tickets_12w",
    "label": "高優先度の問い合わせ(12週)",
    "value": 1.0,
    "impact": 0.2184
   },
   {
    "feature": "signup_rate_4w",
    "label": "登録率(直近4週)",
    "value": 0.73885,
    "impact": 0.1583
   },
   {
    "feature": "config_trend_8w",
    "label": "設定良好率の変化(8週前比)",
    "value": -0.004925000000000068,
    "impact": 0.0711
   }
  ]
 },
 "overrides": {
  "attendance_detect_rate_4w": 0.85,
  "login_rate_4w": 0.8,
  "avg_csat_12w": 4.2,
  "open_tickets": 0.0
 },
 "endpoint": "officepulse-churn-model"
}
```

## `POST /api/accounts/ACC-1120/recommend` → HTTP 200 (21003 ms end-to-end)

```json
{
 "score": {
  "risk_score": 67.2,
  "risk_band": "高",
  "churn_probability": 0.6715909783732332,
  "rule_score": 20.8,
  "drivers": [
   {
    "feature": "attendance_detect_rate_4w",
    "label": "出社検知率(直近4週)",
    "value": 0.610725,
    "impact": 1.3249
   },
   {
    "feature": "avg_csat_12w",
    "label": "平均CSAT(12週)",
    "value": 3.0,
    "impact": 0.7839
   },
   {
    "feature": "login_rate_4w",
    "label": "ログイン率(直近4週)",
    "value": 0.574075,
    "impact": 0.3754
   }
  ],
  "model_version": 5,
  "reasons": [
   "出社検知率(直近4週)",
   "平均CSAT(12週)",
   "ログイン率(直近4週)"
  ]
 },
 "recommendation": {
  "risk_summary": "次回更新（2026-12-25、残り53日）での解約確率は約67.2%で、リスク帯は「高」です。モデルの最大要因は出社検知率（直近4週 61.1%、SHAP寄与 +1.32）で、次いで平均CSAT（12週 3.0、+0.78）、ログイン率（直近4週 57.4%、+0.38）です。検知率は8週トレンドが-0.129、26週前の76.7%から現在62.8%へ低下しており、ARR 1,326万円の自動更新契約でも早急な立て直しが必要です。",
  "key_drivers": [
   "出社検知率(直近4週) 61.1%（SHAP +1.3249）：8週トレンド-0.129で悪化中。26週前の76.7%から低下",
   "平均CSAT(12週) 3.0（SHAP +0.7839）：緊急チケット1件・技術チケット1件が背景。全期間平均は4.13で、直近の体験悪化が示唆される",
   "ログイン率(直近4週) 57.4%（SHAP +0.3754）：8週トレンド-0.100で、利用定着が低下傾向"
  ],
  "recommended_actions": [
   {
    "action": "出社検知率低下の原因調査：貸与センサー（G2×14、Beacon Lite×9）の稼働・接続状況、設置位置、オフライン端末、アプリ設定不備（設定良好率74.5%）を点検し、拠点・フロア別の検知率低下箇所を特定して是正計画を顧客に共有する",
    "priority": "高",
    "owner": "エンジニア",
    "due_in_days": 7,
    "rationale": "最大要因である出社検知率(SHAP +1.3249)に直接効く。検知率の低下は『ダッシュボードの数値がおかしい』という問い合わせとも整合する可能性があり、まず原因を切り分ける"
   },
   {
    "action": "未解決チケット2件（特に『ダッシュボードの数値がおかしい』『Slack通知が届かない』）を最優先で解消し、解決後にCSM同席で顧客へ報告する。MLの open_tickets=0 とサポート状況の未解決2件に差異があるため、チケット状態を同時に確認・整合させる",
    "priority": "高",
    "owner": "サポート",
    "due_in_days": 5,
    "rationale": "平均CSAT(12週 3.0, SHAP +0.7839)の改善に効く。未解決の不満を残したまま更新を迎えるリスクを下げる"
   },
   {
    "action": "鈴木CSMが顧客の情報システム／総務責任者と30分の現状レビューを実施する。検知率低下の原因と是正計画、CSAT低下の背景（緊急・技術チケット）をヒアリングし、改善スケジュールを合意する",
    "priority": "高",
    "owner": "CSM",
    "due_in_days": 7,
    "rationale": "CSAT(SHAP +0.7839)と検知率(SHAP +1.3249)の両方に対し、顧客の不満を直接把握して信頼を回復する。更新まで53日のため早期の対話が必要"
   },
   {
    "action": "利用定着の再活性化：『座席管理の使い方がわからない』が繰り返されているため、拠点・部門ごとのオンライン勉強会（座席管理、モバイルアプリ、Slack連携の活用）を実施し、ログイン未実施ユーザーへ周知する",
    "priority": "中",
    "owner": "CSM",
    "due_in_days": 14,
    "rationale": "ログイン率(直近4週 57.4%, SHAP +0.3754)と下落トレンド-0.100に効く。活用が進めば検知・ログインの両方の底上げにつながる"
   },
   {
    "action": "『追加ライセンスを購入したい』という要望をフォローし、検知率改善の見通しを踏まえた拡張提案と更新条件の事前確認を行う。更新30日前までに更新意思と懸念事項を確認する",
    "priority": "中",
    "owner": "営業",
    "due_in_days": 14,
    "rationale": "拡張意向は継続意欲を示す好材料。更新前に懸念を洗い出し、自動更新（auto_renew=true）でも解約申告されるリスクを下げる"
   },
   {
    "action": "改善結果レポート（検知率・ログイン率の推移、解決済みチケット、今後の改善計画）を作成し、更新判断者に提示する",
    "priority": "低",
    "owner": "CSM",
    "due_in_days": 28,
    "rationale": "3つの主要因の改善を可視化し、更新前に価値を再認識してもらう"
   }
  ],
  "talk_track": "直近で出社検知率やダッシュボードの数値、Slack通知にご不便をおかけしており、申し訳ありません。今週中に原因を特定して、改善計画をお持ちします。まず現場でお困りの点を30分ほどお聞かせいただけますか。",
  "success_metric": "更新日（2026-12-25）の2週間前までに、出社検知率を61%から75%以上（26週前の76.7%水準）へ回復、ログイン率を57%から65%以上へ改善、未解決チケットを0件にする。新規チケットのCSATは4.0以上を維持し、更新30日前までに顧客から更新継続の意思を確認する。"
 }
}
```

## `POST /api/accounts/ACC-1120/actions` → HTTP 200 (720 ms end-to-end)

request: `{"action": "出社検知率低下の原因調査：貸与センサー（G2×14、Beacon Lite×9）の稼働・接続状況、設置位置、オフライン端末、アプリ設定不備（設定良好率74.5%）を点検し、拠点・フロア別の検知率低下箇所を特定して是正計画を顧客に共有する", "priority": "高", "rationale": "最大要因である出社検知率(SHAP +1.3249)に直接効く。検知率の低下は『ダッシュボードの数値がおかしい』という問い合わせとも整合する可能性があり、まず原因を切り分ける", "due_in_days": 7, "add_to_schedule": true}`

```json
{
 "ok": true,
 "action_id": 2
}
```

## `GET /api/actions` → HTTP 200 (759 ms end-to-end)

```json
{
 "actions": [
  {
   "action_id": 2,
   "account_id": "ACC-1120",
   "action": "出社検知率低下の原因調査：貸与センサー（G2×14、Beacon Lite×9）の稼働・接続状況、設置位置、オフライン端末、アプリ設定不備（設定良好率74.5%）を点検し、拠点・フロア別の検知率低下箇所を特定して是正計画を顧客に共有する",
   "priority": "高",
   "rationale": "最大要因である出社検知率(SHAP +1.3249)に直接効く。検知率の低下は『ダッシュボードの数値がおかしい』という問い合わせとも整合する可能性があり、まず原因を切り分ける",
   "owner": "鈴木 彩子",
   "status": "planned",
   "outcome": null,
   "due_date": "2026-11-09",
   "source": "ai_recommendation",
   "churn_probability_at_creation": 0.6715909783732332,
   "model_version": 5,
   "created_at": "2026-11-05 04:25:05.132422+00:00",
   "updated_at": "2026-11-05 04:25:05.132422+00:00",
   "company_name": "飛鳥建設株式会社",
   "risk_band": "高",
   "churn_probability_now": 0.6715909783732332
  },
  {
   "action_id": 1,
   "account_id": "ACC-1120",
   "action": "センサーG2×14台・Beacon Lite×9台の稼働診断を実施する。オンライン状態、設置場所、ファームウェア、未検知エリアを確認し、検知率が落ちている拠点やフロアを特定して是正する。",
   "priority": "高",
   "rationale": "最大要因の出社検知率低下（61.1%、トレンド-12.9pt）に直接効く。機器・設置起因の欠測を解消する。",
   "owner": "鈴木 彩子",
   "status": "planned",
   "outcome": null,
   "due_date": "2026-11-09",
   "source": "ai_recommendation",
   "churn_probability_at_creation": 0.6715909783732332,
   "model_version": 5,
   "created_at": "2026-11-05 04:21:20.089192+00:00",
   "updated_at": "2026-11-05 04:21:20.089192+00:00",
   "company_name": "飛鳥建設株式会社",
   "risk_band": "高",
   "churn_probability_now": 0.6715909783732332
  }
 ]
}
```

## `GET /api/model/summary` → HTTP 200 (2610 ms end-to-end)

```json
{
 "metrics": {
  "test_auc": 0.8469456262360161,
  "test_pr_auc": 0.6206886689894116,
  "test_brier": 0.10710664054850394,
  "rules_auc": 0.7716020046266228,
  "rules_pr_auc": 0.39298007785333255,
  "base_rate": 0.1905476369092273,
  "precision_at_top5pct": 0.8120300751879699,
  "recall_at_top5pct": 0.2125984251968504,
  "rules_precision_at_top5pct": 0.40601503759398494,
  "rules_recall_at_top5pct": 0.1062992125984252,
  "precision_at_top10pct": 0.7631578947368421,
  "recall_at_top10pct": 0.39960629921259844,
  "rules_precision_at_top10pct": 0.40225563909774437,
  "rules_recall_at_top10pct": 0.2106299212598425,
  "precision_at_top20pct": 0.575984990619137,
  "recall_at_top20pct": 0.6043307086614174,
  "rules_precision_at_top20pct": 0.4071294559099437,
  "rules_recall_at_top20pct": 0.4271653543307087,
  "lift_at_top10pct": 4.005076668048074,
  "renewals_at_checkpoint": 247.0,
  "churned_renewals": 47.0,
  "churned_arr_jpy": 124990000.0,
  "ml_recall_at_t90": 0.5531914893617021,
  "ml_arr_recall_at_t90": 0.6059684774781983,
  "ml_alerts_at_t90": 41.0,
  "ml_precision_at_t90": 0.6341463414634146,
  "rules_recall_at_t90": 0.5106382978723404,
  "rules_arr_recall_at_t90": 0.5385230818465477,
  "rules_alerts_at_t90": 41.0,
  "rules_precision_at_t90": 0.5853658536585366,
  "cancel_ticket_recall_at_t90": 0.0,
  "cancel_ticket_arr_recall_at_t90": 0.0,
  "cancel_ticket_alerts_at_t90": 3.0,
  "cancel_ticket_precision_at_t90": 0.0,
  "cancel_ticket_share_of_churners": 0.46808510638297873,
  "cancel_ticket_median_days_before_renewal": 31.5,
  "ml_threshold": 0.4,
  "rules_threshold_same_volume": 9.077806477732794,
  "model_version": 5.0
 },
 "impact": {
  "arr_live_now_jpy": 2190690000.0,
  "arr_start_12m_jpy": 2144320000.0,
  "churned_logos_12m": 93.0,
  "churned_arr_12m_jpy": 329910000.0,
  "gross_revenue_retention_12m": 0.846147030293986,
  "ml_arr_coverage_t90": 0.6059684774781983,
  "rules_arr_coverage_t90": 0.5385230818465477,
  "cancel_ticket_coverage_any_time": 0.46808510638297873,
  "arr_saved_status_quo_jpy": 15442595.744680852,
  "arr_saved_with_ml_jpy": 59974518.12144972,
  "incremental_arr_saved_vs_status_quo_jpy": 44531922.376768865,
  "incremental_arr_saved_vs_rules_jpy": 6675273.141851351,
  "grr_with_ml": 0.8669144168672441,
  "grr_uplift_pts": 2.0767386573258126,
  "alerts_per_quarter_t90": 20.5,
  "alert_precision_t90": 0.6341463414634146,
  "accounts_scored_now": 448.0,
  "high_risk_accounts_now": 41.0,
  "high_risk_arr_now_jpy": 119810000.0,
  "hig
... (truncated)
```

## `GET /api/tickets?company=%E3%83%86%E3%83%83%E3%82%AF%E3%83%96%E3%83%AA%E3%83%83%E3%82%B8` → HTTP 200 (714 ms end-to-end)

```json
{
 "tickets": [
  {
   "ticket_id": "ZD-10055",
   "account_id": "ACC-1004",
   "company_name": "テックブリッジ株式会社",
   "subject": "出社検知が反映されない",
   "category": "技術",
   "priority": "high",
   "status": "open",
   "channel": "chat",
   "assignee": "斎藤 光",
   "created_at": "2026-10-27 13:58:00",
   "updated_at": "2026-10-30 04:03:00",
   "first_response_min": 185,
   "resolution_hours": null,
   "csat": null,
   "risk_band": "中",
   "churn_probability": 0.4115506542381531
  },
  {
   "ticket_id": "ZD-10054",
   "account_id": "ACC-1004",
   "company_name": "テックブリッジ株式会社",
   "subject": "請求金額について確認したい",
   "category": "請求",
   "priority": "normal",
   "status": "solved",
   "channel": "phone",
   "assignee": "斎藤 光",
   "created_at": "2026-10-23 12:04:00",
   "updated_at": "2026-10-25 05:44:00",
   "first_response_min": 280,
   "resolution_hours": 7.3,
   "csat": null,
   "risk_band": "中",
   "churn_probability": 0.4115506542381531
  },
  {
   "ticket_id": "ZD-10053",
   "account_id": "ACC-1004",
   "company_name": "テックブリッジ株式会社",
   "subject": "座席管理の使い方がわからない",
   "category": "使い方",
   "priority": "low",
   "status": "new",
   "channel": "chat",
   "assignee": "加藤 さゆり",
   "created_at": "2026-10-14 14:53:00",
   "updated_at": "2026-10-15 02:41:00",
   "first_response_min": 48,
   "resolution_hours": null,
   "csat": null,
   "risk_band": "中",
   "churn_probability": 0.4115506542381531
  },
  {
   "ticket_id": "ZD-10052",
   "account_id": "ACC-1004",
   "company_name": "テックブリッジ株式会社",
   
... (truncated)
```

## `GET /api/schedule` → HTTP 200 (763 ms end-to-end)

```json
{
 "schedule": [
  {
   "schedule_id": "SC-101",
   "account_id": "ACC-1296",
   "company_name": "信濃証券株式会社",
   "owner": "田中 健一",
   "date": "2026-11-02",
   "title": "信濃証券株式会社 解約リスクヒアリング",
   "kind": "recommended",
   "ticket_id": "ZD-12267",
   "start_time": "10:00",
   "duration_min": 45,
   "action_id": null,
   "ticket_subject": "解約手続きの方法を知りたい",
   "ticket_priority": "urgent",
   "ticket_status": "closed",
   "ticket_category": "解約",
   "risk_band": null,
   "churn_probability": null
  },
  {
   "schedule_id": "SC-114",
   "account_id": "ACC-1579",
   "company_name": "若葉建設株式会社",
   "owner": "高橋 大輔",
   "date": "2026-11-02",
   "title": "若葉建設株式会社 契約更新相談",
   "kind": "confirmed",
   "ticket_id": null,
   "start_time": "10:00",
   "duration_min": 30,
   "action_id": null,
   "ticket_subject": null,
   "ticket_priority": null,
   "ticket_status": null,
   "ticket_category": null,
   "risk_band": "低",
   "churn_probability": 0.02554296094025754
  },
  {
   "schedule_id": "SC-119",
   "account_id": "ACC-1067",
   "company_name": "葵メディカル株式会社",
   "owner": "高橋 大輔",
   "date": "2026-11-02",
   "title": "葵メディカル株式会社 定例フォローアップ",
   "kind": "confirmed",
   "ticket_id": null,
   "start_time": "16:00",
   "duration_min": 30,
   "action_id": null,
   "ticket_subject": null,
   "ticket_priority": null,
   "ticket_status": null,
   "ticket_category": null,
   "risk_band": "低",
   "churn_probability": 0.018204527513335445
  },
  {
   "schedule_id": "SC-106",
   "account_id": "ACC-1169",
  
... (truncated)
```

## `POST /api/genie/ask` → HTTP 200 (17346 ms end-to-end)

request: `{"message": "CSMが未フラグの高リスク顧客は何社？期待損失ARRの合計も"}`

```json
{
 "mode": "chat",
 "conversation_id": "01f1d8d0e3cb171fb8db8f9e85cef69f",
 "message_id": "01f1d8d0e3da137ca46e5fb7dd7eca31",
 "answer": "CSMが未フラグの高リスク顧客の数と、その顧客に対する期待損失ARRの合計を知りたいということですね。\nCSMが未フラグの**高リスク顧客は36社**です。期待損失ARRの合計は**64,870,944円**で、**約6,487万円**です。",
 "query": "SELECT COUNT(*) AS `high_risk_unflagged_accounts`, COALESCE(SUM(`arr_at_risk_jpy`), 0) AS `total_arr_at_risk_jpy` FROM `ytcy_azure_east2classic_stable`.`officepulse_churn`.`gold_account_360` WHERE `hidden_risk` = TRUE AND `risk_band` = '高' AND `end_date` IS NULL AND `status` <> 'prospect'",
 "table": {
  "columns": [
   "high_risk_unflagged_accounts",
   "total_arr_at_risk_jpy"
  ],
  "types": [
   "LONG",
   "DOUBLE"
  ],
  "rows": [
   [
    "36",
    "6.4870944E7"
   ]
  ]
 },
 "viz": null,
 "followups": [
  "CSMが未フラグの高リスク顧客の業界別の件数と期待損失ARRの合計は？",
  "CSMが未フラグの高リスク顧客の地域別の件数と期待損失ARRの合計は？",
  "CSMが未フラグの高リスク顧客のプラン別の件数と期待損失ARRの合計は？"
 ]
}
```
