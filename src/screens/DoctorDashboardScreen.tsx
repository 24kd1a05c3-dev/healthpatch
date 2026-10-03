import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client'
import PatientWorkspace from './PatientWorkspace'
import { useAuth } from '../context/AuthContext'

export default function DoctorDashboardScreen() {
  const { user } = useAuth()
  const [patients, setPatients] = useState<any[]>([])
  const [selected, setSelected] = useState('')
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const allowed = ['doctor', 'admin', 'caregiver'].includes(user.role)
  useEffect(() => { if (!allowed) { setLoading(false); return }; apiFetch<any[]>('/users/patients').then(setPatients).catch(e => setError(e.message)).finally(() => setLoading(false)) }, [allowed])
  if (!allowed) return <p className="p-6 text-sm">This workspace requires an assigned clinician or administrator account.</p>
  return <div className="p-4 md:p-6"><h2 className="mb-4 text-lg font-semibold">Assigned patients</h2><input aria-label="Search patients" placeholder="Search patients" value={search} onChange={e => setSearch(e.target.value)} className="mb-4 w-full max-w-sm rounded-md border bg-white p-3 text-sm" />{loading && <p>Loading patients...</p>}{error && <p role="alert" className="text-red-700">{error}</p>}{!loading && !patients.length && !error && <p className="text-sm text-slate-500">No patients assigned.</p>}<div className="flex flex-wrap gap-2">{patients.filter(p => p.full_name.toLowerCase().includes(search.toLowerCase())).map(p => <button key={p.id} onClick={() => setSelected(p.id)} className={`rounded-md border px-3 py-2 text-sm ${selected === p.id ? 'bg-teal-700 text-white' : 'bg-white'}`}>{p.full_name}</button>)}</div>{selected && <PatientWorkspace patientId={selected} />}</div>
}
