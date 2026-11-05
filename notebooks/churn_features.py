"""Shared churn feature engineering (used by training, batch scoring and documented for the app).

Input is the Lakeflow gold table `gold_account_weekly` (one row per account-week) plus
`silver_contracts` / `silver_accounts`. Output is one row per (account_id, snapshot_week)
with trailing-window features computed only from data at or before the snapshot week
(no look-ahead), and optionally the label "does NOT renew at the next renewal date".

Why this framing: contracts are annual, so churn can only happen at a renewal. The actionable
question for Customer Success is "which accounts up for renewal in the next 30-180 days will not
renew?" — `in_renewal_window` marks those snapshots and is what the model is trained/evaluated on.
"""
import numpy as np
import pandas as pd

PLAN_ORD = {"Starter": 0, "Standard": 1, "Premium": 2, "Enterprise": 3}

FEATURES = [
    "login_rate_4w", "signup_rate_4w", "attendance_detect_rate_4w", "install_rate_4w", "app_config_ok_rate_4w",
    "login_trend_8w", "detect_trend_8w", "config_trend_8w",
    "avg_session_min_4w", "sessions_per_user_4w",
    "tickets_12w", "urgent_tickets_12w", "technical_tickets_12w", "cancellation_tickets_12w",
    "slow_first_responses_12w", "low_csat_tickets_12w", "avg_csat_12w", "open_tickets",
    "auto_renew", "plan_ordinal",
]
# Deliberately excluded (computed, but not model inputs):
#  * seats / ARR: with ~100 renewal events they let the model memorise individual accounts
#    (identity leakage); out-of-time AUC dropped when included.
#  * days_to_renewal / tenure_months: not actionable for a CSM and partly an artefact of the observation
#    window. Renewal timing is used *outside* the model to prioritise (30-180 day action window).

# Japanese labels shown to CSMs in the app (feature -> label)
FEATURE_LABELS_JA = {
    "login_rate_4w": "ログイン率(直近4週)", "signup_rate_4w": "登録率(直近4週)",
    "attendance_detect_rate_4w": "出社検知率(直近4週)", "install_rate_4w": "インストール率(直近4週)",
    "app_config_ok_rate_4w": "アプリ設定良好率(直近4週)",
    "login_trend_8w": "ログイン率の変化(8週前比)", "detect_trend_8w": "出社検知率の変化(8週前比)",
    "config_trend_8w": "設定良好率の変化(8週前比)",
    "avg_session_min_4w": "平均セッション時間", "sessions_per_user_4w": "1人あたりセッション数",
    "tickets_12w": "問い合わせ件数(12週)", "urgent_tickets_12w": "高優先度の問い合わせ(12週)",
    "technical_tickets_12w": "技術系の問い合わせ(12週)", "cancellation_tickets_12w": "解約検討の問い合わせ(12週)",
    "slow_first_responses_12w": "一次応答8時間超(12週)", "low_csat_tickets_12w": "低CSAT(1-2)の件数(12週)",
    "avg_csat_12w": "平均CSAT(12週)", "open_tickets": "未解決チケット数",
    "days_to_renewal": "更新日までの日数", "auto_renew": "自動更新", "tenure_months": "契約継続月数",
    "seats": "契約席数", "log_arr": "ARR(対数)", "plan_ordinal": "プラン",
}


def _renewal_after(start: pd.Series, snap: pd.Series) -> pd.Series:
    """Next anniversary of `start` strictly after `snap` (annual contracts)."""
    years = (snap.dt.year - start.dt.year).clip(lower=0)
    out = []
    for s, sn, y in zip(start, snap, years):
        r = s + pd.DateOffset(years=int(y))
        while r <= sn:
            r = r + pd.DateOffset(years=1)
        out.append(r)
    return pd.Series(out, index=snap.index)


def build_features(weekly: pd.DataFrame, contracts: pd.DataFrame, accounts: pd.DataFrame,
                   snapshot_weeks=None, with_label: bool = True) -> pd.DataFrame:
    w = weekly.copy()
    w["week_start"] = pd.to_datetime(w["week_start"])
    w = w.sort_values(["account_id", "week_start"]).reset_index(drop=True)
    g = w.groupby("account_id", group_keys=False)

    def roll_mean(col, n):
        return g[col].transform(lambda s: s.rolling(n, min_periods=1).mean())

    def roll_sum(col, n):
        return g[col].transform(lambda s: s.rolling(n, min_periods=1).sum())

    for src, dst in [("login_rate", "login_rate_4w"), ("signup_rate", "signup_rate_4w"),
                     ("attendance_detect_rate", "attendance_detect_rate_4w"), ("install_rate", "install_rate_4w"),
                     ("app_config_ok_rate", "app_config_ok_rate_4w"), ("avg_session_min", "avg_session_min_4w")]:
        w[dst] = roll_mean(src, 4)
    for src, dst in [("login_rate", "login_trend_8w"), ("attendance_detect_rate", "detect_trend_8w"),
                     ("app_config_ok_rate", "config_trend_8w")]:
        prev = g[src].transform(lambda s: s.shift(8).rolling(4, min_periods=1).mean())
        w[dst] = roll_mean(src, 4) - prev
    w["sessions_per_user_4w"] = roll_sum("sessions", 4) / roll_sum("dau", 4).replace(0, np.nan)
    for c in ["tickets_created", "urgent_tickets", "technical_tickets", "cancellation_tickets",
              "slow_first_responses", "low_csat_tickets", "csat_sum", "csat_n"]:
        w[f"{c}_12w"] = roll_sum(c, 12)
    w = w.rename(columns={"tickets_created_12w": "tickets_12w"})
    w["avg_csat_12w"] = w["csat_sum_12w"] / w["csat_n_12w"].replace(0, np.nan)
    w["weeks_observed"] = g.cumcount() + 1

    if snapshot_weeks is not None:
        w = w[w["week_start"].isin(pd.to_datetime(pd.Series(list(snapshot_weeks))))]

    c = contracts[["account_id", "start_date", "end_date", "auto_renew"]].copy()
    c["start_date"] = pd.to_datetime(c["start_date"])
    c["end_date"] = pd.to_datetime(c["end_date"])
    a = accounts[["account_id", "plan", "seats", "arr_jpy"]].rename(columns={"seats": "crm_seats"})
    df = w.merge(c, on="account_id", how="inner").merge(a, on="account_id", how="left")
    df["snapshot_week"] = df["week_start"]
    df["next_renewal_date"] = _renewal_after(df["start_date"], df["snapshot_week"])
    df["days_to_renewal"] = (df["next_renewal_date"] - df["snapshot_week"]).dt.days
    df["in_renewal_window"] = df["days_to_renewal"].between(30, 180)
    df["auto_renew"] = df["auto_renew"].astype(int)
    df["tenure_months"] = ((df["snapshot_week"] - df["start_date"]).dt.days / 30.4).round(1)
    df["seats"] = df["crm_seats"].fillna(df["seats"])
    df["log_arr"] = np.log1p(df["arr_jpy"].astype(float))
    df["plan_ordinal"] = df["plan"].map(PLAN_ORD).fillna(1)
    if with_label:
        df["label"] = ((df["end_date"] > df["snapshot_week"]) &
                       (df["end_date"] <= df["next_renewal_date"])).astype(int)
    keep = (["account_id", "snapshot_week", "weeks_observed", "end_date", "next_renewal_date", "in_renewal_window",
             "days_to_renewal", "tenure_months"]
            + FEATURES + (["label"] if with_label else []))
    return df[keep].reset_index(drop=True)


def rule_score(df: pd.DataFrame) -> pd.Series:
    """Re-implementation of the app's original rule-based score (server/churn.py) on the same
    snapshot features, used as the status-quo baseline the ML model must beat."""
    s = pd.Series(0.0, index=df.index)
    for col, wgt in [("login_rate_4w", 12), ("attendance_detect_rate_4w", 12),
                     ("install_rate_4w", 8), ("app_config_ok_rate_4w", 8)]:
        s += ((0.75 - df[col]).clip(lower=0) / 0.75 * wgt)
    s += np.where(df["login_trend_8w"] < -0.05, np.minimum(12, df["login_trend_8w"].abs() * 80), 0)
    s += np.where(df["detect_trend_8w"] < -0.05, np.minimum(8, df["detect_trend_8w"].abs() * 60), 0)
    s += np.where(df["open_tickets"] >= 3, 8, 0)
    s += np.where(df["urgent_tickets_12w"] >= 3, 6, 0)
    s += np.where(df["avg_csat_12w"].fillna(5) < 3.0, 10, 0)
    s += np.where(df["cancellation_tickets_12w"] > 0, 12, 0)
    s += np.where(df["slow_first_responses_12w"] >= 2, 5, 0)
    s += np.where(df["auto_renew"] == 0, 6, 0)
    return s.clip(upper=100)
