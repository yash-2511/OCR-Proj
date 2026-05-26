import React from 'react'

export default function MetricCard({ label, value, trend }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="dm-mono" style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 600, marginTop: 8 }}>{value}</div>
      {trend ? <div className="dm-mono" style={{ fontSize: 12, marginTop: 6 }}>{trend}</div> : null}
    </div>
  )
}
