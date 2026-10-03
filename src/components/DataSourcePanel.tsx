import { useEffect, useState } from 'react'
import { Database, Pause, Play, RefreshCcw, RotateCcw, WifiOff } from 'lucide-react'
import {
  getDatasets, getReplayStatus, pauseReplay, restartReplay, resumeReplay,
  seekReplay, setReplaySpeed, startReplay, stopReplay, type ReplaySpeed,
} from '../api/replay'
import { useHealthData } from '../context/HealthDataContext'

const failures = {
  packet_loss_percent: 0, duplicate_percent: 0, latency_ms: 0,
  disconnect_every_batches: null, disconnect_duration_ms: 1000,
}

export default function DataSourcePanel() {
  const { replayState } = useHealthData()
  const [datasets, setDatasets] = useState<any[]>([])
  const [recordId, setRecordId] = useState('')
  const [speed, setSpeed] = useState<ReplaySpeed>(1)
  const [status, setStatus] = useState<any>({ state: 'STOPPED', position_seconds: 0, duration_seconds: 0 })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    Promise.all([getDatasets(), getReplayStatus()])
      .then(([available, current]) => {
        setDatasets(available)
        setStatus(current)
        const first = available[0]?.records?.[0]?.record_id
        if (first) setRecordId(first)
      })
      .catch(err => setError(err.message))
  }, [])
  useEffect(() => { if (replayState) setStatus(replayState) }, [replayState])

  const run = async (action: () => Promise<any>) => {
    setBusy(true); setError('')
    try { setStatus(await action()) } catch (err: any) { setError(err.message) } finally { setBusy(false) }
  }
  const records = datasets[0]?.records ?? []
  const playing = status.state === 'PLAYING'
  const paused = status.state === 'PAUSED'

  return (
    <section className="hp-card p-5 space-y-4" aria-label="Data source controls">
      <div className="flex items-start gap-3 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] p-4">
        <Database size={17} className="mt-0.5 text-[#1A6BCC]" />
        <div><div className="text-xs font-bold text-[#1A6BCC]">BIDMC REPLAY CONTROLS</div><p className="mt-1 text-xs text-[#475569]">PhysioNet · recorded physiological signals</p></div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#E8F1FB] text-[#1A6BCC] flex items-center justify-center"><Database size={18} /></div>
          <div>
            <div className="text-[11px] font-bold tracking-wide text-[#1A6BCC]">REAL RECORDED DATA</div>
            <div className="text-sm font-semibold text-[#0F172A]">Dataset Replay</div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#64748B]"><span className="w-2 h-2 rounded-full bg-[#F59E0B]" />{status.state}</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3">
        <label className="text-xs text-[#64748B]">Dataset
          <select className="mt-1 w-full h-10 px-3 border border-[#E2E8F0] rounded-lg bg-white text-sm" disabled><option>BIDMC PPG and Respiration</option></select>
        </label>
        <label className="text-xs text-[#64748B]">Record
          <select value={recordId} onChange={e => setRecordId(e.target.value)} className="mt-1 w-full h-10 px-3 border border-[#E2E8F0] rounded-lg bg-white text-sm" disabled={!records.length || playing}>
            {!records.length && <option>No local recordings installed</option>}
            {records.map((record: any) => <option key={record.record_id} value={record.record_id}>{record.record_id}</option>)}
          </select>
        </label>
        <div className="text-xs text-[#64748B]">Speed
          <div className="mt-1 flex h-10 border border-[#E2E8F0] rounded-lg overflow-hidden">
            {([1, 2, 5] as ReplaySpeed[]).map(value => <button key={value} onClick={() => { setSpeed(value); if (playing || paused) run(() => setReplaySpeed(value)) }} className={`w-12 text-sm font-medium ${speed === value ? 'bg-[#1A6BCC] text-white' : 'bg-white text-[#64748B]'}`}>{value}x</button>)}
          </div>
        </div>
      </div>

      <div>
        <input type="range" min={0} max={status.duration_seconds || 480} value={status.position_seconds || 0} onChange={e => setStatus({ ...status, position_seconds: Number(e.target.value) })} onMouseUp={e => run(() => seekReplay(Number((e.target as HTMLInputElement).value)))} disabled={!playing && !paused} className="w-full accent-[#1A6BCC]" />
        <div className="flex justify-between text-[11px] font-data text-[#64748B]"><span>{formatTime(status.position_seconds)}</span><span>{formatTime(status.duration_seconds)}</span></div>
      </div>

      <div className="flex flex-wrap gap-2">
        {!playing && !paused && <button disabled={!recordId || busy} onClick={() => run(() => startReplay(recordId, speed, failures))} className="h-9 px-4 rounded-lg bg-[#1A6BCC] text-white text-sm font-semibold flex items-center gap-2 disabled:opacity-50"><Play size={15} />Start</button>}
        {playing && <button disabled={busy} onClick={() => run(pauseReplay)} className="h-9 px-4 rounded-lg border border-[#E2E8F0] bg-white text-sm flex items-center gap-2"><Pause size={15} />Pause</button>}
        {paused && <button disabled={busy} onClick={() => run(resumeReplay)} className="h-9 px-4 rounded-lg bg-[#1A6BCC] text-white text-sm flex items-center gap-2"><Play size={15} />Resume</button>}
        {(playing || paused || status.state === 'COMPLETED') && <button disabled={busy} onClick={() => run(restartReplay)} title="Restart replay" className="w-9 h-9 rounded-lg border border-[#E2E8F0] bg-white flex items-center justify-center"><RefreshCcw size={15} /></button>}
        {(playing || paused) && <button disabled={busy} onClick={() => run(stopReplay)} title="Stop replay" className="w-9 h-9 rounded-lg border border-[#E2E8F0] bg-white flex items-center justify-center"><RotateCcw size={15} /></button>}
      </div>
      {!records.length && <div className="flex items-start gap-2 text-xs text-[#64748B] bg-[#F8FAFC] p-3 rounded-lg"><WifiOff size={14} className="mt-0.5 shrink-0" />Place licensed BIDMC CSV files in <span className="font-data">backend/datasets/bidmc_csv</span>, then restart the API.</div>}
      {error && <div className="text-xs text-[#B91C1C] bg-[#FEF2F2] p-3 rounded-lg">{error}</div>}
    </section>
  )
}

function formatTime(value = 0) {
  const seconds = Math.max(0, Math.floor(value))
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}
