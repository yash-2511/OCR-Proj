import { useCallback, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { uploadBatch, uploadDocument } from '../services/api'

const DOC_TYPES = ['invoice', 'receipt', 'business_card', 'form', 'id_card', 'contract', 'report', 'handwritten']

export default function DocumentUploader({ onUploaded }) {
  const [selectedType, setSelectedType] = useState('auto')
  const [queue, setQueue] = useState([])
  const [busy, setBusy] = useState(false)

  const handleDrop = useCallback((acceptedFiles) => {
    setQueue((current) => {
      const seen = new Set(current.map((file) => `${file.name}-${file.size}-${file.lastModified}`))
      const next = [...current]
      acceptedFiles.forEach((file) => {
        const key = `${file.name}-${file.size}-${file.lastModified}`
        if (seen.has(key)) return
        seen.add(key)
        next.push(file)
      })
      return next
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.webp'],
      'application/pdf': ['.pdf'],
    },
    multiple: true,
    onDrop: handleDrop,
  })

  const label = useMemo(() => (selectedType === 'auto' ? 'Auto classify' : `Force ${selectedType.replace('_', ' ')}`), [selectedType])
  const buttonLabel = useMemo(() => {
    if (!queue.length) return label
    if (queue.length === 1) return `${label}`
    return `Upload & analyze ${queue.length} files`
  }, [label, queue.length])

  async function submit() {
    if (!queue.length) {
      toast.error('Choose at least one file first.')
      return
    }

    setBusy(true)
    try {
      if (queue.length === 1) {
        const data = await uploadDocument(queue[0], selectedType === 'auto' ? null : selectedType)
        toast.success('Document uploaded')
        onUploaded?.(data.data || data)
      } else {
        const data = await uploadBatch(queue)
        toast.success('Files uploaded')
        onUploaded?.(data.data || data)
      }
      setQueue([])
    } catch (error) {
      toast.error(error.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel p-6 animate-rise">
      <div {...getRootProps()} className={`rounded-3xl border-2 border-dashed p-8 text-center transition ${isDragActive ? 'card-raised' : 'card'}`}>
        <input {...getInputProps()} />
        <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>Drop JPG, PNG, WEBP, or PDF files here</h2>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>Maximum upload size 20MB.</p>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
        <label className="block">
          <span className="mb-2 block text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Document type override</span>
          <select className="w-full input" value={selectedType} onChange={(event) => setSelectedType(event.target.value)}>
            <option value="auto">Auto</option>
            {DOC_TYPES.map((type) => <option key={type} value={type}>{type.replace('_', ' ')}</option>)}
          </select>
        </label>
        <button className="glass-button btn-primary disabled:opacity-50" disabled={busy} onClick={submit}>
          {busy ? 'Processing...' : buttonLabel}
        </button>
      </div>

      <div className="mt-5 space-y-2">
        {queue.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No files queued.</p>
        ) : (
          queue.map((file) => (
            <div key={`${file.name}-${file.size}`} className="flex items-center justify-between rounded-2xl card px-4 py-3 text-sm">
              <span style={{ color: 'var(--text-primary)' }}>{file.name}</span>
              <span className="dm-mono" style={{ color: 'var(--text-muted)' }}>{Math.round(file.size / 1024)} KB</span>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
