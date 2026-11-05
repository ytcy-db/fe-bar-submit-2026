"""Create (or update) the Genie space 'OfficePulse Churn Agent' over the governed gold/silver tables.

usage: python genie/create_genie_space.py --profile Azure-ytcy-east2 [--space-id <id to update>]
Writes the resulting space id to genie/space_id.txt.
"""
import argparse, json, subprocess, uuid

ap = argparse.ArgumentParser()
ap.add_argument("--profile", required=True)
ap.add_argument("--space-id")
ap.add_argument("--catalog", default="ytcy_azure_east2classic_stable")
ap.add_argument("--schema", default="officepulse_churn")
ap.add_argument("--warehouse", default="9c8fac7a0b250221")
a = ap.parse_args()
FQ = f"{a.catalog}.{a.schema}"

TABLES = ["gold_account_360", "gold_business_impact", "gold_churn_monthly", "gold_kpi_weekly", "gold_model_metrics",
          "silver_contracts", "silver_tickets", "silver_usage_weekly"]

INSTRUCTIONS = f"""あなたは CloudNest 社（SaaS「OfficePulse」: 出社検知センサー＋アプリ）のカスタマーサクセス向けデータアナリストです。日本語で回答してください。
- データの基準日（今日）は 2026-11-02（最新の利用週）。「今後90日」は 2026-11-02 から 90 日。
- 現在の解約リスクは gold_account_360 を使う。churn_probability = 次回の年次更新で解約（更新しない）確率（MLモデル officepulse_churn.churn_model@champion、0〜1）。risk_band は '高'(>=0.5) / '中'(>=0.25) / '低'。risk_score = churn_probability×100。
- arr_at_risk_jpy = churn_probability × arr_jpy（期待損失ARR）。金額は日本円(JPY)。百万円単位で示すと読みやすい。
- hidden_risk = MLは高リスクだが CSM が status='churn_risk' と手動フラグしていない顧客（見落とし）。csm_flagged = CSM が手動でフラグ済み。
- status: active / onboarding / churn_risk / churned / prospect。解約済みは end_date が NOT NULL。現役顧客は end_date IS NULL かつ status <> 'prospect'。
- 利用率（login_rate, attendance_detect_rate 等）は 0〜1 の比率。% 表示時は 100 を掛ける。gold_kpi_weekly の *_pct は既に %。
- top_drivers は SHAP による主要因の JSON 配列（label が日本語の要因名）。
- 解約検討の問い合わせは silver_tickets.is_cancellation_intent = true。
- テーブル結合キーは account_id（ACC-xxxx）。
- モデル精度・ビジネス効果は gold_model_metrics（metric, value）と gold_business_impact（kpi, value）。
"""

SAMPLES = [
    "CSMがまだフラグしていない高リスク顧客をARRの大きい順に10社教えて",
    "今後90日以内に更新日を迎える高リスク顧客と期待損失ARRの合計は？",
    "業界別の平均解約確率と期待損失ARRを教えて",
    "直近12ヶ月の月別解約件数と解約ARRの推移を見せて",
    "出社検知率が低い高リスク顧客の主要因は？",
    "MLモデルとルールベースの精度（AUC）を比較して",
]

BENCH = [
    ("CSMがまだフラグしていない高リスク顧客は何社？",
     f"SELECT count(*) AS hidden_risk_accounts FROM {FQ}.gold_account_360 WHERE hidden_risk = true"),
    ("今後90日以内に更新日を迎える高リスク顧客の期待損失ARR合計は？",
     f"SELECT round(sum(arr_at_risk_jpy)) AS arr_at_risk_jpy FROM {FQ}.gold_account_360 WHERE risk_band = '高' AND end_date IS NULL AND renewal_date BETWEEN DATE'2026-11-02' AND DATE'2026-11-02' + INTERVAL 90 DAYS"),
    ("直近12ヶ月の解約ARRの合計は？",
     f"SELECT sum(churned_arr_jpy) AS churned_arr_12m FROM {FQ}.gold_churn_monthly WHERE month >= DATE'2025-11-01' AND month < DATE'2026-11-01'"),
]

space = {
    "version": 2,
    "config": {"sample_questions": sorted([{"id": uuid.uuid4().hex, "question": [q]} for q in SAMPLES], key=lambda x: x["id"])},
    "data_sources": {"tables": sorted([{"identifier": f"{FQ}.{t}"} for t in TABLES], key=lambda x: x["identifier"])},
    "instructions": {"text_instructions": [{"id": uuid.uuid4().hex, "content": [INSTRUCTIONS]}]},
    "benchmarks": {"questions": [{"id": uuid.uuid4().hex, "question": [q], "answer": [{"format": "SQL", "content": [s]}]} for q, s in BENCH]},
}
body = {
    "title": "OfficePulse Churn Agent",
    "description": "解約予測（MLスコア・SHAP主要因）・利用状況・サポート・契約データに自然言語で質問できるCS向けGenieエージェント。",
    "warehouse_id": a.warehouse,
    "serialized_space": json.dumps(space, ensure_ascii=False),
}
cli = ["/opt/homebrew/bin/databricks", "api"]
if a.space_id:
    out = subprocess.run(cli + ["patch", f"/api/2.0/genie/spaces/{a.space_id}", "--json", json.dumps(body), "--profile", a.profile], capture_output=True, text=True)
else:
    out = subprocess.run(cli + ["post", "/api/2.0/genie/spaces", "--json", json.dumps(body), "--profile", a.profile], capture_output=True, text=True)
print(out.stdout[:600], out.stderr[:600])
sid = json.loads(out.stdout)["space_id"]
open("genie/space_id.txt", "w").write(sid + "\n")
print("space_id:", sid)
