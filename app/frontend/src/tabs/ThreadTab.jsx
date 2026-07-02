import { useEffect, useMemo, useState } from 'react'
import { ReactFlow, Background, Controls, MarkerType } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { api, fmtPct } from '../api.js'

const FOCUS = [
  { id: 'incidents', label: '市場不良に繋がったロット' },
  { id: 'low_yield', label: '歩留まり下位10ロット' },
  { id: 'recent', label: '直近10ロット' },
]

const nodeStyle = (bg, fg = '#1b3139') => ({
  background: bg, color: fg, border: '1px solid rgba(0,0,0,.15)',
  borderRadius: 8, padding: '8px 10px', fontSize: 11.5, width: 190,
  whiteSpace: 'pre-line', textAlign: 'left',
})

// 製品→リビジョン→ロット→出荷→市場不良 を層状レイアウトでReact Flowのnodes/edgesに変換
function buildGraph(productName, rows) {
  const X = { product: 0, rev: 260, lot: 520, ship: 780, inc: 1040 }
  const nodes = [], edges = [], seen = new Set()
  const ys = { rev: 0, lot: 0, ship: 0, inc: 0 }
  const addNode = (id, x, yKey, label, bg, fg) => {
    if (seen.has(id)) return
    seen.add(id)
    nodes.push({ id, position: { x, y: ys[yKey] }, data: { label }, style: nodeStyle(bg, fg), sourcePosition: 'right', targetPosition: 'left' })
    ys[yKey] += 86
  }
  const addEdge = (s, t) => {
    const id = `${s}->${t}`
    if (seen.has(id)) return
    seen.add(id)
    edges.push({ id, source: s, target: t, markerEnd: { type: MarkerType.ArrowClosed }, style: { stroke: '#8fa3af' } })
  }

  nodes.push({ id: 'product', position: { x: X.product, y: 200 }, data: { label: `📦 ${productName}` },
               style: nodeStyle('#1b3139', '#fff'), sourcePosition: 'right', targetPosition: 'left' })
  seen.add('product')

  for (const r of rows) {
    const revId = `rev_${r.revision_no}`
    const eco = r.eco_number ? `\n${r.eco_number}` : ''
    addNode(revId, X.rev, 'rev', `📐 ${r.revision_no}\n${r.change_type}${eco}`, '#b3d4fc')
    addEdge('product', revId)

    const y = Number(r.yield_rate)
    const lotColor = y < 0.8 ? '#f8b4b4' : y < 0.88 ? '#fce8b2' : '#cdeacd'
    addNode(r.lot_id, X.lot, 'lot', `🏭 ${r.lot_id}\n${r.fab_name}\n歩留 ${(y * 100).toFixed(1)}%`, lotColor)
    addEdge(revId, r.lot_id)

    if (r.shipment_id) {
      addNode(r.shipment_id, X.ship, 'ship',
        `🚚 ${r.shipment_id}\n${r.destination_region ?? '-'} / ${r.customer_name ?? '-'}`, '#e2d5f8')
      addEdge(r.lot_id, r.shipment_id)
      if (r.incident_id) {
        addNode(r.incident_id, X.inc, 'inc',
          `⚠️ ${r.incident_id}\n${r.incident_type}\n重大度: ${r.severity}`,
          r.severity === '高' ? '#f28b82' : '#fdd663')
        addEdge(r.shipment_id, r.incident_id)
      }
    }
  }
  return { nodes, edges }
}

export default function ThreadTab({ products }) {
  const [pid, setPid] = useState('')
  const [focus, setFocus] = useState('incidents')
  const [data, setData] = useState(null)
  const [showDetail, setShowDetail] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => { if (products.length && !pid) setPid(products[0].product_id) }, [products])
  useEffect(() => {
    if (!pid) return
    setData(null)
    api(`/api/thread/${pid}?focus=${focus}`).then(setData).catch((e) => setError(String(e)))
  }, [pid, focus])

  const productName = products.find((p) => p.product_id === pid)?.product_name ?? ''
  const graph = useMemo(
    () => (data ? buildGraph(productName, data.rows) : { nodes: [], edges: [] }),
    [data, productName])

  return (
    <div className="card">
      <h2>デジタルスレッド樹形図（トレーサビリティ）</h2>
      <div className="desc">製品 → 設計リビジョン(ECO) → 製造ロット → 品質検査 → 出荷 → 顧客 → 市場不良 を1本の糸で追跡</div>
      <select value={pid} onChange={(e) => setPid(e.target.value)}>
        {products.map((p) => <option key={p.product_id} value={p.product_id}>{p.product_name}</option>)}
      </select>
      {data && (
        <div className="kpis">
          <div className="kpi"><div className="label">設計リビジョン</div><div className="value">{data.kpi.revisions}</div></div>
          <div className="kpi"><div className="label">製造ロット</div><div className="value">{data.kpi.lots}</div></div>
          <div className="kpi"><div className="label">出荷</div><div className="value">{data.kpi.shipments}</div></div>
          <div className="kpi"><div className="label">市場不良</div><div className="value">{data.kpi.incidents}</div></div>
          <div className="kpi"><div className="label">最低ロット歩留まり</div><div className="value">{fmtPct(data.kpi.worst_yield)}</div></div>
        </div>
      )}
      <div className="radio-row">
        {FOCUS.map((f) => (
          <label key={f.id}>
            <input type="radio" checked={focus === f.id} onChange={() => setFocus(f.id)} />
            {f.label}
          </label>
        ))}
      </div>
      {error && <div className="error">{error}</div>}
      {!data && !error && <div className="spinner">トレーサビリティを検索中...</div>}
      {data && data.rows.length === 0 && (
        <div className="note">該当するロットがありません。別の表示条件を選択してください。</div>)}
      {data && data.rows.length > 0 && (
        <div className="flow-wrap">
          <ReactFlow nodes={graph.nodes} edges={graph.edges} fitView
                     nodesDraggable={false} nodesConnectable={false} proOptions={{ hideAttribution: true }}>
            <Background gap={18} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      )}
      {data && data.rows.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <button className="btn" onClick={() => setShowDetail(!showDetail)}>
            {showDetail ? '明細を閉じる' : '明細データを表示（トレーサビリティビュー）'}
          </button>
          {showDetail && (
            <div style={{ overflowX: 'auto', marginTop: 10 }}>
              <table className="data">
                <thead><tr>
                  <th>Rev</th><th>変更種別</th><th>ECO</th><th>ロット</th><th>Fab</th>
                  <th>着工日</th><th className="num">歩留まり</th><th>出荷</th><th>顧客</th><th>市場不良</th><th>重大度</th>
                </tr></thead>
                <tbody>
                  {data.rows.map((r, i) => (
                    <tr key={i}>
                      <td>{r.revision_no}</td><td>{r.change_type}</td><td>{r.eco_number ?? '-'}</td>
                      <td>{r.lot_id}</td><td>{r.fab_name}</td><td>{r.start_date}</td>
                      <td className="num">{fmtPct(r.yield_rate)}</td>
                      <td>{r.shipment_id ?? '-'}</td><td>{r.customer_name ?? '-'}</td>
                      <td>{r.incident_type ?? '-'}</td><td>{r.severity ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
