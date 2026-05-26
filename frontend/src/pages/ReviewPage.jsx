import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import DocumentViewer from '../components/DocumentViewer'
import PreprocessPreview from '../components/PreprocessPreview'
import ExportPanel from '../components/ExportPanel'
import { getDocument, getDocumentInsights } from '../services/api'

export default function ReviewPage() {
  const location = useLocation()
  const [document, setDocument] = useState(null)
  const [fields, setFields] = useState([])
  const [tables, setTables] = useState([])
  const [insights, setInsights] = useState(null)
  const documentId = location.state?.documentId

  function normalizeFields(payloadFields) {
    if (!payloadFields) return []
    if (Array.isArray(payloadFields)) return payloadFields
    if (typeof payloadFields !== 'object') return []

    return Object.entries(payloadFields).map(([field_name, value]) => {
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        return {
          field_name,
          field_value: value.value ?? null,
          confidence: value.confidence ?? 'low',
        }
      }

      return {
        field_name,
        field_value: value,
        confidence: 'low',
      }
    })
  }

  useEffect(() => {
    if (!documentId) return
    getDocument(documentId)
      .then((response) => {
        const body = response.data || response
        const payload = body.data || body
        setDocument(payload)
        setFields(normalizeFields(payload.fields || payload.field_annotations || []))
        setTables(payload.tables || [])
      })
      .catch((error) => toast.error(error.message))
    getDocumentInsights(documentId)
      .then((response) => {
        const body = response.data || response
        setInsights(body.data || body)
      })
      .catch((error) => toast.error(error.message))
  }, [documentId])

  if (!documentId) {
    return <div className="panel p-6" style={{ color: 'var(--text-secondary)' }}>Pick a document from the upload flow or the library to inspect its extraction results.</div>
  }

  return (
    <div className="space-y-6">
      <section className="max-h-[78vh] overflow-auto rounded-3xl">
        <DocumentViewer imageUrl={document?.preview_url || (document?.document_id ? `/api/documents/${document.document_id || document.id}/preview` : null)} boxes={[]} />
      </section>

      <section className="rounded-3xl panel p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Structured fields</h3>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Clean extracted data returned by the backend.</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {fields.map((field) => (
            <div key={field.field_name} className="rounded-2xl border p-4" style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }}>
              <div className="text-xs font-semibold uppercase tracking-[0.08em]" style={{ color: 'var(--text-secondary)' }}>{field.field_name}</div>
              <div className="mt-2 text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{String(field.field_value ?? 'null')}</div>
              <div className="mt-2 text-xs" style={{ color: 'var(--text-muted)' }}>Confidence: {field.confidence || 'low'}</div>
            </div>
          ))}
          {fields.length === 0 ? <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No structured fields available yet.</p> : null}
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
