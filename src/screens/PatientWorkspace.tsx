import { useEffect, useState } from 'react'
import { Download, RefreshCw } from 'lucide-react'
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { API_BASE, apiFetch, getToken } from '../api/client'
import { acknowledgeAlert } from '../api/alerts'
import EmergencyButton from '../components/EmergencyButton'

export default function PatientWorkspace({ view = 'overview', patientId }: { view?: 'overview' | 'insights' | 'history' | 'alerts'; patientId?: string }) {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [metric, setMetric] = useState('heart_rate')
  const query = patientId ? `?user_id=${encodeURIComponent(patientId)}` : ''
  const refresh = async () => {
    try { setData(await apiFetch(`/api/v1/workspace${query}`)); setError('') }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to load monitoring data') }
  }
  useEffect(() => {
    let active = true
    setData(null)
    const load = async () => { try { const result = await apiFetch(`/api/v1/workspace${query}`); if (active) { setData(result); setError('') } } catch (err) { if (active) setError(err instanceof Error ? err.message : 'Unable to load monitoring data') } }
    void load(); const timer = window.setInterval(load, 5000)
    return () => { active = false; clearInterval(timer) }
  }, [query])
  const exportReport = async () => {
    setBusy(true)
    try {
      const response = await fetch(`${API_BASE}/api/v1/reports/telemetry.csv${query}`, { headers: { Authorization: `Bearer ${getToken()}` }, credentials: 'include' })
      if (!response.ok) throw new Error('Report export failed. Refresh and try again.')
      const url = URL.createObjectURL(await response.blob()); const link = document.createElement('a'); link.href = url; link.download = 'healthpatch-telemetry.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) { setError(err instanceof Error ? err.message : 'Export failed') } finally { setBusy(false) }
  }
  const ack = async (id: string) => { setBusy(true); try { await acknowledgeAlert(id); await refresh() } catch (err) { setError(err instanceof Error ? err.message : 'Acknowledgment failed') } finally { setBusy(false) } }
  const twin = data?.twin
  const stats = twin?.statistics
  const features = stats?.features ?? {}
  const metrics: Record<string, [string, string]> = { heart_rate: ['Heart rate', 'bpm'], pulse_rate: ['Pulse rate', 'bpm'], spo2: ['SpO2', '%'], respiratory_rate: ['Respiratory rate', 'br/min'], temperature: ['Temperature', 'C'] }
  return <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4"><div><h2 className="text-xl font-semibold">{view === 'insights' ? 'Digital twin observations' : view === 'history' ? 'Recorded telemetry' : view === 'alerts' ? 'Alert center' : 'Patient command center'}</h2><p className="mt-1 text-xs text-slate-500">Research monitoring prototype</p></div><div className="flex gap-2"><button title="Refresh monitoring data" onClick={refresh} className="rounded-md border p-2"><RefreshCw size={17} /></button><button disabled={!twin || busy} onClick={exportReport} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm disabled:opacity-40"><Download size={16} />Export CSV</button></div></div>
    {error && <p role="alert" className="border-l-2 border-red-600 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
    {!data && !error && <p role="status">Loading monitoring data...</p>}
    {data && <>
      <div className="flex flex-wrap items-center gap-3 text-xs"><strong className="rounded bg-teal-100 px-2 py-1 text-teal-900">{twin?.source_type === 'DATASET_REPLAY' ? 'DATASET REPLAY' : twin?.source_type === 'SYNTHETIC_SIMULATOR' ? 'SIMULATED DATA' : twin?.source_type ?? 'NO TELEMETRY'}</strong>{twin?.record_id && <span>{twin.record_id}</span>}<span>{twin ? `Last sample: ${new Date(twin.timestamp).toLocaleString()}` : 'No measurements received'}</span>{twin?.stale && <strong className="text-amber-800">STALE / PAUSED</strong>}</div>
      {!twin && <section className="border-y py-10"><h3 className="font-medium">No recorded measurements yet</h3><p className="mt-2 text-sm text-slate-500">Open Signal Lab and start an installed recording to populate this workspace.</p></section>}
      {twin && view !== 'alerts' && <>
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border bg-slate-200 sm:grid-cols-5">{Object.entries(metrics).map(([key, [label, unit]]) => <section key={key} className="bg-white p-4"><h3 className="text-xs text-slate-500">{label}</h3><p className="mt-2 font-data text-2xl">{twin.vitals[key] == null ? '--' : Number(twin.vitals[key]).toFixed(key === 'temperature' ? 1 : 0)} <small className="text-xs text-slate-500">{unit}</small></p><p className="mt-2 text-xs text-slate-500">{features[key]?.trend ?? 'Not recorded'}</p></section>)}</div>
        <section className="border-y bg-white py-5"><div className="mb-4 flex items-center justify-between gap-3"><h3 className="text-sm font-semibold">Latest stream history</h3><select aria-label="Chart metric" value={metric} onChange={e => setMetric(e.target.value)} className="rounded-md border p-2 text-sm">{Object.entries(metrics).map(([key, [label]]) => <option key={key} value={key}>{label}</option>)}</select></div><div className="h-56"><ResponsiveContainer width="100%" height="100%"><LineChart data={(data.history ?? []).map((row: any) => ({ t: row.second, value: row.vitals[metric] }))}><CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" /><XAxis dataKey="t" tick={{ fontSize: 10 }} /><YAxis domain={['auto', 'auto']} width={45} tick={{ fontSize: 10 }} /><Tooltip labelFormatter={v => `${v} s`} /><Line dataKey="value" stroke="#0D9488" dot={false} connectNulls={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></div></section>
        <section><h3 className="mb-3 text-sm font-semibold">Baseline comparison</h3><p className="mb-4 text-xs text-slate-500">{stats?.method} {stats?.baseline_ready ? '' : 'Collecting baseline samples.'}</p><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b text-xs text-slate-500"><tr><th className="p-2">Metric</th><th>Baseline</th><th>Recent mean</th><th>Deviation (z)</th><th>Samples</th></tr></thead><tbody>{Object.entries(features).map(([key, f]: [string, any]) => <tr key={key} className="border-b"><td className="p-2">{metrics[key]?.[0] ?? key}</td><td>{f.baseline?.toFixed(2) ?? '--'}</td><td>{f.recent_mean.toFixed(2)}</td><td>{f.z_score?.toFixed(2) ?? '--'}</td><td>{f.samples}</td></tr>)}</tbody></table></div><p className="mt-3 text-xs text-slate-500">Signal quality: {twin.signal_quality == null ? 'not supplied by source' : `${Math.round(twin.signal_quality * 100)}%`}. Statistical observations are not diagnoses.</p></section>
      </>}
      {view !== 'history' && <section className="border-t pt-5"><h3 className="mb-3 text-sm font-semibold">Recorded alerts</h3>{!data.alerts.length && <p className="text-sm text-slate-500">No alerts recorded.</p>}<div className="divide-y">{data.alerts.map((alert: any) => <article key={alert.id} className="flex flex-wrap items-start justify-between gap-4 py-4"><div className="min-w-0 flex-1"><h4 className="text-sm font-semibold">{alert.title}</h4><p className="mt-1 text-sm text-slate-600">{alert.message}</p><p className="mt-2 text-xs text-slate-500">{alert.level} · {alert.source_type ?? 'Source not recorded'} · {new Date(alert.created_at).toLocaleString()}</p></div><button disabled={busy || alert.acknowledged} onClick={() => ack(alert.id)} className="rounded-md border px-3 py-2 text-xs disabled:opacity-50">{alert.acknowledged ? 'Acknowledged' : 'Acknowledge'}</button></article>)}</div></section>}
    </>}
    {!patientId && <EmergencyButton />}
  </div>
}
