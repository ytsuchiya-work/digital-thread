-- デジタルスレッドデモ: Bronzeパーケット -> Silver/Gold Deltaテーブル
USE CATALOG ytcy_azure_east2classic_stable;
USE SCHEMA digital_thread;

CREATE OR REPLACE TABLE dim_product
COMMENT '製品マスタ。NAND/SSD製品の諸元・ライフサイクル情報（エンジニアリングチェーンの起点）'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/dim_product.parquet`;

CREATE OR REPLACE TABLE dim_customer
COMMENT '顧客マスタ。セグメント（データセンター/PC OEM/スマートフォンOEM/車載・産業/代理店）と地域'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/dim_customer.parquet`;

CREATE OR REPLACE TABLE dim_fab
COMMENT '工場マスタ。四日市・北上の各Fabと基準歩留まり'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/dim_fab.parquet`;

CREATE OR REPLACE TABLE dim_supplier
COMMENT 'サプライヤマスタ。主要部材の調達先'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/dim_supplier.parquet`;

CREATE OR REPLACE TABLE fact_design_revisions
COMMENT '設計変更履歴（ECO）。製品ごとの設計・工程・部材・FW変更のリビジョン管理（エンジニアリングチェーン）'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_design_revisions.parquet`;

CREATE OR REPLACE TABLE fact_sales_orders
COMMENT '受注トランザクション。顧客×製品の受注数量・単価・金額（サプライチェーン: 販売）'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_sales_orders.parquet`;

CREATE OR REPLACE TABLE fact_demand_plan
COMMENT '需要計画（S&OP）。製品×月の計画数量・計画売上'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_demand_plan.parquet`;

CREATE OR REPLACE TABLE fact_manufacturing_lots
COMMENT '製造ロット実績（MES）。適用設計リビジョン・Fab・投入/良品数・歩留まりを保持しデジタルスレッドの中核となる'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_manufacturing_lots.parquet`;

CREATE OR REPLACE TABLE fact_quality_inspections
COMMENT '品質検査実績。ロット別の試験種別・不良率(ppm)・判定'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_quality_inspections.parquet`;

CREATE OR REPLACE TABLE fact_shipments
COMMENT '出荷・物流実績。受注とロットを紐づけるトレーサビリティの要'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_shipments.parquet`;

CREATE OR REPLACE TABLE fact_inventory
COMMENT '在庫スナップショット。月次×製品×拠点の在庫数量・金額'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_inventory.parquet`;

CREATE OR REPLACE TABLE fact_purchase_orders
COMMENT '調達発注。Fab×部材×サプライヤの発注実績（サプライチェーン: 調達）'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_purchase_orders.parquet`;

CREATE OR REPLACE TABLE fact_field_incidents
COMMENT '市場品質情報（保守）。フィールド不良をロット・顧客まで遡って追跡できる'
AS SELECT * FROM parquet.`/Volumes/ytcy_azure_east2classic_stable/digital_thread/raw/fact_field_incidents.parquet`;

-- ============ 制約（Genie/リネージのための情報制約） ============
ALTER TABLE dim_product ALTER COLUMN product_id SET NOT NULL;
ALTER TABLE dim_product ADD CONSTRAINT pk_product PRIMARY KEY(product_id);
ALTER TABLE dim_customer ALTER COLUMN customer_id SET NOT NULL;
ALTER TABLE dim_customer ADD CONSTRAINT pk_customer PRIMARY KEY(customer_id);
ALTER TABLE dim_fab ALTER COLUMN fab_id SET NOT NULL;
ALTER TABLE dim_fab ADD CONSTRAINT pk_fab PRIMARY KEY(fab_id);
ALTER TABLE dim_supplier ALTER COLUMN supplier_id SET NOT NULL;
ALTER TABLE dim_supplier ADD CONSTRAINT pk_supplier PRIMARY KEY(supplier_id);
ALTER TABLE fact_design_revisions ALTER COLUMN revision_id SET NOT NULL;
ALTER TABLE fact_design_revisions ADD CONSTRAINT pk_revision PRIMARY KEY(revision_id);
ALTER TABLE fact_manufacturing_lots ALTER COLUMN lot_id SET NOT NULL;
ALTER TABLE fact_manufacturing_lots ADD CONSTRAINT pk_lot PRIMARY KEY(lot_id);
ALTER TABLE fact_sales_orders ALTER COLUMN order_id SET NOT NULL;
ALTER TABLE fact_sales_orders ADD CONSTRAINT pk_order PRIMARY KEY(order_id);

ALTER TABLE fact_sales_orders ADD CONSTRAINT fk_so_product FOREIGN KEY(product_id) REFERENCES dim_product;
ALTER TABLE fact_sales_orders ADD CONSTRAINT fk_so_customer FOREIGN KEY(customer_id) REFERENCES dim_customer;
ALTER TABLE fact_design_revisions ADD CONSTRAINT fk_rev_product FOREIGN KEY(product_id) REFERENCES dim_product;
ALTER TABLE fact_manufacturing_lots ADD CONSTRAINT fk_lot_product FOREIGN KEY(product_id) REFERENCES dim_product;
ALTER TABLE fact_manufacturing_lots ADD CONSTRAINT fk_lot_fab FOREIGN KEY(fab_id) REFERENCES dim_fab;
ALTER TABLE fact_manufacturing_lots ADD CONSTRAINT fk_lot_rev FOREIGN KEY(revision_id) REFERENCES fact_design_revisions;
ALTER TABLE fact_quality_inspections ADD CONSTRAINT fk_qc_lot FOREIGN KEY(lot_id) REFERENCES fact_manufacturing_lots;
ALTER TABLE fact_shipments ADD CONSTRAINT fk_sh_order FOREIGN KEY(order_id) REFERENCES fact_sales_orders;
ALTER TABLE fact_shipments ADD CONSTRAINT fk_sh_lot FOREIGN KEY(lot_id) REFERENCES fact_manufacturing_lots;
ALTER TABLE fact_inventory ADD CONSTRAINT fk_inv_product FOREIGN KEY(product_id) REFERENCES dim_product;
ALTER TABLE fact_demand_plan ADD CONSTRAINT fk_dp_product FOREIGN KEY(product_id) REFERENCES dim_product;
ALTER TABLE fact_purchase_orders ADD CONSTRAINT fk_po_fab FOREIGN KEY(fab_id) REFERENCES dim_fab;
ALTER TABLE fact_purchase_orders ADD CONSTRAINT fk_po_supplier FOREIGN KEY(supplier_id) REFERENCES dim_supplier;
ALTER TABLE fact_field_incidents ADD CONSTRAINT fk_fi_product FOREIGN KEY(product_id) REFERENCES dim_product;
ALTER TABLE fact_field_incidents ADD CONSTRAINT fk_fi_lot FOREIGN KEY(lot_id) REFERENCES fact_manufacturing_lots;
ALTER TABLE fact_field_incidents ADD CONSTRAINT fk_fi_customer FOREIGN KEY(customer_id) REFERENCES dim_customer;

-- ============ Gold層ビュー ============
CREATE OR REPLACE VIEW v_product_monthly_pnl
COMMENT '製品×月の売上・売上原価・粗利（Gold）。ライフサイクル分析とLTV算出の基礎'
AS
SELECT
  date_trunc('MONTH', o.order_date)::date AS month,
  o.product_id, p.product_name, p.category, p.nand_generation, p.lifecycle_stage,
  p.launch_date,
  timestampdiff(MONTH, p.launch_date, date_trunc('MONTH', o.order_date)) AS months_since_launch,
  SUM(o.order_qty) AS total_qty,
  SUM(o.order_amount_usd) AS revenue_usd,
  SUM(o.order_qty * p.unit_cost_usd * power(0.990, greatest(0, timestampdiff(MONTH, p.launch_date, o.order_date)))) AS cogs_usd,
  SUM(o.order_amount_usd) - SUM(o.order_qty * p.unit_cost_usd * power(0.990, greatest(0, timestampdiff(MONTH, p.launch_date, o.order_date)))) AS gross_margin_usd
FROM fact_sales_orders o JOIN dim_product p USING(product_id)
GROUP BY ALL;

CREATE OR REPLACE VIEW v_product_ltv_actual
COMMENT '製品別の実績LTV（累計粗利・累計売上）とライフサイクル特徴量（Gold）'
AS
SELECT
  product_id, product_name, category, nand_generation, lifecycle_stage, launch_date,
  COUNT(DISTINCT month) AS active_months,
  SUM(revenue_usd) AS lifetime_revenue_usd,
  SUM(gross_margin_usd) AS lifetime_margin_usd,
  AVG(gross_margin_usd / nullif(revenue_usd, 0)) AS avg_margin_rate,
  MAX(revenue_usd) AS peak_monthly_revenue_usd
FROM v_product_monthly_pnl
GROUP BY ALL;

CREATE OR REPLACE VIEW v_lot_traceability
COMMENT 'デジタルスレッド・トレーサビリティビュー: 製品→設計リビジョン→製造ロット→品質→出荷→顧客→市場不良を1本に連結（Gold）'
AS
SELECT
  p.product_id, p.product_name, p.category,
  r.revision_id, r.revision_no, r.change_type, r.eco_number, r.description AS change_description,
  l.lot_id, f.fab_name, l.start_date, l.yield_rate, l.good_units, l.status AS lot_status,
  q.test_type, q.defect_ppm, q.result AS qc_result,
  s.shipment_id, s.ship_date, s.destination_region,
  o.order_id, c.customer_name, c.segment,
  i.incident_id, i.incident_type, i.severity, i.resolution_status
FROM fact_manufacturing_lots l
JOIN dim_product p USING(product_id)
JOIN dim_fab f USING(fab_id)
LEFT JOIN fact_design_revisions r ON l.revision_id = r.revision_id
LEFT JOIN fact_quality_inspections q ON l.lot_id = q.lot_id
LEFT JOIN fact_shipments s ON l.lot_id = s.lot_id
LEFT JOIN fact_sales_orders o ON s.order_id = o.order_id
LEFT JOIN dim_customer c ON o.customer_id = c.customer_id
LEFT JOIN fact_field_incidents i ON l.lot_id = i.lot_id;

CREATE OR REPLACE VIEW v_monthly_yield
COMMENT 'Fab×製品×月の歩留まり推移（Gold）'
AS
SELECT
  date_trunc('MONTH', l.start_date)::date AS month,
  f.fab_name, f.site, p.product_name, p.category, p.nand_generation,
  COUNT(*) AS lot_count,
  SUM(l.input_units) AS input_units,
  SUM(l.good_units) AS good_units,
  SUM(l.good_units) / SUM(l.input_units) AS yield_rate
FROM fact_manufacturing_lots l
JOIN dim_fab f USING(fab_id) JOIN dim_product p USING(product_id)
GROUP BY ALL;
