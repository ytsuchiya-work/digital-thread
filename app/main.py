"""デジタルスレッド・デモアプリ バックエンド（FastAPI / Databricks Apps）.

Reactフロントエンド（./static）を配信しつつ、Unity Catalog上のデジタルスレッド
データへのクエリと、LTV予測モデルサービング呼び出しをAPIとして提供する。
"""
import os
import time
from typing import Any

from databricks.sdk import WorkspaceClient
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]
SERVING_ENDPOINT = os.environ.get("SERVING_ENDPOINT", "digital-thread-ltv")
DASHBOARD_ID = os.environ.get("DASHBOARD_ID", "")
GENIE_SPACE_ID = os.environ.get("GENIE_SPACE_ID", "")
SCHEMA = os.environ.get("SCHEMA_FQN", "ytcy_azure_east2classic_stable.digital_thread")

app = FastAPI(title="Digital Thread API")
_ws: WorkspaceClient | None = None
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 600


def ws() -> WorkspaceClient:
    global _ws
    if _ws is None:
        _ws = WorkspaceClient()
    return _ws


def sql(query: str) -> list[dict]:
    """SQLを実行し dict のリストで返す（10分キャッシュ）."""
    now = time.time()
    hit = _cache.get(query)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    resp = ws().statement_execution.execute_statement(
        statement=query, warehouse_id=WAREHOUSE_ID, wait_timeout="50s")
    if resp.status.state.value != "SUCCEEDED":
        raise HTTPException(500, f"SQL failed: {resp.status.error.message if resp.status.error else resp.status.state}")
    cols = [c.name for c in resp.manifest.schema.columns]
    rows = [dict(zip(cols, r)) for r in (resp.result.data_array or [])]
    _cache[query] = (now, rows)
    return rows


# ------------------------------------------------------------------ config
@app.get("/api/config")
def config():
    host = ws().config.host.rstrip("/")
    return {
        "workspaceHost": host,
        "dashboardEmbedUrl": f"{host}/embed/dashboardsv3/{DASHBOARD_ID}",
        "genieEmbedUrl": f"{host}/embed/genie/rooms/{GENIE_SPACE_ID}",
        "genieUrl": f"{host}/genie/rooms/{GENIE_SPACE_ID}",
        "dashboardUrl": f"{host}/dashboardsv3/{DASHBOARD_ID}/published",
        "catalogUrl": f"{host}/explore/data/{SCHEMA.replace('.', '/')}",
        "modelUrl": f"{host}/explore/data/models/{SCHEMA.replace('.', '/')}/ltv_predictor",
        "servingUrl": f"{host}/ml/endpoints/{SERVING_ENDPOINT}",
        "schema": SCHEMA,
        "servingEndpoint": SERVING_ENDPOINT,
    }


# ---------------------------------------------------------------- products
@app.get("/api/products")
def products():
    return sql(f"""SELECT product_id, product_name, category, nand_generation,
                   lifecycle_stage, capacity_gb FROM {SCHEMA}.dim_product ORDER BY product_name""")


@app.get("/api/lifecycle")
def lifecycle(ids: str):
    pids = [p for p in ids.split(",") if p.startswith("P")][:12]
    if not pids:
        return []
    idlist = ",".join(f"'{p}'" for p in pids)
    return sql(f"""
        SELECT product_id, product_name, months_since_launch,
               CAST(revenue_usd AS DOUBLE) AS revenue_usd,
               CAST(gross_margin_usd AS DOUBLE) AS gross_margin_usd
        FROM {SCHEMA}.v_product_monthly_pnl
        WHERE product_id IN ({idlist}) ORDER BY months_since_launch""")


# --------------------------------------------------------------------- LTV
@app.get("/api/ltv/ranking")
def ltv_ranking():
    return sql(f"""
        SELECT product_name, category, lifecycle_stage,
               round(lifetime_revenue_usd/1e6, 1) AS lifetime_revenue_musd,
               round(lifetime_margin_usd/1e6, 1) AS lifetime_margin_musd,
               round(avg_margin_rate*100, 1) AS avg_margin_pct
        FROM {SCHEMA}.v_product_ltv_actual ORDER BY lifetime_margin_usd DESC LIMIT 15""")


FEATURE_QUERY = """
WITH pnl AS (SELECT * FROM {S}.v_product_monthly_pnl),
yld AS (
  SELECT l.product_id, date_trunc('MONTH', l.start_date)::date AS month,
         SUM(l.good_units)/SUM(l.input_units) AS yield_rate
  FROM {S}.fact_manufacturing_lots l GROUP BY 1,2),
inc AS (
  SELECT product_id, date_trunc('MONTH', incident_date)::date AS month, COUNT(*) AS incidents
  FROM {S}.fact_field_incidents GROUP BY 1,2),
base AS (
  SELECT p.product_id, p.product_name, p.category, p.nand_generation, p.month,
         p.months_since_launch, dp.capacity_gb, dp.list_price_usd, dp.lifecycle_months,
         p.revenue_usd, p.gross_margin_usd,
         coalesce(y.yield_rate, 0.9) AS yield_rate, coalesce(i.incidents, 0) AS incidents
  FROM pnl p JOIN {S}.dim_product dp USING(product_id)
  LEFT JOIN yld y ON p.product_id=y.product_id AND p.month=y.month
  LEFT JOIN inc i ON p.product_id=i.product_id AND p.month=i.month),
feat AS (
  SELECT product_id, product_name, category, nand_generation, month,
         months_since_launch, capacity_gb, list_price_usd, lifecycle_months,
         SUM(revenue_usd) OVER w3 AS rev_3m,
         SUM(gross_margin_usd) OVER w3 AS margin_3m,
         SUM(gross_margin_usd) OVER w3 / nullif(SUM(revenue_usd) OVER w3,0) AS margin_rate_3m,
         AVG(yield_rate) OVER w3 AS yield_3m,
         SUM(incidents) OVER wcum AS incidents_to_date,
         ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY month DESC) AS rn
  FROM base
  WINDOW w3 AS (PARTITION BY product_id ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),
         wcum AS (PARTITION BY product_id ORDER BY month ROWS UNBOUNDED PRECEDING))
SELECT * FROM feat WHERE rn = 1
"""

NUM_FEATS = ["months_since_launch", "capacity_gb", "list_price_usd", "lifecycle_months",
             "rev_3m", "margin_3m", "margin_rate_3m", "yield_3m", "incidents_to_date"]


def latest_features(product_id: str) -> dict:
    rows = sql(FEATURE_QUERY.format(S=SCHEMA))
    for r in rows:
        if r["product_id"] == product_id:
            return {k: (float(v) if k in NUM_FEATS else v) for k, v in r.items() if v is not None}
    raise HTTPException(404, f"product {product_id} not found")


@app.get("/api/ltv/features/{product_id}")
def ltv_features(product_id: str):
    return latest_features(product_id)


class PredictRequest(BaseModel):
    product_id: str
    adj_margin_pt: float = 0.0  # 粗利率変化（ポイント）
    adj_yield_pt: float = 0.0   # 歩留まり変化（ポイント）


@app.post("/api/ltv/predict")
def ltv_predict(req: PredictRequest):
    f = latest_features(req.product_id)
    rec = {k: f[k] for k in NUM_FEATS}
    rec["category"] = f["category"]
    rec["nand_generation"] = f["nand_generation"]
    what_if = dict(rec,
                   margin_rate_3m=rec["margin_rate_3m"] + req.adj_margin_pt / 100,
                   yield_3m=rec["yield_3m"] + req.adj_yield_pt / 100)
    res = ws().serving_endpoints.query(SERVING_ENDPOINT, dataframe_records=[rec, what_if])
    actual_rows = sql(f"""SELECT CAST(lifetime_margin_usd AS DOUBLE) AS m
                          FROM {SCHEMA}.v_product_ltv_actual WHERE product_id='{req.product_id}'""")
    actual = float(actual_rows[0]["m"]) if actual_rows else 0.0
    return {"actual_ltv": actual,
            "predicted_remaining": float(res.predictions[0]),
            "what_if_remaining": float(res.predictions[1]),
            "features": f}


# ------------------------------------------------------------------ thread
@app.get("/api/thread/{product_id}")
def thread(product_id: str, focus: str = "incidents"):
    kpi = sql(f"""
        SELECT COUNT(DISTINCT revision_id) AS revisions, COUNT(DISTINCT lot_id) AS lots,
               COUNT(DISTINCT shipment_id) AS shipments, COUNT(DISTINCT incident_id) AS incidents,
               CAST(MIN(yield_rate) AS DOUBLE) AS worst_yield
        FROM {SCHEMA}.v_lot_traceability WHERE product_id = '{product_id}'""")[0]
    cond, order = "", "ORDER BY start_date DESC"
    if focus == "incidents":
        cond = "AND t.incident_id IS NOT NULL"
    elif focus == "low_yield":
        order = "ORDER BY yield_rate ASC"
    rows = sql(f"""
        SELECT DISTINCT t.product_name, t.revision_no, t.change_type, t.eco_number,
               t.change_description, t.lot_id, t.fab_name,
               CAST(t.start_date AS STRING) AS start_date,
               CAST(t.yield_rate AS DOUBLE) AS yield_rate,
               t.shipment_id, t.destination_region, t.customer_name, t.segment,
               t.incident_id, t.incident_type, t.severity
        FROM {SCHEMA}.v_lot_traceability t
        WHERE t.product_id = '{product_id}' {cond} {order} LIMIT 10""")
    return {"kpi": kpi, "rows": rows}


# ----------------------------------------------------------- static (SPA)
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    return FileResponse("static/index.html")
