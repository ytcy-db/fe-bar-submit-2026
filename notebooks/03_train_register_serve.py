# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Train, evaluate, register and serve the churn model
# MAGIC
# MAGIC **Prediction task (renewal risk).** Contracts are annual, so churn happens at renewal. For every
# MAGIC live account and snapshot week, predict *"will this account NOT renew at its next renewal?"*.
# MAGIC Training and evaluation use snapshots **30–180 days before renewal** — the window in which a CSM
# MAGIC can still run a save play (a renewal-date-only model would otherwise look deceptively good).
# MAGIC
# MAGIC * Features come from the Lakeflow gold table `gold_account_weekly` (usage + support) and
# MAGIC   `silver_contracts` (renewal timing, auto-renew) — see `churn_features.py`. Only data at or
# MAGIC   before the snapshot week is used.
# MAGIC * **Out-of-time split by renewal event**: train only on renewals that happened before
# MAGIC   2026-05-01 (outcomes a team would actually have known), test on renewals 2026-05-01 … 2026-11-02.
# MAGIC   Splitting by snapshot date instead would leak: the same renewal would appear on both sides.
# MAGIC * **Baseline** = the rule-based score that the CRM app used before this project.
# MAGIC * The model is logged with MLflow, registered in Unity Catalog as `officepulse_churn.churn_model`
# MAGIC   (alias `champion`) and deployed to a Model Serving endpoint for real-time what-if scoring.

# COMMAND ----------

# MAGIC %pip install -q "mlflow>=2.21,<4" "scikit-learn==1.5.2" "shap==0.46.0" "numpy<2.2"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import json
import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

from churn_features import FEATURES, FEATURE_LABELS_JA, build_features, rule_score

dbutils.widgets.text("catalog", "ytcy_azure_east2classic_stable")
dbutils.widgets.text("schema", "officepulse_churn")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
FQ = f"{CATALOG}.{SCHEMA}"
MODEL_NAME = f"{FQ}.churn_model"
ENDPOINT_NAME = "officepulse-churn-model"
TRAIN_END = pd.Timestamp("2026-05-01")
TODAY = pd.Timestamp("2026-11-02")
mlflow.set_registry_uri("databricks-uc")

# COMMAND ----------

weekly = spark.table(f"{FQ}.gold_account_weekly").toPandas()
contracts = spark.table(f"{FQ}.silver_contracts").toPandas()
accounts = spark.table(f"{FQ}.silver_accounts").select("account_id", "plan", "seats", "arr_jpy", "status").toPandas()
print("gold_account_weekly rows:", len(weekly), " accounts:", weekly.account_id.nunique())

all_weeks = sorted(pd.to_datetime(weekly.week_start).unique())
feat = build_features(weekly, contracts, accounts)
# need >= 8 weeks of history for trend features; keep only snapshots whose next renewal already happened
feat = feat[(feat.weeks_observed >= 8) & (feat.next_renewal_date <= TODAY)]
snap_weeks = set(all_weeks[12::2])  # bi-weekly evaluation snapshots (reduces autocorrelation)
train = feat[feat.next_renewal_date < TRAIN_END]                 # all weekly snapshots, renewals known before cutoff
test = feat[feat.next_renewal_date >= TRAIN_END]                 # every week before each test renewal (lead time)
test_eval = test[test.in_renewal_window & test.snapshot_week.isin(snap_weeks)]  # the actionable 30-180 day window
print(f"train rows={len(train)} pos_rate={train.label.mean():.3f} | test rows={len(test_eval)} pos_rate={test_eval.label.mean():.3f}")

spark.createDataFrame(feat.assign(split=np.where(feat.next_renewal_date < TRAIN_END, "train", "test"))) \
    .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.ml_churn_training_set")

# COMMAND ----------

# MAGIC %md ## Train with MLflow tracking

# COMMAND ----------


def fill(X):
    X = X.copy()
    X["avg_csat_12w"] = X["avg_csat_12w"].fillna(4.0)
    return X.fillna(0.0)


def top_k_metrics(y, score, k_frac):
    n = max(1, int(len(y) * k_frac))
    idx = np.argsort(-np.asarray(score))[:n]
    tp = np.asarray(y)[idx].sum()
    return tp / n, tp / max(1, np.asarray(y).sum())


class ChurnModel(mlflow.pyfunc.PythonModel):
    """Returns churn probability + top-3 SHAP drivers so the app can explain every score."""

    def __init__(self, clf, features, labels):
        self.clf, self.features, self.labels = clf, features, labels

    def load_context(self, context):
        try:
            import shap
            self.explainer = shap.TreeExplainer(self.clf)
        except Exception:
            self.explainer = None

    def predict(self, context, model_input, params=None):
        X = model_input[self.features].astype(float).copy()
        X["avg_csat_12w"] = X["avg_csat_12w"].fillna(4.0)
        X = X.fillna(0.0)
        p = self.clf.predict_proba(X)[:, 1]
        drivers = [[] for _ in range(len(X))]
        if getattr(self, "explainer", None) is not None:
            sv = np.asarray(self.explainer.shap_values(X))
            if sv.ndim == 3:
                sv = sv[..., 1]
            for i in range(len(X)):
                order = np.argsort(-sv[i])[:3]
                drivers[i] = [{"feature": self.features[j], "label": self.labels.get(self.features[j], self.features[j]),
                               "value": float(X.iloc[i, j]), "impact": round(float(sv[i, j]), 4)}
                              for j in order if sv[i, j] > 0]
        return pd.DataFrame({"churn_probability": p, "top_drivers": [json.dumps(d, ensure_ascii=False) for d in drivers]})


mlflow.set_experiment(f"/Users/{spark.sql('select current_user()').first()[0]}/officepulse-churn")
params = dict(n_estimators=250, learning_rate=0.05, max_depth=2, subsample=0.8, min_samples_leaf=50, random_state=42)

with mlflow.start_run(run_name="gbm_renewal_risk") as run:
    clf = GradientBoostingClassifier(**params).fit(fill(train[FEATURES]), train.label)
    p_test = clf.predict_proba(fill(test_eval[FEATURES]))[:, 1]
    r_test = rule_score(test_eval)
    m = {
        "test_auc": roc_auc_score(test_eval.label, p_test),
        "test_pr_auc": average_precision_score(test_eval.label, p_test),
        "test_brier": brier_score_loss(test_eval.label, p_test),
        "rules_auc": roc_auc_score(test_eval.label, r_test),
        "rules_pr_auc": average_precision_score(test_eval.label, r_test),
        "base_rate": float(test_eval.label.mean()),
    }
    for k in (0.05, 0.10, 0.20):
        pm, rm = top_k_metrics(test_eval.label, p_test, k)
        pr, rr = top_k_metrics(test_eval.label, r_test, k)
        m[f"precision_at_top{int(k*100)}pct"], m[f"recall_at_top{int(k*100)}pct"] = pm, rm
        m[f"rules_precision_at_top{int(k*100)}pct"], m[f"rules_recall_at_top{int(k*100)}pct"] = pr, rr
    m["lift_at_top10pct"] = m["precision_at_top10pct"] / m["base_rate"]
    mlflow.log_params(params | {"label": "no_renew_at_next_renewal", "window_days": "30-180", "train_end": str(TRAIN_END.date()), "n_features": len(FEATURES)})
    mlflow.log_metrics(m)

    imp = pd.DataFrame({"feature": FEATURES, "importance": clf.feature_importances_}) \
        .assign(label_ja=lambda d: d.feature.map(FEATURE_LABELS_JA)).sort_values("importance", ascending=False)
    mlflow.log_table(imp, "feature_importance.json")

    example = test_eval[FEATURES].head(5)
    wrapped = ChurnModel(clf, FEATURES, FEATURE_LABELS_JA)
    wrapped.load_context(None)
    signature = infer_signature(example, wrapped.predict(None, example))
    info = mlflow.pyfunc.log_model(
        artifact_path="model", python_model=wrapped, signature=signature, input_example=example,
        code_paths=["churn_features.py"], registered_model_name=MODEL_NAME,
        pip_requirements=["mlflow>=2.21,<4", "scikit-learn==1.5.2", "shap==0.46.0", "numpy<2.2", "pandas"],
    )
    run_id = run.info.run_id

print(json.dumps({k: round(v, 4) for k, v in m.items()}, indent=2))
display(imp)

# COMMAND ----------

# MAGIC %md ## Register as champion in Unity Catalog

# COMMAND ----------

from mlflow import MlflowClient

client = MlflowClient()
version = info.registered_model_version
client.set_registered_model_alias(MODEL_NAME, "champion", version)
client.update_registered_model(MODEL_NAME, description=(
    "Renewal-risk model: probability an OfficePulse account does not renew at its next annual renewal. GradientBoosting on Lakeflow gold features "
    "(usage KPIs, support signals, renewal timing). Output: churn_probability + top SHAP drivers."))
client.set_model_version_tag(MODEL_NAME, version, "test_auc", f"{m['test_auc']:.3f}")
client.set_model_version_tag(MODEL_NAME, version, "rules_auc", f"{m['rules_auc']:.3f}")
print(f"registered {MODEL_NAME} v{version} as @champion (run {run_id})")

# COMMAND ----------

# MAGIC %md ## Persist evaluation + lead-time analysis for the app, Genie and the business case

# COMMAND ----------

# Business evaluation at the "T-90 days" checkpoint: for every renewal in the test period, take the
# snapshot ~90 days before the renewal date (time to run a save play) and ask: who raised the alarm?
#   * ML model (probability >= ML_THRESHOLD)
#   * the old rule score, at a threshold giving the SAME number of alerts (fair comparison)
#   * the customer's own cancellation ticket (the status quo: CSMs react when the customer says so)
ML_THRESHOLD = 0.40
scored = test.assign(ml_prob=clf.predict_proba(fill(test[FEATURES]))[:, 1], rule=rule_score(test).values)
cp = scored[scored.days_to_renewal.between(84, 97)].sort_values("days_to_renewal") \
    .groupby(["account_id", "next_renewal_date"], as_index=False).first()
RULE_THRESHOLD = float(np.quantile(cp.rule, 1 - (cp.ml_prob >= ML_THRESHOLD).mean()))

tix = spark.table(f"{FQ}.silver_tickets").where("is_cancellation_intent").select("account_id", "created_at").toPandas()
tix["created_at"] = pd.to_datetime(tix.created_at).dt.tz_localize(None)
cp = cp.merge(accounts[["account_id", "arr_jpy"]], on="account_id", how="left")
cp["ml_flag"] = cp.ml_prob >= ML_THRESHOLD
cp["rule_flag"] = cp.rule >= RULE_THRESHOLD
cp["cancel_ticket_flag"] = [((tix.account_id == a) & (tix.created_at <= s)).any() for a, s in zip(cp.account_id, cp.snapshot_week)]
first_cancel = tix.groupby("account_id").created_at.min()

ch = cp[cp.label == 1]
lead_summary = {"renewals_at_checkpoint": float(len(cp)), "churned_renewals": float(len(ch)),
                "churned_arr_jpy": float(ch.arr_jpy.sum())}
for flag, name in [("ml_flag", "ml"), ("rule_flag", "rules"), ("cancel_ticket_flag", "cancel_ticket")]:
    lead_summary[f"{name}_recall_at_t90"] = float(ch[flag].mean())
    lead_summary[f"{name}_arr_recall_at_t90"] = float((ch.arr_jpy * ch[flag]).sum() / ch.arr_jpy.sum())
    lead_summary[f"{name}_alerts_at_t90"] = float(cp[flag].sum())
    lead_summary[f"{name}_precision_at_t90"] = float(cp[cp[flag]].label.mean()) if cp[flag].any() else 0.0
gaps = [(r.next_renewal_date - first_cancel[r.account_id]).days for r in ch.itertuples()
        if r.account_id in first_cancel.index and first_cancel[r.account_id] < r.next_renewal_date]
lead_summary["cancel_ticket_share_of_churners"] = float(len(gaps) / max(1, len(ch)))
lead_summary["cancel_ticket_median_days_before_renewal"] = float(np.median(gaps)) if gaps else 0.0
print(json.dumps({k: round(v, 3) for k, v in lead_summary.items()}, indent=2))
with mlflow.start_run(run_id=run_id):
    mlflow.log_metrics(lead_summary)
lead = cp[["account_id", "next_renewal_date", "snapshot_week", "label", "arr_jpy", "ml_prob", "rule",
           "ml_flag", "rule_flag", "cancel_ticket_flag"]]

metrics_rows = [(k, float(v), "model_eval") for k, v in m.items()] + [(k, float(v), "t90_checkpoint") for k, v in lead_summary.items()]
metrics_rows += [("ml_threshold", ML_THRESHOLD, "config"), ("rules_threshold_same_volume", RULE_THRESHOLD, "config"),
                 ("model_version", float(version), "config")]
spark.createDataFrame(pd.DataFrame(metrics_rows, columns=["metric", "value", "metric_group"])) \
    .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.gold_model_metrics")
spark.createDataFrame(imp).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.gold_feature_importance")
spark.createDataFrame(lead).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.gold_churn_lead_time")
display(lead.sort_values("next_renewal_date"))

# COMMAND ----------

# MAGIC %md ## Deploy / update the Model Serving endpoint (scale-to-zero)

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

w = WorkspaceClient()
served = [ServedEntityInput(entity_name=MODEL_NAME, entity_version=str(version), workload_size="Small",
                            scale_to_zero_enabled=True)]
existing = [e.name for e in w.serving_endpoints.list()]
if ENDPOINT_NAME in existing:
    from datetime import timedelta
    w.serving_endpoints.wait_get_serving_endpoint_not_updating(ENDPOINT_NAME, timeout=timedelta(minutes=40))
    w.serving_endpoints.update_config(name=ENDPOINT_NAME, served_entities=served)
    print("updating endpoint", ENDPOINT_NAME, "->", version)
else:
    w.serving_endpoints.create(name=ENDPOINT_NAME, config=EndpointCoreConfigInput(name=ENDPOINT_NAME, served_entities=served))
    print("creating endpoint", ENDPOINT_NAME, "with", version)


# COMMAND ----------

dbutils.notebook.exit(json.dumps({"model": MODEL_NAME, "version": version, "run_id": run_id,
                                  **{k: round(v, 4) for k, v in m.items()},
                                  **{k: round(v, 4) for k, v in lead_summary.items()}}))
