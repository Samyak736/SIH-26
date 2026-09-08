import React, { useState, useEffect } from 'react'

const SIF_COLORS = {
  'High-Confidence SIF': '#dc2626',
  'Potential SIF': '#f59e0b',
  'Non-SIF': '#16a34a',
}

function KpiCard({ label, value, sub }) {
  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: 12, minWidth: 160, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: '#0f172a' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

function ScoreBadge({ score }) {
  const bg = score >= 80 ? '#dc2626' : score >= 50 ? '#f97316' : '#6b7280'
  return <span style={{ background: bg, color: '#fff', padding: '4px 8px', borderRadius: 6, fontWeight: 700 }}>{score}</span>
}

function TrendChart({ data = [] }) {
  if (!data || !data.length) return <div style={{ height: 120, display: 'flex', alignItems: 'center', color: '#94a3b8' }}>No trend data</div>
  const W = 420, H = 120, PAD = 20
  const max = Math.max(...data.map((d) => d.total || 0), 1)
  const x = (i) => PAD + (i / (data.length - 1)) * (W - PAD * 2)
  const y = (v) => H - PAD - (v / max) * (H - PAD * 2)
  const path = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${x(i)} ${y(d.total)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 140 }}>
      <path d={path} fill="none" stroke="#94a3b8" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      {data.map((d, i) => (<circle key={i} cx={x(i)} cy={y(d.total)} r={3} fill="#0f172a" />))}
    </svg>
  )
}

export default function SIFDashboardFixed() {
  const [data, setData] = useState(null)
  useEffect(() => {
    fetch('/api/data')
      .then((r) => r.json())
      .then((d) => setData(d))
      .catch(() => setData(null))
  }, [])

  if (!data) return <div style={{ padding: 24 }}>Loading dashboard data…</div>

  const k = data.kpi || {}

  return (
    <div style={{ padding: 24, fontFamily: "Inter, system-ui, sans-serif" }}>
      <h2 style={{ marginTop: 0 }}>OIL SIF Dashboard</h2>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 18 }}>
        <KpiCard label="Total Reports" value={k.total_reports} />
        <KpiCard label="SIF Potential" value={k.sif_potential_reports} sub={`${k.sif_rate_pct}% of total`} />
        <KpiCard label="High SIF Risk (70+)" value={k.high_sif_risk_reports} />
        <KpiCard label="High-Potential No Injury" value={k.high_potential_no_injury} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16 }}>
        <div style={{ background: '#fff', padding: 16, borderRadius: 10 }}>
          <div style={{ fontSize: 13, color: '#374151', fontWeight: 700, marginBottom: 8 }}>SIF Precursor Trend</div>
          <TrendChart data={data.trend} />
        </div>
        <div style={{ background: '#fff', padding: 16, borderRadius: 10 }}>
          <div style={{ fontSize: 13, color: '#374151', fontWeight: 700, marginBottom: 10 }}>Top Risk Site</div>
          <div style={{ fontSize: 16, fontWeight: 800 }}>{k.highest_risk_site}</div>
          <div style={{ marginTop: 12 }}><strong>Top failed barrier:</strong> {k.top_failed_barrier}</div>
        </div>
      </div>
    </div>
  )
}
