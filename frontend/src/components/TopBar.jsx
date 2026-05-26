import React, { useEffect, useState } from 'react'

const THEME_KEY = 'documind-theme'

function applyTheme(theme) {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('theme-light', theme === 'light')
}

export default function TopBar({ breadcrumb, onLogout }) {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) || 'dark'
    } catch {
      return 'dark'
    }
  })

  useEffect(() => {
    applyTheme(theme)
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {}
  }, [theme])

  return (
    <div className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{breadcrumb}</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            className="btn-secondary"
            onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
            aria-label="Toggle theme"
            title="Toggle light / dark"
          >
            {theme === 'dark' ? 'Light' : 'Dark'} Mode
          </button>
          <button className="btn-secondary" onClick={onLogout} aria-label="Logout" title="Logout">
            Logout
          </button>
        </div>
        <div style={{ width: 32, height: 32, borderRadius: 16, background: 'var(--bg-raised)', display: 'flex', alignItems: 'center', justifyContent: 'center' }} className="dm-mono">DU</div>
      </div>
    </div>
  )
}
