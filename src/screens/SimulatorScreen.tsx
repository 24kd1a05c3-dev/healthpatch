import { useEffect, useRef, useState } from 'react'
import { Battery, Pause, Play, Square, Wifi, WifiOff } from 'lucide-react'
import { apiFetch } from '../api/client'
import PatientWorkspace from './PatientWorkspace'

export default function SimulatorScreen() {
  const [status, setStatus] = useState<any>({ state: 'STOPPED' })
  const [scenarios, setScenarios] = useState<string[]>([])
  const [scenario, setScenario] = useState('RESTING')
  const [speed, setSpeed] = useState(1)
  const [quality, setQuality] = useState(0.95)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const editing = useRef(false)
  const revision = useRef(0)
  const applyStatus = (next: any) => {
    setStatus(next)
    if (next.scenario) setScenario(next.scenario)
    if (next.speed) setSpeed(next.speed)
    if (next.signal_quality != null && !editing.current) setQuality(next.signal_quality)
  }
  useEffect(() => {
    let mounted = true
    let initialized = false
    const load = async () => {
      const requestedRevision = revision.current
      try {
        const next = await apiFetch<any>('/api/v1/simulation')
        if (mounted && requestedRevision === revision.current) {
          if (!initialized || ['PLAYING', 'PAUSED', 'DISCONNECTED'].includes(next.state)) applyStatus(next)
          else setStatus(next)
          initialized = true
          setScenarios(next.scenarios)
        }
      } catch (e) { if (mounted) setError(e instanceof Error ? e.message : 'Status unavailable') }
    }
    void load()
    const timer = setInterval(load, 3000)
    return () => { mounted = false; clearInterval(timer) }
  }, [])
  const control = async (action: string, extra = {}) => {
    revision.current++
    setBusy(true); setError('')
    try {
      applyStatus(await apiFetch('/api/v1/simulation', { method: 'POST', body: JSON.stringify({ action, scenario, speed, ...extra }) }))
    } catch (e) { setError(e instanceof Error ? e.message : 'Simulation failed') }
    finally { revision.current++; setBusy(false) }
  }
  const active = ['PLAYING', 'PAUSED', 'DISCONNECTED'].includes(status.state)
  const buttons = active
    ? [...(status.state === 'DISCONNECTED' ? [] : [status.state === 'PAUSED' ? 'resume' : 'pause']), 'stop', status.state === 'DISCONNECTED' ? 'reconnect' : 'disconnect']
    : ['start']
  const icons: Record<string, typeof Play> = { start: Play, resume: Play, pause: Pause, stop: Square, disconnect: WifiOff, reconnect: Wifi }
  const commitQuality = (value: number) => { editing.current = false; void control('quality', { quality: value }) }
  return <div>
    <section className="m-4 space-y-4 border-y bg-white p-4 md:m-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">Research patch simulator</h2>
        <strong className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-900">SIMULATED DATA · {status.state}</strong>
      </div>
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm">Scenario
          <select disabled={busy} className="ml-2 max-w-full rounded-md border p-2" value={scenario} onChange={e => { setScenario(e.target.value); if (active) void control('scenario', { scenario: e.target.value }) }}>
            {scenarios.map(s => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label className="text-sm">Speed
          <select disabled={busy} className="ml-2 rounded-md border p-2" value={speed} onChange={e => { setSpeed(Number(e.target.value)); if (active) void control('speed', { speed: Number(e.target.value) }) }}>
            {[1, 2, 5].map(s => <option key={s} value={s}>{s}x</option>)}
          </select>
        </label>
      </div>
      <div className="flex flex-wrap gap-2">{buttons.map(action => {
        const Icon = icons[action]
        return <button key={action} disabled={busy || !scenarios.length} onClick={() => control(action)} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm capitalize disabled:opacity-50"><Icon size={15} />{action}</button>
      })}</div>
      {active && <label className="flex flex-wrap items-center gap-3 text-sm">Signal quality
        <input aria-label="Simulated signal quality" disabled={busy} type="range" min={0} max={1} step={0.05} value={quality}
          onChange={e => { editing.current = true; setQuality(Number(e.target.value)) }}
          onPointerUp={e => commitQuality(Number(e.currentTarget.value))}
          onKeyUp={e => { if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) commitQuality(Number(e.currentTarget.value)) }} />
        <span>{Math.round(quality * 100)}%</span>
      </label>}
      {status.battery != null && <p className="flex items-center gap-2 text-xs text-slate-600"><Battery size={15} />Modeled battery: {status.battery.toFixed(1)}%</p>}
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    </section>
    <PatientWorkspace />
  </div>
}
