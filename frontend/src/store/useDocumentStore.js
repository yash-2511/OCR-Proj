import create from 'zustand'
import mockData from '../data/mock'

const stepNames = ['QUEUED', 'PREPROCESSING', 'OCR', 'EXTRACTING', 'EXTRACTED']

const useDocumentStore = create((set, get) => ({
  documents: mockData.documents.map((d) => ({ ...d })),
  batch: mockData.batch,
  batches: mockData.batches.map((b) => ({ ...b })),
  addDocument(doc) {
    set((s) => ({ documents: [doc, ...s.documents] }))
  },
  getDocument(id) {
    return get().documents.find((d) => d.id === id)
  },
  updateDocument(id, patch) {
    set((s) => ({ documents: s.documents.map((d) => (d.id === id ? { ...d, ...patch } : d)) }))
  },
  updateBatch(id, patch) {
    set((s) => ({ batches: s.batches.map((batch) => (batch.id === id ? { ...batch, ...patch } : batch)) }))
  },
  simulateExtract(id) {
    const doc = get().getDocument(id)
    if (!doc) return Promise.reject(new Error('Document not found'))
    // if already processing or extracted, ignore
    if (doc.status === 'PROCESSING' || doc.status === 'EXTRACTED') return Promise.resolve(doc)

    let step = 0
    get().updateDocument(id, { status: 'PROCESSING', confidence: 0 })

    return new Promise((resolve) => {
      const tick = () => {
        step += 1
        const status = stepNames[Math.min(step, stepNames.length - 1)]
        const conf = Math.min(95, Math.floor(Math.random() * 40 + step * 15))
        get().updateDocument(id, { status, confidence: conf })
        if (status === 'EXTRACTED') {
          // add some fake extracted fields if empty
          const cur = get().getDocument(id)
          if (!cur.extractedFields || Object.keys(cur.extractedFields).length === 0) {
            get().updateDocument(id, { extractedFields: { TOTAL: '₹' + (Math.floor(Math.random() * 90000) + 1000) } })
          }
          resolve(get().getDocument(id))
        } else {
          setTimeout(tick, 800)
        }
      }
      setTimeout(tick, 600)
    })
  },
  simulateExtractAll() {
    const ids = get().documents.map((d) => d.id)
    return Promise.all(ids.map((id) => get().simulateExtract(id)))
  },
  processBatch(id) {
    const batch = get().batches.find((item) => item.id === id)
    if (!batch) return Promise.reject(new Error('Batch not found'))

    const documentIds = batch.document_ids || (batch.documents || []).map((document) => document.id)
    if (!documentIds.length) return Promise.reject(new Error('Batch has no documents to process'))

    get().updateBatch(id, { status: 'running', processed: 0, successful: 0, failed: 0 })

    return Promise.all(documentIds.map((documentId) => get().simulateExtract(documentId).then(() => true).catch(() => false))).then((results) => {
      const processed = results.length
      const successful = results.filter(Boolean).length
      const failed = processed - successful
      const status = failed === 0 ? 'done' : 'failed'
      get().updateBatch(id, { status, processed, successful, failed })
      return { batch_id: id, processed, successful, failed, status }
    })
  },
}))

export default useDocumentStore
