import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const COLORS = ['#3fb7a9', '#ff7a59', '#20506e', '#c8b092']

export default function StatsPanel({ documents = [] }) {
  const byType = documents.reduce((accumulator, document) => {
    const key = document.doc_type || 'unknown'
    accumulator[key] = (accumulator[key] || 0) + 1
    return accumulator
  }, {})

  const pieData = Object.entries(byType).map(([name, value]) => ({ name, value }))
  const statuses = documents.reduce((accumulator, document) => {
    const key = document.status || 'unknown'
    accumulator[key] = (accumulator[key] || 0) + 1
    return accumulator
  }, {})
  const barData = Object.entries(statuses).map(([name, value]) => ({ name, value }))
  const hasData = pieData.length > 0 || barData.length > 0

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="panel p-5" style={{ background: 'linear-gradient(180deg, var(--bg-raised), var(--bg-surface))', borderColor: 'var(--border-strong)' }}>
        <h3 className="mb-4 text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Documents by type</h3>
        <div className="h-72 rounded-3xl border p-3" style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }}>
          {hasData ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90} paddingAngle={5}>
                  {pieData.map((entry, index) => <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />)}
                </Pie>
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(34, 211, 238, 0.08)' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No documents yet" description="Upload documents to see type distribution appear here." />
          )}
        </div>
      </div>
      <div className="panel p-5" style={{ background: 'linear-gradient(180deg, var(--bg-raised), var(--bg-surface))', borderColor: 'var(--border-strong)' }}>
        <h3 className="mb-4 text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Status distribution</h3>
        <div className="h-72 rounded-3xl border p-3" style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }}>
          {hasData ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={{ stroke: 'var(--border)' }} />
                <YAxis tick={{ fill: 'var(--text-secondary)' }} axisLine={{ stroke: 'var(--border)' }} tickLine={{ stroke: 'var(--border)' }} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(34, 211, 238, 0.08)' }} />
                <Bar dataKey="value" fill="#20506e" radius={[10, 10, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="Nothing to chart yet" description="Status counts will appear once files are uploaded and analyzed." />
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ title, description }) {
  return (
    <div className="flex h-full flex-col items-center justify-center rounded-2xl border text-center" style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
      <div className="dm-mono" style={{ color: 'var(--text-primary)', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase' }}>{title}</div>
      <p className="mt-2 max-w-xs text-sm">{description}</p>
    </div>
  )
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null

  return (
    <div
      style={{
        background: 'var(--bg-raised)',
        border: '1px solid var(--border-strong)',
        borderRadius: 12,
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.28)',
        color: 'var(--text-primary)',
        padding: '10px 12px',
        minWidth: 140,
      }}
    >
      <div className="dm-mono" style={{ color: 'var(--text-secondary)', fontSize: 11, marginBottom: 6 }}>{label}</div>
      {payload.map((entry) => (
        <div key={entry.dataKey} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, fontSize: 13 }}>
          <span style={{ color: 'var(--text-secondary)' }}>{entry.name}</span>
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{entry.value}</span>
        </div>
      ))}
    </div>
  )
}
