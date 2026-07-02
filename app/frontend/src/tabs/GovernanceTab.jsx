export default function GovernanceTab({ config }) {
  const rows = [
    ['Deltaテーブル (13)', '受注・調達・製造・品質・出荷・在庫・保守・設計変更・需給計画', config.catalogUrl, 'カタログエクスプローラ'],
    ['Gold層ビュー (4)', '損益・LTV実績・トレーサビリティ・歩留まり', config.catalogUrl, '同上'],
    ['メトリクスビュー (3)', '販売パフォーマンス / 製造・品質 / 市場品質（指標定義の一元化）', `${config.catalogUrl}/mv_sales_performance`, 'mv_sales_performance'],
    ['MLモデル', 'ltv_predictor（UC登録・バージョン管理）', config.modelUrl, 'モデル'],
    ['モデルサービング', `${config.servingEndpoint} エンドポイント`, config.servingUrl, 'Serving'],
    ['ダッシュボード', '製品ライフサイクル分析（2ページ）', config.dashboardUrl, 'Dashboard'],
    ['Genieスペース', '自然言語分析（セマンティクス定義済み）', config.genieUrl, 'Genie'],
  ]
  return (
    <div className="card">
      <h2>Unity Catalog によるガバナンス</h2>
      <div className="desc">
        このデモの全データ・AI資産は Unity Catalog <code>{config.schema}</code> 配下で横断的に統制されています
      </div>
      <table className="data links-table">
        <thead><tr><th>資産</th><th>内容</th><th>リンク</th></tr></thead>
        <tbody>
          {rows.map(([a, b, url, label]) => (
            <tr key={a}>
              <td><b>{a}</b></td><td>{b}</td>
              <td><a href={url} target="_blank" rel="noreferrer">{label} ↗</a></td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2 style={{ fontSize: 15, marginTop: 18 }}>検証ポイント（提案書の活動テーマとの対応）</h2>
      <ul style={{ fontSize: 13, lineHeight: 1.9 }}>
        <li><b>機能充足性</b>: デジタルスレッド構想（製品→設計→製造→出荷→保守の連鎖）をPK/FK制約付きDeltaテーブルとGold層ビューで実現</li>
        <li><b>運用性/ガバナンス</b>: テーブル・モデル・ダッシュボードの権限とリネージをUnity Catalogで一元管理</li>
        <li><b>セマンティックレイヤー</b>: メトリクスビューで指標定義（粗利率・歩留まり率など）を一元化し、Genie/BIから共通利用</li>
      </ul>
      <div className="note">
        テーブルのリネージは カタログエクスプローラ → テーブル選択 →「リネージ」タブで、
        生データ(Volume) → テーブル → Gold層ビュー → ダッシュボード/モデルの流れを確認できます。
      </div>
    </div>
  )
}
