import { useState } from 'react'
import { Phone, Save, Edit3 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { updateProfile } from '../api/auth'
import FormField from '../components/FormField'
import PhoneInput, { normalizePhone, type PhoneDraft } from '../components/PhoneInput'

export default function PatientProfileScreen() {
  const { user, refreshProfile } = useAuth()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(user.full_name)
  const [phone, setPhone] = useState<PhoneDraft>({ country: 'IN', number: user.phone ?? '' })
  const [emergencyPhone, setEmergencyPhone] = useState<PhoneDraft>({ country: 'IN', number: user.emergency_contact_phone ?? '' })
  const [contactName, setContactName] = useState(user.emergency_contact_name ?? '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const save = async () => {
    setBusy(true); setError('')
    try {
      await updateProfile({ full_name: name, phone: normalizePhone(phone), emergency_contact_name: contactName || null, emergency_contact_phone: normalizePhone(emergencyPhone) })
      await refreshProfile(); setEditing(false)
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to save profile') }
    finally { setBusy(false) }
  }
  return <div className="mx-auto max-w-5xl p-4 md:p-6">
    <div className="flex items-center justify-between gap-4 border-b pb-5"><div><h2 className="text-xl font-semibold">{user.full_name}</h2><p className="mt-1 break-all text-xs text-slate-500">{user.email}</p></div><button onClick={() => setEditing(!editing)} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"><Edit3 size={15} />{editing ? 'Cancel' : 'Edit contact details'}</button></div>
    {editing ? <form className="grid max-w-xl gap-4 py-6" onSubmit={e => { e.preventDefault(); void save() }}><FormField label="Full name" value={name} required maxLength={120} onChange={e => setName(e.target.value)} /><PhoneInput label="Phone number" value={phone} onChange={setPhone} /><FormField label="Emergency contact name" value={contactName} maxLength={120} onChange={e => setContactName(e.target.value)} /><PhoneInput label="Emergency phone number" value={emergencyPhone} onChange={setEmergencyPhone} />{error && <p role="alert" className="text-sm text-red-700">{error}</p>}<button disabled={busy} className="flex items-center justify-center gap-2 rounded-md bg-teal-700 p-3 text-white"><Save size={16} />{busy ? 'Saving...' : 'Save details'}</button></form> : <dl className="grid gap-6 py-6 sm:grid-cols-2">
      {[['Patient ID', user.id], ['Date of birth', user.date_of_birth], ['Gender', user.gender], ['Blood group', user.blood_type], ['Address', user.address], ['Enrolled', new Date(user.created_at).toLocaleDateString()]].map(([label, value]) => <div key={label}><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm">{value || 'Not provided'}</dd></div>)}
      <div><dt className="text-xs text-slate-500">Phone numbers</dt><dd className="mt-2 space-y-2">{[user.phone, ...(user.additional_phones ?? [])].filter(Boolean).map((number: string, index: number) => <a key={`${number}-${index}`} className="flex items-center gap-2 text-sm text-teal-700 underline" href={`tel:${number}`}><Phone size={14} />{number}</a>)}{!user.phone && !user.additional_phones?.length && 'Not provided'}</dd></div>
      <div><dt className="text-xs text-slate-500">Emergency contact</dt><dd className="mt-1 text-sm">{user.emergency_contact_name || 'Not provided'}{user.emergency_contact_relationship && ` (${user.emergency_contact_relationship})`}{user.emergency_contact_phone && <a className="mt-2 flex items-center gap-2 text-teal-700 underline" href={`tel:${user.emergency_contact_phone}`}><Phone size={14} />{user.emergency_contact_phone}</a>}{user.emergency_contact_email && <div className="mt-2 break-all">{user.emergency_contact_email}</div>}</dd></div>
    </dl>}
    <div className="grid gap-6 border-t py-6 sm:grid-cols-3">{[['Reported conditions', user.medical_conditions], ['Reported allergies', user.allergies], ['Reported medications', user.medications]].map(([label, values]) => <section key={label}><h3 className="mb-3 text-sm font-semibold">{label}</h3>{values?.length ? <ul className="space-y-2 text-sm text-slate-600">{values.map((value: string, i: number) => <li key={i}>{value}</li>)}</ul> : <p className="text-sm text-slate-500">None recorded</p>}</section>)}</div>
  </div>
}
