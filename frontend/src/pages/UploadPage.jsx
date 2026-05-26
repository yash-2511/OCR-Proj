import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import DocumentUploader from '../components/DocumentUploader'
import StatsPanel from '../components/StatsPanel'
import { useEffect, useState } from 'react'
import { extractDocument, getStats, listDocuments } from '../services/api'

export default function UploadPage() {
  const [documents, setDocuments] = useState([])
  const [statsDocuments, setStatsDocuments] = useState([])
  const [analysisResults, setAnalysisResults] = useState([])
  const [isAnalyzingFiles, setIsAnalyzingFiles] = useState(false)
  const navigate = useNavigate()

  function refreshDocuments() {
    listDocuments()
      .then((response) => setDocuments(response.data || response))
      .catch(() => toast.error('Could not load documents'))
  }

  function refreshStats() {
    getStats().then(() => listDocuments().then((response) => setStatsDocuments(response.data || response)).catch(() => null))
  }

  useEffect(() => {
    refreshDocuments()
    refreshStats()
  }, [])

  async function handleUploaded(payload) {
    const isBatchUpload = Array.isArray(payload?.document_ids) && payload.document_ids.length > 1
    if (isBatchUpload) {
      setIsAnalyzingFiles(true)
      setAnalysisResults([])
      try {
        toast.loading('Uploading and analyzing files...', { id: 'analyze-batch' })

        const results = []
        for (const documentId of payload.document_ids) {
          try {
            const response = await extractDocument(documentId)
            results.push({ status: 'done', ...(response.data || response) })
          } catch (error) {
            results.push({ status: 'failed', document: { id: documentId, filename: 'Unknown file' }, error: error.message })
          }
        }

        setAnalysisResults(results)
        toast.success(`Analyzed ${results.length} files`, { id: 'analyze-batch' })
        refreshDocuments()
        refreshStats()
      } catch (error) {
        toast.error(error.message, { id: 'analyze-batch' })
      } finally {
        setIsAnalyzingFiles(false)
      }
      return
    }

    const document = payload?.document || payload
    if (!document?.id) return

    const shouldExtract = document.status !== 'extracted' && !document.preview_path
    try {
      if (shouldExtract) {
        toast.loading('Extracting document...', { id: 'extract-document' })
        await extractDocument(document.id)
        toast.success('Ready for review', { id: 'extract-document' })
      } else {
        toast.success(document.duplicate ? 'Already uploaded, opening existing document' : 'Ready for review')
      }
      navigate('/review', { state: { documentId: document.id } })
    } catch (error) {
      toast.error(error.message, { id: 'extract-document' })
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="space-y-6">
        <DocumentUploader onUploaded={handleUploaded} />

        {analysisResults.length > 0 ? (
          <div className="panel p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-ink-900">Multi-file analysis result</h2>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Each uploaded document was processed separately and is listed below with its own extraction summary.
                </p>
              </div>
              <span className="rounded-full badge" style={{ background: 'var(--bg-raised)', color: 'var(--text-primary)', padding: '6px 10px' }}>
                {isAnalyzingFiles ? 'Analyzing...' : 'Complete'}
              </span>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-4">
              <Metric label="Processed" value={analysisResults.length} />
              <Metric label="Success" value={analysisResults.filter((item) => item.status === 'done').length} />
              <Metric label="Failed" value={analysisResults.filter((item) => item.status === 'failed').length} />
              <Metric label="Files" value={analysisResults.length} />
            </div>

            <div className="mt-5 grid gap-3 lg:grid-cols-2">
              {analysisResults.map((item) => (
                <div key={item.document?.id || item.document?.filename} className="rounded-2xl border p-4" style={{ background: 'var(--bg-raised)', borderColor: 'var(--border-strong)' }}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold" style={{ color: 'var(--text-primary)' }}>{item.document?.filename || 'Untitled file'}</div>
                      <div className="mt-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
                        {item.document?.doc_type || 'unknown'} • {item.fields?.length || 0} fields • {item.tables?.length || 0} tables
                      </div>
                    </div>
                    <span className="rounded-full badge" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)', padding: '6px 10px' }}>
                      {item.status || 'done'}
                    </span>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <MiniStat label="Confidence" value={Math.round((item.document?.classification_confidence || 0) * 100)} suffix="%" />
                    <MiniStat label="Fields" value={item.fields?.length || 0} />
                    <MiniStat label="Tables" value={item.tables?.length || 0} />
                  </div>

                  {item.error ? <p className="mt-3 text-sm" style={{ color: 'var(--confidence-low)' }}>{item.error}</p> : null}

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button className="glass-button bg-ink-900 text-white" onClick={() => navigate('/review', { state: { documentId: item.document?.id } })} disabled={!item.document?.id}>
                      Review file
                    </button>
                    {item.document?.id ? (
                      <button className="btn-secondary" onClick={() => navigate('/library')}>
                        Open library
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="panel p-5">
          <h2 className="text-lg font-bold text-ink-900">Recent documents</h2>
          <div className="mt-4 space-y-3">
            {documents.slice(0, 5).map((document) => (
              <div key={document.id} className="flex items-center justify-between card p-3 text-sm">
                <span>{document.filename}</span>
                <span>{document.doc_type || 'unknown'}</span>
              </div>
            ))}
            {documents.length === 0 && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No documents uploaded yet.</p>}
          </div>
        </div>
      </div>
      <StatsPanel documents={statsDocuments} />
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="card" style={{ padding: 12, background: 'linear-gradient(180deg, var(--bg-raised), var(--bg-surface))', borderColor: 'var(--border-strong)' }}>
      <div className="dm-mono" style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, marginTop: 8, color: 'var(--text-primary)' }}>{value ?? 0}</div>
    </div>
  )
}

function MiniStat({ label, value, suffix = '' }) {
  return (
    <div className="card" style={{ padding: 10, background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
      <div className="dm-mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ marginTop: 6, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>{value}{suffix}</div>
    </div>
  )
}
