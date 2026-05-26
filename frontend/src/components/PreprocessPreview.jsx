export default function PreprocessPreview({ beforeUrl, afterUrl }) {
  return (
    <div className="panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Preprocess preview</h3>
        <span className="rounded-full badge" style={{ padding: '6px 10px', background: 'var(--bg-raised)', color: 'var(--text-secondary)' }}>before / after</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <PreviewCard title="Original" imageUrl={beforeUrl} />
        <PreviewCard title="Preprocessed" imageUrl={afterUrl} />
      </div>
    </div>
  )
}

function PreviewCard({ title, imageUrl }) {
  return (
    <div className="overflow-hidden rounded-2xl card">
      <div className="px-4 py-2 text-sm font-semibold" style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)' }}>{title}</div>
      <img alt={title} className="h-72 w-full object-cover" src={imageUrl || 'https://placehold.co/900x700/f4eee5/0a1d2d?text=Preview'} />
    </div>
  )
}
