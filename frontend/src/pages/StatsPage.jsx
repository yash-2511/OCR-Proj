import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import StatsPanel from '../components/StatsPanel'
import { getStats, listDocuments } from '../services/api'

export default function StatsPage() {
  const [documents, setDocuments] = useState([])
  const [summary, setSummary] = useState({ documents: 0, batches: 0 })

  useEffect(() => {
    Promise.all([listDocuments(), getStats()])
      .then(([docsResponse, statsResponse]) => {
        setDocuments(docsResponse.data || docsResponse || [])
        const payload = statsResponse.data || statsResponse || {}
        setSummary({
          documents: payload.documents || 0,
          batches: payload.batches || 0,
        })
      })
      .catch((error) => toast.error(error.message))
  }, [])

  const totals = useMemo(() => {
    const extracted = documents.filter((doc) => (doc.status || '').toLowerCase() === 'extracted').length
    const review = documents.filter((doc) => (doc.status || '').toLowerCase().includes('review')).length
    const queued = documents.filter((doc) => (doc.status || '').toLowerCase() === 'queued').length
    return { extracted, review, queued }
  }, [documents])

  return (
    <div className="space-y-6">
      <div className="panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Analytics overview</h2>
            <p className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>A live snapshot of document intake, extraction, and review status across the workspace.</p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <Metric label="Documents" value={summary.documents} />
            <Metric label="Batches" value={summary.batches} />
            <Metric label="Extracted" value={totals.extracted} />
          </div>
        </div>
      </div>

      <StatsPanel documents={documents} />

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Needs review" value={totals.review} note="Items waiting on manual verification" />
        <MetricCard label="Queued" value={totals.queued} note="Items still waiting to be processed" />
        <MetricCard label="Processed total" value={documents.length} note="All documents currently known to the system" />
      </div>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="card px-4 py-3 min-w-[110px]" style={{ background: 'linear-gradient(180deg, var(--bg-raised), var(--bg-surface))', borderColor: 'var(--border-strong)' }}>
      <div className="dm-mono" style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ marginTop: 6, fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</div>
    </div>
  )
}

function MetricCard({ label, value, note }) {
  return (
    <div className="card p-5" style={{ background: 'linear-gradient(180deg, var(--bg-raised), var(--bg-surface))', borderColor: 'var(--border-strong)' }}>
      <div className="dm-mono" style={{ color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase' }}>{label}</div>
      <div style={{ marginTop: 10, fontSize: 30, fontWeight: 700, color: 'var(--text-primary)' }}>{value}</div>
      <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>{note}</p>
    </div>
  )
}