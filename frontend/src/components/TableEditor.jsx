import { useMemo, useState } from 'react'
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from '@tanstack/react-table'

export default function TableEditor({ table, onChange }) {
  const initialRows = (table?.rows || []).map((row) => (Array.isArray(row) ? [...row] : { ...row }))
  const [rows, setRows] = useState(initialRows)
  const headers = table?.headers || []

  const columnHelper = createColumnHelper()
  const columns = useMemo(
    () =>
      headers.map((header) =>
        columnHelper.accessor((row) => (Array.isArray(row) ? row[headers.indexOf(header)] : row[header]), {
          id: header,
          header: () => header,
          cell: (info) => info.getValue() ?? '',
        }),
      ),
    [columnHelper, headers],
  )

  const tableInstance = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  if (!headers.length) {
    return <div className="panel p-5 text-sm" style={{ color: 'var(--text-secondary)' }}>No tables detected.</div>
  }

  return (
    <div className="panel p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Table editor</h3>
        <button className="glass-button btn-primary" onClick={() => onChange?.(rows)}>Save tables</button>
      </div>

      <div className="overflow-auto rounded-2xl card">
        <table className="min-w-full text-sm" style={{ borderCollapse: 'collapse' }}>
          <thead style={{ background: 'var(--bg-raised)' }}>
            {tableInstance.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th key={header.id} className="px-4 py-3 text-left font-semibold" style={{ color: 'var(--text-secondary)' }}>{flexRender(header.column.columnDef.header, header.getContext())}</th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {headers.map((header) => (
                  <td key={header} className="px-4 py-2">
                    <input
                      className="w-full rounded-lg input"
                      value={Array.isArray(row) ? row[headers.indexOf(header)] ?? '' : row[header] ?? ''}
                      onChange={(event) => {
                        const value = event.target.value
                        setRows((current) =>
                          current.map((currentRow, currentIndex) => {
                            if (currentIndex !== rowIndex) return currentRow
                            if (Array.isArray(currentRow)) {
                              const nextRow = [...currentRow]
                              nextRow[headers.indexOf(header)] = value
                              return nextRow
                            }
                            return { ...currentRow, [header]: value }
                          }),
                        )
                      }}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
