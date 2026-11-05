import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'
import { api, oku, pct } from '../api'
import { Card, Loading } from '../components/ui'

/** ML model quality (out-of-time) and the business case in the buyer's KPIs. Source: UC gold tables via SQL warehouse. */
export default function Impact() {
  const [d, setD] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { api.modelSummary().then(setD).catch((e) => setErr(e.message)) }, [])
  if (err) return <div className="badge high">{err}</div>
  if (!d) return <Loading />
  const m = d.metrics, b = d.impact

  const coverage = [
    { name: '顧客の解約申し出（現状）', v: 0, note: `申し出は解約者の${pct(m.cancel_ticket_share_of_churners)}・更新${m.cancel_ticket_median_days_before_renewal}日前` },
    { name: '旧ルールスコア', v: m.rules_arr_recall_at_t90 },
    { name: 'ML モデル', v: m.ml_arr_recall_at_t90 },
  ]
  const imp = (d.importance || []).map((r: any) => ({ name: r.label_ja || r.feature, v: r.importance }))

  return (
    <>
      <h1 className="page-title">ML・ビジネス効果</h1>
      <p className="page-sub">
        モデル {d.model}（Unity Catalog 登録・Model Serving 配信）の検証結果。学習＝2026-05-01 より前に結果が判明した更新、検証＝それ以降の更新（アウトオブタイム）
      </p>

      <div className="kpi-grid">
        <Kpi label="GRR（直近12ヶ月）" value={pct(b.gross_revenue_retention_12m, 1)} sub={`解約 ${b.churned_logos_12m} 社・${oku(b.churned_arr_12m_jpy)}`} />
        <Kpi label="GRR（ML 早期警戒あり）" value={pct(b.grr_with_ml, 1)} sub={`+${b.grr_uplift_pts?.toFixed(1)} pt`} good />
        <Kpi label="年間 ARR 防衛額（増分）" value={oku(b.incremental_arr_saved_vs_status_quo_jpy)} sub={`現状 ${oku(b.arr_saved_status_quo_jpy)} → ML ${oku(b.arr_saved_with_ml_jpy)}`} good />
        <Kpi label="今、CSM が見落としている高リスク" value={`${b.hidden_risk_accounts_now} 社`} sub={`ARR ${oku(b.hidden_risk_arr_now_jpy)}`} danger />
      </div>

      <div className="grid-2">
        <Card className="card-pad">
          <h3 className="section-title">更新 90 日前時点で捕捉できた解約 ARR の割合</h3>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
            検証期間の解約 {m.churned_renewals} 件（{oku(m.churned_arr_jpy)}）。ML とルールは同じアラート件数（{m.ml_alerts_at_t90} 件）で比較
          </div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={coverage} layout="vertical" margin={{ left: 40, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => pct(v)} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <Tooltip formatter={(v: any) => pct(v, 1)} />
                <Bar dataKey="v" radius={[0, 6, 6, 0]} isAnimationActive={false}>
                  {coverage.map((_, i) => <Cell key={i} fill={i === 2 ? '#0b7a4b' : i === 1 ? '#c9861b' : '#9aa5a0'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{coverage[0].note}</div>
        </Card>

        <Card className="card-pad">
          <h3 className="section-title">モデル精度（アウトオブタイム検証）</h3>
          <table className="data">
            <thead><tr><th>指標</th><th>ML モデル</th><th>旧ルール</th></tr></thead>
            <tbody>
              <tr><td>ROC AUC</td><td><b>{m.test_auc?.toFixed(3)}</b></td><td>{m.rules_auc?.toFixed(3)}</td></tr>
              <tr><td>PR AUC（基準率 {pct(m.base_rate)}）</td><td><b>{m.test_pr_auc?.toFixed(3)}</b></td><td>{m.rules_pr_auc?.toFixed(3)}</td></tr>
              <tr><td>上位10%の適合率</td><td><b>{pct(m.precision_at_top10pct)}</b></td><td>{pct(m.rules_precision_at_top10pct)}</td></tr>
              <tr><td>上位20%の再現率</td><td><b>{pct(m.recall_at_top20pct)}</b></td><td>{pct(m.rules_recall_at_top20pct)}</td></tr>
              <tr><td>T-90 アラート適合率</td><td><b>{pct(m.ml_precision_at_t90)}</b></td><td>{pct(m.rules_precision_at_t90)}</td></tr>
            </tbody>
          </table>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 10 }}>
            前提: 90日前に着手した施策の保全率 {pct(b.save_rate_early)}、解約申し出後の保全率 {pct(b.save_rate_late)}（gold_business_impact で変更可能）
          </div>
        </Card>
      </div>

      <Card className="card-pad" style={{ marginTop: 20 }}>
        <h3 className="section-title">特徴量重要度（どのシグナルが解約を予兆するか）</h3>
        <div style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={imp} layout="vertical" margin={{ left: 60, right: 30 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis type="category" dataKey="name" width={190} tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <Tooltip />
              <Bar dataKey="v" fill="#2563a8" radius={[0, 6, 6, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </>
  )
}

function Kpi({ label, value, sub, good, danger }: { label: string; value: string; sub?: string; good?: boolean; danger?: boolean }) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className="value" style={{ fontSize: 26, color: good ? 'var(--ok)' : danger ? 'var(--danger)' : undefined }}>{value}</div>
      {sub && <div className="delta">{sub}</div>}
    </div>
  )
}
