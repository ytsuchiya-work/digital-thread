import { useEffect, useState } from 'react'
import { api } from './api.js'
import LifecycleTab from './tabs/LifecycleTab.jsx'
import LtvTab from './tabs/LtvTab.jsx'
import ThreadTab from './tabs/ThreadTab.jsx'
import GenieTab from './tabs/GenieTab.jsx'
import GovernanceTab from './tabs/GovernanceTab.jsx'
import DemoFlowTab from './tabs/DemoFlowTab.jsx'

const TABS = [
  { id: 'flow', label: '🗺️ デモの流れ' },
  { id: 'lifecycle', label: '📈 製品ライフサイクル分析' },
  { id: 'ltv', label: '💰 収益性LTV予測' },
  { id: 'thread', label: '🌳 デジタルスレッド樹形図' },
  { id: 'genie', label: '🧞 Genie（自然言語分析）' },
  { id: 'gov', label: '🛡️ ガバナンス・環境' },
]

export default function App() {
  const [tab, setTab] = useState('flow')
  const [config, setConfig] = useState(null)
  const [products, setProducts] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api('/api/config'), api('/api/products')])
      .then(([cfg, prods]) => { setConfig(cfg); setProducts(prods) })
      .catch((e) => setError(String(e)))
  }, [])

  return (
    <div>
      <div className="header">
        <h1>🧵 デジタルスレッド分析プラットフォーム</h1>
        <div className="subtitle">
          商品開発工程（設計変更 → 製造ロット → 品質）とサプライチェーン（受注 → 調達 → 在庫 → 出荷 → 保守）を
          Unity Catalog（<code>{config?.schema ?? '...'}</code>）上で一元管理するデジタルスレッド・デモ
        </div>
        <div className="tabs">
          {TABS.map((t) => (
            <button key={t.id} className={`tab ${tab === t.id ? 'active' : ''}`}
                    onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </div>
      </div>
      <div className="page">
        {error && <div className="error">{error}</div>}
        {!config && !error && <div className="spinner">読み込み中...</div>}
        {config && tab === 'flow' && <DemoFlowTab onNavigate={setTab} />}
        {config && tab === 'lifecycle' && <LifecycleTab config={config} products={products} />}
        {config && tab === 'ltv' && <LtvTab products={products} />}
        {config && tab === 'thread' && <ThreadTab products={products} />}
        {config && tab === 'genie' && <GenieTab config={config} />}
        {config && tab === 'gov' && <GovernanceTab config={config} />}
      </div>
    </div>
  )
}
