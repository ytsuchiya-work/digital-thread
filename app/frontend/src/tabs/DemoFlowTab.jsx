const STEPS = [
  {
    tab: null, emoji: '🗺️', title: '背景の説明（このタブ）',
    duration: '2分',
    points: [
      'NEXT-K構想: エンジニアリングチェーン（企画→設計→試作→生産準備）とサプライチェーン（販売計画→調達→製造→販売→保守）のデータを1本の糸で繋ぐ',
      'このデモでは NAND/SSD 50製品 × 3年分の合成データ（受注・調達・製造ロット・品質・出荷・保守など13テーブル）を Unity Catalog で一元管理',
      'アプリ・BI・自然言語分析・MLがすべて同じガバナンス配下の同じデータを参照していることがポイント',
    ],
  },
  {
    tab: 'lifecycle', emoji: '📈', title: '製品ライフサイクル分析',
    duration: '3分',
    points: [
      '埋め込みダッシュボードで全体像: 累計売上$27億・平均粗利率22.3%、カテゴリ別の月次売上推移',
      '「製品ライフサイクルカーブ」でランプアップ→ピーク→減衰の形を確認（ライフサイクル段階別に色分け）',
      '2ページ目「製造・品質・在庫」でFab別歩留まり推移・市場不良の内訳に触れる',
      '下部のクイック分析で製品を選び、発売からの月数で正規化したカーブを重ねて比較',
    ],
  },
  {
    tab: 'genie', emoji: '🧞', title: 'Genieで自然言語アドホック分析',
    duration: '3分',
    points: [
      'ダッシュボードにない疑問はGenieへ。例:「市場不良が多い製品トップ5と、その製造ロットの歩留まりを教えて」',
      '「設計変更（ECO）が多い製品はどれ？変更タイプの内訳も」→ エンジニアリングチェーン側のデータも同じ場で分析できることを見せる',
      'テーブルコメント・PK/FK・指示（セマンティクス）を設定済みのため、日本語で正確なSQLが生成される',
    ],
  },
  {
    tab: 'thread', emoji: '🌳', title: 'デジタルスレッド樹形図でトレースバック',
    duration: '4分',
    points: [
      'Genieで見つけた不良の多い製品を選択し、「市場不良に繋がったロット」を表示',
      '市場不良（⚠️）→ 出荷（🚚）→ 製造ロット（🏭）→ 適用設計リビジョン（📐）と右から左へ遡る',
      '赤いロット（歩留まり80%未満）と不良の関係、同一リビジョン配下のロット品質のばらつきに注目',
      '「これが紙とExcelでは追えなかった一気通貫のトレーサビリティ」というメッセージ',
    ],
  },
  {
    tab: 'ltv', emoji: '💰', title: '収益性LTV予測（What-ifシミュレーション）',
    duration: '4分',
    points: [
      'まず実績LTVランキングで収益貢献の大きい製品を確認',
      '製品を選び「LTVを予測する」→ UC登録モデルがModel Serving経由で今後12ヶ月の残存粗利を予測',
      'What-ifスライダーで「歩留まり+5pt」「粗利率+3pt」を試し、改善施策の金額インパクトを提示',
      '樹形図で見つけた品質問題を直すと、LTVがいくら改善するか — 分析→意思決定の流れを閉じる',
    ],
  },
  {
    tab: 'gov', emoji: '🛡️', title: 'ガバナンス・環境（クロージング）',
    duration: '2分',
    points: [
      'ここまで使った資産（テーブル・ビュー・モデル・ダッシュボード・Genie）が全てUnity Catalogで統制されていることを示す',
      'カタログエクスプローラのリネージタブで Volume→テーブル→ビュー→BI/ML の流れを実演',
      'メトリクスビューによる指標定義の一元化（粗利率・歩留まり率の定義が全ツールで共通）に言及',
    ],
  },
]

export default function DemoFlowTab({ onNavigate }) {
  return (
    <div className="card">
      <h2>デモの流れ（推奨シナリオ・約18分）</h2>
      <div className="desc">
        「全体を俯瞰 → 疑問を深掘り → 原因をトレース → 打ち手の効果を予測 → 統制を確認」というストーリーで進めます。
        各ステップのタイトルをクリックすると該当タブに移動します。
      </div>
      {STEPS.map((s, i) => (
        <div key={i} style={{ display: 'flex', gap: 14, padding: '14px 4px',
                              borderBottom: i < STEPS.length - 1 ? '1px solid var(--border)' : 'none' }}>
          <div style={{ minWidth: 34, height: 34, borderRadius: '50%', background: 'var(--navy)',
                        color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: 700, fontSize: 15 }}>{i + 1}</div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
              {s.tab ? (
                <a href="#" style={{ fontSize: 15, fontWeight: 700, textDecoration: 'none' }}
                   onClick={(e) => { e.preventDefault(); onNavigate(s.tab) }}>
                  {s.emoji} {s.title} →
                </a>
              ) : (
                <span style={{ fontSize: 15, fontWeight: 700 }}>{s.emoji} {s.title}</span>
              )}
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>目安 {s.duration}</span>
            </div>
            <ul style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 13, lineHeight: 1.8 }}>
              {s.points.map((p, j) => <li key={j}>{p}</li>)}
            </ul>
          </div>
        </div>
      ))}
      <div className="note">
        💡 補足: LTV予測の初回実行はServingエンドポイントのスケールアップで数十秒かかることがあります。
        デモ直前に一度予測を実行して温めておくとスムーズです。
      </div>
    </div>
  )
}
