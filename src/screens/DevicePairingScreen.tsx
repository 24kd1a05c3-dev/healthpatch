import { useEffect, useState } from 'react'
import { listDevices, pairDevice } from '../api/devices'
import FormField from '../components/FormField'

export default function DevicePairingScreen() {
  const [devices, setDevices] = useState<any[]>([])
  const [serial, setSerial] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const load = () => listDevices().then(setDevices).catch(e => setError(e.message))
  useEffect(() => { void load() }, [])
  const pair = async () => { setBusy(true); setError(''); try { await pairDevice(encodeURIComponent(serial.trim())); await load(); setSerial('') } catch (e) { setError(e instanceof Error ? e.message : 'Pairing failed') } finally { setBusy(false) } }
  return <div className="max-w-3xl space-y-6 p-6"><h2 className="text-lg font-semibold">Registered devices</h2><p className="text-sm text-slate-500">Pair a device registered by an administrator. Physical sensor connectivity requires a configured hardware adapter.</p><form className="flex items-end gap-3" onSubmit={e => { e.preventDefault(); void pair() }}><div className="min-w-0 flex-1"><FormField label="Device ID" value={serial} onChange={e => setSerial(e.target.value)} required maxLength={80} /></div><button disabled={busy} className="rounded-md bg-teal-700 px-4 py-3 text-sm text-white">{busy ? 'Pairing...' : 'Pair'}</button></form>{error && <p role="alert" className="text-sm text-red-700">{error}</p>}{!devices.length && <p className="border-t py-5 text-sm text-slate-500">No paired devices found.</p>}<div className="divide-y">{devices.map(device => <div key={device.device_id} className="py-4"><h3 className="text-sm font-semibold">{device.device_id}</h3><p className="mt-2 text-xs text-slate-500">{device.status} · Firmware {device.firmware_version ?? 'unknown'} · Last seen {device.last_seen ? new Date(device.last_seen).toLocaleString() : 'never'}</p></div>)}</div></div>
}
