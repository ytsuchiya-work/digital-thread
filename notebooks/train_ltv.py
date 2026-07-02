"""製品別収益性LTV予測モデルの学習とUC登録.

各製品×月の断面で「直近3ヶ月の売上・粗利・歩留まり・不良実績」等から
「今後12ヶ月の粗利（残存LTV）」を予測する回帰モデルを学習する。
"""
import json
import subprocess
import sys
from pathlib import Path

import mlflow
import pandas as pd
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

sys.path.insert(0, str(Path(__file__).parent.parent / "sql"))
from run_sql import run_statement, HOST, token  # noqa: E402

FEATURE_SQL = """
WITH pnl AS (SELECT * FROM v_product_monthly_pnl),
yld AS (
  SELECT l.product_id, date_trunc('MONTH', l.start_date)::date AS month,
         SUM(l.good_units)/SUM(l.input_units) AS yield_rate
  FROM fact_manufacturing_lots l GROUP BY 1, 2),
inc AS (
  SELECT product_id, date_trunc('MONTH', incident_date)::date AS month, COUNT(*) AS incidents
  FROM fact_field_incidents GROUP BY 1, 2),
base AS (
  SELECT p.product_id, p.month, p.months_since_launch, p.category, p.nand_generation,
         dp.capacity_gb, dp.list_price_usd, dp.lifecycle_months,
         p.revenue_usd, p.gross_margin_usd,
         coalesce(y.yield_rate, 0.9) AS yield_rate,
         coalesce(i.incidents, 0) AS incidents
  FROM pnl p
  JOIN dim_product dp USING(product_id)
  LEFT JOIN yld y ON p.product_id = y.product_id AND p.month = y.month
  LEFT JOIN inc i ON p.product_id = i.product_id AND p.month = i.month)
SELECT product_id, month, months_since_launch, category, nand_generation,
       capacity_gb, list_price_usd, lifecycle_months,
       SUM(revenue_usd) OVER w3 AS rev_3m,
       SUM(gross_margin_usd) OVER w3 AS margin_3m,
       SUM(gross_margin_usd) OVER w3 / nullif(SUM(revenue_usd) OVER w3, 0) AS margin_rate_3m,
       AVG(yield_rate) OVER w3 AS yield_3m,
       SUM(incidents) OVER wcum AS incidents_to_date,
       SUM(gross_margin_usd) OVER wf12 AS margin_next12,
       COUNT(*) OVER wf12 AS months_ahead_observed
FROM base
WINDOW w3 AS (PARTITION BY product_id ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),
       wcum AS (PARTITION BY product_id ORDER BY month ROWS UNBOUNDED PRECEDING),
       wf12 AS (PARTITION BY product_id ORDER BY month ROWS BETWEEN 1 FOLLOWING AND 12 FOLLOWING)
"""

NUM = ["months_since_launch", "capacity_gb", "list_price_usd", "lifecycle_months",
       "rev_3m", "margin_3m", "margin_rate_3m", "yield_3m", "incidents_to_date"]
CAT = ["category", "nand_generation"]
MODEL_NAME = "ytcy_azure_east2classic_stable.digital_thread.ltv_predictor"


def fetch_features():
    res = run_statement(FEATURE_SQL)
    assert res["status"]["state"] == "SUCCEEDED", res["status"]
    cols = [c["name"] for c in res["manifest"]["schema"]["columns"]]
    rows = res["result"].get("data_array", [])
    # 複数チャンク対応
    from run_sql import api
    sid = res["statement_id"]
    nxt = res["result"].get("next_chunk_index")
    while nxt is not None:
        ch = api("GET", f"/api/2.0/sql/statements/{sid}/result/chunks/{nxt}")
        rows += ch.get("data_array", [])
        nxt = ch.get("next_chunk_index")
    df = pd.DataFrame(rows, columns=cols)
    for c in NUM + ["margin_next12", "months_ahead_observed"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main():
    df = fetch_features()
    print(f"feature rows: {len(df)}")
    train = df[(df.months_ahead_observed >= 12) & df.margin_next12.notna()].copy()
    train = train.dropna(subset=NUM)
    print(f"training rows: {len(train)}")

    X, y = train[NUM + CAT], train["margin_next12"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    pipe = Pipeline([
        ("prep", ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CAT)],
                                   remainder="passthrough")),
        ("model", GradientBoostingRegressor(n_estimators=300, max_depth=4,
                                            learning_rate=0.05, random_state=42)),
    ])
    pipe.fit(X_tr, y_tr)
    pred = pipe.predict(X_te)
    mae, r2 = mean_absolute_error(y_te, pred), r2_score(y_te, pred)
    print(f"MAE={mae:,.0f} USD  R2={r2:.3f}")

    mlflow.set_tracking_uri("databricks")
    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment("/Users/yusuke.tsuchiya@databricks.com/digital_thread_demo/ltv_experiment")
    with mlflow.start_run(run_name="ltv_gbr"):
        mlflow.log_params({"model": "GradientBoostingRegressor", "n_estimators": 300,
                           "max_depth": 4, "learning_rate": 0.05,
                           "target": "margin_next12(残存12ヶ月粗利)"})
        mlflow.log_metrics({"mae_usd": mae, "r2": r2})
        sig = infer_signature(X_tr, pred[:5])
        info = mlflow.sklearn.log_model(
            pipe, name="model", signature=sig,
            input_example=X_tr.head(3),
            registered_model_name=MODEL_NAME)
        print("registered:", info.registered_model_version)
    Path(__file__).with_name("model_version.txt").write_text(str(info.registered_model_version))


if __name__ == "__main__":
    import os
    os.environ["DATABRICKS_HOST"] = HOST
    os.environ["DATABRICKS_TOKEN"] = token()
    main()
