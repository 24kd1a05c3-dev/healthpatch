import { useState, type FormEvent, type ChangeEvent } from 'react'
import { Activity, ArrowLeft, ArrowRight, Check, Plus, Trash2 } from 'lucide-react'
import type { Screen } from '../components/Sidebar'
import { useAuth } from '../context/AuthContext'
import FormField, { inputClass } from '../components/FormField'
import PhoneInput, { emptyPhone, normalizePhone, type PhoneDraft } from '../components/PhoneInput'

const steps = ['Patient details', 'Emergency contact', 'Medical history', 'Account']
const conditions = ['Hypertension', 'Diabetes Type 2', 'Atrial Fibrillation', 'COPD', 'Heart Failure', 'Asthma', 'Kidney Disease']

export default function RegisterScreen({ onNavigate }: { onNavigate: (s: Screen) => void }) {
  const { register } = useAuth()
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({ first: '', last: '', dob: '', gender: '', blood: '', address: '', contact: '', relationship: '', contactEmail: '', conditions: [] as string[], allergies: '', medications: '', email: '', password: '', confirm: '' })
  const [phone, setPhone] = useState(emptyPhone)
  const [contactPhone, setContactPhone] = useState(emptyPhone)
  const [additional, setAdditional] = useState<{ id: string; value: PhoneDraft }[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const field = (key: keyof typeof form) => ({ value: String(form[key]), onChange: (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setForm(current => ({ ...current, [key]: e.target.value })) })
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (loading) return
    setError('')
    try {
      if (step === 0) {
        if (!form.first.trim() || !form.last.trim()) throw new Error('Enter your first and last name.')
        normalizePhone(phone)
        additional.forEach(item => normalizePhone(item.value))
      }
      if (step === 1) {
        const number = normalizePhone(contactPhone)
        if ((form.contact.trim() && !number) || (number && !form.contact.trim())) throw new Error('Provide both the emergency contact name and phone number, or leave both empty.')
      }
      if (step < 3) { setStep(step + 1); return }
      if (form.password !== form.confirm) throw new Error('Passwords do not match.')
      setLoading(true)
      await register({
        full_name: `${form.first.trim()} ${form.last.trim()}`, email: form.email.trim().toLowerCase(), password: form.password,
        phone: normalizePhone(phone), additional_phones: additional.map(item => normalizePhone(item.value)).filter(Boolean),
        date_of_birth: form.dob || null, gender: form.gender || null, blood_type: form.blood || null, address: form.address.trim() || null,
        emergency_contact_name: form.contact.trim() || null, emergency_contact_phone: normalizePhone(contactPhone),
        emergency_contact_relationship: form.relationship || null, emergency_contact_email: form.contactEmail.trim() || null,
        medical_conditions: form.conditions, allergies: form.allergies.split(',').map(s => s.trim()).filter(Boolean),
        medications: form.medications.split('\n').map(s => s.trim()).filter(Boolean),
      })
    } catch (err) { setError(err instanceof Error ? err.message : 'Registration failed.'); setLoading(false) }
  }
  return <main className="min-h-screen bg-[#F5F8FC] px-4 py-8 sm:py-12">
    <div className="mx-auto max-w-[640px]">
      <div className="mb-8 flex items-center gap-3"><Activity className="text-[#0D9488]" /><span className="text-lg font-semibold">HealthPatch</span></div>
      <h1 className="text-2xl font-semibold">Patient registration</h1><p className="mt-2 text-sm text-[#64748B]">Create your monitoring profile</p>
      <ol className="my-6 grid grid-cols-4 gap-2">{steps.map((label, i) => <li key={label} aria-current={i === step ? 'step' : undefined} className={`border-t-2 pt-2 text-xs ${i <= step ? 'border-[#0D9488] text-[#0F766E]' : 'border-[#CBD5E1] text-[#64748B]'}`}>{i + 1}. {label}</li>)}</ol>
      <form onSubmit={submit} className="rounded-lg border border-[#CBD5E1] bg-white p-5 sm:p-7">
        <h2 className="mb-5 text-lg font-semibold">{steps[step]}</h2>
        <fieldset disabled={loading} className="space-y-4">
          {step === 0 && <>
            <div className="grid gap-4 sm:grid-cols-2"><FormField label="First name" autoComplete="given-name" required maxLength={60} {...field('first')} /><FormField label="Last name" autoComplete="family-name" required maxLength={59} {...field('last')} /></div>
            <div className="grid gap-4 sm:grid-cols-2"><FormField label="Date of birth" type="date" max={new Date().toISOString().slice(0, 10)} autoComplete="bday" {...field('dob')} /><label className="block text-sm font-medium">Gender<select className={inputClass} {...field('gender')}><option value="">Not specified</option>{['Male', 'Female', 'Non-binary', 'Prefer not to say'].map(v => <option key={v}>{v}</option>)}</select></label></div>
            <PhoneInput label="Phone number" value={phone} onChange={setPhone} />
            {additional.map((item, index) => <div key={item.id} className="flex items-end gap-2"><div className="min-w-0 flex-1"><PhoneInput label={`Additional phone ${index + 1}`} value={item.value} onChange={value => setAdditional(rows => rows.map(row => row.id === item.id ? { ...row, value } : row))} /></div><button type="button" title="Remove phone number" className="mb-1 p-2 text-red-700" onClick={() => setAdditional(rows => rows.filter(row => row.id !== item.id))}><Trash2 size={17} /></button></div>)}
            <button type="button" disabled={additional.length >= 5} className="flex items-center gap-2 text-sm text-[#0F766E] disabled:opacity-40" onClick={() => setAdditional(rows => [...rows, { id: crypto.randomUUID(), value: emptyPhone() }])}><Plus size={16} />Add phone number</button>
            <FormField label="Address (optional)" autoComplete="street-address" maxLength={500} {...field('address')} />
            <label className="block text-sm font-medium">Blood group<select className={inputClass} {...field('blood')}><option value="">Not specified</option>{['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].map(v => <option key={v}>{v}</option>)}</select></label>
          </>}
          {step === 1 && <>
            <FormField label="Contact name" maxLength={120} {...field('contact')} />
            <FormField label="Relationship" maxLength={60} {...field('relationship')} />
            <PhoneInput label="Emergency phone number" value={contactPhone} onChange={setContactPhone} />
            <FormField label="Contact email (optional)" type="email" {...field('contactEmail')} />
            <p className="text-xs text-[#64748B]">Saved contacts can be called from your profile using your device's phone app. Automatic telephone alerts are not enabled.</p>
          </>}
          {step === 2 && <>
            <fieldset><legend className="mb-3 text-sm font-medium">Reported conditions</legend><div className="grid gap-3 sm:grid-cols-2">{conditions.map(condition => <label key={condition} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.conditions.includes(condition)} onChange={e => setForm(current => ({ ...current, conditions: e.target.checked ? [...current.conditions, condition] : current.conditions.filter(v => v !== condition) }))} />{condition}</label>)}</div></fieldset>
            <FormField label="Allergies (comma separated)" maxLength={1000} {...field('allergies')} />
            <label className="block text-sm font-medium">Medications (one per line)<textarea rows={4} maxLength={4000} className={inputClass} {...field('medications')} /></label>
          </>}
          {step === 3 && <>
            <FormField label="Email address" type="email" autoComplete="email" required {...field('email')} />
            <FormField label="Password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required {...field('password')} />
            <p className="text-xs text-[#64748B]">Use at least 12 characters.</p>
            <FormField label="Confirm password" type="password" autoComplete="new-password" required {...field('confirm')} />
            <p className="text-xs leading-relaxed text-[#64748B]">HealthPatch is a research and educational prototype. Profile details are stored on this deployment. Enter only information you intend to share with its authorized operators.</p>
          </>}
        </fieldset>
        {error && <p role="alert" className="mt-5 rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        <div className="mt-7 flex gap-3"><button type="button" disabled={loading} onClick={() => { setError(''); if (step) setStep(step - 1); else onNavigate('login') }} className="flex h-11 flex-1 items-center justify-center gap-2 rounded-md border border-[#CBD5E1] text-sm"><ArrowLeft size={16} />{step ? 'Back' : 'Sign in'}</button><button type="submit" disabled={loading} className="flex h-11 flex-1 items-center justify-center gap-2 rounded-md bg-[#0F766E] px-3 text-sm font-semibold text-white disabled:opacity-50">{loading ? 'Creating account...' : step === 3 ? <><Check size={16} />Create account</> : <>Continue<ArrowRight size={16} /></>}</button></div>
      </form>
    </div>
  </main>
}
