import { useEffect, useMemo, useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { api, fmtUsd } from '../api.js'

const COLORS = ['#ff5f46', '#1b8ac4', '#00a972', '#f2a93b', '#8b5cd6', '#5f7281']

export default function LifecycleTab({ config, products }) {
  const [selected, setSelected] = useState([])
  const [series, setSeries] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (products.length && selected.length === 0) {
      setSelected(products.filter((p) => p.category === 'エンタープライズSSD').slice(0, 5).map((p) => p.product_id))
    }
  }, [products])

  useEffect(() => {
    if (!selected.length) { setSeries([]); return }
    api(`/api/lifecycle?ids=${selected.join(',')}`)
      .then(setSeries).catch((e) => setError(String(e)))
  }, [selected])

  // 発売からの月数 × 製品ごとの売上 をピボット
  const chartData = useMemo(() => {
    const byMonth = new Map()
    for (const r of series) {
      const m = Number(r.months_since_launch)
      if (!byMonth.has(m)) byMonth.set(m, { month: m })
      byMonth.get(m)[r.product_name] = Number(r.revenue_usd)
    }
    return [...byMonth.values()].sort((a, b) => a.month - b.month)
  }, [series])

  const names = useMemo(
    () => [...new Set(series.map((r) => r.product_name))], [series])

  const toggle = (pid) =>
    setSelected((cur) => cur.includes(pid)
      ? cur.filter((x) => x !== pid)
      : cur.length < 8 ? [...cur, pid] : cur)

  return (
    <div>
      <div className="card">
        <h2>製品ライフサイクル・収益性ダッシュボード</h2>
        <div className="desc">AI/BI Dashboard をアプリに埋め込んで表示しています（データはUnity Catalogメトリクスビュー/Gold層ビュー）</div>
        <iframe className="iframe-embed" src={config.dashboardEmbedUrl} height={820} title="dashboard" />
      </div>

      <div className="card">
        <h2>クイック分析: 製品別ライフサイクルカーブ</h2>
        <div className="desc">発売からの月数で正規化した月次売上カーブを重ね合わせ（最大8製品）</div>
        <div className="chips">
          {products.map((p) => (
            <span key={p.product_id}
                  className={`chip ${selected.includes(p.product_id) ? 'on' : ''}`}
                  onClick={() => toggle(p.product_id)}>
              {p.product_name}
            </span>
          ))}
        </div>
        {error && <div className="error">{error}</div>}
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" label={{ value: '発売からの月数', position: 'insideBottom', offset: -5, fontSize: 12 }} tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => fmtUsd(v)} labelFormatter={(l) => `発売${l}ヶ月目`} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {names.map((n, i) => (
              <Line key={n} dataKey={n} type="monotone" stroke={COLORS[i % COLORS.length]}
                    dot={false} strokeWidth={2} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
