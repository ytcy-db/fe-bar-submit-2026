import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, RotateCcw, Download, Sparkles, EyeOff, Database } from 'lucide-react'
import { api, yen, oku, pct, bandClass } from '../api'
import { Card, Loading, Badge, StatusBadge } from '../components/ui'
import AccountDrawer from '../components/AccountDrawer'

const INDUSTRIES = ['IT・Web', '製造', '小売', '金融', '医療・福祉', '人材', '教育', '物流', '外食', '建設', 'エネルギー', 'コンサル', '商社・卸', '不動産']
const STATUSES = [
  { v: 'active', l: '運用中' }, { v: 'onboarding', l: 'オンボーディング中' },
  { v: 'churn_risk', l: '解約リスク（CSM判定）' }, { v: 'churned', l: '解約済み' }, { v: 'prospect', l: '見込み' },
]
const BANDS = [{ v: '高', l: '高リスク（50%以上）' }, { v: '中', l: '中リスク（25〜50%）' }, { v: '低', l: '低リスク' }]

function RiskBar({ p }: { p: number | null }) {
  if (p == null) return <span style={{ color: 'var(--text-faint)', fontSize: 12 }}>対象外</span>
  const color = p >= 0.5 ? 'var(--danger)' : p >= 0.25 ? 'var(--warn)' : 'var(--ok)'
  return (
    <div className="progress" style={{ width: 64 }}>
      <div style={{ width: `${Math.round(p * 100)}%`, background: color }} />
    </div>
  )
}

export default function Accounts() {
  const [params] = useSearchParams()
  const [all, setAll] = useState<any[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [latency, setLatency] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [industry, setIndustry] = useState('')
  const [status, setStatus] = useState('')
  const [band, setBand] = useState(params.get('band') || '')
  const [hiddenOnly, setHiddenOnly] = useState(params.get('hidden') === '1')
  const [selected, setSelected] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    api.accounts().then((r) => { setAll(r.accounts); setLatency(r.latency_ms) }).catch(console.error).finally(() => setLoading(false))
    api.churnSummary().then(setSummary).catch(console.error)
  }
  useEffect(() => { load() }, [])

  const filtered = all.filter((a) => {
    if (q && !(a.company_name || '').includes(q)) return false
    if (industry && a.industry !== industry) return false
    if (status && a.status !== status) return false
    if (band && a.risk_band !== band) return false
    if (hiddenOnly && !a.hidden_risk) return false
    return true
  })

  const reset = () => { setQ(''); setIndustry(''); setStatus(''); setBand(''); setHiddenOnly(false) }

  const exportCsv = () => {
    const header = ['企業名', '業界', 'プラン', 'ステータス', 'ARR', '解約確率', 'リスク帯', '主要因', '更新日', '担当']
    const lines = filtered.map((a) => [a.company_name, a.industry, a.plan, a.status, a.arr_jpy,
      a.churn_probability != null ? a.churn_probability.toFixed(3) : '', a.risk_band || '',
      (a.top_drivers || []).map((d: any) => d.label).join(' / '), a.renewal_date || '', a.csm_owner].join(','))
    const csv = [header.join(','), ...lines].join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url; link.download = 'accounts_churn_risk.csv'; link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">アカウント／チャーンリスク</h1>
          <p className="page-sub">
            ML モデル（次回更新で解約する確率）と SHAP 主要因で優先順位付け。行クリックで詳細・What-if・AI 推奨アクション
          </p>
        </div>
        <button className="btn" onClick={exportCsv}><Download size={15} /> CSVダウンロード</button>
      </div>

      <div className="kpi-grid">
        <div className="kpi">
          <div className="label">高リスク（ML）</div>
          <div className="value" style={{ color: 'var(--danger)' }}>{summary?.high ?? '—'}</div>
          <div className="delta">ARR {oku(summary?.high_arr_jpy)}</div>
        </div>
        <div className="kpi">
          <div className="label">見落とし（CSM未フラグ） <EyeOff size={15} /></div>
          <div className="value" style={{ color: 'var(--danger)' }}>{summary?.hidden ?? '—'}</div>
          <div className="delta">ARR {oku(summary?.hidden_arr_jpy)}／CSMフラグ済み {summary?.csm_flagged ?? '—'} 社</div>
        </div>
        <div className="kpi">
          <div className="label">期待損失 ARR（Σ確率×ARR）</div>
          <div className="value" style={{ fontSize: 24 }}>{oku(summary?.expected_arr_at_risk_jpy)}</div>
          <div className="delta">中リスク {summary?.mid ?? '—'} 社</div>
        </div>
        <div className="kpi">
          <div className="label">スコア対象 <Database size={15} /></div>
          <div className="value">{summary?.scored ?? '—'}</div>
          <div className="delta">model v{summary?.model_version ?? '—'}・Lakebase {latency != null ? `${latency}ms` : ''}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 20, alignItems: 'start' }}>
        <Card className="card-pad">
          <label className="field-label">フリーワード</label>
          <input className="input" placeholder="企業名など" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginBottom: 16 }} />

          <FilterGroup title="見落としリスク">
            <Radio label="CSM未フラグの高リスクのみ" checked={hiddenOnly} onChange={() => setHiddenOnly(!hiddenOnly)} />
          </FilterGroup>

          <FilterGroup title="リスク帯（ML）">
            {BANDS.map((b) => (
              <Radio key={b.v} label={b.l} checked={band === b.v} onChange={() => setBand(band === b.v ? '' : b.v)} />
            ))}
          </FilterGroup>

          <FilterGroup title="取引ステータス">
            {STATUSES.map((s) => (
              <Radio key={s.v} label={s.l} checked={status === s.v} onChange={() => setStatus(status === s.v ? '' : s.v)} />
            ))}
          </FilterGroup>

          <FilterGroup title="業界">
            {INDUSTRIES.map((i) => (
              <Radio key={i} label={i} checked={industry === i} onChange={() => setIndustry(industry === i ? '' : i)} />
            ))}
          </FilterGroup>

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button className="btn primary" style={{ flex: 1 }}><Search size={15} /> 検索</button>
            <button className="btn" onClick={reset}><RotateCcw size={15} /> リセット</button>
          </div>
        </Card>

        <Card>
          {loading ? <Loading /> : (
            <div className="table-wrap">
              <table className="data wide">
                <thead>
                  <tr>
                    <th style={{ width: 140 }}>解約確率</th>
                    <th>企業名</th><th>ステータス</th><th>主要因（SHAP）</th><th>更新日</th><th>ARR</th><th>担当</th>
                    <th style={{ width: 60 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 300).map((a) => (
                    <tr key={a.account_id} className="clickable" onClick={() => setSelected(a.account_id)}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <RiskBar p={a.churn_probability} />
                          {a.risk_band && <Badge kind={bandClass(a.risk_band)}>{pct(a.churn_probability)}</Badge>}
                        </div>
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {a.company_name}
                        {a.hidden_risk && <span className="badge high" style={{ marginLeft: 6, fontSize: 10.5 }}>見落とし</span>}
                      </td>
                      <td><StatusBadge status={a.status} /></td>
                      <td style={{ fontSize: 12, maxWidth: 200, whiteSpace: 'normal', lineHeight: 1.4 }}>
                        {(a.top_drivers || []).slice(0, 2).map((d: any) => d.label.replace(/\(.*\)/, '')).join('・') || '—'}
                      </td>
                      <td style={{ fontSize: 12.5 }}>{a.end_date ? '—' : a.renewal_date || '—'}</td>
                      <td>{yen(a.arr_jpy)}</td>
                      <td>{a.csm_owner}</td>
                      <td>
                        <button className="btn sm primary" onClick={(e) => { e.stopPropagation(); setSelected(a.account_id) }}>
                          <Sparkles size={14} /> 分析
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ padding: '14px 16px', fontSize: 13, color: 'var(--text-muted)' }}>
                全 {filtered.length} 件{filtered.length > 300 ? '（上位300件を表示）' : ''}・データソース: Lakebase serving.account_360
              </div>
            </div>
          )}
        </Card>
      </div>

      {selected && <AccountDrawer accountId={selected} onClose={() => { setSelected(null) }} />}
    </>
  )
}

function FilterGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>{title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>{children}</div>
    </div>
  )
}

function Radio({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
      <input type="checkbox" checked={checked} onChange={onChange} />
      {label}
    </label>
  )
}
