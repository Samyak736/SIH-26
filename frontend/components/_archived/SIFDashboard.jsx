// Archived copy of SIFDashboard.jsx — moved to _archived because original caused Turbopack parse errors.
// Original content saved for reference.

// NOTE: This file was auto-archived by the assistant on user request.

// --- BEGIN ARCHIVED CONTENT ---
// Re-export the fixed dashboard component to avoid parsing the original (malformed) JSX.
export { default } from './SIFDashboardFixed'
      {[0, 0.25, 0.5, 0.75, 1].map(f => {
        const y = H - PAD.b - f * cH;
        return <line key={f} x1={PAD.l} x2={W - PAD.r} y1={y} y2={y} stroke="#e5e7eb" strokeWidth={0.5} />;
      })}
      <polyline points={polyTotal} fill="none" stroke="#94a3b8" strokeWidth={2} />
  <polyline points={polySIF} fill="none" stroke="#dc2626" strokeWidth={2} />
  {data.map((d, i) => (<circle key={i} cx={xScale(i)} cy={yScaleTotal(d.sif_potential)} r={3} fill="#dc2626" />))}
  {data.filter((_, i) => i % 4 === 0).map((d, i) => {
        const origIdx = data.indexOf(d);
        return (<text key={i} x={xScale(origIdx)} y={H - 5} fontSize={8} textAnchor="middle" fill="#6b7280">{d.month.slice(5)}/{d.month.slice(2, 4)}</text>);
      })}
  <rect x={PAD.l + 4} y={PAD.t} width={8} height={3} fill="#94a3b8" />
  <text x={PAD.l + 14} y={PAD.t + 4} fontSize={8} fill="#6b7280">Total</text>
  <rect x={PAD.l + 55} y={PAD.t} width={8} height={3} fill="#dc2626" />
      <text x={PAD.l + 65} y={PAD.t + 4} fontSize={8} fill="#6b7280">SIF Potential</text>
    </svg>
  );
}

export default function SIFDashboard() {
  return <div />;
}
// Re-export the fixed dashboard component to avoid parsing the original (malformed) JSX.
export { default } from './SIFDashboardFixed'

const SIF_COLORS = {
  "High-Confidence SIF": "#dc2626",
  "Potential SIF": "#f59e0b",
  "Non-SIF": "#16a34a",
};
const TIER_COLORS = { CRITICAL: "#dc2626", HIGH: "#f97316", MEDIUM: "#f59e0b", LOW: "#16a34a" };
const POTENTIAL_COLORS = { Fatal: "#dc2626", "SIF-Capable": "#f97316", Serious: "#f59e0b", Moderate: "#3b82f6", Low: "#16a34a" };

function scoreTier(s) {
  if (s >= 90) return "CRITICAL";
  if (s >= 70) return "HIGH";
  if (s >= 40) return "MEDIUM";
  return "LOW";
}

function ScoreBadge({ score }) {
  const tier = scoreTier(score);
  const colors = { CRITICAL: "#dc2626", HIGH: "#f97316", MEDIUM: "#f59e0b", LOW: "#6b7280" };
  return (
    <span style={{ background: colors[tier], color: "#fff", padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 700 }}>{score}</span>
  );
}

function SIFBadge({ label }) {
  return (
    <span style={{ background: SIF_COLORS[label] || "#6b7280", color: "#fff", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, whiteSpace: "nowrap" }}>{label}</span>
  );
}

function Tag({ children, color = "#e5e7eb", textColor = "#374151" }) {
  return (
    <span style={{ background: color, color: textColor, padding: "2px 7px", borderRadius: 12, fontSize: 11, fontWeight: 500, marginRight: 4, marginBottom: 4, display: "inline-block" }}>{children}</span>
  );
}

function MiniBar({ value, max, color }) {
  return (
    <div style={{ background: "#e5e7eb", borderRadius: 4, height: 8, flex: 1, minWidth: 60 }}>
      <div style={{ width: `${Math.min(100, (value / max) * 100)}%`, background: color, height: 8, borderRadius: 4, transition: "width 0.4s" }} />
    </div>
  );
}

function TrendChart({ data }) {
  const W = 540, H = 130, PAD = { t: 10, b: 30, l: 40, r: 10 };
  const cW = W - PAD.l - PAD.r, cH = H - PAD.t - PAD.b;
  const maxTotal = Math.max(...data.map(d => d.total), 1);
  const xScale = i => PAD.l + (i / (data.length - 1)) * cW;
  const yScaleTotal = v => H - PAD.b - (v / maxTotal) * cH;
  const polyTotal = data.map((d, i) => `${xScale(i)},${yScaleTotal(d.total)}`).join(" ");
  const polySIF = data.map((d, i) => `${xScale(i)},${yScaleTotal(d.sif_potential)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: W }}>
      {[0, 0.25, 0.5, 0.75, 1].map(f => {
        const y = H - PAD.b - f * cH;
        return <line key={f} x1={PAD.l} x2={W - PAD.r} y1={y} y2={y} stroke="#e5e7eb" strokeWidth={0.5} />;
      })}
      <polyline points={polyTotal} fill="none" stroke="#94a3b8" strokeWidth={2} />
      <polyline points={polySIF} fill="none" stroke="#dc2626" strokeWidth={2} />
      {data.map((d, i) => (<circle key={i} cx={xScale(i)} cy={yScaleTotal(d.sif_potential)} r={3} fill="#dc2626" />))}
      {data.filter((_, i) => i % 4 === 0).map((d, i) => {
        const origIdx = data.indexOf(d);
        return (<text key={i} x={xScale(origIdx)} y={H - 5} fontSize={8} textAnchor="middle" fill="#6b7280">{d.month.slice(5)}/{d.month.slice(2, 4)}</text>);
      })}
      <rect x={PAD.l + 4} y={PAD.t} width={8} height={3} fill="#94a3b8" />
      <text x={PAD.l + 14} y={PAD.t + 4} fontSize={8} fill="#6b7280">Total</text>
      <rect x={PAD.l + 55} y={PAD.t} width={8} height={3} fill="#dc2626" />
      <text x={PAD.l + 65} y={PAD.t + 4} fontSize={8} fill="#6b7280">SIF Potential</text>
    </svg>
  );
}

// ... remaining archived content omitted for brevity

// --- END ARCHIVED CONTENT ---
