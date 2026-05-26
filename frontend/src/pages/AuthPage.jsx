import { useState } from 'react'
import toast from 'react-hot-toast'
import { loginUser, signupUser } from '../services/api'

export default function AuthPage({ onAuthSuccess }) {
  const [mode, setMode] = useState('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    try {
      const payload = mode === 'signup' ? { name, email, password } : { email, password }
      const response = mode === 'signup' ? await signupUser(payload) : await loginUser(payload)
      const data = response.data || response
      onAuthSuccess?.(data.user, data.token)
      toast.success(mode === 'signup' ? 'Account created' : 'Signed in successfully')
    } catch (error) {
      toast.error(error.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto grid min-h-[calc(100vh-140px)] max-w-6xl items-center gap-8 rounded-[2rem] p-6 md:grid-cols-[1.1fr_0.9fr] md:p-10">
      <div className="space-y-6">
        <div className="inline-flex rounded-full px-4 py-2 text-xs uppercase tracking-[0.35em]" style={{ border: '1px solid var(--border)', background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>Secure access</div>
        <h2 className="max-w-xl text-4xl font-bold leading-tight md:text-6xl" style={{ color: 'var(--text-primary)' }}>Sign in to upload, review, and manage documents.</h2>
        <p className="max-w-lg text-sm leading-6 md:text-base" style={{ color: 'var(--text-secondary)' }}>Create an account or log in with your email. The app keeps your session locally with a signed token from the backend.</p>
      </div>

      <form className="card p-6" onSubmit={handleSubmit}>
        <div className="mb-6 grid grid-cols-2 gap-2 rounded-2xl p-1 text-sm font-semibold" style={{ background: 'var(--bg-elevated)' }}>
          <button type="button" className={`rounded-xl px-4 py-2 transition`} style={mode === 'login' ? { background: 'var(--bg-raised)', color: 'var(--text-primary)' } : { color: 'var(--text-secondary)' }} onClick={() => setMode('login')}>Login</button>
          <button type="button" className={`rounded-xl px-4 py-2 transition`} style={mode === 'signup' ? { background: 'var(--bg-raised)', color: 'var(--text-primary)' } : { color: 'var(--text-secondary)' }} onClick={() => setMode('signup')}>Sign up</button>
        </div>

        <div className="space-y-4">
          {mode === 'signup' ? (
            <label className="block">
              <span className="mb-2 block text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Name</span>
              <input className="w-full rounded-2xl input" value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" />
            </label>
          ) : null}

          <label className="block">
            <span className="mb-2 block text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Email</span>
            <input className="w-full rounded-2xl input" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" type="email" />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Password</span>
            <input className="w-full rounded-2xl input" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Minimum 6 characters" type="password" />
          </label>
        </div>

        <button className="glass-button mt-6 w-full btn-primary disabled:opacity-50" disabled={busy} type="submit">
          {busy ? 'Please wait...' : mode === 'signup' ? 'Create account' : 'Login'}
        </button>
      </form>
    </div>
  )
}
