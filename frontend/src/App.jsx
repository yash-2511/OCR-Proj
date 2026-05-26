import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import ReviewPage from './pages/ReviewPage'
import LibraryPage from './pages/LibraryPage'
import PDFPage from './pages/PDFPage'
import StatsPage from './pages/StatsPage'
import AuthPage from './pages/AuthPage'
import { clearAuthToken, getCurrentUser, healthCheck, logoutUser, setAuthToken } from './services/api'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import useStore from './store/useDocumentStore'

function AppShell({ children, status, user, onLogout, pathname }) {
  return (
    <div className="shell">
      <Sidebar user={user} />
      <div className="main">
        <TopBar breadcrumb={pathname.replace('/', '') || 'Upload'} onLogout={onLogout} />
        <div className="content">{children}</div>
      </div>
    </div>
  )
}

export default function App() {
  const [status, setStatus] = useState('Connecting...')
  const [authLoading, setAuthLoading] = useState(true)
  const [user, setUser] = useState(null)
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    healthCheck()
      .then(() => setStatus('Backend healthy'))
      .catch(() => {
        setStatus('Backend offline')
        toast.error('Backend is not reachable yet.')
      })
  }, [])

  useEffect(() => {
    getCurrentUser()
      .then((response) => {
        const payload = response.data || response
        setUser(payload.user)
      })
      .catch(() => {
        clearAuthToken()
        setUser(null)
      })
      .finally(() => setAuthLoading(false))
  }, [])

  function handleAuthSuccess(nextUser, token) {
    setAuthToken(token)
    setUser(nextUser)
    navigate('/upload')
  }

  async function handleLogout() {
    try {
      await logoutUser()
    } catch {
      // Ignore logout failures and clear local auth state anyway.
    }
    clearAuthToken()
    setUser(null)
    navigate('/auth')
  }

  if (authLoading) {
    return <div className="flex min-h-screen items-center justify-center" style={{ background: 'var(--background)', color: 'var(--text-primary)' }}>Loading...</div>
  }

  if (location.pathname === '/auth' && user) {
    return <Navigate to="/upload" replace />
  }

  if (location.pathname === '/auth') {
    return (
      <div className="min-h-screen" style={{ background: 'var(--background)', color: 'var(--text-primary)', padding: '24px 32px' }}>
        <AuthPage onAuthSuccess={handleAuthSuccess} />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/auth" replace />
  }
  return (
    <AppShell status={status} user={user} onLogout={handleLogout} pathname={location.pathname} key={location.pathname}>
      <Routes>
        <Route path="/" element={<Navigate to={user ? '/upload' : '/auth'} replace />} />
        <Route path="/upload" element={user ? <UploadPage /> : <Navigate to="/auth" replace />} />
        <Route path="/review" element={user ? <ReviewPage /> : <Navigate to="/auth" replace />} />
        <Route path="/library" element={user ? <LibraryPage /> : <Navigate to="/auth" replace />} />
        <Route path="/pdf" element={user ? <PDFPage /> : <Navigate to="/auth" replace />} />
        <Route path="/stats" element={user ? <StatsPage /> : <Navigate to="/auth" replace />} />
      </Routes>
    </AppShell>
  )
}
