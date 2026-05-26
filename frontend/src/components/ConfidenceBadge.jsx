import React from 'react'

function colorFor(conf) {
  if (conf >= 85) return 'var(--confidence-high)'
  if (conf >= 60) return 'var(--confidence-medium)'
  return 'var(--confidence-low)'
}

export default function ConfidenceBadge({ value }) {
  const color = colorFor(value)
  return (
    <div className="dm-mono" style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span style={{ width: 8, height: 8, borderRadius: 4, background: color, display: 'inline-block' }} />
      <span style={{ fontSize: 12 }}>{value ?? '--'}%</span>
    </div>
  )
}
