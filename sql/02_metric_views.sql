CREATE OR REPLACE VIEW mv_sales_performance
WITH METRICS
LANGUAGE YAML
COMMENT 'メトリクスビュー: 販売パフォーマンス。売上・粗利・数量・粗利率を製品/カテゴリ/世代/ライフサイクル段階/月で分析'
AS $$
version: 0.1
source: ytcy_azure_east2classic_stable.digital_thread.v_product_monthly_pnl
dimensions:
  - name: 月
    expr: month
  - name: 製品名
    expr: product_name
  - name: カテゴリ
    expr: category
  - name: NAND世代
    expr: nand_generation
  - name: ライフサイクル段階
    expr: lifecycle_stage
  - name: 発売からの月数
    expr: months_since_launch
measures:
  - name: 売上金額USD
    expr: SUM(revenue_usd)
  - name: 売上原価USD
    expr: SUM(cogs_usd)
  - name: 粗利USD
    expr: SUM(gross_margin_usd)
  - name: 粗利率
    expr: SUM(gross_margin_usd) / SUM(revenue_usd)
  - name: 販売数量
    expr: SUM(total_qty)
  - name: 平均月次売上USD
    expr: AVG(revenue_usd)
$$;

CREATE OR REPLACE VIEW mv_manufacturing_quality
WITH METRICS
LANGUAGE YAML
COMMENT 'メトリクスビュー: 製造・品質。歩留まり・投入/良品数量をFab/拠点/製品カテゴリ/月で分析'
AS $$
version: 0.1
source: ytcy_azure_east2classic_stable.digital_thread.v_monthly_yield
dimensions:
  - name: 月
    expr: month
  - name: Fab
    expr: fab_name
  - name: 拠点
    expr: site
  - name: 製品名
    expr: product_name
  - name: カテゴリ
    expr: category
  - name: NAND世代
    expr: nand_generation
measures:
  - name: ロット数
    expr: SUM(lot_count)
  - name: 投入数量
    expr: SUM(input_units)
  - name: 良品数量
    expr: SUM(good_units)
  - name: 歩留まり率
    expr: SUM(good_units) / SUM(input_units)
$$;

CREATE OR REPLACE VIEW mv_field_quality
WITH METRICS
LANGUAGE YAML
COMMENT 'メトリクスビュー: 市場品質（保守）。フィールド不良の件数・影響台数を製品/顧客セグメント/重大度で分析'
AS $$
version: 0.1
source: ytcy_azure_east2classic_stable.digital_thread.fact_field_incidents
joins:
  - name: product
    source: ytcy_azure_east2classic_stable.digital_thread.dim_product
    on: source.product_id = product.product_id
  - name: customer
    source: ytcy_azure_east2classic_stable.digital_thread.dim_customer
    on: source.customer_id = customer.customer_id
dimensions:
  - name: 発生月
    expr: DATE_TRUNC('MONTH', incident_date)
  - name: 製品名
    expr: product.product_name
  - name: カテゴリ
    expr: product.category
  - name: 顧客セグメント
    expr: customer.segment
  - name: 不良タイプ
    expr: incident_type
  - name: 重大度
    expr: severity
  - name: 対応状況
    expr: resolution_status
measures:
  - name: 不良件数
    expr: COUNT(incident_id)
  - name: 影響台数
    expr: SUM(affected_units)
$$;
