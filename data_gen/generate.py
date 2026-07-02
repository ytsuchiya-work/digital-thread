"""デジタルスレッドデモ用の合成データ生成（半導体メーカー想定: NAND/SSD）.

商品開発工程（設計変更・製造ロット・品質）とサプライチェーン（受注・調達・在庫・
出荷・保守・需給計画）を1本のスレッドで繋げられるよう、FKで連鎖させる。
出力: ./out/*.parquet
"""

import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

MONTHS = pd.date_range("2023-07-01", "2026-06-01", freq="MS")  # 36ヶ月
TODAY = pd.Timestamp("2026-07-01")

# ---------------------------------------------------------------- dim_product
CATEGORIES = [
    ("エンタープライズSSD", "ES", [1920, 3840, 7680, 15360], 0.055, 0.30),
    ("データセンターSSD", "DC", [960, 1920, 3840, 7680], 0.045, 0.28),
    ("クライアントSSD", "CL", [256, 512, 1024, 2048], 0.020, 0.22),
    ("UFS", "UF", [128, 256, 512, 1024], 0.012, 0.20),
    ("eMMC", "EM", [64, 128, 256], 0.006, 0.15),
    ("NANDコンポーネント", "NC", [512, 1024], 0.008, 0.25),
]
GENS = ["BiCS4", "BiCS5", "BiCS6", "BiCS8"]

products = []
pid = 0
for cat, code, caps, price_per_gb, margin in CATEGORIES:
    n = {"ES": 10, "DC": 9, "CL": 9, "UF": 8, "EM": 6, "NC": 8}[code]
    for i in range(n):
        pid += 1
        cap = caps[rng.integers(len(caps))]
        gen = GENS[min(3, max(0, int(rng.normal(1.6, 0.9))))]
        launch = pd.Timestamp("2021-01-01") + pd.Timedelta(days=int(rng.uniform(0, 365 * 5.2)))
        launch = launch.normalize().replace(day=1)
        life_m = int(rng.uniform(30, 60))  # ライフサイクル月数
        eol = launch + pd.DateOffset(months=life_m)
        base_price = cap * price_per_gb * rng.uniform(0.85, 1.15)
        if launch > TODAY:
            stage = "企画・開発"
        elif launch > TODAY - pd.DateOffset(months=6):
            stage = "立ち上げ"
        elif eol < TODAY:
            stage = "EOL"
        elif eol < TODAY + pd.DateOffset(months=9):
            stage = "縮退"
        else:
            stage = "量産" if launch < TODAY - pd.DateOffset(months=18) else "拡大"
        products.append(dict(
            product_id=f"P{pid:03d}",
            product_name=f"KX {code}{gen[-1]}{i:02d}-{cap}",
            category=cat, nand_generation=gen, capacity_gb=int(cap),
            launch_date=launch, planned_eol_date=eol, lifecycle_stage=stage,
            list_price_usd=round(base_price, 2),
            unit_cost_usd=round(base_price * (1 - margin) * rng.uniform(0.9, 1.05), 2),
            lifecycle_months=life_m,
        ))
dim_product = pd.DataFrame(products)

# --------------------------------------------------------------- dim_customer
SEGS = [("データセンター", 8, ["北米", "北米", "欧州", "アジア"]),
        ("PC OEM", 7, ["アジア", "アジア", "北米", "日本"]),
        ("スマートフォンOEM", 6, ["アジア", "アジア", "日本"]),
        ("車載・産業", 5, ["日本", "欧州", "北米"]),
        ("代理店", 4, ["日本", "アジア", "欧州"])]
CNAMES = ["アクシオン", "ノーステック", "グラビス", "ヘリオス", "ヴェルテクス", "オリオンMC",
          "シグマデバイス", "アルタイル", "ポラリス", "セレスタ", "ネクサスOEM", "タウラス",
          "リゲル電子", "デネブHD", "カペラ", "スピカーテック", "アンタレス", "ベガシステムズ",
          "フォーマルハウト", "アークトゥルス", "プロキオン", "カノープス", "ミラホールディングス",
          "アルデバラン", "レグルス", "ミザール", "アルビレオ", "シリウスDC", "アケルナル", "ハダル"]
customers, cid, ci = [], 0, 0
for seg, n, regions in SEGS:
    for _ in range(n):
        cid += 1
        customers.append(dict(customer_id=f"C{cid:03d}", customer_name=CNAMES[ci] + "株式会社",
                              segment=seg, region=regions[rng.integers(len(regions))]))
        ci += 1
dim_customer = pd.DataFrame(customers)

# -------------------------------------------------------------------- dim_fab
dim_fab = pd.DataFrame([
    dict(fab_id="F01", fab_name="四日市 Fab5", site="四日市", process_focus="BiCS4/BiCS5", base_yield=0.90),
    dict(fab_id="F02", fab_name="四日市 Fab6", site="四日市", process_focus="BiCS5/BiCS6", base_yield=0.92),
    dict(fab_id="F03", fab_name="四日市 Fab7", site="四日市", process_focus="BiCS6/BiCS8", base_yield=0.88),
    dict(fab_id="F04", fab_name="北上 K1", site="北上", process_focus="BiCS5/BiCS6", base_yield=0.91),
    dict(fab_id="F05", fab_name="北上 K2", site="北上", process_focus="BiCS6/BiCS8", base_yield=0.87),
])

# --------------------------------------------------------- fact_design_revisions
CHANGE_TYPES = ["設計変更", "工程変更", "部材変更", "ファームウェア更新"]
CHANGE_DESC = {
    "設計変更": ["コントローラ回路の消費電力最適化", "NANDアレイ配置の見直し", "信号品質改善のための配線変更"],
    "工程変更": ["エッチング工程条件の最適化", "成膜工程のスループット改善", "検査工程の自動化対応"],
    "部材変更": ["基板サプライヤ変更に伴う仕様更新", "樹脂封止材の変更", "DRAMベンダ追加認定"],
    "ファームウェア更新": ["ウェアレベリングアルゴリズム改善", "省電力モード制御の修正", "ホスト互換性改善"],
}
revs, rid = [], 0
for _, p in dim_product.iterrows():
    rid += 1
    revs.append(dict(revision_id=f"R{rid:04d}", product_id=p.product_id, revision_no="Rev1.0",
                     change_type="初版", description="初版リリース", eco_number=None,
                     effective_date=p.launch_date, status="適用中"))
    n_rev = rng.integers(1, 6)
    for j in range(n_rev):
        rid += 1
        ct = CHANGE_TYPES[rng.integers(4)]
        eff = p.launch_date + pd.DateOffset(months=int(rng.uniform(3, max(4, p.lifecycle_months - 3))))
        revs.append(dict(revision_id=f"R{rid:04d}", product_id=p.product_id,
                         revision_no=f"Rev{1 + (j + 1) // 2}.{(j + 1) % 2}",
                         change_type=ct, description=CHANGE_DESC[ct][rng.integers(3)],
                         eco_number=f"ECO-{2021 + eff.year - 2021}{rid:04d}",
                         effective_date=eff,
                         status="適用中" if eff <= TODAY else "承認済(未適用)"))
fact_design_revisions = pd.DataFrame(revs)

# 月次需要曲線（ランプ→ピーク→減衰）
def demand_curve(p, month):
    m = (month.year - p.launch_date.year) * 12 + (month.month - p.launch_date.month)
    if m < 0 or m > p.lifecycle_months:
        return 0.0
    x = m / p.lifecycle_months
    curve = (x ** 1.3) * ((1 - x) ** 0.9) * 6.2  # 0..~1.4
    base = {"エンタープライズSSD": 24000, "データセンターSSD": 30000, "クライアントSSD": 90000,
            "UFS": 140000, "eMMC": 110000, "NANDコンポーネント": 60000}[p.category]
    return base * curve

price_erosion = lambda p, month: p.list_price_usd * (0.985 ** max(0, (month.year - p.launch_date.year) * 12 + month.month - p.launch_date.month))
cost_decline = lambda p, month: p.unit_cost_usd * (0.990 ** max(0, (month.year - p.launch_date.year) * 12 + month.month - p.launch_date.month))

# ------------------------------------------------- fact_sales_orders / demand_plan
orders, plans, oid = [], [], 0
cust_by_seg = {s: dim_customer[dim_customer.segment == s].customer_id.tolist() for s, *_ in SEGS}
SEG_MIX = {"エンタープライズSSD": ["データセンター", "車載・産業", "代理店"],
           "データセンターSSD": ["データセンター", "代理店"],
           "クライアントSSD": ["PC OEM", "代理店"],
           "UFS": ["スマートフォンOEM", "車載・産業"],
           "eMMC": ["車載・産業", "スマートフォンOEM", "代理店"],
           "NANDコンポーネント": ["代理店", "PC OEM", "データセンター"]}
for _, p in dim_product.iterrows():
    for month in MONTHS:
        dq = demand_curve(p, month)
        plans.append(dict(plan_month=month, product_id=p.product_id,
                          planned_qty=int(dq * rng.uniform(0.92, 1.12)),
                          planned_revenue_usd=round(dq * price_erosion(p, month) * rng.uniform(0.9, 1.1), 0)))
        if dq <= 0 or month > TODAY:
            continue
        segs = SEG_MIX[p.category]
        n_ord = int(rng.uniform(14, 28))
        weights = rng.dirichlet(np.ones(n_ord) * 0.8)
        for w in weights:
            qty = int(dq * w * rng.uniform(0.85, 1.15))
            if qty < 10:
                continue
            oid += 1
            cust = rng.choice(cust_by_seg[segs[rng.integers(len(segs))]])
            price = price_erosion(p, month) * rng.uniform(0.93, 1.04)
            odate = month + pd.Timedelta(days=int(rng.uniform(0, 27)))
            orders.append(dict(order_id=f"SO{oid:07d}", order_date=odate, product_id=p.product_id,
                               customer_id=cust, order_qty=qty, unit_price_usd=round(price, 2),
                               order_amount_usd=round(price * qty, 2),
                               status=rng.choice(["出荷済", "出荷済", "出荷済", "出荷済", "生産中", "受注確定"])
                               if odate > TODAY - pd.DateOffset(months=2) else "出荷済"))
fact_sales_orders = pd.DataFrame(orders)
fact_demand_plan = pd.DataFrame(plans)

# ------------------------------------------------------- fact_manufacturing_lots
rev_lookup = fact_design_revisions.sort_values("effective_date").groupby("product_id")
lots, lid = [], 0
monthly_qty = fact_sales_orders.assign(m=fact_sales_orders.order_date.values.astype("datetime64[M]")) \
    .groupby(["product_id", "m"]).order_qty.sum().reset_index()
fab_for_gen = {"BiCS4": ["F01"], "BiCS5": ["F01", "F02", "F04"],
               "BiCS6": ["F02", "F03", "F04", "F05"], "BiCS8": ["F03", "F05"]}
fab_yield = dim_fab.set_index("fab_id").base_yield.to_dict()
for _, row in monthly_qty.iterrows():
    p = dim_product[dim_product.product_id == row.product_id].iloc[0]
    month = pd.Timestamp(row.m)
    n_lots = max(1, min(10, int(row.order_qty / 7000) + 1))
    per_lot = row.order_qty * rng.uniform(1.02, 1.12) / n_lots  # 歩留まり分多めに投入
    prevs = fact_design_revisions[(fact_design_revisions.product_id == p.product_id)
                                  & (fact_design_revisions.effective_date <= month)]
    rev = prevs.sort_values("effective_date").iloc[-1]
    maturity = max(0, (month.year - p.launch_date.year) * 12 + month.month - p.launch_date.month)
    for _ in range(n_lots):
        lid += 1
        fab = rng.choice(fab_for_gen[p.nand_generation])
        y = fab_yield[fab] + min(0.06, maturity * 0.004) + rng.normal(0, 0.015)
        if rng.random() < 0.03:  # 歩留まり異常ロット
            y -= rng.uniform(0.10, 0.25)
        y = float(np.clip(y, 0.55, 0.995))
        start = month + pd.Timedelta(days=int(rng.uniform(0, 20)))
        input_units = int(per_lot / y)
        lots.append(dict(lot_id=f"LOT{lid:06d}", product_id=p.product_id, fab_id=fab,
                         revision_id=rev.revision_id, start_date=start,
                         end_date=start + pd.Timedelta(days=int(rng.uniform(12, 30))),
                         input_units=input_units, good_units=int(input_units * y),
                         yield_rate=round(y, 4),
                         status="完了" if start < TODAY - pd.Timedelta(days=35) else "生産中"))
fact_manufacturing_lots = pd.DataFrame(lots)

# ------------------------------------------------------ fact_quality_inspections
insp, qid = [], 0
TESTS = ["電気特性試験", "信頼性試験(高温動作)", "外観検査", "ファームウェア機能試験"]
for _, lot in fact_manufacturing_lots.iterrows():
    for t in rng.choice(TESTS, size=2, replace=False):
        qid += 1
        base_ppm = (1 - lot.yield_rate) * 8000
        ppm = max(5, rng.normal(base_ppm, base_ppm * 0.3))
        insp.append(dict(inspection_id=f"QC{qid:07d}", lot_id=lot.lot_id, test_type=t,
                         inspection_date=lot.end_date, sample_size=int(rng.uniform(200, 1200)),
                         defect_ppm=round(ppm, 1),
                         result="不合格" if ppm > 2500 else ("要確認" if ppm > 1200 else "合格")))
fact_quality_inspections = pd.DataFrame(insp)

# ------------------------------------------------------------- fact_shipments
ship, sid = [], 0
lots_by_prod = {k: v.lot_id.tolist() for k, v in fact_manufacturing_lots.groupby("product_id")}
CARRIERS = ["日本ロジ急送", "グローバルフレート", "パシフィック海運", "エアカーゴJP"]
shipped = fact_sales_orders[fact_sales_orders.status == "出荷済"]
for _, o in shipped.iterrows():
    sid += 1
    cand = lots_by_prod.get(o.product_id, [None])
    ship.append(dict(shipment_id=f"SH{sid:07d}", order_id=o.order_id,
                     lot_id=cand[rng.integers(len(cand))] if cand[0] else None,
                     ship_date=o.order_date + pd.Timedelta(days=int(rng.uniform(7, 35))),
                     ship_qty=o.order_qty, carrier=CARRIERS[rng.integers(4)],
                     destination_region=dim_customer.set_index("customer_id").loc[o.customer_id, "region"]))
fact_shipments = pd.DataFrame(ship)

# ------------------------------------------------------------ fact_inventory
inv = []
SITES = ["四日市倉庫", "北上倉庫", "成田DC", "シンガポールDC"]
for _, p in dim_product.iterrows():
    lvl = 0
    for month in MONTHS:
        dq = demand_curve(p, month)
        lvl = max(0, lvl * 0.3 + dq * rng.uniform(0.25, 0.6))
        for s in SITES:
            share = rng.dirichlet(np.ones(4))[0]
            q = int(lvl * share)
            if q > 0:
                inv.append(dict(snapshot_month=month, product_id=p.product_id, site=s,
                                on_hand_qty=q,
                                inventory_value_usd=round(q * cost_decline(p, month), 0)))
fact_inventory = pd.DataFrame(inv)

# ------------------------------------------------------- fact_purchase_orders
SUPPLIERS = [("S01", "東洋シリコン", "シリコンウェハ"), ("S02", "グローバルウェハーズJP", "シリコンウェハ"),
             ("S03", "アペックスIC", "コントローラIC"), ("S04", "セントラル電子", "コントローラIC"),
             ("S05", "北陸メモリ部材", "DRAM"), ("S06", "サンライズ基板", "基板"),
             ("S07", "ミナト化成", "樹脂封止材"), ("S08", "テストマスターズ", "検査治具"),
             ("S09", "ケミカルワン", "薬液・ガス"), ("S10", "プレシジョン装置", "装置部品")]
dim_supplier = pd.DataFrame([dict(supplier_id=a, supplier_name=b, main_material=c) for a, b, c in SUPPLIERS])
pos, poid = [], 0
lot_month = fact_manufacturing_lots.assign(m=fact_manufacturing_lots.start_date.values.astype("datetime64[M]"))
fab_load = lot_month.groupby(["fab_id", "m"]).input_units.sum().reset_index()
MAT_COST = {"シリコンウェハ": 0.9, "コントローラIC": 1.4, "DRAM": 0.7, "基板": 0.35,
            "樹脂封止材": 0.12, "薬液・ガス": 0.20, "検査治具": 0.05, "装置部品": 0.10}
for _, r in fab_load.iterrows():
    for supp_id, supp_name, mat in [SUPPLIERS[i] for i in rng.choice(10, size=4, replace=False)]:
        poid += 1
        amt = r.input_units * MAT_COST[mat] * rng.uniform(0.8, 1.2)
        pos.append(dict(po_id=f"PO{poid:06d}", po_date=pd.Timestamp(r.m) + pd.Timedelta(days=int(rng.uniform(0, 25))),
                        fab_id=r.fab_id, supplier_id=supp_id, material=mat,
                        po_qty=int(r.input_units * rng.uniform(0.2, 0.5)),
                        po_amount_usd=round(amt, 0),
                        delivery_status=rng.choice(["納入済", "納入済", "納入済", "輸送中", "発注済"])))
fact_purchase_orders = pd.DataFrame(pos)

# ---------------------------------------------------------- fact_field_incidents
incidents, iid = [], 0
ITYPES = ["読み出しエラー", "コントローラ不具合", "ホスト互換性問題", "経年劣化", "ファームウェア不具合"]
bad_lots = fact_manufacturing_lots[fact_manufacturing_lots.yield_rate < 0.85]
pool = pd.concat([bad_lots, fact_manufacturing_lots.sample(frac=0.06, random_state=7)])
ship_by_lot = fact_shipments.dropna(subset=["lot_id"]).groupby("lot_id").first()
order_cust = fact_sales_orders.set_index("order_id").customer_id.to_dict()
for _, lot in pool.iterrows():
    if lot.lot_id not in ship_by_lot.index or rng.random() < 0.45:
        continue
    iid += 1
    sh = ship_by_lot.loc[lot.lot_id]
    idate = sh.ship_date + pd.Timedelta(days=int(rng.uniform(30, 400)))
    if idate > TODAY:
        continue
    sev = rng.choice(["低", "中", "高"], p=[0.55, 0.33, 0.12])
    incidents.append(dict(incident_id=f"FI{iid:05d}", product_id=lot.product_id, lot_id=lot.lot_id,
                          customer_id=order_cust.get(sh.order_id), incident_date=idate,
                          incident_type=ITYPES[rng.integers(5)], severity=sev,
                          affected_units=int(rng.uniform(1, 60) * (3 if sev == "高" else 1)),
                          resolution_status=rng.choice(["解決済", "解決済", "対応中", "原因調査中"])))
fact_field_incidents = pd.DataFrame(incidents)

# -------------------------------------------------------------------- 保存
tables = dict(dim_product=dim_product, dim_customer=dim_customer, dim_fab=dim_fab,
              dim_supplier=dim_supplier, fact_design_revisions=fact_design_revisions,
              fact_sales_orders=fact_sales_orders, fact_demand_plan=fact_demand_plan,
              fact_manufacturing_lots=fact_manufacturing_lots,
              fact_quality_inspections=fact_quality_inspections,
              fact_shipments=fact_shipments, fact_inventory=fact_inventory,
              fact_purchase_orders=fact_purchase_orders,
              fact_field_incidents=fact_field_incidents)
for name, df in tables.items():
    for c in df.columns:  # 日付をdateに正規化
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.date
    df.to_parquet(OUT / f"{name}.parquet", index=False)
    print(f"{name:28s} {len(df):>8,d} rows")
