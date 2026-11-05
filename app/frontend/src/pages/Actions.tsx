import { useEffect, useState } from 'react'
import { api, pct, bandClass } from '../api'
import { Card, Loading, Badge } from '../components/ui'

const STATUS_LABEL: Record<string, string> = { planned: '計画', in_progress: '実行中', done: '完了', dropped: '中止' }

/** Retention action tracker — transactional rows in Lakebase crm_ops.retention_actions. */
export default function Actions() {
  const [rows, setRows] = useState<any[] | null>(null)
  const load = () => api.actions().then((r) => setRows(r.actions)).catch(console.error)
  useEffect(() => { load() }, [])
  if (!rows) return <Loading />

  const by = (s: string) => rows.filter((r) => r.status === s).length
  return (
    <>
      <h1 className="page-title">リテンション施策トラッカー</h1>
      <p className="page-sub">AI プレイブックから登録した施策の進捗（Lakebase に記録）。登録時と現在の解約確率を並べて効果を追跡します。</p>
      <div className="kpi-grid">
        {['planned', 'in_progress', 'done', 'dropped'].map((s) => (
          <div className="kpi" key={s}><div className="label">{STATUS_LABEL[s]}</div><div className="value">{by(s)}</div></div>
        ))}
      </div>
      <Card>
        {rows.length === 0 ? <div className="empty">施策はまだありません。アカウント詳細の「AI リテンション・プレイブック」から登録できます。</div> : (
          <div className="table-wrap">
            <table className="data wide">
              <thead><tr><th>企業名</th><th>施策</th><th>優先度</th><th>担当</th><th>期限</th><th>登録時確率</th><th>現在確率</th><th>状態</th><th>出所</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.action_id}>
                    <td style={{ fontWeight: 600 }}>{r.company_name}</td>
                    <td style={{ fontSize: 12.5, minWidth: 320, maxWidth: 420, whiteSpace: "normal", lineHeight: 1.5 }}>{r.action}</td>
                    <td><Badge kind={bandClass(r.priority)}>{r.priority}</Badge></td>
                    <td>{r.owner}</td>
                    <td style={{ fontSize: 12.5 }}>{r.due_date}</td>
                    <td>{pct(r.churn_probability_at_creation)}</td>
                    <td>{pct(r.churn_probability_now)}</td>
                    <td>
                      <select className="input" style={{ padding: '2px 6px', fontSize: 12 }} value={r.status}
                        onChange={(e) => api.updateAction(r.action_id, { status: e.target.value }).then(load)}>
                        {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    </td>
                    <td style={{ fontSize: 12 }}>{r.source === 'ai_recommendation' ? 'AI' : '手動'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}
