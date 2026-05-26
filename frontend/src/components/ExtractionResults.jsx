import { useEffect, useState } from 'react'

export default function ExtractionResults({ fields = [], onChange }) {
  const [draft, setDraft] = useState(fields)

  useEffect(() => setDraft(fields), [fields])

  function updateField(index, key, value) {
    setDraft((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, [key]: value } : item)))
  }

  return (
    <div className="panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-bold text-ink-900">Extracted fields</h3>
        <button className="glass-button bg-coral text-white" onClick={() => onChange?.(draft)}>Save corrections</button>
      </div>

      <div className="space-y-3">
        {draft.map((field, index) => (
          <label key={field.field_name} className="block card p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{field.field_name}</span>
              <span className={`rounded-full px-2 py-1 text-xs font-semibold`} style={{ background: 'var(--bg-raised)', color: 'var(--text-secondary)' }}>{field.confidence}</span>
            </div>
            <input
              className="w-full input"
              value={field.field_value ?? ''}
              onChange={(event) => updateField(index, 'field_value', event.target.value)}
            />
          </label>
        ))}
        {draft.length === 0 && <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No extracted fields yet.</p>}
      </div>
    </div>
  )
}
