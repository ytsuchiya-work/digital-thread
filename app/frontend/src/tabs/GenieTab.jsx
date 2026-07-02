export default function GenieTab({ config }) {
  return (
    <div className="card">
      <h2>Genie: 自然言語でデジタルスレッドを分析</h2>
      <div className="desc">
        Genieスペースをアプリに埋め込んで表示しています。
        例:「市場不良が多い製品トップ5と、その製造ロットの歩留まりを教えて」
      </div>
      <iframe className="iframe-embed" src={config.genieEmbedUrl} height={760} title="genie" />
      <div style={{ marginTop: 10 }}>
        <a href={config.genieUrl} target="_blank" rel="noreferrer">Genieスペースをワークスペースで開く ↗</a>
      </div>
    </div>
  )
}
