import { useState } from 'react'
import toast from 'react-hot-toast'
import { exportBatch, exportDocument } from '../services/api'

export default function ExportPanel({ documentId, batchId }) {
  const [format, setFormat] = useState('json')
  const [busy, setBusy] = useState(false)

  async function runExport() {
    setBusy(true)
    try {
      const response = documentId ? await exportDocument(documentId, format) : await exportBatch(batchId)
      const blob = new Blob([response.data])
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = documentId ? `document-${documentId}.${format === 'excel' ? 'xlsx' : format}` : `batch-${batchId}.zip`
      link.click()
      URL.revokeObjectURL(url)
      toast.success('Export ready')
    } catch (error) {
      toast.error(error.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="panel p-5">
      <div className="flex flex-wrap items-end gap-3">
        <label className="block flex-1 min-w-40">
          <span className="mb-2 block text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Format</span>
          <select className="w-full input" value={format} onChange={(event) => setFormat(event.target.value)}>
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
            <option value="excel">Excel</option>
          </select>
        </label>
        <button className="glass-button btn-primary disabled:opacity-50" disabled={busy} onClick={runExport}>{busy ? 'Exporting...' : 'Download export'}</button>
      </div>
    </div>
  )
}
