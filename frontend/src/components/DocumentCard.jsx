import React from 'react'
import ConfidenceBadge from './ConfidenceBadge'

export default function DocumentCard({ doc, onClick }) {
  return (
    <div className="card" style={{ cursor: 'pointer' }} onClick={() => onClick && onClick(doc)}>
      <div style={{ height: 140, background: 'linear-gradient(180deg, #0f1114, #121417)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        <div className="dm-mono" style={{ fontSize: 13 }}>{(doc.type || 'PDF').slice(0, 4).toUpperCase()}</div>
      </div>
      <div style={{ padding: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 500 }}>{doc.filename}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
          <div className="dm-mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{doc.type}</div>
          <div style={{ marginLeft: 'auto' }}><ConfidenceBadge value={doc.confidence} /></div>
        </div>
      </div>
    </div>
  )
}
