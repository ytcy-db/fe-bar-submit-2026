# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Generate synthetic raw source data (CRM / GA4 / Zendesk)
# MAGIC
# MAGIC **Scenario.** A Japanese B2B SaaS vendor sells a workplace "attendance detection" product
# MAGIC (loaned sensors + mobile app) on annual contracts. In this repo the vendor and product are
# MAGIC fictionalised as **CloudNest / OfficePulse**; all companies, people and numbers are synthetic.
# MAGIC
# MAGIC This notebook lands *raw* files exactly as the three source systems would export them, into a
# MAGIC Unity Catalog Volume. Nothing here is cleaned — that is the job of the Lakeflow pipeline (`pipelines/`).
# MAGIC
# MAGIC | Source system | Raw format | Volume path |
# MAGIC |---|---|---|
# MAGIC | CRM (accounts, contacts, contracts) | CSV | `raw/crm/accounts/`, `raw/crm/contracts/` |
# MAGIC | GA4 product analytics (weekly tenant report) | JSON lines, one file per week | `raw/ga4/` |
# MAGIC | Zendesk (tickets with nested comments) | JSON lines, one file per month | `raw/zendesk/` |
# MAGIC
# MAGIC The generator has a latent "account health" process: accounts that will churn show a gradual
# MAGIC usage decline 8–22 weeks before their renewal date, more (and angrier) support tickets, and only
# MAGIC ~55% of them ever send an explicit cancellation ticket. Some healthy accounts have temporary dips
# MAGIC (false alarms for simple rules), and ~25% of churners are "silent" (shallow decline).
# MAGIC Raw data also contains realistic defects (duplicates, null keys, impossible values) so the
# MAGIC pipeline's data-quality expectations have something to catch.

# COMMAND ----------

import csv
import datetime as dt
import json
import math
import os
import random

try:
    dbutils  # noqa: F821  (defined on Databricks)
    dbutils.widgets.text("catalog", "ytcy_azure_east2classic_stable")
    dbutils.widgets.text("schema", "officepulse_churn")
    CATALOG = dbutils.widgets.get("catalog")
    SCHEMA = dbutils.widgets.get("schema")
    ON_DATABRICKS = True
except NameError:
    CATALOG, SCHEMA, ON_DATABRICKS = "local", "local", False

SEED = 20261102
TODAY = dt.date(2026, 11, 2)          # Monday of the latest complete week
N_WEEKS = 78                           # 18 months of weekly GA4 history
W0 = TODAY - dt.timedelta(weeks=N_WEEKS - 1)
N_GENERATED = 580                      # + 20 hand-written "hero" accounts = 600
N_PROSPECTS = 12

# COMMAND ----------

if ON_DATABRICKS:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")  # noqa: F821
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw")  # noqa: F821
    # UC column-mask function used by the Lakeflow pipeline on contact PII (silver_accounts)
    spark.sql(f"""CREATE OR REPLACE FUNCTION {CATALOG}.{SCHEMA}.mask_contact(v STRING) RETURNS STRING
        COMMENT 'Masks customer contact PII unless the caller is in officepulse-cs-leads'
        RETURN CASE WHEN is_account_group_member('officepulse-cs-leads') THEN v
                    WHEN v IS NULL THEN NULL ELSE concat(substr(v, 1, 2), '****') END""")  # noqa: F821
    RAW = f"/Volumes/{CATALOG}/{SCHEMA}/raw"
else:
    RAW = os.environ.get("RAW_DIR", "/tmp/officepulse_churn_raw")
print("raw landing zone:", RAW)

# COMMAND ----------

# MAGIC %md ## Master data (fictional)

# COMMAND ----------

rng = random.Random(SEED)

INDUSTRY_WORDS = {
    "商事": "商社・卸", "製作所": "製造", "工業": "製造", "電機": "製造", "システムズ": "IT・Web",
    "テクノロジーズ": "IT・Web", "フーズ": "外食", "メディカル": "医療・福祉", "ロジスティクス": "物流",
    "建設": "建設", "エナジー": "エネルギー", "不動産": "不動産", "証券": "金融", "保険": "金融",
    "リテール": "小売", "ホテルズ": "外食", "教育サービス": "教育", "人材開発": "人材",
    "コンサルティング": "コンサル", "ホールディングス": "商社・卸",
}
PREFIXES = ["あおば", "いずみ", "ひので", "あさひ", "やまと", "東邦", "中央", "北斗", "南海", "西日本",
            "東日本", "光", "新星", "未来", "青葉", "若葉", "富士", "瑞穂", "千代田", "丸の内", "銀河",
            "星野", "葵", "楓", "高砂", "白鷺", "常盤", "武蔵", "相模", "播磨", "筑紫", "奥州", "信濃",
            "飛鳥", "日向", "黎明", "紺碧", "翠嶺", "朱雀", "玄武"]
PLANS = ["Starter", "Standard", "Premium", "Enterprise"]
PLAN_W = [0.33, 0.35, 0.21, 0.11]
SEATS = {"Starter": (20, 60), "Standard": (80, 250), "Premium": (250, 700), "Enterprise": (800, 3000)}
PRICE_PER_SEAT = {"Starter": 18000, "Standard": 15000, "Premium": 13000, "Enterprise": 11000}
CSMS = ["佐藤 美咲", "田中 健一", "鈴木 彩子", "高橋 大輔", "伊藤 直樹", "渡部 由香", "松本 亮"]
REGIONS = ["東京", "大阪", "名古屋", "福岡", "札幌", "横浜", "仙台", "広島"]
DEVICE_MODELS = ["OfficePulse Sensor G2", "OfficePulse Sensor G3", "OfficePulse Gateway", "OfficePulse Beacon Lite"]
SERVICES = ["出社検知", "座席管理", "入退室ログ", "利用分析ダッシュボード", "Slack連携", "API連携", "モバイルアプリ", "SSO/SAML"]
CHURN_REASONS = ["価格が高い", "他社ツールへ移行", "利用が定着しなかった", "社内体制変更",
                 "オフィス縮小・リモート移行", "サポート対応への不満", "機能不足", "予算削減"]
FAMILY = ["山田", "佐々木", "井上", "木村", "林", "清水", "山口", "森", "池田", "橋本", "石川", "前田"]
GIVEN = ["翔太", "陽菜", "大輝", "結衣", "拓海", "美月", "健太", "彩花", "直人", "真央"]

# Hero accounts keep the names used by the existing demo storyline.
# kind: healthy | dip | churned_past | future_churn_flagged | future_churn_hidden | future_churn_silent | onboarding | prospect
HEROES = [
    ("みなと商事株式会社", "商社・卸", "Enterprise", "healthy", 28),
    ("北山製造ホールディングス", "製造", "Enterprise", "healthy", 34),
    ("さくら医療グループ", "医療・福祉", "Enterprise", "healthy", 22),
    ("テックブリッジ株式会社", "IT・Web", "Premium", "future_churn_hidden", 16),
    ("フロンティア物流株式会社", "物流", "Standard", "healthy", 19),
    ("東海リテールシステムズ", "小売", "Standard", "dip", 14),
    ("グリーンエナジー株式会社", "エネルギー", "Premium", "future_churn_flagged", 26),
    ("関西フードサービス株式会社", "外食", "Standard", "future_churn_flagged", 18),
    ("大和建設株式会社", "建設", "Premium", "future_churn_silent", 21),
    ("スカイITソリューションズ", "IT・Web", "Enterprise", "healthy", 30),
    ("ひかり教育サービス", "教育", "Standard", "onboarding", 2),
    ("ノースフィナンシャル株式会社", "金融", "Enterprise", "healthy", 24),
    ("まるみ食品工業", "製造", "Standard", "future_churn_flagged", 20),
    ("アクティブ人材サービス", "人材", "Premium", "healthy", 17),
    ("湘南リゾートホテルズ", "外食", "Standard", "onboarding", 1),
    ("セントラル商店", "小売", "Starter", "prospect", 0),
    ("いろは印刷株式会社", "製造", "Starter", "prospect", 0),
    ("東雲メディカルクリニック", "医療・福祉", "Standard", "healthy", 12),
    ("ゆにおん運輸株式会社", "物流", "Standard", "churned_past", 30),
    ("みらいエデュケーション", "教育", "Starter", "churned_past", 22),
]


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def monday(d):
    return d - dt.timedelta(days=d.weekday())

# COMMAND ----------

# MAGIC %md ## Accounts, contracts and the latent churn process

# COMMAND ----------


def make_accounts():
    accts = []
    used = set()
    # heroes
    for i, (name, ind, plan, kind, months) in enumerate(HEROES, start=1):
        used.add(name)
        accts.append(dict(account_id=f"ACC-{1000 + i}", company_name=name, industry=ind, plan=plan,
                          kind=kind, start=TODAY - dt.timedelta(days=int(months * 30.4)) if months else None))
    # generated
    i = len(accts)
    while len(accts) < 20 + N_GENERATED + N_PROSPECTS:
        word = rng.choice(list(INDUSTRY_WORDS))
        name = f"{rng.choice(PREFIXES)}{word}株式会社" if rng.random() < 0.6 else f"株式会社{rng.choice(PREFIXES)}{word}"
        if name in used:
            continue
        used.add(name)
        i += 1
        is_prospect = len(accts) >= 20 + N_GENERATED
        plan = rng.choices(PLANS, PLAN_W)[0]
        # start dates: 2022-06 .. 2026-10, recent cohorts slightly larger (growing company)
        days_back = int((1 - rng.random() ** 1.3) * (TODAY - dt.date(2022, 6, 1)).days)
        accts.append(dict(account_id=f"ACC-{1000 + i}", company_name=name, industry=INDUSTRY_WORDS[word],
                          plan=plan, kind="prospect" if is_prospect else "generated",
                          start=None if is_prospect else TODAY - dt.timedelta(days=max(14, days_back))))
    return accts


def assign_lifecycle(a):
    """Decide health, support quality, renewal dates and (possible) churn date."""
    plan_bonus = {"Starter": -0.35, "Standard": 0.0, "Premium": 0.2, "Enterprise": 0.45}[a["plan"]]
    ind_bonus = {"外食": -0.3, "小売": -0.2, "IT・Web": 0.1, "金融": 0.15}.get(a["industry"], 0.0)
    a["z"] = rng.gauss(0, 1) + plan_bonus + ind_bonus
    a["slow_support"] = rng.random() < 0.18
    lo, hi = SEATS[a["plan"]]
    a["seats"] = rng.randint(lo, hi)
    a["arr_jpy"] = int(round(a["seats"] * PRICE_PER_SEAT[a["plan"]] * rng.uniform(0.9, 1.15), -4))
    a["churn_date"] = None
    a["decline"] = None   # (start_date, end_date, depth)
    a["dips"] = []
    a["cancel_ticket_date"] = None
    a["false_cancel_date"] = None
    if a["kind"] == "prospect":
        return a

    kind = a["kind"]
    start = a["start"]
    renewals = [add_years(start, k) for k in range(1, 8)]
    a["renewals"] = renewals

    def set_churn(R, depth=None, silent=False, cancel=None, decline_weeks=None):
        a["churn_date"] = R
        D = decline_weeks or rng.randint(8, 22)
        depth = depth if depth is not None else (rng.uniform(0.0, 0.12) if silent else rng.uniform(0.22, 0.55))
        a["decline"] = (R - dt.timedelta(weeks=D), R, depth)
        if cancel is None:
            cancel = (not silent) and rng.random() < 0.55
        if cancel:
            a["cancel_ticket_date"] = R - dt.timedelta(days=rng.randint(14, 49))

    if kind == "generated":
        for R in renewals:
            if R < W0 + dt.timedelta(weeks=10) or R > TODAY + dt.timedelta(weeks=26):
                continue
            p = sigmoid(-1.85 - 1.35 * a["z"] + 0.85 * a["slow_support"])
            if rng.random() < p:
                set_churn(R, silent=rng.random() < 0.4)
                break
            if rng.random() < 0.22:
                # "declined but renewed": usage sags into the renewal, then recovers (save / downgrade)
                a["dips"].append((R - dt.timedelta(weeks=rng.randint(8, 16)), R + dt.timedelta(weeks=rng.randint(3, 8)),
                                  rng.uniform(0.2, 0.5)))
        if a["churn_date"] is None and rng.random() < 0.35:
            ds = W0 + dt.timedelta(weeks=rng.randint(4, N_WEEKS - 4))
            a["dips"].append((ds, ds + dt.timedelta(weeks=rng.randint(6, 12)), rng.uniform(0.2, 0.4)))
        if a["churn_date"] is None and rng.random() < 0.03:
            a["false_cancel_date"] = W0 + dt.timedelta(days=rng.randint(30, N_WEEKS * 7 - 7))
    elif kind == "churned_past":
        R = TODAY - dt.timedelta(days=rng.randint(45, 120))
        a["start"] = add_years(R, -2)
        set_churn(R, depth=0.55, cancel=True)
    elif kind == "future_churn_flagged":
        R = TODAY + dt.timedelta(weeks=rng.randint(3, 8))
        a["start"] = add_years(R, -2)
        set_churn(R, depth=0.5, cancel=False, decline_weeks=rng.randint(14, 18))
        a["cancel_ticket_date"] = TODAY - dt.timedelta(days=rng.randint(5, 20))
    elif kind == "future_churn_hidden":
        R = TODAY + dt.timedelta(weeks=6)
        a["start"] = add_years(R, -1)
        set_churn(R, depth=0.5, cancel=False, decline_weeks=17)
    elif kind == "future_churn_silent":
        R = TODAY + dt.timedelta(weeks=10)
        a["start"] = add_years(R, -2)
        set_churn(R, depth=0.32, cancel=False, decline_weeks=20)
    elif kind == "dip":
        a["z"] = max(a["z"], 0.6)
        a["dips"].append((TODAY - dt.timedelta(weeks=9), TODAY + dt.timedelta(weeks=1), 0.3))
    elif kind == "healthy":
        a["z"] = max(a["z"], 0.8)
        a["slow_support"] = False
    elif kind == "onboarding":
        a["z"] = max(a["z"], 0.3)
    a["renewals"] = [add_years(a["start"], k) for k in range(1, 8)]
    return a


accounts = [assign_lifecycle(a) for a in make_accounts()]


def crm_status(a):
    if a["kind"] == "prospect":
        return "prospect"
    if a["churn_date"] and a["churn_date"] <= TODAY:
        return "churned"
    if (TODAY - a["start"]).days <= 90:
        return "onboarding"
    # CSMs only flag risk once the customer *says* so (cancellation ticket) — the status quo problem
    if a["cancel_ticket_date"] and a["cancel_ticket_date"] <= TODAY:
        return "churn_risk"
    if rng.random() < 0.02:
        return "churn_risk"
    return "active"


for a in accounts:
    a["status"] = crm_status(a)
    a["csm_owner"] = rng.choice(CSMS)
    a["region"] = rng.choice(REGIONS)

print({s: sum(1 for a in accounts if a["status"] == s) for s in ["active", "onboarding", "churn_risk", "churned", "prospect"]})

# COMMAND ----------

# MAGIC %md ## Weekly product usage (GA4-style tenant report)

# COMMAND ----------


def health_factor(a, week):
    f = 1.0
    if a["decline"]:
        ds, de, depth = a["decline"]
        if ds <= week <= de:
            prog = (week - ds).days / max(1, (de - ds).days)
            f *= 1 - depth * prog ** 1.3
    for ds, de, depth in a["dips"]:
        if ds <= week <= de:
            mid = (week - ds).days / max(1, (de - ds).days)
            f *= 1 - depth * math.sin(math.pi * mid)
    return f


def decline_progress(a, week):
    if a["decline"]:
        ds, de, _ = a["decline"]
        if ds <= week <= de:
            return (week - ds).days / max(1, (de - ds).days)
    return 0.0


def ga4_rows():
    out = []
    for a in accounts:
        if a["kind"] == "prospect":
            continue
        z = a["z"] + rng.gauss(0, 0.6)  # observed level only loosely reflects true health
        base = dict(login=0.72 + 0.07 * z, signup=0.80 + 0.06 * z, detect=0.80 + 0.06 * z,
                    install=0.86 + 0.04 * z, config=0.88 + 0.05 * z)
        devices_total = max(2, a["seats"] // 25)
        for k in range(N_WEEKS):
            week = W0 + dt.timedelta(weeks=k)
            if week < monday(a["start"]):
                continue
            if a["churn_date"] and week >= a["churn_date"]:
                break
            weeks_live = (week - monday(a["start"])).days // 7
            ramp = min(1.0, 0.35 + 0.065 * weeks_live)
            hf = health_factor(a, week)
            # sensor problems hit attendance detection harder than logins during decline
            det_hf = hf - 0.1 * decline_progress(a, week)

            season = 0.85 if (week.month == 8 and 10 <= week.day <= 20) or (week.month == 1 and week.day <= 7) or (week.month == 12 and week.day >= 26) else 1.0

            def r(x, extra=1.0, ramp_w=1.0):
                v = x * (ramp ** ramp_w) * extra * season + rng.gauss(0, 0.045)
                return min(0.99, max(0.02, v))

            login = r(base["login"], hf)
            signup = r(base["signup"], 0.5 + 0.5 * hf, ramp_w=0.6)
            detect = r(base["detect"], det_hf)
            install = r(base["install"], 0.6 + 0.4 * hf, ramp_w=0.8)
            config = r(base["config"], 0.55 + 0.45 * hf, ramp_w=0.7)
            seats = a["seats"]
            login_users = int(round(seats * login))
            expected = seats * 5 // 2   # 5 workdays x 50% office ratio
            row = {
                "report_week": week.isoformat(),
                "property_id": "GA4-OFFICEPULSE-PROD",
                "tenant_id": a["account_id"].lower(),
                "dimensions": {"plan": a["plan"], "app_version": rng.choice(["5.2.1", "5.3.0", "5.3.2"])},
                "metrics": {
                    "licensed_seats": seats,
                    "active_users": login_users,
                    "registered_users": int(round(seats * signup)),
                    "app_installs": int(round(seats * install)),
                    "attendance_detect_events": int(round(expected * detect)),
                    "expected_detect_events": expected,
                    "devices_total": devices_total,
                    "devices_config_ok": int(round(devices_total * config)),
                    "sessions": int(login_users * rng.uniform(2.0, 5.0)),
                    "avg_session_sec": round(rng.uniform(210, 1080) * (0.7 + 0.3 * hf), 1),
                },
                "exported_at": (week + dt.timedelta(days=7, hours=3)).isoformat() + "T03:00:00Z",
            }
            out.append(row)
    # --- realistic defects for the DQ expectations ---
    for row in rng.sample(out, k=len(out) // 200):            # 0.5% duplicates (re-exports)
        out.append(json.loads(json.dumps(row)))
    for row in rng.sample(out, k=len(out) // 400):            # 0.25% missing tenant
        row["tenant_id"] = None
    for row in rng.sample(out, k=len(out) // 500):            # 0.2% impossible counts
        row["metrics"]["active_users"] = row["metrics"]["licensed_seats"] * 3
    return out


ga4 = ga4_rows()
print("ga4 rows:", len(ga4))

# COMMAND ----------

# MAGIC %md ## Support tickets with nested comments (Zendesk-style)

# COMMAND ----------

SUBJECTS = {
    # subject: (category, default priority, weight_healthy, weight_declining)
    "座席管理の使い方がわからない": ("使い方", "low", 6, 2),
    "CSVエクスポートの項目を増やしたい": ("要望", "low", 5, 1),
    "追加ライセンスを購入したい": ("営業", "normal", 4, 0.3),
    "SSO 設定の手順を教えてほしい": ("設定", "normal", 4, 1),
    "Slack通知が届かない": ("設定", "normal", 3, 3),
    "請求金額について確認したい": ("請求", "normal", 2, 4),
    "出社検知が反映されない": ("技術", "high", 2, 7),
    "センサーがオフラインになる": ("技術", "urgent", 1.5, 6),
    "管理画面にログインできない": ("アカウント", "high", 1.5, 3),
    "モバイルアプリが起動しない": ("技術", "high", 1.5, 4),
    "ダッシュボードの数値がおかしい": ("技術", "high", 1, 4),
    "APIのレスポンスが遅い": ("技術", "high", 1, 3),
    "他社ツールとの比較資料がほしい": ("営業", "normal", 0.3, 3),
    "利用人数を減らしたい": ("請求", "normal", 0.3, 3),
    "端末の返却方法について": ("その他", "low", 0.5, 2),
}
CANCEL_SUBJECTS = ["解約を検討している", "契約更新を見送りたい"]
AGENTS = ["山本 拓也", "中村 玲奈", "小林 翔", "加藤 さゆり", "渡辺 健", "斎藤 光"]
CUSTOMER_LINES = {
    "技術": ["現場から「出社が記録されていない」と苦情が来ています。", "昨日から一部のフロアで検知が止まっています。至急確認してください。"],
    "請求": ["今期の請求額が想定より高いので内訳を教えてください。", "利用人数に対して費用が見合っているか社内で議論になっています。"],
    "営業": ["来期の予算検討のため、プラン比較の資料をいただけますか。"],
    "解約": ["社内でツールの見直しを行っており、次回更新は見送る方向です。", "利用が定着せず、更新するか検討しています。"],
}


def make_tickets():
    tickets = []
    tid = 10000
    for a in accounts:
        if a["kind"] == "prospect":
            continue
        lam0 = 0.08 * (a["seats"] / 100) ** 0.4
        frm_mult = 2.6 if a["slow_support"] else 1.0
        org = {"id": 360000 + int(a["account_id"][4:]), "external_id": a["account_id"], "name": a["company_name"]}
        scheduled = []
        if a["cancel_ticket_date"]:
            scheduled.append((a["cancel_ticket_date"], rng.choice(CANCEL_SUBJECTS), True))
        if a["false_cancel_date"]:
            scheduled.append((a["false_cancel_date"], "解約手続きの方法を知りたい", True))
        for k in range(N_WEEKS):
            week = W0 + dt.timedelta(weeks=k)
            if week < monday(a["start"]) or (a["churn_date"] and week >= a["churn_date"]):
                continue
            prog = decline_progress(a, week)
            dip = any(ds <= week <= de for ds, de, _ in a["dips"])
            lam = lam0 * (1 + 2.5 * prog) * (1.8 if dip else 1.0)
            n = sum(1 for _ in range(6) if rng.random() < lam / 6 * 1.0) if lam < 6 else int(lam)
            for _ in range(n):
                w_mix = [(s, v[2] * (1 - prog) + v[3] * prog) for s, v in SUBJECTS.items()]
                subj = rng.choices([s for s, _ in w_mix], [w for _, w in w_mix])[0]
                scheduled.append((week + dt.timedelta(days=rng.randint(0, 4)), subj, False))
        for created_day, subj, is_cancel in scheduled:
            if created_day > TODAY or (a["churn_date"] and created_day >= a["churn_date"]):
                continue
            tid += 1
            prog = decline_progress(a, created_day)
            if is_cancel:
                cat, pri = "解約", "urgent"
            else:
                cat, pri, _, _ = SUBJECTS[subj]
                if prog > 0.3 and rng.random() < 0.4:
                    pri = rng.choice(["high", "urgent"])
            created = dt.datetime.combine(created_day, dt.time(rng.randint(8, 19), rng.randint(0, 59)))
            frm = int(rng.lognormvariate(math.log(55), 0.8) * frm_mult * (1 + 0.8 * prog))
            age_days = (TODAY - created_day).days
            if age_days > 21:
                status = rng.choices(["solved", "closed", "pending"], [55, 40, 5])[0]
            else:
                status = rng.choices(["new", "open", "pending", "solved"], [3, 4, 2, 3])[0]
            resolved = status in ("solved", "closed")
            res_min = int(rng.lognormvariate(math.log(900), 0.9) * (1 + prog)) if resolved else None
            csat = None
            if resolved and rng.random() < 0.7:
                mood = 0.9 * prog + (0.6 if a["slow_support"] else 0) + (0.8 if is_cancel else 0) - 0.25 * a["z"]
                csat = max(1, min(5, int(round(rng.gauss(4.3 - 2.2 * mood, 0.8)))))
            agent = rng.choice(AGENTS)
            comments = []
            t = created
            first_line = rng.choice(CUSTOMER_LINES.get(cat, [f"{subj}について確認させてください。"]))
            comments.append({"id": tid * 10, "author_role": "end-user", "author_name": f"{a['company_name']} 担当者",
                             "created_at": t.isoformat() + "+09:00", "body": first_line, "public": True})
            t = t + dt.timedelta(minutes=frm)
            for c in range(rng.randint(1, 4)):
                role = "agent" if c % 2 == 0 else "end-user"
                body = ("ご連絡ありがとうございます。状況を確認し、手順をご案内します。" if role == "agent"
                        else "ご案内の手順を試しましたが、まだ解決していません。")
                comments.append({"id": tid * 10 + c + 1, "author_role": role,
                                 "author_name": agent if role == "agent" else f"{a['company_name']} 担当者",
                                 "created_at": t.isoformat() + "+09:00", "body": body, "public": True})
                t = t + dt.timedelta(hours=rng.randint(1, 30))
            updated = min(t, dt.datetime.combine(TODAY, dt.time(18, 0)))
            tickets.append({
                "id": tid,
                "subject": subj,
                "description": f"{a['company_name']} より「{subj}」に関する問い合わせ。",
                "status": status,
                "priority": pri,
                "type": "incident" if cat == "技術" else "question",
                "tags": [cat],
                "via": {"channel": rng.choice(["email", "chat", "phone", "web_form"])},
                "organization": org,
                "assignee": {"name": agent},
                "created_at": created.isoformat() + "+09:00",
                "updated_at": updated.isoformat() + "+09:00",
                "metric_set": {"reply_time_in_minutes": {"calendar": frm},
                               "full_resolution_time_in_minutes": {"calendar": res_min}},
                "satisfaction_rating": {"score": csat} if csat else None,
                "comments": comments,
            })
    return tickets


tickets = make_tickets()
print("tickets:", len(tickets), " comments:", sum(len(t["comments"]) for t in tickets))

# COMMAND ----------

# MAGIC %md ## CRM exports (accounts with contact PII, contracts)

# COMMAND ----------


def crm_rows():
    acc_rows, con_rows = [], []
    for a in accounts:
        cname = f"{rng.choice(FAMILY)} {rng.choice(GIVEN)}"
        acc_rows.append({
            "account_id": a["account_id"], "company_name": a["company_name"], "industry": a["industry"],
            "plan": a["plan"], "status": a["status"], "csm_owner": a["csm_owner"],
            "seats": a["seats"], "arr_jpy": a["arr_jpy"], "region": a["region"],
            "created_at": (a["start"] or TODAY - dt.timedelta(days=rng.randint(5, 60))).isoformat(),
            "contact_name": cname,
            "contact_email": f"it-admin{a['account_id'][4:]}@example-{a['account_id'][4:]}.co.jp",
            "contact_phone": f"03-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}",
            "exported_at": TODAY.isoformat(),
        })
        if a["kind"] == "prospect":
            continue
        churned = a["churn_date"] is not None and a["churn_date"] <= TODAY
        next_renewal = next((r for r in a["renewals"] if r > TODAY), None)
        n_dev = max(1, a["seats"] // 60)
        devices = rng.sample(DEVICE_MODELS, k=rng.randint(1, 3))
        n_srv = {"Starter": 2, "Standard": 4, "Premium": 6, "Enterprise": 8}[a["plan"]]
        will_churn = a["churn_date"] is not None
        auto_renew = (rng.random() > 0.6) if will_churn else (rng.random() > 0.12)
        if a["kind"] == "future_churn_hidden":
            auto_renew = False
        con_rows.append({
            "contract_id": f"CT-{20260000 + int(a['account_id'][4:])}", "account_id": a["account_id"],
            "plan": a["plan"], "start_date": a["start"].isoformat(),
            "end_date": a["churn_date"].isoformat() if churned else "",
            "renewal_date": (a["churn_date"] if churned else next_renewal).isoformat(),
            "term_months": 12,
            "loaned_devices": ", ".join(f"{d}×{rng.randint(2, max(2, n_dev))}" for d in devices),
            "used_services": ", ".join(rng.sample(SERVICES, n_srv)),
            "churn_reason": rng.choice(CHURN_REASONS) if churned else "",
            "mrr_jpy": a["arr_jpy"] // 12,
            "auto_renew": "Y" if auto_renew else "N",
        })
    # a re-export with a status change: the pipeline keeps the latest row per account
    for r in rng.sample(acc_rows, 15):
        dup = dict(r)
        dup["exported_at"] = (TODAY - dt.timedelta(days=7)).isoformat()
        acc_rows.append(dup)
    return acc_rows, con_rows


acc_rows, con_rows = crm_rows()
print("crm accounts rows:", len(acc_rows), " contracts:", len(con_rows))

# COMMAND ----------

# MAGIC %md ## Write raw files to the landing zone

# COMMAND ----------


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


write_csv(f"{RAW}/crm/accounts/accounts_{TODAY:%Y%m%d}.csv", acc_rows)
write_csv(f"{RAW}/crm/contracts/contracts_{TODAY:%Y%m%d}.csv", con_rows)

by_week = {}
for r in ga4:
    by_week.setdefault(r["report_week"], []).append(r)
for wk, rows in by_week.items():
    write_jsonl(f"{RAW}/ga4/ga4_tenant_weekly_{wk}.json", rows)

by_month = {}
for t in tickets:
    by_month.setdefault(t["created_at"][:7], []).append(t)
for m, rows in by_month.items():
    write_jsonl(f"{RAW}/zendesk/tickets_{m}.json", rows)

summary = {
    "accounts": len(accounts),
    "crm_status": {s: sum(1 for a in accounts if a["status"] == s) for s in ["active", "onboarding", "churn_risk", "churned", "prospect"]},
    "churned_in_window": sum(1 for a in accounts if a["churn_date"] and W0 <= a["churn_date"] <= TODAY),
    "future_churners_hidden_in_data": sum(1 for a in accounts if a["churn_date"] and a["churn_date"] > TODAY),
    "ga4_rows": len(ga4), "ga4_files": len(by_week),
    "zendesk_tickets": len(tickets), "zendesk_files": len(by_month),
    "crm_account_rows": len(acc_rows), "contracts": len(con_rows),
    "total_arr_jpy": sum(a["arr_jpy"] for a in accounts if a["kind"] != "prospect" and not (a["churn_date"] and a["churn_date"] <= TODAY)),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))

# COMMAND ----------

if ON_DATABRICKS:
    display(dbutils.fs.ls(RAW))  # noqa: F821

# COMMAND ----------

if ON_DATABRICKS:
    dbutils.notebook.exit(json.dumps(summary, ensure_ascii=False))  # noqa: F821
