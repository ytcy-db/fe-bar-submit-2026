# Genie evidence — space `01f1d8cbb15c14b6bae5441db40aed47` (OfficePulse Churn Agent)

Generated 2026-11-05 13:22 by `genie/run_genie_evidence.py` via the Genie Conversation API.


## Q: CSMがまだフラグしていない高リスク顧客をARRの大きい順に10社教えて

status: `COMPLETED`

**Generated SQL** (CSMがまだフラグしていない高リスク顧客のうち、現役顧客でARRが大きい順に上位10社の情報を知りたいということですね。):

```sql
SELECT `account_id`, `company_name`, `csm_owner`, `plan`, `region`, `arr_jpy`, `risk_score`, `churn_probability`, `arr_at_risk_jpy`, `renewal_date`, `top_drivers`
FROM `ytcy_azure_east2classic_stable`.`officepulse_churn`.`gold_account_360`
WHERE `hidden_risk` = TRUE
  AND `end_date` IS NULL
  AND `status` <> 'prospect'
  AND `account_id` IS NOT NULL
  AND `company_name` IS NOT NULL
  AND `arr_jpy` IS NOT NULL
  AND `risk_score` IS NOT NULL
  AND `arr_at_risk_jpy` IS NOT NULL
ORDER BY `arr_jpy` DESC, `account_id` ASC
LIMIT 10
```

| account_id | company_name | csm_owner | plan | region | arr_jpy | risk_score | churn_probability | arr_at_risk_jpy | renewal_date | top_drivers |
|---|---|---|---|---|---|---|---|---|---|---|
| ACC-1273 | 未来フーズ株式会社 | 高橋 大輔 | Enterprise | 大阪 | 13970000 | 59.0 | 0.5897346283505115 | 8238593.0 | 2026-12-07 | [{"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.651525, "impact": 0.7081}, {"feature": "auto_renew", "label": "自動更新", "value": 0.0, "impact": 0.5936}, {"feature": "login_rate_4w", "label": "ログイン率(直近4週)", "value": 0.63025, "impact": 0.2958}] |
| ACC-1120 | 飛鳥建設株式会社 | 鈴木 彩子 | Enterprise | 広島 | 13260000 | 67.2 | 0.6715909783732332 | 8905296.0 | 2026-12-25 | [{"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.610725, "impact": 1.3249}, {"feature": "avg_csat_12w", "label": "平均CSAT(12週)", "value": 3.0, "impact": 0.7839}, {"feature": "login_rate_4w", "label": "ログイン率(直近4週)", "value": 0.574075, "impact": 0.3754}] |
| ACC-1095 | 筑紫ホテルズ株式会社 | 渡部 由香 | Enterprise | 東京 | 10300000 | 68.2 | 0.6816826236123936 | 7021331.0 | 2027-01-26 | [{"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.66885, "impact": 1.1162}, {"feature": "avg_csat_12w", "label": "平均CSAT(12週)", "value": 2.0, "impact": 1.0216}, {"feature": "login_rate_4w", "label": "ログイン率(直近4週)", "value": 0.593075, "impact": 0.4229}] |
| ACC-1397 | 株式会社黎明システムズ | 佐藤 美咲 | Premium | 広島 | 7070000 | 56.4 | 0.5636138556843722 | 3984750.0 | 2026-12-20 | [{"feature": "auto_renew", "label": "自動更新", "value": 0.0, "impact": 0.7733}, {"feature": "avg_csat_12w", "label": "平均CSAT(12週)", "value": 3.0, "impact": 0.5988}, {"feature": "app_config_ok_rate_4w", "label": "アプリ設定良好率(直近4週)", "value": 0.8332999999999999, "impact": 0.2788}] |
| ACC-1169 | 青葉ホールディングス株式会社 | 高橋 大輔 | Premium | 広島 | 5700000 | 84.7 | 0.8471285028563523 | 4828632.0 | 2027-07-02 | [{"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.619475, "impact": 1.3701}, {"feature": "avg_csat_12w", "label": "平均CSAT(12週)", "value": 1.75, "impact": 1.3043}, {"feature": "login_rate_4w", "label": "ログイン率(直近4週)", "value": 0.611425, "impact": 0.4038}] |
| ACC-1514 | 株式会社星野ロジスティクス | 高橋 大輔 | Premium | 横浜 | 5240000 | 75.2 | 0.752004039773217 | 3940501.0 | 2027-07-22 | [{"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.625125, "impact": 1.3137}, {"feature": "avg_csat_12w", "label": "平均CSAT(12週)", "value": 2.0, "impact": 1.1301}, {"feature": "login_rate_4w", "label": "ログイン率(直近4週)", "value": 0.552675, "impact": 0.2809}] |
| ACC-1059 | 北斗人材開発株式会社 | 田中 健一 | Premium | 横浜 | 5170000 | 71.8 | 0.7177377592543615 | 3710704.0 | 2026-11-03 | [{"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.46965, "impact": 2.0708}, {"feature": "avg_csat_12w", "label": "平均CSAT(12週)", "value": 3.0, "impact": 0.626}, {"feature": "login_trend_8w", "label": "ログイン率の変化(8週前比)", "value": -0.06132500000000002, "impact": 0.3198}] |
| ACC-1023 | 株式会社新星教育サービス | 松本 亮 | Premium | 東京 | 4950000 | 51.0 | 0.5096917088451391 | 2522974.0 | 2027-04-08 | [{"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.665025, "impact": 0.9965}, {"feature": "avg_csat_12w", "label": "平均CSAT(12週)", "value": 3.0, "impact": 0.6486}, {"feature": "login_rate_4w", "label": "ログイン率(直近4週)", "value": 0.635425, "impact": 0.3745}] |
| ACC-1087 | 株式会社銀河商事 | 伊藤 直樹 | Premium | 福岡 | 4030000 | 52.4 | 0.5236109963183955 | 2110152.0 | 2026-11-06 | [{"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.583925, "impact": 1.1049}, {"feature": "auto_renew", "label": "自動更新", "value": 0.0, "impact": 0.5884}, {"feature": "login_rate_4w", "label": "ログイン率(直近4週)", "value": 0.571925, "impact": 0.2974}] |
| ACC-1599 | 玄武製作所株式会社 | 高橋 大輔 | Standard | 福岡 | 3750000 | 70.9 | 0.7085099325188791 | 2656912.0 | 2027-03-08 | [{"feature": "auto_renew", "label": "自動更新", "value": 0.0, "impact": 0.7846}, {"feature": "attendance_detect_rate_4w", "label": "出社検知率(直近4週)", "value": 0.659425, "impact": 0.7546}, {"feature": "avg_csat_12w", "label": "平均CSAT(12週)", "value": 3.0, "impact": 0.7012}] |

_10 row(s)_

**Answer:** CSMが未フラグの高リスク顧客は、ARRの大きい順で以下の**10社**です。リスト全体では、ARRは**375万円〜1,397万円**、リスクスコアは**51.0〜84.7**で、更新日が**2026-11-03〜2027-07-22**に分布しています。

- **未来フーズ株式会社** — ARR **1,397万円**、リスクスコア **59.0**、期待損失ARR **約824万円**、更新日 **2026-12-07**
- **飛鳥建設株式会社** — ARR **1,326万円**、リスクスコア **67.2**、期待損失ARR **約891万円**、更新日 **2026-12-25**
- **筑紫ホテルズ株式会社** — ARR **1,030万円**、リスクスコア **68.2**、期待損失ARR **約702万円**、更新日 **2027-01-26**
- **株式会社黎明システムズ** — ARR **707万円**、リスクスコア **56.4**、期待損失ARR **約398万円**、更新日 **2026-12-20**
- **青葉ホールディングス株式会社** — ARR **570万円**、リスクスコア **84.7**、期待損失ARR **約483万円**、更新日 **2027-07-02**


## Q: 今後90日以内に更新日を迎える高リスク顧客と期待損失ARRの合計は？

status: `COMPLETED`

**Generated SQL** (今後90日以内に更新日を迎える高リスク顧客の数と、その顧客に対する期待損失ARRの合計を知りたいということですね。):

```sql
SELECT COUNT(*) AS `high_risk_accounts`, SUM(`arr_at_risk_jpy`) AS `total_expected_arr_loss_jpy` FROM `ytcy_azure_east2classic_stable`.`officepulse_churn`.`gold_account_360` WHERE `renewal_date` IS NOT NULL AND `renewal_date` BETWEEN DATE '2026-11-02' AND DATE_ADD(DATE '2026-11-02', 90) AND `risk_band` = '高' AND `end_date` IS NULL AND `status` <> 'prospect'
```

| high_risk_accounts | total_expected_arr_loss_jpy |
|---|---|
| 20 | 5.4653638E7 |

_1 row(s)_

**Answer:** 2026-11-02から**今後90日以内**に更新日を迎える**高リスク顧客は20社**で、期待損失ARRの合計は**54,653,638円**です。金額を百万円単位で見ると、期待損失ARRの合計は**約54.7百万円**です。


## Q: 業界別の平均解約確率と期待損失ARRを教えて

status: `COMPLETED`

**Generated SQL** (業界ごとに、現在解約リスクのある顧客の平均解約確率と期待損失ARRの合計を知りたいということですね。):

```sql
SELECT
  `industry`,
  AVG(`churn_probability`) AS `avg_churn_probability`,
  SUM(`arr_at_risk_jpy`) AS `expected_arr_loss_jpy`
FROM `ytcy_azure_east2classic_stable`.`officepulse_churn`.`gold_account_360`
WHERE `industry` IS NOT NULL
  AND `end_date` IS NULL
  AND `status` IS NOT NULL
  AND `status` <> 'prospect'
GROUP BY `industry`
ORDER BY `expected_arr_loss_jpy` DESC
```

| industry | avg_churn_probability | expected_arr_loss_jpy |
|---|---|---|
| IT・Web | 0.14342025208426096 | 3.7417662E7 |
| 外食 | 0.19949727531622768 | 3.5331846E7 |
| 製造 | 0.16640630526075573 | 3.2217929E7 |
| 商社・卸 | 0.1664741807438063 | 2.5637191E7 |
| 物流 | 0.1635545649682037 | 2.1644257E7 |
| エネルギー | 0.16020045459885188 | 2.1374668E7 |
| コンサル | 0.20058646784107406 | 1.9584529E7 |
| 金融 | 0.1437026941863902 | 1.8414975E7 |
| 建設 | 0.20399801409493118 | 1.6144227E7 |
| 医療・福祉 | 0.16519911153869418 | 1.3220459E7 |
| 小売 | 0.2213124641758402 | 1.2445558E7 |
| 不動産 | 0.10558721424944209 | 1.1358043E7 |

_14 row(s)_

**Answer:** 期待損失ARRは合計ではなく平均や中央値で見るほうがよろしいですか？

**Answer:** 現役顧客14業界の集計では、期待損失ARRが最も大きいのは**IT・Web**で**約3,742万円**、次いで**外食**で**約3,533万円**、**製造**で**約3,222万円**でした。平均解約確率は**小売**が**22.1%**で最も高く、**建設**が**20.4%**、**コンサル**が**20.1%**と続き、期待損失ARRの上位業界とはやや異なります。

代表的な業界は以下の通りです:
- **IT・Web**: 平均解約確率 **14.3%**、期待損失ARR **約3,742万円**
- **外食**: 平均解約確率 **19.9%**、期待損失ARR **約3,533万円**
- **製造**: 平均解約確率 **16.6%**、期待損失ARR **約3,222万円**
- **小売**: 平均解約確率 **22.1%**、期待損失ARR **約1,245万円**
- **不動産**: 平均解約確率 **10.6%**、期待損失ARR **約1,136万円**


## Q: 直近12ヶ月の月別解約件数と解約ARRの推移を見せて

status: `COMPLETED`

**Generated SQL** (直近12ヶ月（2025年12月から2026年11月まで）の月ごとの解約件数と解約によるARR（年間経常収益）の合計金額の推移を見たいということですね。):

```sql
SELECT
  `month`,
  `churned_accounts`,
  `churned_arr_jpy`
FROM `ytcy_azure_east2classic_stable`.`officepulse_churn`.`gold_churn_monthly`
WHERE `month` IS NOT NULL
  AND `month` >= DATE '2025-12-01'
  AND `month` < DATE '2026-12-01'
ORDER BY `month` ASC
```

| month | churned_accounts | churned_arr_jpy |
|---|---|---|
| 2025-12-01 | 7 | 45970000 |
| 2026-01-01 | 4 | 8270000 |
| 2026-02-01 | 2 | 9280000 |
| 2026-03-01 | 15 | 57610000 |
| 2026-04-01 | 8 | 31380000 |
| 2026-05-01 | 5 | 3800000 |
| 2026-06-01 | 12 | 29350000 |
| 2026-07-01 | 15 | 33970000 |
| 2026-08-01 | 7 | 39320000 |
| 2026-09-01 | 3 | 11920000 |
| 2026-10-01 | 5 | 6630000 |
| 2026-11-01 | 0 | 0 |

_12 row(s)_

**Answer:** 直近12ヶ月では、解約件数・解約ARRともに**2026年3月**が最大で、**15件・5,761万円**でした。全12か月のうち**2026年11月は0件・0円**で、月ごとの振れ幅が大きく、件数が多い月でも解約ARRは必ずしも同じ比率では増えていません。

代表的な月次データは以下の通りです:
- **2025年12月**: **7件**、**4,597万円**
- **2026年3月**: **15件**、**5,761万円**
- **2026年6月**: **12件**、**2,935万円**
- **2026年8月**: **7件**、**3,932万円**
- **2026年11月**: **0件**、**0円**


## Q: MLモデルとルールベースの精度（AUC）を比較して

status: `COMPLETED`

**Generated SQL** (MLモデルとルールベースのAUC（精度指標）を比較したいというご要望です。):

```sql
SELECT
  CASE
    WHEN `metric` ILIKE '%rule%' OR `metric_group` ILIKE '%rule%' THEN 'ルールベース'
    WHEN `metric` ILIKE '%model%' OR `metric` ILIKE '%ml%' OR `metric_group` ILIKE '%model%' OR `metric_group` ILIKE '%ml%' THEN 'MLモデル'
    ELSE 'その他'
  END AS `モデル種別`,
  `metric` AS `metric`,
  `metric_group` AS `metric_group`,
  `value` AS `auc`
FROM `ytcy_azure_east2classic_stable`.`officepulse_churn`.`gold_model_metrics`
WHERE `value` IS NOT NULL
  AND `metric` IS NOT NULL
  AND (
    `metric` ILIKE '%auc%'
    OR (`metric_group` IS NOT NULL AND `metric_group` ILIKE '%auc%')
  )
  AND (
    `metric` ILIKE '%rule%'
    OR `metric` ILIKE '%model%'
    OR `metric` ILIKE '%ml%'
    OR (`metric_group` IS NOT NULL AND (`metric_group` ILIKE '%rule%' OR `metric_group` ILIKE '%model%' OR `metric_group` ILIKE '%ml%'))
  )
ORDER BY `モデル種別`, `metric`
```

| モデル種別 | metric | metric_group | auc |
|---|---|---|---|
| MLモデル | test_auc | model_eval | 0.8469456262360161 |
| MLモデル | test_pr_auc | model_eval | 0.6206886689894116 |
| ルールベース | rules_auc | model_eval | 0.7716020046266228 |
| ルールベース | rules_pr_auc | model_eval | 0.39298007785333255 |

_4 row(s)_

**Answer:** AUCの比較では、**MLモデルの方が高精度**です。通常のAUCは **MLモデル 0.8469**、**ルールベース 0.7716** で、PR-AUCも **MLモデル 0.6207**、**ルールベース 0.3930** と、今回の4件の指標ではいずれもMLモデルが上回っています。

