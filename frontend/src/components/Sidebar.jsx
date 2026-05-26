import React from 'react'
import { NavLink } from 'react-router-dom'

function NavItem({ to, icon: Icon, children }) {
  return (
    <NavLink to={to} className={({ isActive }) => `flex items-center gap-3 px-4 py-2 h-9 text-sm ${isActive ? 'border-l-2 border-accent-cyan bg-[var(--bg-hover)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'}`}>
      {Icon ? <Icon size={16} /> : null}
      <span style={{ fontFamily: '"IBM Plex Sans"', fontWeight: 500 }}>{children}</span>
    </NavLink>
  )
}

export default function Sidebar({ user }) {
  return (
    <aside className="sidebar flex flex-col">
      <div style={{ height: 56, display: 'flex', alignItems: 'center', paddingLeft: 20 }}>
        <div style={{ width: 6, height: 6, background: 'var(--accent-cyan)', marginRight: 8 }} />
        <div style={{ fontWeight: 600, fontSize: 16 }}>DocuMind</div>
      </div>

      <nav style={{ paddingTop: 8 }}>
        <div style={{ padding: '20px 0 0 16px', fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'DM Mono' }}>Workspace</div>
        <div style={{ marginTop: 8 }}>
          <NavItem to="/upload">Upload</NavItem>
          <NavItem to="/library">Library</NavItem>
        </div>
        <div style={{ padding: '20px 0 0 16px', fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'DM Mono' }}>Analytics</div>
        <div style={{ marginTop: 8 }}>
          <NavItem to="/stats">Stats</NavItem>
        </div>
      </nav>

      <div style={{ marginTop: 'auto', padding: 16, borderTop: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 28, height: 28, borderRadius: 14, background: 'var(--bg-raised)', display: 'flex', alignItems: 'center', justifyContent: 'center' }} className="dm-mono">DU</div>
          <div>
            <div style={{ fontSize: 13 }}>{user?.username || 'Demo User'}</div>
            <div className="dm-mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>{user?.role || 'Admin'}</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
