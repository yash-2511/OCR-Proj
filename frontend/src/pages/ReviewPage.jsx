import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import DocumentViewer from '../components/DocumentViewer'
import PreprocessPreview from '../components/PreprocessPreview'
import ExportPanel from '../components/ExportPanel'
import { getDocument, getDocumentInsights } from '../services/api'

export default function ReviewPage() {
  const location = useLocation()
  const [document, setDocument] = useState(null)
  const [tables, setTables] = useState([])
  const [insights, setInsights] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const documentId = location.state?.documentId

  function formatTableValue(value) {
    if (value === null || value === undefined || value === '') return '—'
    if (typeof value === 'string') return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    if (Array.isArray(value)) return value.map((item) => formatTableValue(item)).join(', ')
    if (typeof value === 'object') return JSON.stringify(value, null, 2)
    return String(value)
  }

  function buildFieldRows(payload) {
    if (!payload || typeof payload !== 'object') return []
    if (Array.isArray(payload.field_rows)) {
      return payload.field_rows.filter((row) => row?.field_name && String(row.field_name).trim() !== 'fields')
    }

    const fieldMap = payload.fields && typeof payload.fields === 'object' ? payload.fields : {}
    const rows = []

    function pushRow(fieldName, fieldValue) {
      if (!fieldName) return
      const normalizedName = String(fieldName).trim()
      if (!normalizedName || normalizedName === 'fields' || normalizedName.startsWith('_')) return
      if (Array.isArray(fieldValue) && fieldValue.every((item) => item && typeof item === 'object' && ('label' in item || 'field_name' in item || 'name' in item) && 'value' in item)) {
        fieldValue.forEach((item) => pushRow(item.label || item.field_name || item.name, item.value))
        return
      }
      if (fieldValue && typeof fieldValue === 'object' && !Array.isArray(fieldValue)) {
        return
      }
      rows.push({
        field_name: normalizedName,
        field_value: fieldValue,
        confidence: null,
        page_number: null,
      })
    }

    Object.entries(fieldMap).forEach(([fieldName, fieldValue]) => pushRow(fieldName, fieldValue))
    return rows
  }

  useEffect(() => {
    if (!documentId) return
    let active = true
    setIsLoading(true)
    setLoadError('')
    setDocument(null)
    setTables([])
    setInsights(null)

    Promise.allSettled([getDocument(documentId), getDocumentInsights(documentId)]).then(([documentResult, insightsResult]) => {
      if (!active) return

      if (documentResult.status === 'fulfilled') {
        const body = documentResult.value.data || documentResult.value
        const payload = body.data || body
        setDocument(payload)
        setTables(payload.tables || payload.extraction_result?.tables || [])
      } else {
        const message = documentResult.reason?.message || 'Could not load document data'
        setLoadError(message)
        toast.error(message)
      }

      if (insightsResult.status === 'fulfilled') {
        const body = insightsResult.value.data || insightsResult.value
        setInsights(body.data || body)
      } else {
        toast.error(insightsResult.reason?.message || 'Could not load OCR and AI insights')
      }

      setIsLoading(false)
    })

    return () => {
      active = false
    }
  }, [documentId])

  const fieldRows = useMemo(() => buildFieldRows(document || {}), [document])

  if (!documentId) {
    return <div className="panel p-6" style={{ color: 'var(--text-secondary)' }}>Pick a document from the upload flow or the library to inspect its extraction results.</div>
  }

  if (isLoading) {
    return <LoadingState />
  }

  if (loadError && !document) {
    return <div className="panel p-6" style={{ color: 'var(--text-secondary)' }}>{loadError}</div>
  }

  return (
    <div className="space-y-6">
      <section className="max-h-[78vh] overflow-auto rounded-3xl">
        <DocumentViewer imageUrl={document?.preview_url || (document?.document_id ? `/api/documents/${document.document_id || document.id}/preview` : null)} boxes={[]} />
      </section>

      <section className="rounded-3xl panel p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Corrected fields</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Structured field rows built from the corrected JSON payload.</p>
          </div>
        </div>
        <div className="overflow-auto rounded-2xl border" style={{ borderColor: 'var(--border)' }}>
          <table className="min-w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead style={{ background: 'var(--bg-raised)' }}>
              <tr>
                <th className="px-4 py-3 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>Field</th>
                <th className="px-4 py-3 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>Value</th>
                <th className="px-4 py-3 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>Confidence</th>
                <th className="px-4 py-3 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>Page</th>
              </tr>
            </thead>
            <tbody>
              {fieldRows.map((row) => (
                <tr key={row.field_name} style={{ borderTop: '1px solid var(--border)' }}>
                  <td className="px-4 py-3 align-top font-medium" style={{ color: 'var(--text-primary)' }}>{row.field_name}</td>
                  <td className="px-4 py-3 align-top whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>{formatTableValue(row.field_value)}</td>
                  <td className="px-4 py-3 align-top" style={{ color: 'var(--text-primary)' }}>{formatTableValue(row.confidence)}</td>
                  <td className="px-4 py-3 align-top" style={{ color: 'var(--text-primary)' }}>{formatTableValue(row.page_number)}</td>
                </tr>
              ))}
              {fieldRows.length === 0 ? (
                <tr>
                  <td className="px-4 py-4 text-sm" colSpan={4} style={{ color: 'var(--text-secondary)' }}>No corrected field data available yet.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="max-h-[72vh] overflow-auto rounded-3xl">
        <PreprocessPreview
          beforeUrl={document?.document_id ? `/api/documents/${document.document_id || document.id}/original` : null}
          afterUrl={document?.document_id ? `/api/documents/${document.document_id || document.id}/preprocessed` : null}
        />
      </section>

      <section className="max-h-[72vh] overflow-auto rounded-3xl panel p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Document insight</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Raw OCR text and an LLM-generated interpretation of what the document contains.</p>
          </div>
        </div>
        <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-2xl border p-4" style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }}>
            <div className="mb-3 text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Extracted text</div>
            <div className="max-h-[36vh] overflow-auto whitespace-pre-wrap rounded-2xl card p-4 text-sm" style={{ color: 'var(--text-primary)' }}>
              {insights?.extracted_text || 'No OCR text available yet.'}
            </div>
          </div>
          <div className="rounded-2xl border p-4" style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }}>
            <div className="mb-3 text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>AI insight</div>
            <div className="space-y-4">
              <div className="rounded-2xl card p-4 text-sm" style={{ color: 'var(--text-primary)' }}>
                {insights?.summary || 'A summary will appear here once the document is analyzed.'}
              </div>
              {insights?.sections?.length ? (
                <div className="space-y-2">
                  {insights.sections.map((section) => (
                    <div key={`${section.title}-${section.value}`} className="rounded-2xl border px-4 py-3" style={{ background: 'var(--bg-raised)', borderColor: 'var(--border)' }}>
                      <div className="text-xs font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-secondary)' }}>{section.title}</div>
                      <div className="mt-1 text-sm" style={{ color: 'var(--text-primary)' }}>{section.value}</div>
                    </div>
                  ))}
                </div>
              ) : null}
              {insights?.highlights?.length ? (
                <div className="space-y-2">
                  {insights.highlights.map((item) => (
                    <div key={item} className="rounded-2xl card px-4 py-3 text-sm" style={{ color: 'var(--text-secondary)' }}>{item}</div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      {tables.length > 0 ? (
        <section className="max-h-[72vh] overflow-auto rounded-3xl panel p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Extracted tables</h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Only tables found in the document are shown here.</p>
            </div>
          </div>
          <div className="space-y-4">
            {tables.map((table, index) => (
              <ReadOnlyTable key={table.id || index} table={table} index={index} />
            ))}
          </div>
        </section>
      ) : null}

      <section className="max-h-[60vh] overflow-auto rounded-3xl">
        <ExportPanel documentId={documentId} />
      </section>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="space-y-6">
      <section className="panel rounded-3xl p-6">
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-3">
            <div className="h-5 w-48 animate-pulse rounded-full" style={{ background: 'var(--bg-raised)' }} />
            <div className="h-4 w-72 animate-pulse rounded-full" style={{ background: 'var(--bg-raised)' }} />
            <div className="h-4 w-56 animate-pulse rounded-full" style={{ background: 'var(--bg-raised)' }} />
          </div>
          <div className="rounded-2xl border p-4" style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }}>
            <div className="h-4 w-24 animate-pulse rounded-full" style={{ background: 'var(--bg-raised)' }} />
            <div className="mt-4 space-y-3">
              <div className="h-3 w-full animate-pulse rounded-full" style={{ background: 'var(--bg-raised)' }} />
              <div className="h-3 w-5/6 animate-pulse rounded-full" style={{ background: 'var(--bg-raised)' }} />
              <div className="h-3 w-3/4 animate-pulse rounded-full" style={{ background: 'var(--bg-raised)' }} />
            </div>
          </div>
        </div>
      </section>

      <section className="panel rounded-3xl p-6">
        <div className="mb-4 h-5 w-44 animate-pulse rounded-full" style={{ background: 'var(--bg-raised)' }} />
        <div className="overflow-hidden rounded-2xl border" style={{ borderColor: 'var(--border)' }}>
          <div className="grid grid-cols-2 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="h-12 animate-pulse" style={{ background: 'var(--bg-raised)' }} />
            <div className="h-12 animate-pulse" style={{ background: 'var(--bg-raised)' }} />
          </div>
          <div className="space-y-px">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="grid grid-cols-2 gap-px">
                <div className="h-14 animate-pulse" style={{ background: 'var(--bg-base)' }} />
                <div className="h-14 animate-pulse" style={{ background: 'var(--bg-base)' }} />
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

function ReadOnlyTable({ table, index }) {
  const rows = table?.rows || []
  const headers = table?.headers || []

  return (
    <div className="rounded-2xl border p-4" style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h4 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Table {index + 1}</h4>
        <span className="rounded-full badge" style={{ background: 'var(--bg-raised)', color: 'var(--text-secondary)', padding: '6px 10px' }}>
          {rows.length} rows
        </span>
      </div>
      {headers.length ? (
        <div className="max-h-[32vh] overflow-auto rounded-2xl border" style={{ borderColor: 'var(--border)' }}>
          <table className="min-w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead style={{ background: 'var(--bg-raised)' }}>
              <tr>
                {headers.map((header) => (
                  <th key={header} className="px-4 py-3 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIndex) => (
                <tr key={rowIndex} style={{ borderTop: '1px solid var(--border)' }}>
                  {headers.map((header) => (
                    <td key={header} className="px-4 py-3" style={{ color: 'var(--text-primary)' }}>{Array.isArray(row) ? row[headers.indexOf(header)] ?? '' : row[header] ?? ''}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No tabular structure was detected for this section.</p>
      )}
    </div>
  )
}
