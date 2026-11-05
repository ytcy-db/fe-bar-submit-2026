import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import { LogIn, UserPlus, MapPin, Download, Settings2, ArrowRight } from 'lucide-react'
import { api, oku } from '../api'
import { Card, Loading } from '../components/ui'

const KPI_DEFS: { key: string; label: string; icon: any }[] = [
  { key: 'login_rate', label: 'ログイン率', icon: LogIn },
  { key: 'signup_rate', label: '登録率', icon: UserPlus },
  { key: 'attendance_detect_rate', label: '出社検知率', icon: MapPin },
  { key: 'install_rate', label: 'インストール率', icon: Download },
  { key: 'app_config_ok_rate', label: 'アプリ設定良好率', icon: Settings2 },
]

export default function Dashboard() {
  const nav = useNavigate()
  const [data, setData] = useState<any>(null)
  const [trend, setTrend] = useState<any[]>([])

  useEffect(() => {
    api.dashboardKpis().then(setData).catch(console.error)
    api.kpiTrend().then((r) => setTrend(r.trend)).catch(console.error)
  }, [])

  if (!data) return <Loading />

  const { kpis, kpis_prev, counts, open_tickets, latency } = data

  return (
    <>
      <h1 className="page-title">ダッシュボード</h1>
      <p className="page-sub">
        CloudNest OfficePulse — CS/AM チームの主要指標と解約リスクの俯瞰
        {latency && <span style={{ marginLeft: 10, fontSize: 12 }}>（UC gold via SQL Warehouse {latency.sql_warehouse_ms}ms ／ Lakebase {latency.lakebase_ms}ms）</span>}
      </p>

      {/* 5 大 KPI */}
      <div className="kpi-grid">
        {KPI_DEFS.map(({ key, label, icon: Icon }) => {
          const val = kpis[key]
          const prev = kpis_prev?.[key]
          const delta = prev != null ? +(val - prev).toFixed(1) : null
          return (
            <div className="kpi" key={key}>
              <div className="label">{label} <Icon size={16} /></div>
              <div className="value">{val != null ? `${val}%` : '—'}</div>
              {delta != null && (
                <div className={`delta ${delta >= 0 ? 'up' : 'down'}`}>
                  {delta >= 0 ? '▲' : '▼'} {Math.abs(delta)}pt（前週比）
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* サマリカウント */}
      <div className="kpi-grid">
        <SummaryTile label="アカウント数" value={counts.total} />
        <SummaryTile label="運用中" value={counts.active} />
        <SummaryTile label="オンボーディング中" value={counts.onboarding} />
        <SummaryTile label="解約リスク（CSM判定）" value={counts.churn_risk} />
        <SummaryTile label="高リスク（ML）" value={counts.ml_high} danger onClick={() => nav('/accounts?band=高')} />
        <SummaryTile label="うち CSM 未フラグ" value={counts.ml_hidden} danger onClick={() => nav('/accounts?hidden=1')} />
        <SummaryTile label="未解決チケット" value={open_tickets} />
      </div>

      <div className="kpi-grid">
        <div className="kpi"><div className="label">稼働中 ARR</div><div className="value" style={{ fontSize: 24 }}>{oku(counts.live_arr_jpy)}</div></div>
        <div className="kpi"><div className="label">高リスク ARR（ML）</div><div className="value" style={{ fontSize: 24, color: 'var(--danger)' }}>{oku(counts.high_risk_arr_jpy)}</div></div>
        <div className="kpi"><div className="label">期待損失 ARR（Σ確率×ARR）</div><div className="value" style={{ fontSize: 24 }}>{oku(counts.expected_arr_at_risk_jpy)}</div></div>
      </div>

      <div className="grid-2">
        <Card className="card-pad">
          <h3 className="section-title">主要 KPI の週次トレンド（全社平均）</h3>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="week" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} domain={[0, 100]} unit="%" />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12, color: 'var(--text)' }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="login_rate" name="ログイン率" stroke="#0b7a4b" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="attendance_detect_rate" name="出社検知率" stroke="#2563a8" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="install_rate" name="インストール率" stroke="#c9861b" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="app_config_ok_rate" name="設定良好率" stroke="#9b59b6" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="card-pad">
          <h3 className="section-title">クイックアクセス</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <QuickLink label="解約リスク（ML 高リスク）を確認" onClick={() => nav('/accounts?band=高')} />
            <QuickLink label="CSM が見落としている高リスク顧客" onClick={() => nav('/accounts?hidden=1')} />
            <QuickLink label="ML・ビジネス効果" onClick={() => nav('/impact')} />
            <QuickLink label="アカウント一覧を見る" onClick={() => nav('/accounts')} />
            <QuickLink label="ヘルプデスク（チケット）" onClick={() => nav('/tickets')} />
            <QuickLink label="今週のスケジュール" onClick={() => nav('/schedule')} />
            <QuickLink label="Genie で自然言語分析" onClick={() => nav('/genie')} />
          </div>
        </Card>
      </div>
    </>
  )
}

function SummaryTile({ label, value, danger, onClick }: { label: string; value: number; danger?: boolean; onClick?: () => void }) {
  return (
    <div className="kpi" onClick={onClick} style={onClick ? { cursor: 'pointer' } : {}}>
      <div className="label">{label}</div>
      <div className="value" style={danger && value > 0 ? { color: 'var(--danger)' } : {}}>{value ?? '—'}</div>
    </div>
  )
}

function QuickLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button className="quicklink" onClick={onClick} style={{ cursor: 'pointer' }}>
      <span style={{ fontWeight: 600 }}>{label}</span>
      <ArrowRight size={17} />
    </button>
  )
}
