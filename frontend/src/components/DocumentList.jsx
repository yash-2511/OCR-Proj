import { useMemo, useState } from 'react'

export default function DocumentList({ documents = [], onSelect, onDelete }) {
  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')

  const filtered = useMemo(
    () => documents.filter((document) => {
      const matchesQuery = !query || [document.filename, document.doc_type, document.status].some((value) => String(value || '').toLowerCase().includes(query.toLowerCase()))
      const matchesType = typeFilter === 'all' || document.doc_type === typeFilter
      return matchesQuery && matchesType
    }),
    [documents, query, typeFilter],
  )

  return (
    <div className="panel p-5">
      <div className="mb-4 grid gap-3 md:grid-cols-[1fr_220px]">
        <input className="input rounded-2xl" placeholder="Search filename, status, or type" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select className="input rounded-2xl" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
          <option value="all">All types</option>
          <option value="invoice">Invoice</option>
          <option value="receipt">Receipt</option>
          <option value="business_card">Business card</option>
          <option value="form">Form</option>
          <option value="id_card">ID card</option>
        </select>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((document) => (
          <div key={document.id} className="card p-4 transition hover:opacity-95">
            <button className="w-full text-left" onClick={() => onSelect?.(document)}>
              <div className="flex items-center justify-between gap-3">
                <div className="truncate font-semibold" style={{ color: 'var(--text-primary)' }}>{document.filename}</div>
                <span className="rounded-full badge" style={{ background: 'var(--bg-raised)', color: 'var(--text-secondary)', padding: '4px 8px' }}>{document.status}</span>
              </div>
              <div className="mt-3 text-sm" style={{ color: 'var(--text-secondary)' }}>Type: {document.doc_type || 'unknown'}</div>
              <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>Confidence: {Math.round((document.classification_confidence || 0) * 100)}%</div>
            </button>
            {onDelete ? (
              <button className="mt-3 rounded-full badge" style={{ background: 'var(--bg-raised)', color: 'var(--text-secondary)', padding: '6px 10px' }} onClick={() => onDelete(document)}>
                Delete
              </button>
            ) : null}
          </div>
        ))}
      </div>
      {filtered.length === 0 && <p className="mt-3 text-sm" style={{ color: 'var(--text-secondary)' }}>No documents match the current filters.</p>}
    </div>
  )
}
