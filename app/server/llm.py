"""GenAI retention advisor.

Calls the LLM through the Unity Catalog model service `officepulse_churn.churn_advisor_llm`
(Unity AI Gateway, OpenAI-compatible `/ai-gateway/mlflow/v1/chat/completions`), so usage is
governed, permissioned (EXECUTE grant to the app SP) and logged centrally.

The prompt is *grounded* on the ML model's output: churn probability, the top SHAP drivers and the
raw feature values — the LLM explains and plans, it does not score.
"""
import json
import urllib.request

from .config import get_host, get_token, LLM_MODEL_SERVICE


def _chat(system: str, user: str, max_tokens: int = 3000) -> str:
    body = {
        "model": LLM_MODEL_SERVICE,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        get_host().rstrip("/") + "/ai-gateway/mlflow/v1/chat/completions",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + get_token(), "Content-Type": "application/json"})
    # single call with a long timeout (no SDK auto-retry that would re-run a long generation)
    with urllib.request.urlopen(req, timeout=240) as r:
        resp = json.loads(r.read())
    content = resp["choices"][0]["message"]["content"]
    if isinstance(content, list):  # Claude via the gateway may return content blocks (reasoning + text)
        content = "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content or ""


def _parse_json(text: str) -> dict | None:
    text = text.strip()
    if "```" in text:
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def recommend_actions(account: dict, ml: dict, metrics: dict, tickets_summary: dict) -> dict:
    """Retention playbook grounded on the ML score and SHAP drivers. Returns JSON."""
    sys = (
        "あなたは B2B SaaS（出社検知センサー＋アプリ）のカスタマーサクセス責任者です。"
        "機械学習モデルが算出した『次回更新で解約する確率』と、その主要因（SHAP 寄与度）、"
        "利用データ・サポート状況をもとに、CSM が今週から実行できるリテンション施策を立案してください。"
        "スコアの再計算はせず、モデルの主要因を根拠として必ず引用すること。更新日までの日数を考慮して優先度を決めること。"
        "出力は次の JSON のみ（前置き不要）:\n"
        '{"risk_summary": "リスクの要約(2-3文。確率と主要因に言及)", '
        '"key_drivers": ["主要因1", "主要因2", "主要因3"], '
        '"recommended_actions": [{"action":"具体的なアクション","priority":"高|中|低","owner":"CSM|サポート|営業|エンジニア","due_in_days":7,"rationale":"どの主要因に効くか"}], '
        '"talk_track": "顧客との会話で使える一言", '
        '"success_metric": "施策の効果を測る指標と目標値"}'
    )
    as_of = "2026-11-02"  # latest complete usage week in the data
    renewal = account.get("renewal_date")
    days_left = None
    if renewal:
        from datetime import date
        days_left = (date.fromisoformat(str(renewal)[:10]) - date.fromisoformat(as_of)).days
    ctx = {
        "基準日": as_of,
        "次回更新日までの日数": days_left,
        "顧客": {k: account.get(k) for k in ["company_name", "industry", "plan", "status", "seats", "arr_jpy",
                                            "used_services", "loaned_devices", "renewal_date", "auto_renew", "csm_owner"]},
        "MLモデル": ml,
        "直近利用指標": metrics,
        "サポート状況": tickets_summary,
    }
    user = "以下のデータに基づき JSON を生成してください。\n" + json.dumps(ctx, ensure_ascii=False, indent=2, default=str)
    text = _chat(sys, user)
    parsed = _parse_json(text)
    if parsed:
        return parsed
    return {"risk_summary": text, "key_drivers": [], "recommended_actions": [], "talk_track": "", "success_metric": ""}
