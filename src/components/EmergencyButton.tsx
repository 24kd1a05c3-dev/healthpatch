import { useState } from 'react'
import { Phone } from 'lucide-react'
import Modal from './Modal'
import { useAuth } from '../context/AuthContext'
import { apiFetch } from '../api/client'

export default function EmergencyButton() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const record = async () => {
    setBusy(true); setMessage('')
    try {
      await apiFetch('/emergency/', { method: 'POST', body: JSON.stringify({ user_id: user.id, triggered_by: 'patient', notes: 'Requested review from patient workspace' }) })
      setMessage('Request recorded in HealthPatch. No telephone call or SMS has been sent.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Request failed') }
    finally { setBusy(false) }
  }
  return <><button onClick={() => { setOpen(true); setMessage('') }} className="fixed bottom-20 right-5 z-30 flex h-12 w-12 items-center justify-center rounded-full bg-red-700 text-white md:bottom-6" title="Emergency contact"><Phone size={20} /></button><Modal open={open} onClose={() => setOpen(false)}>
    <h2 className="mb-3 text-lg font-semibold">Emergency contact</h2><p className="mb-5 text-sm text-slate-600">For immediate help, call your local emergency service directly. HealthPatch is not an emergency dispatch service.</p>
    {user.emergency_contact_phone ? <a className="mb-4 flex items-center justify-center gap-2 rounded-md bg-teal-700 p-3 text-white" href={`tel:${user.emergency_contact_phone}`}><Phone size={16} />Call {user.emergency_contact_name || user.emergency_contact_phone}</a> : <p className="mb-4 text-sm">No emergency contact phone number saved.</p>}
    <button disabled={busy} onClick={record} className="w-full rounded-md border p-3 text-sm">{busy ? 'Recording...' : 'Record a review request'}</button>{message && <p role="status" className="mt-3 text-sm">{message}</p>}
  </Modal></>
}
