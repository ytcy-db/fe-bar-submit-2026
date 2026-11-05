import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { Sparkles, X, TrendingDown, AlertTriangle, FlaskConical, CalendarPlus, ClipboardCheck, Check } from 'lucide-react'
import { api, yen, pct, bandClass } from '../api'
import { Card, Loading, Badge } from './ui'

/** What-if levers a CSM can actually move (feature name -> UI definition). */
const LEVERS: { key: string; label: string; min: number; max: number; step: number; fmt: (v: number) => string }[] = [
  { key: 'attendance_detect_rate_4w', label: '出社検知率（センサー再設定）', min: 0, max: 1, step: 0.01, fmt: (v) => pct(v) },
  { key: 'login_rate_4w', label: 'ログイン率（利用定着支援）', min: 0, max: 1, step: 0.01, fmt: (v) => pct(v) },
  { key: 'app_config_ok_rate_4w', label: 'アプリ設定良好率', min: 0, max: 1, step: 0.01, fmt: (v) => pct(v) },
  { key: 'avg_csat_12w', label: '平均CSAT（サポート品質）', min: 1, max: 5, step: 0.1, fmt: (v) => v.toFixed(1) },
  { key: 'open_tickets', label: '未解決チケット数', min: 0, max: 10, step: 1, fmt: (v) => `${v}件` },
  { key: 'auto_renew', label: '自動更新（1=オン）', min: 0, max: 1, step: 1, fmt: (v) => (v ? 'オン' : 'オフ') },
]

export default function AccountDrawer({ accountId, onClose }: { accountId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<any>(null)
  const [rec, setRec] = useState<any>(null)
  const [loadingRec, setLoadingRec] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [levers, setLevers] = useState<Record<string, number>>({})
  const [whatIf, setWhatIf] = useState<any>(null)
  const [wiLoading, setWiLoading] = useState(false)
  const [saved, setSaved] = useState<Record<number, string>>({})

  const reload = () => api.accountDetail(accountId).then((d) => {
    setDetail(d)
    if (d.account.features) {
      const init: Record<string, number> = {}
      LEVERS.forEach((l) => { init[l.key] = Number(d.account.features[l.key] ?? (l.key === 'avg_csat_12w' ? 4 : 0)) })
      setLevers(init)
    }
  }).catch(console.error)
  useEffect(() => { reload() }, [accountId])

  const runRecommend = () => {
    setLoadingRec(true); setErr(null)
    api.recommend(accountId).then((r) => setRec(r.recommendation)).catch((e) => setErr(e.message)).finally(() => setLoadingRec(false))
  }
  const runWhatIf = () => {
    setWiLoading(true); setErr(null)
    api.whatIf(accountId, levers).then(setWhatIf).catch((e) => setErr(e.message)).finally(() => setWiLoading(false))
  }
  const saveAction = (i: number, act: any, addToSchedule: boolean) => {
    api.createAction(accountId, {
      action: act.action, priority: act.priority || '中', rationale: act.rationale, due_in_days: act.due_in_days || 7,
      source: 'ai_recommendation', add_to_schedule: addToSchedule,
    }).then(() => { setSaved((s) => ({ ...s, [i]: addToSchedule ? 'スケジュール登録済み' : '施策登録済み' })); reload() })
      .catch((e) => setErr(e.message))
  }
  const setActionStatus = (id: number, status: string) => api.updateAction(id, { status }).then(reload)

  if (!detail) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal card-pad" onClick={(e) => e.stopPropagation()}><Loading /></div>
      </div>
    )
  }

  const a = detail.account
  const score = detail.score
  const tickets = detail.tickets || []
  const actions = detail.actions || []
  const chartData = (detail.metrics || []).map((m: any) => ({
    week: String(m.week_start).slice(5, 10),
    login: Math.round(m.login_rate * 100),
    detect: Math.round(m.attendance_detect_rate * 100),
    config: Math.round(m.app_config_ok_rate * 100),
  }))
  const scoreColor = score.risk_band === '高' ? 'var(--danger)' : score.risk_band === '中' ? 'var(--warn)' : 'var(--ok)'
  const maxImpact = Math.max(0.01, ...(score.drivers || []).map((d: any) => d.impact))

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 780 }}>
        <div className="modal-head">
          <div>
            <div style={{ fontWeight: 800, fontSize: 18 }}>
              {a.company_name}
              {a.hidden_risk && <span className="badge high" style={{ marginLeft: 8, fontSize: 11 }}>CSM未フラグの高リスク</span>}
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{a.industry}・{a.plan}・{a.csm_owner}・{a.account_id}</div>
          </div>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="card-pad">
          {/* ML score + SHAP drivers */}
          <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap' }}>
            <div className="risk-meter">
              <div className="risk-num" style={{ color: scoreColor }}>{score.churn_probability != null ? pct(score.churn_probability) : '—'}</div>
              <div>
                {score.risk_band && <Badge kind={bandClass(score.risk_band)}>リスク {score.risk_band}</Badge>}
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>次回更新での解約確率（ML v{score.model_version ?? '—'}）</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-faint)', marginTop: 2 }}>旧ルールスコア: {score.rule_score ?? '—'} / 100</div>
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 260 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <TrendingDown size={15} /> 主要因（SHAP 寄与度）
              </div>
              {(score.drivers || []).length ? score.drivers.map((d: any, i: number) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: 12.5 }}>
                  <div style={{ width: 170 }}>{d.label}</div>
                  <div className="progress" style={{ flex: 1 }}><div style={{ width: `${(d.impact / maxImpact) * 100}%`, background: 'var(--danger)' }} /></div>
                  <div style={{ width: 70, textAlign: 'right', color: 'var(--text-muted)' }}>
                    {d.feature.includes('rate') ? pct(d.value) : Number(d.value).toFixed(1)}
                  </div>
                </div>
              )) : <span style={{ color: 'var(--text-faint)', fontSize: 13 }}>目立ったリスク要因はありません</span>}
            </div>
          </div>

          {/* Contract */}
          <div className="kv" style={{ marginBottom: 20 }}>
            <span className="k">契約ID</span><span>{a.contract_id || '—'}</span>
            <span className="k">利用開始日</span><span>{a.start_date || '—'}</span>
            <span className="k">次回更新日</span><span>{a.end_date ? `（${a.end_date} 解約済み）` : a.renewal_date || '—'}</span>
            <span className="k">利用サービス</span><span>{a.used_services || '—'}</span>
            <span className="k">貸出端末</span><span>{a.loaned_devices || '—'}</span>
            <span className="k">ARR</span><span>{yen(a.arr_jpy)}（自動更新: {a.auto_renew ? 'オン' : 'オフ'}）</span>
          </div>

          <h3 className="section-title">利用トレンド（直近26週・Lakebase）</h3>
          <div style={{ height: 190, marginBottom: 20 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="week" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} domain={[0, 100]} unit="%" />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, color: 'var(--text)' }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="login" name="ログイン率" stroke="#0b7a4b" fill="transparent" strokeWidth={2} />
                <Area type="monotone" dataKey="detect" name="出社検知率" stroke="#2563a8" fill="transparent" strokeWidth={2} />
                <Area type="monotone" dataKey="config" name="設定良好率" stroke="#c9861b" fill="transparent" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {tickets.length > 0 && (
            <>
              <h3 className="section-title">直近の問い合わせ（{tickets.length}件）</h3>
              <div className="pill-row" style={{ marginBottom: 20 }}>
                {tickets.slice(0, 6).map((t: any) => (
                  <span className="chip" key={t.ticket_id} title={t.status}>
                    {t.subject}{t.csat != null ? `（★${t.csat}）` : ''}
                  </span>
                ))}
              </div>
            </>
          )}

          {err && <div className="badge high" style={{ marginBottom: 12 }}><AlertTriangle size={14} /> {err}</div>}

          {/* What-if on Model Serving */}
          {a.features && (
            <Card className="card-pad" style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <h3 className="section-title" style={{ margin: 0 }}><FlaskConical size={16} /> What-if シミュレーション</h3>
                <button className="btn" onClick={runWhatIf} disabled={wiLoading}>
                  {wiLoading ? <><span className="spinner" /> 推論中…</> : 'リアルタイム再スコア'}
                </button>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
                施策で改善できる指標を動かし、Model Serving 上のモデルで解約確率を再計算します。
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 20px' }}>
                {LEVERS.map((l) => (
                  <label key={l.key} style={{ fontSize: 12.5 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>{l.label}</span><b>{l.fmt(levers[l.key] ?? 0)}</b>
                    </div>
                    <input type="range" min={l.min} max={l.max} step={l.step} value={levers[l.key] ?? 0} style={{ width: '100%' }}
                      onChange={(e) => setLevers({ ...levers, [l.key]: Number(e.target.value) })} />
                  </label>
                ))}
              </div>
              {whatIf && (
                <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginTop: 10, fontSize: 14 }}>
                  <span>現状 <b>{pct(whatIf.baseline.churn_probability, 1)}</b></span>
                  <span>→</span>
                  <span>施策後 <b style={{ color: whatIf.scenario.churn_probability < whatIf.baseline.churn_probability ? 'var(--ok)' : 'var(--danger)' }}>
                    {pct(whatIf.scenario.churn_probability, 1)}</b></span>
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                    期待損失 ARR 削減 {yen(Math.round((whatIf.baseline.churn_probability - whatIf.scenario.churn_probability) * a.arr_jpy))}
                  </span>
                </div>
              )}
            </Card>
          )}

          {/* GenAI playbook */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 className="section-title" style={{ margin: 0 }}>AI リテンション・プレイブック</h3>
            <button className="btn primary" onClick={runRecommend} disabled={loadingRec}>
              {loadingRec ? <><span className="spinner" /> 生成中…</> : <><Sparkles size={15} /> 推奨アクションを生成</>}
            </button>
          </div>

          {rec && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 20 }}>
              {rec.risk_summary && (
                <Card className="card-pad" style={{ background: 'var(--accent-soft)' }}>
                  <div style={{ fontSize: 13.5, lineHeight: 1.7 }}>{rec.risk_summary}</div>
                </Card>
              )}
              {rec.recommended_actions?.map((act: any, i: number) => (
                <Card className="card-pad" key={i}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                    <div style={{ fontWeight: 600, fontSize: 13.5 }}>{act.action}</div>
                    <Badge kind={bandClass(act.priority)}>{act.priority}</Badge>
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)', marginTop: 6 }}>
                    {act.owner && <>担当: {act.owner}・</>}{act.due_in_days && <>期限: {act.due_in_days}日以内・</>}根拠: {act.rationale}
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    {saved[i] ? <span className="badge low"><Check size={13} /> {saved[i]}</span> : (
                      <>
                        <button className="btn sm" onClick={() => saveAction(i, act, false)}><ClipboardCheck size={13} /> 施策として登録</button>
                        <button className="btn sm" onClick={() => saveAction(i, act, true)}><CalendarPlus size={13} /> スケジュールに追加</button>
                      </>
                    )}
                  </div>
                </Card>
              ))}
              {rec.talk_track && (
                <Card className="card-pad" style={{ borderLeft: '3px solid var(--accent)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 4 }}>💬 トークスクリプト</div>
                  <div style={{ fontSize: 13.5, fontStyle: 'italic' }}>「{rec.talk_track}」</div>
                </Card>
              )}
              {rec.success_metric && (
                <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>📏 効果測定: {rec.success_metric}</div>
              )}
            </div>
          )}

          {/* Retention actions (Lakebase crm_ops.retention_actions) */}
          <h3 className="section-title">登録済みリテンション施策（{actions.length}件）</h3>
          {actions.length === 0 ? <div style={{ fontSize: 13, color: 'var(--text-faint)' }}>まだ施策はありません</div> : (
            <table className="data">
              <thead><tr><th>施策</th><th>優先度</th><th>期限</th><th>登録時確率</th><th>状態</th></tr></thead>
              <tbody>
                {actions.map((x: any) => (
                  <tr key={x.action_id}>
                    <td style={{ fontSize: 12.5, whiteSpace: "normal", lineHeight: 1.5 }}>{x.action}</td>
                    <td><Badge kind={bandClass(x.priority)}>{x.priority}</Badge></td>
                    <td style={{ fontSize: 12.5 }}>{x.due_date}</td>
                    <td style={{ fontSize: 12.5 }}>{pct(x.churn_probability_at_creation)}</td>
                    <td>
                      <select className="input" style={{ padding: '2px 6px', fontSize: 12 }} value={x.status} onChange={(e) => setActionStatus(x.action_id, e.target.value)}>
                        <option value="planned">計画</option><option value="in_progress">実行中</option>
                        <option value="done">完了</option><option value="dropped">中止</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
