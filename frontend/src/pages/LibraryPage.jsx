import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import DocumentList from '../components/DocumentList'
import { deleteDocument, listDocuments } from '../services/api'

export default function LibraryPage() {
  const [documents, setDocuments] = useState([])
  const navigate = useNavigate()

  function refresh() {
    listDocuments()
      .then((response) => setDocuments(response.data || response))
      .catch((error) => toast.error(error.message))
  }

  useEffect(() => {
    refresh()
  }, [])

  return (
    <div className="space-y-6">
      <DocumentList
        documents={documents}
        onSelect={(document) => navigate('/review', { state: { documentId: document.id } })}
        onDelete={async (document) => {
          if (!confirm(`Delete ${document.filename}?`)) return
          try {
            await deleteDocument(document.id)
            toast.success('Deleted')
            refresh()
          } catch (error) {
            toast.error(error.message)
          }
        }}
      />
    </div>
  )
}
