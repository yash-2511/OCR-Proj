export default function PDFViewer({ document }) {
  if (!document) {
    return <div className="panel p-5 text-sm" style={{ color: 'var(--text-secondary)' }}>Select a PDF document from the library.</div>
  }

  const pages = Array.from({ length: document.page_count || 1 }, (_, index) => index + 1)

  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{document.filename}</h3>
        <span className="rounded-full badge" style={{ padding: '6px 10px', background: 'var(--bg-raised)', color: 'var(--text-primary)' }}>{pages.length} pages</span>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        {pages.map((page) => (
          <div key={page} className="card px-4 py-6 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>Page {page}</div>
        ))}
      </div>
    </div>
  )
}
