import React, { useState } from 'react'

const SAMPLE = {
  kpi: { total_reports: 12, sif_potential_reports: 5, high_sif_risk_reports: 2, sif_rate_pct: 41 },
  reports: [
    { id: 'R-001', date: '2025-01-12', site: 'Site_A', sif_score: 82, sif_label: 'High-Confidence SIF', activity: 'Lifting', text: 'Crane near-miss', actual_severity: 'No Injury', lsr: [], hazards: ['Struck-by'], barriers_failed: [] },
    { id: 'R-002', date: '2025-02-05', site: 'Site_B', sif_score: 45, sif_label: 'Potential SIF', activity: 'Maintenance', text: 'Energy isolation not followed', actual_severity: 'Medical Treatment', lsr: ['Energy Isolation'], hazards: ['Energy'], barriers_failed: ['Lockout'] },
  ]
}

export default function SIFDashboard() {
  const [selected, setSelected] = useState(null)
  return (
    <div style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
      <h1 style={{ marginBottom: 8 }}>OIL SIF Intelligence — Demo</h1>
      <div style={{ display: 'flex', gap: 12 }}>
        <div style={{ padding: 12, borderRadius: 8, background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{SAMPLE.kpi.total_reports}</div>
          <div style={{ fontSize: 12, color: '#64748b' }}>Total reports</div>
        </div>
        <div style={{ padding: 12, borderRadius: 8, background: '#fff', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{SAMPLE.kpi.sif_potential_reports}</div>
          <div style={{ fontSize: 12, color: '#64748b' }}>SIF potential</div>
        </div>
      </div>

      <h2 style={{ marginTop: 18 }}>Recent reports</h2>
      <div>
        {SAMPLE.reports.map(r => (
          <div key={r.id} onClick={() => setSelected(r)} style={{ background: '#fff', padding: 10, borderRadius: 8, marginBottom: 8, cursor: 'pointer' }}>
            <div style={{ fontWeight: 700 }}>{r.id} · {r.site} · {r.sif_score}</div>
            <div style={{ color: '#475569' }}>{r.activity} — {r.text}</div>
          </div>
        ))}
      </div>

      {selected && (
        <div style={{ marginTop: 12, padding: 12, background: '#f8fafc', borderRadius: 8 }}>
          <div style={{ fontWeight: 800 }}>{selected.id} · {selected.activity}</div>
          <div style={{ marginTop: 6 }}>{selected.text}</div>
          <div style={{ marginTop: 8, color: '#64748b' }}>Severity: {selected.actual_severity}</div>
        </div>
      )}
    </div>
  )
}
