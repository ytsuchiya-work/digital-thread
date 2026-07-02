"""AI/BI (Lakeview) ダッシュボード定義を生成し、作成・公開する."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "sql"))
from run_sql import api  # noqa: E402

SCHEMA = "ytcy_azure_east2classic_stable.digital_thread"
WAREHOUSE = "9c8fac7a0b250221"

datasets = [
    dict(name="ds_pnl", displayName="製品×月 損益",
         queryLines=[f"SELECT * FROM {SCHEMA}.v_product_monthly_pnl"]),
    dict(name="ds_ltv", displayName="製品別LTV実績",
         queryLines=[f"SELECT * FROM {SCHEMA}.v_product_ltv_actual"]),
    dict(name="ds_yield", displayName="月次歩留まり",
         queryLines=[f"SELECT * FROM {SCHEMA}.v_monthly_yield"]),
    dict(name="ds_incidents", displayName="市場品質情報",
         queryLines=[
             f"SELECT i.*, p.product_name, p.category, c.segment FROM {SCHEMA}.fact_field_incidents i",
             f" JOIN {SCHEMA}.dim_product p USING(product_id)",
             f" LEFT JOIN {SCHEMA}.dim_customer c USING(customer_id)"]),
    dict(name="ds_inventory", displayName="在庫スナップショット",
         queryLines=[
             f"SELECT v.*, p.category FROM {SCHEMA}.fact_inventory v JOIN {SCHEMA}.dim_product p USING(product_id)"]),
    dict(name="ds_plan_actual", displayName="需要計画vs受注実績",
         queryLines=[
             "SELECT dp.plan_month, p.category, SUM(dp.planned_qty) AS planned_qty, SUM(coalesce(a.actual_qty,0)) AS actual_qty",
             f" FROM {SCHEMA}.fact_demand_plan dp JOIN {SCHEMA}.dim_product p USING(product_id)",
             " LEFT JOIN (SELECT product_id, date_trunc('MONTH', order_date)::date m, SUM(order_qty) actual_qty",
             f"   FROM {SCHEMA}.fact_sales_orders GROUP BY 1,2) a",
             " ON dp.product_id = a.product_id AND dp.plan_month = a.m",
             " WHERE dp.plan_month <= current_date() GROUP BY 1,2"]),
]


def counter(name, ds, field, expr, title, fmt=None):
    enc_value = {"fieldName": field, "displayName": title}
    if fmt:
        enc_value["format"] = fmt
    return {"name": name,
            "queries": [{"name": "main_query",
                         "query": {"datasetName": ds,
                                   "fields": [{"name": field, "expression": expr}],
                                   "disaggregated": False}}],
            "spec": {"version": 2, "widgetType": "counter",
                     "frame": {"showTitle": True, "title": title},
                     "encodings": {"value": enc_value}}}


def chart(name, ds, wtype, fields, encodings, title):
    return {"name": name,
            "queries": [{"name": "main_query",
                         "query": {"datasetName": ds, "fields": fields, "disaggregated": False}}],
            "spec": {"version": 3, "widgetType": wtype,
                     "frame": {"showTitle": True, "title": title},
                     "encodings": encodings}}


USD = {"type": "number-currency", "currencyCode": "USD", "abbreviation": "compact", "decimalPlaces": {"type": "max", "places": 1}}
PCT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}

page1_widgets = [
    (counter("c_rev", "ds_pnl", "rev", "SUM(`revenue_usd`)", "累計売上", USD), 0, 0, 2, 3),
    (counter("c_margin", "ds_pnl", "gm", "SUM(`gross_margin_usd`)", "累計粗利", USD), 2, 0, 2, 3),
    (counter("c_products", "ds_ltv", "np", "COUNT(DISTINCT `product_id`)", "販売実績のある製品数"), 4, 0, 1, 3),
    (counter("c_mrate", "ds_pnl", "mr", "SUM(`gross_margin_usd`)/SUM(`revenue_usd`)", "平均粗利率", PCT), 5, 0, 1, 3),
    (chart("w_rev_trend", "ds_pnl", "bar",
           [{"name": "month", "expression": "`month`"},
            {"name": "rev", "expression": "SUM(`revenue_usd`)"},
            {"name": "category", "expression": "`category`"}],
           {"x": {"fieldName": "month", "scale": {"type": "temporal"}, "displayName": "月"},
            "y": {"fieldName": "rev", "scale": {"type": "quantitative"}, "displayName": "売上USD"},
            "color": {"fieldName": "category", "scale": {"type": "categorical"}, "displayName": "カテゴリ"}},
           "月次売上推移（カテゴリ別）"), 0, 3, 3, 7),
    (chart("w_lifecycle", "ds_pnl", "line",
           [{"name": "msl", "expression": "`months_since_launch`"},
            {"name": "rev", "expression": "SUM(`revenue_usd`)"},
            {"name": "stage", "expression": "`lifecycle_stage`"}],
           {"x": {"fieldName": "msl", "scale": {"type": "quantitative"}, "displayName": "発売からの月数"},
            "y": {"fieldName": "rev", "scale": {"type": "quantitative"}, "displayName": "売上USD"},
            "color": {"fieldName": "stage", "scale": {"type": "categorical"}, "displayName": "ライフサイクル段階"}},
           "製品ライフサイクルカーブ（発売からの月数×売上）"), 3, 3, 3, 7),
    (chart("w_ltv_top", "ds_ltv", "bar",
           [{"name": "pn", "expression": "`product_name`"},
            {"name": "ltv", "expression": "SUM(`lifetime_margin_usd`)"},
            {"name": "cat", "expression": "`category`"}],
           {"x": {"fieldName": "ltv", "scale": {"type": "quantitative"}, "displayName": "累計粗利USD"},
            "y": {"fieldName": "pn", "scale": {"type": "categorical", "sort": {"by": "x-reversed"}}, "displayName": "製品"},
            "color": {"fieldName": "cat", "scale": {"type": "categorical"}, "displayName": "カテゴリ"}},
           "製品別LTV（累計粗利）Top"), 0, 10, 3, 7),
    (chart("w_plan_actual", "ds_plan_actual", "line",
           [{"name": "m", "expression": "`plan_month`"},
            {"name": "planned", "expression": "SUM(`planned_qty`)"},
            {"name": "actual", "expression": "SUM(`actual_qty`)"}],
           {"x": {"fieldName": "m", "scale": {"type": "temporal"}, "displayName": "月"},
            "y": {"scale": {"type": "quantitative"},
                  "fields": [{"fieldName": "planned", "displayName": "計画数量"},
                             {"fieldName": "actual", "displayName": "受注実績数量"}]}},
           "需要計画 vs 受注実績（S&OP）"), 3, 10, 3, 7),
]

page2_widgets = [
    (chart("w_yield", "ds_yield", "line",
           [{"name": "month", "expression": "`month`"},
            {"name": "y", "expression": "SUM(`good_units`)/SUM(`input_units`)"},
            {"name": "fab", "expression": "`fab_name`"}],
           {"x": {"fieldName": "month", "scale": {"type": "temporal"}, "displayName": "月"},
            "y": {"fieldName": "y", "scale": {"type": "quantitative"}, "displayName": "歩留まり率", "format": PCT},
            "color": {"fieldName": "fab", "scale": {"type": "categorical"}, "displayName": "Fab"}},
           "Fab別歩留まり推移"), 0, 0, 3, 7),
    (chart("w_inv", "ds_inventory", "area",
           [{"name": "m", "expression": "`snapshot_month`"},
            {"name": "v", "expression": "SUM(`inventory_value_usd`)"},
            {"name": "site", "expression": "`site`"}],
           {"x": {"fieldName": "m", "scale": {"type": "temporal"}, "displayName": "月"},
            "y": {"fieldName": "v", "scale": {"type": "quantitative"}, "displayName": "在庫金額USD"},
            "color": {"fieldName": "site", "scale": {"type": "categorical"}, "displayName": "拠点"}},
           "拠点別在庫金額推移"), 3, 0, 3, 7),
    (chart("w_incident_type", "ds_incidents", "bar",
           [{"name": "t", "expression": "`incident_type`"},
            {"name": "n", "expression": "COUNT(`incident_id`)"},
            {"name": "sev", "expression": "`severity`"}],
           {"x": {"fieldName": "t", "scale": {"type": "categorical"}, "displayName": "不良タイプ"},
            "y": {"fieldName": "n", "scale": {"type": "quantitative"}, "displayName": "件数"},
            "color": {"fieldName": "sev", "scale": {"type": "categorical"}, "displayName": "重大度"}},
           "市場不良: タイプ×重大度"), 0, 7, 3, 7),
    (chart("w_incident_seg", "ds_incidents", "pie",
           [{"name": "seg", "expression": "`segment`"},
            {"name": "n", "expression": "SUM(`affected_units`)"}],
           {"angle": {"fieldName": "n", "scale": {"type": "quantitative"}, "displayName": "影響台数"},
            "color": {"fieldName": "seg", "scale": {"type": "categorical"}, "displayName": "顧客セグメント"}},
           "市場不良 影響台数（顧客セグメント別）"), 3, 7, 3, 7),
]


def layout(widgets):
    return [{"widget": w, "position": {"x": x, "y": y, "width": wd, "height": h}}
            for w, x, y, wd, h in widgets]


dashboard = {
    "datasets": datasets,
    "pages": [
        {"name": "page_lifecycle", "displayName": "製品ライフサイクル・収益性", "layout": layout(page1_widgets)},
        {"name": "page_ops", "displayName": "製造・品質・在庫", "layout": layout(page2_widgets)},
    ],
}

if __name__ == "__main__":
    body = {
        "display_name": "デジタルスレッド: 製品ライフサイクル分析",
        "warehouse_id": WAREHOUSE,
        "serialized_dashboard": json.dumps(dashboard, ensure_ascii=False),
        "parent_path": "/Workspace/Users/yusuke.tsuchiya@databricks.com/digital_thread_demo",
    }
    res = api("POST", "/api/2.0/lakeview/dashboards", body)
    did = res["dashboard_id"]
    print("dashboard_id:", did)
    pub = api("POST", f"/api/2.0/lakeview/dashboards/{did}/published",
              {"embed_credentials": True, "warehouse_id": WAREHOUSE})
    print("published:", json.dumps(pub)[:200])
    Path(__file__).with_name("dashboard_id.txt").write_text(did)
