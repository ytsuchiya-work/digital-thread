import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import { api, fmtUsd } from '../api.js'

export default function LtvTab({ products }) {
  const [pid, setPid] = useState('')
  const [features, setFeatures] = useState(null)
  const [ranking, setRanking] = useState([])
  const [adjMargin, setAdjMargin] = useState(0)
  const [adjYield, setAdjYield] = useState(0)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => { if (products.length && !pid) setPid(products[0].product_id) }, [products])
  useEffect(() => { api('/api/ltv/ranking').then(setRanking).catch((e) => setError(String(e))) }, [])
  useEffect(() => {
    if (!pid) return
    setResult(null)
    api(`/api/ltv/features/${pid}`).then(setFeatures).catch((e) => setError(String(e)))
  }, [pid])

  const predict = async () => {
    setBusy(true); setError(null)
    try {
      setResult(await api('/api/ltv/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: pid, adj_margin_pt: adjMargin, adj_yield_pt: adjYield }),
      }))
    } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }

  // ウォーターフォール: 透明ベース + 値 の積み上げで表現
  const waterfall = result ? (() => {
    const a = result.actual_ltv, b = result.predicted_remaining
    const eff = result.what_if_remaining - result.predicted_remaining
    return [
      { name: '実績LTV', base: 0, value: a, color: '#1b3139' },
      { name: '予測 残存LTV', base: a, value: b, color: '#1b8ac4' },
      { name: 'What-if効果', base: a + b + Math.min(0, eff), value: Math.abs(eff), color: eff >= 0 ? '#00a972' : '#e0533d', signed: eff },
      { name: '予測トータルLTV', base: 0, value: a + result.what_if_remaining, color: '#ff5f46' },
    ]
  })() : []

  return (
    <div>
      <div className="card">
        <h2>製品別収益性LTV予測（モデルサービング）</h2>
        <div className="desc">
          Unity Catalog登録モデル <code>ltv_predictor</code> をサービングエンドポイント経由で呼び出し、今後12ヶ月の残存粗利（LTV）を予測します
        </div>
        <div className="row">
          <div className="col" style={{ maxWidth: 380 }}>
            <select value={pid} onChange={(e) => setPid(e.target.value)} style={{ width: '100%' }}>
              {products.map((p) => (
                <option key={p.product_id} value={p.product_id}>{p.product_name}（{p.category}）</option>
              ))}
            </select>
            {features && (
              <div className="kpis" style={{ marginTop: 12 }}>
                <div className="kpi"><div className="label">カテゴリ / NAND世代</div>
                  <div className="value small">{features.category} / {features.nand_generation}</div></div>
                <div className="kpi"><div className="label">発売からの月数</div>
                  <div className="value small">{Math.round(features.months_since_launch)} ヶ月</div></div>
                <div className="kpi"><div className="label">直近3ヶ月売上</div>
                  <div className="value small">{fmtUsd(features.rev_3m)}</div></div>
              </div>
            )}
            <div className="slider-row">
              <b>What-if シナリオ</b>
              <div>粗利率の変化: {adjMargin.toFixed(1)} pt</div>
              <input type="range" min={-10} max={10} step={0.5} value={adjMargin}
                     onChange={(e) => setAdjMargin(Number(e.target.value))} />
              <div>歩留まりの変化: {adjYield.toFixed(1)} pt</div>
              <input type="range" min={-10} max={10} step={0.5} value={adjYield}
                     onChange={(e) => setAdjYield(Number(e.target.value))} />
            </div>
            <button className="btn primary" style={{ width: '100%' }} disabled={busy || !features} onClick={predict}>
              {busy ? '予測中...' : '🔮 LTVを予測する'}
            </button>
          </div>
          <div className="col">
            {result ? (
              <>
                <div className="kpis">
                  <div className="kpi"><div className="label">実績LTV（累計粗利）</div>
                    <div className="value">{fmtUsd(result.actual_ltv)}</div></div>
                  <div className="kpi"><div className="label">予測 残存LTV（今後12ヶ月）</div>
                    <div className="value">{fmtUsd(result.predicted_remaining)}</div></div>
                  <div className="kpi"><div className="label">What-ifシナリオ適用時</div>
                    <div className="value">{fmtUsd(result.what_if_remaining)}</div></div>
                </div>
                <ResponsiveContainer width="100%" height={340}>
                  <BarChart data={waterfall} margin={{ top: 24, right: 20, bottom: 5, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 11.5 }} />
                    <YAxis tickFormatter={(v) => `$${(v / 1e6).toFixed(1)}M`} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v, n, p) => n === 'value' ? fmtUsd(p.payload.signed ?? v) : null}
                             labelStyle={{ fontSize: 12 }} />
                    <Bar dataKey="base" stackId="wf" fill="transparent" isAnimationActive={false} />
                    <Bar dataKey="value" stackId="wf" isAnimationActive={false}>
                      {waterfall.map((d, i) => <Cell key={i} fill={d.color} />)}
                      <LabelList dataKey="value" position="top" formatter={(v) => fmtUsd(v)} style={{ fontSize: 11 }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div className="note">
                  モデル: GradientBoostingRegressor（MLflowでUCに登録、テストR²=0.99）。
                  特徴量は直近3ヶ月の売上・粗利率・歩留まり・累計市場不良件数など。
                </div>
              </>
            ) : (
              <>
                <h2 style={{ fontSize: 15 }}>製品別 実績LTVランキング</h2>
                <table className="data">
                  <thead><tr>
                    <th>製品</th><th>カテゴリ</th><th>段階</th>
                    <th className="num">累計売上(M USD)</th><th className="num">累計粗利(M USD)</th><th className="num">平均粗利率(%)</th>
                  </tr></thead>
                  <tbody>
                    {ranking.map((r) => (
                      <tr key={r.product_name}>
                        <td>{r.product_name}</td><td>{r.category}</td><td>{r.lifecycle_stage}</td>
                        <td className="num">{r.lifetime_revenue_musd}</td>
                        <td className="num">{r.lifetime_margin_musd}</td>
                        <td className="num">{r.avg_margin_pct}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
            {error && <div className="error">{error}</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
