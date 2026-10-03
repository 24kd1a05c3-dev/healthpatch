import { useState, type FormEvent } from 'react'
import { apiFetch } from '../api/client'
import FormField from '../components/FormField'

export default function PasswordResetScreen({ onBack }: { onBack: () => void }) {
  const token = new URLSearchParams(window.location.search).get('token')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setMessage('')
    if (token && password !== confirm) { setMessage('Passwords do not match.'); return }
    setBusy(true)
    try {
      const result = await apiFetch<{ message: string }>(token ? '/auth/reset-password' : '/auth/forgot-password', { method: 'POST', body: JSON.stringify(token ? { token, new_password: password } : { email }) })
      setMessage(result.message); setPassword(''); setConfirm('')
    } catch (err) { setMessage(err instanceof Error ? err.message : 'Reset failed') } finally { setBusy(false) }
  }
  return <main className="mx-auto max-w-lg px-5 py-16"><h1 className="mb-6 text-2xl font-semibold">Reset password</h1><form className="space-y-5" onSubmit={submit}>{token ? <><FormField label="New password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} /><FormField label="Confirm password" type="password" required autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} /></> : <FormField label="Account email" type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} />}{message && <p role="status" className="rounded-md border p-3 text-sm">{message}</p>}<button disabled={busy} className="w-full rounded-md bg-teal-700 p-3 text-white">{busy ? 'Submitting...' : token ? 'Update password' : 'Send reset email'}</button><button type="button" onClick={() => { window.history.replaceState(null, '', '/'); onBack() }} className="text-sm text-teal-700">Back to sign in</button></form></main>
}
