import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import PDFViewer from '../components/PDFViewer'
import { listDocuments } from '../services/api'

export default function PDFPage() {
  const [documents, setDocuments] = useState([])

  useEffect(() => {
    listDocuments()
      .then((response) => setDocuments(response.data || response))
      .catch((error) => toast.error(error.message))
  }, [])

  const pdfDocument = documents.find((document) => String(document.filename || '').toLowerCase().endsWith('.pdf'))

  return <PDFViewer document={pdfDocument} />
}
