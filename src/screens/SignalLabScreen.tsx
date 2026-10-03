import { useEffect, useMemo, useState } from 'react'
import {
  Activity, Database, Eye, EyeOff, Gauge, Pause, Play, RefreshCcw,
  RotateCcw, Snowflake, Waves,
} from 'lucide-react'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import {
  getDatasets, getReplayStatus, pauseReplay, restartReplay, resumeReplay,
  seekReplay, setReplaySpeed, startReplay, stopReplay, type ReplaySpeed,
} from '../api/replay'
import { useHealthData, type WaveformHistory } from '../context/HealthDataContext'

const noFailures = {
  packet_loss_percent: 0,
  duplicate_percent: 0,
  latency_ms: 0,
  disconnect_every_batches: null,
  disconnect_duration_ms: 1000,
}

type ChannelKey = keyof WaveformHistory

const channelMeta: Record<ChannelKey, { label: string; detail: string; color: string; unit: string }> = {
  ppg: { label: 'Photoplethysmogram', detail: 'PLETH · optical pulse', color: '#0D9488', unit: 'a.u.' },
  ecg: { label: 'ECG Lead II', detail: 'cardiac electrical activity', color: '#EF4444', unit: 'mV' },
  ecg_v: { label: 'ECG Lead V', detail: 'precordial lead', color: '#7C3AED', unit: 'mV' },
  ecg_avr: { label: 'ECG Lead aVR', detail: 'augmented limb lead', color: '#D97706', unit: 'mV' },
  respiration: { label: 'Impedance Respiration', detail: 'thoracic impedance', color: '#1A6BCC', unit: 'a.u.' },
}

function formatTime(value = 0) {
  const seconds = Math.max(0, Math.floor(value))
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function WaveformPlot({ channel, data }: { channel: ChannelKey; data: WaveformHistory[ChannelKey] }) {
  const meta = channelMeta[channel]
  const latest = data.at(-1)?.v
  const plotData = useMemo(() => {
    const maxRenderedPoints = 500
    if (data.length <= maxRenderedPoints) return data
    // Retain bucket extrema so narrow ECG peaks survive display downsampling.
    const stride = Math.ceil(data.length / (maxRenderedPoints / 2))
    const sampled: typeof data = []
    for (let start = 0; start < data.length; start += stride) {
      const bucket = data.slice(start, start + stride)
      // A gap must remain visible rather than be bridged by decimation.
      const gap = bucket.find(point => point.v === null)
      if (gap) { sampled.push(gap); continue }
      const low = bucket.reduce((a, b) => a.v! < b.v! ? a : b)
      const high = bucket.reduce((a, b) => a.v! > b.v! ? a : b)
      sampled.push(...(low.t <= high.t ? [low, high] : [high, low]))
    }
    if (sampled.at(-1) !== data.at(-1)) sampled.push(data.at(-1)!)
    return sampled
  }, [data])

  return (
    <section className="border-b border-[#E2E8F0] last:border-b-0 bg-white" aria-label={`${meta.label} waveform`}>
      <div className="grid min-h-[190px] grid-cols-1 lg:grid-cols-[210px_minmax(0,1fr)]">
        <div className="flex flex-row items-center justify-between gap-4 border-b border-[#E2E8F0] px-5 py-4 lg:flex-col lg:items-start lg:justify-center lg:border-b-0 lg:border-r">
          <div>
            <div className="mb-2 h-1 w-10" style={{ backgroundColor: meta.color }} />
            <h3 className="text-sm font-semibold text-[#0F172A]">{meta.label}</h3>
            <p className="mt-1 text-[11px] text-[#64748B]">{meta.detail}</p>
          </div>
          <div className="text-right lg:text-left">
            <div className="font-data text-xl font-medium text-[#0F172A]">{latest == null ? '--' : latest.toFixed(3)}</div>
            <div className="text-[10px] uppercase text-[#94A3B8]">{meta.unit} · latest sample</div>
          </div>
        </div>
        <div className="h-[190px] min-w-0 px-2 py-3">
          {data.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={plotData} margin={{ top: 4, right: 14, bottom: 0, left: 2 }}>
                <CartesianGrid stroke="#E8EDF3" strokeDasharray="2 4" vertical={false} />
                <XAxis dataKey="t" type="number" domain={['dataMin', 'dataMax']} tickFormatter={value => `${Number(value).toFixed(1)}s`} tick={{ fontSize: 10, fill: '#64748B' }} tickLine={false} axisLine={false} />
                <YAxis domain={['auto', 'auto']} width={45} tick={{ fontSize: 10, fill: '#64748B' }} tickLine={false} axisLine={false} tickFormatter={value => Number(value).toFixed(2)} />
                <Tooltip
                  labelFormatter={value => `Original recording ${Number(value).toFixed(3)} s`}
                  formatter={value => [`${Number(value).toFixed(4)} ${meta.unit}`, meta.label]}
                  contentStyle={{ border: '1px solid #CBD5E1', borderRadius: 6, boxShadow: '0 8px 24px rgba(15,23,42,.10)', fontSize: 11 }}
                />
                <Line type="linear" dataKey="v" stroke={meta.color} strokeWidth={1.4} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-[#94A3B8]">Start dataset replay to inspect this channel</div>
          )}
        </div>
      </div>
    </section>
  )
}

export default function SignalLabScreen() {
  const { waveformHistory, normalizedTelemetry, replayState, connectionStatus } = useHealthData()
  const [datasets, setDatasets] = useState<any[]>([])
  const [recordId, setRecordId] = useState('')
  const [speed, setSpeed] = useState<ReplaySpeed>(1)
  const [status, setStatus] = useState<any>({ state: 'STOPPED', position_seconds: 0, duration_seconds: 0 })
  const [visible, setVisible] = useState<Record<ChannelKey, boolean>>({ ppg: true, ecg: true, ecg_v: true, ecg_avr: true, respiration: true })
  const [frozenData, setFrozenData] = useState<WaveformHistory | null>(null)
  const [seekPosition, setSeekPosition] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getDatasets(), getReplayStatus()])
      .then(([available, current]) => {
        setDatasets(available)
        setStatus(current)
        setSeekPosition(current.position_seconds ?? 0)
        setRecordId(current.record_id ?? available[0]?.records?.[0]?.record_id ?? '')
        if (current.speed) setSpeed(current.speed)
      })
      .catch(err => setError(err.message))
  }, [])

  useEffect(() => {
    if (!replayState) return
    setStatus(replayState)
    setSeekPosition(replayState.position_seconds ?? 0)
    if (replayState.record_id) setRecordId(replayState.record_id)
  }, [replayState])

  const run = async (action: () => Promise<any>) => {
    setBusy(true)
    setError('')
    try {
      const next = await action()
      setStatus(next)
      setSeekPosition(next.position_seconds ?? 0)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const records = datasets[0]?.records ?? []
  const selected = records.find((record: any) => record.record_id === recordId)
  const playing = status.state === 'PLAYING'
  const paused = status.state === 'PAUSED'
  const displayData = frozenData ?? waveformHistory
  const datasetTelemetry = normalizedTelemetry?.source_type === 'DATASET_REPLAY' ? normalizedTelemetry : null
  const vitals = datasetTelemetry?.vitals ?? {}
  const shownChannels = useMemo(() => (Object.keys(visible) as ChannelKey[]).filter(channel => visible[channel]), [visible])

  const toggleFreeze = () => {
    setFrozenData(current => current ? null : {
      ppg: [...waveformHistory.ppg], ecg: [...waveformHistory.ecg], ecg_v: [...waveformHistory.ecg_v],
      ecg_avr: [...waveformHistory.ecg_avr], respiration: [...waveformHistory.respiration],
    })
  }

  return (
    <div className="mx-auto max-w-[1600px] space-y-4 p-4 md:p-6">
      <section className="overflow-hidden rounded-lg border border-[#CBD5E1] bg-white shadow-sm">
        <div className="flex flex-col gap-4 border-b border-[#CBD5E1] bg-[#0F172A] px-5 py-4 text-white xl:flex-row xl:items-center xl:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[#0D9488]"><Waves size={20} /></div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-base font-semibold">BIDMC Recorded Signal Workstation</h2>
                <span className="rounded-sm bg-[#D1FAE5] px-2 py-0.5 text-[10px] font-bold tracking-wide text-[#047857]">REAL RECORDED DATA</span>
              </div>
              <p className="mt-0.5 text-xs text-[#94A3B8]">Clinical recording replayed at acquisition cadence · not a live patient feed</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
            <span className="font-data text-[#CBD5E1]">125 Hz waveforms</span>
            <span className="font-data text-[#CBD5E1]">1 Hz numerics</span>
            <span className="flex items-center gap-2"><i className={`h-2 w-2 rounded-full ${connectionStatus === 'connected' ? 'bg-[#34D399]' : 'bg-[#F59E0B]'}`} />{status.state}</span>
          </div>
        </div>

        <div className="grid gap-4 p-5 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-end">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[220px_1fr]">
            <label className="text-xs font-medium text-[#475569]">Dataset
              <div className="mt-1 flex h-10 items-center gap-2 rounded-md border border-[#CBD5E1] bg-[#F8FAFC] px-3 text-sm text-[#0F172A]"><Database size={15} className="text-[#1A6BCC]" />BIDMC v1.0.0</div>
            </label>
            <label className="text-xs font-medium text-[#475569]">Recording
              <select value={recordId} onChange={event => setRecordId(event.target.value)} disabled={playing || !records.length} className="mt-1 h-10 w-full rounded-md border border-[#CBD5E1] bg-white px-3 text-sm text-[#0F172A] disabled:bg-[#F8FAFC]">
                {!records.length && <option>No recording installed</option>}
                {records.map((record: any) => <option key={record.record_id} value={record.record_id}>{record.record_id} · {formatTime(record.duration_seconds)} · {record.signals.length} channels</option>)}
              </select>
            </label>
          </div>

          <div>
            <div className="mb-1 text-xs font-medium text-[#475569]">Replay speed</div>
            <div className="flex h-10 overflow-hidden rounded-md border border-[#CBD5E1]">
              {([1, 2, 5] as ReplaySpeed[]).map(value => (
                <button key={value} onClick={() => { setSpeed(value); if (playing || paused) run(() => setReplaySpeed(value)) }} className={`w-14 text-sm font-semibold ${speed === value ? 'bg-[#1A6BCC] text-white' : 'bg-white text-[#475569] hover:bg-[#F8FAFC]'}`}>{value}×</button>
              ))}
            </div>
          </div>
        </div>

        <div className="border-t border-[#E2E8F0] px-5 py-4">
          <input type="range" min={0} max={status.duration_seconds || selected?.duration_seconds || 480} step={0.2} value={seekPosition} disabled={!playing && !paused} onChange={event => setSeekPosition(Number(event.target.value))} onPointerUp={event => run(() => seekReplay(Number(event.currentTarget.value)))} onKeyUp={event => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) run(() => seekReplay(Number(event.currentTarget.value))) }} className="w-full accent-[#1A6BCC] disabled:opacity-40" aria-label="Replay position" />
          <div className="mt-1 flex justify-between font-data text-[11px] text-[#64748B]"><span>{formatTime(seekPosition)}</span><span>{formatTime(status.duration_seconds || selected?.duration_seconds)}</span></div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {!playing && !paused && <button disabled={!recordId || busy} onClick={() => run(() => startReplay(recordId, speed, noFailures))} className="flex h-9 items-center gap-2 rounded-md bg-[#1A6BCC] px-4 text-sm font-semibold text-white disabled:opacity-50"><Play size={15} />Start replay</button>}
            {playing && <button disabled={busy} onClick={() => run(pauseReplay)} className="flex h-9 items-center gap-2 rounded-md bg-[#0F172A] px-4 text-sm font-semibold text-white"><Pause size={15} />Pause stream</button>}
            {paused && <button disabled={busy} onClick={() => run(resumeReplay)} className="flex h-9 items-center gap-2 rounded-md bg-[#1A6BCC] px-4 text-sm font-semibold text-white"><Play size={15} />Resume</button>}
            {(playing || paused || status.state === 'COMPLETED') && <button disabled={busy} onClick={() => run(restartReplay)} title="Restart recording" className="flex h-9 w-9 items-center justify-center rounded-md border border-[#CBD5E1] bg-white text-[#475569]"><RefreshCcw size={15} /></button>}
            {(playing || paused) && <button disabled={busy} onClick={() => run(stopReplay)} title="Stop replay" className="flex h-9 w-9 items-center justify-center rounded-md border border-[#CBD5E1] bg-white text-[#475569]"><RotateCcw size={15} /></button>}
            <button onClick={toggleFreeze} title={frozenData ? 'Resume display updates' : 'Freeze plots for inspection'} className={`ml-auto flex h-9 items-center gap-2 rounded-md border px-3 text-xs font-semibold ${frozenData ? 'border-[#0D9488] bg-[#CCFBF1] text-[#0F766E]' : 'border-[#CBD5E1] bg-white text-[#475569]'}`}><Snowflake size={14} />{frozenData ? 'Display frozen' : 'Freeze display'}</button>
          </div>
          {error && <div className="mt-3 rounded-md border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-xs text-[#B91C1C]">{error}</div>}
        </div>
      </section>

      <section className="grid grid-cols-2 overflow-hidden rounded-lg border border-[#CBD5E1] bg-white shadow-sm sm:grid-cols-4" aria-label="Recorded numeric sensors">
        {[
          ['Heart rate', vitals.heart_rate, 'bpm', '#EF4444'],
          ['Pulse rate', vitals.pulse_rate, 'bpm', '#0D9488'],
          ['SpO₂', vitals.spo2, '%', '#1A6BCC'],
          ['Respiratory rate', vitals.respiratory_rate, 'br/min', '#D97706'],
        ].map(([label, value, unit, color], index) => (
          <div key={String(label)} className={`px-5 py-4 ${index < 3 ? 'sm:border-r' : ''} ${index < 2 ? 'border-b sm:border-b-0' : ''} border-[#E2E8F0]`}>
            <div className="flex items-center gap-2 text-[11px] font-medium text-[#64748B]"><Gauge size={13} style={{ color: String(color) }} />{label}</div>
            <div className="mt-2 font-data text-2xl text-[#0F172A]">{value === undefined || value === null ? '--' : Number(value).toFixed(0)} <span className="text-xs text-[#94A3B8]">{unit}</span></div>
          </div>
        ))}
      </section>

      <section className="overflow-hidden rounded-lg border border-[#CBD5E1] bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-[#CBD5E1] bg-[#F8FAFC] px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-2"><Activity size={17} className="text-[#0D9488]" /><h2 className="text-sm font-semibold text-[#0F172A]">Synchronized waveform channels</h2><span className="font-data text-[10px] text-[#64748B]">20 s rolling window</span></div>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(channelMeta) as ChannelKey[]).map(channel => (
              <button key={channel} onClick={() => setVisible(current => ({ ...current, [channel]: !current[channel] }))} className={`flex h-8 items-center gap-2 rounded-md border px-2.5 text-[11px] font-medium ${visible[channel] ? 'border-[#CBD5E1] bg-white text-[#334155]' : 'border-[#E2E8F0] bg-[#F1F5F9] text-[#94A3B8]'}`}>
                {visible[channel] ? <Eye size={13} /> : <EyeOff size={13} />}<span className="h-2 w-2 rounded-full" style={{ backgroundColor: channelMeta[channel].color }} />{channelMeta[channel].label.replace('Photoplethysmogram', 'PPG').replace('Impedance Respiration', 'RESP')}
              </button>
            ))}
          </div>
        </div>
        {shownChannels.length ? shownChannels.map(channel => <WaveformPlot key={channel} channel={channel} data={displayData[channel]} />) : <div className="flex h-40 items-center justify-center text-sm text-[#64748B]">Select at least one waveform channel.</div>}
      </section>

      <section className="grid gap-3 rounded-lg border border-[#CBD5E1] bg-[#F8FAFC] p-4 text-xs text-[#475569] sm:grid-cols-2 lg:grid-cols-4">
        <div><div className="text-[10px] font-bold uppercase text-[#94A3B8]">Provenance</div><div className="mt-1 font-medium text-[#0F172A]">PhysioNet · BIDMC v1.0.0</div></div>
        <div><div className="text-[10px] font-bold uppercase text-[#94A3B8]">Record</div><div className="mt-1 font-data text-[#0F172A]">{datasetTelemetry?.provenance?.record_id ?? recordId ?? '--'}</div></div>
        <div><div className="text-[10px] font-bold uppercase text-[#94A3B8]">Original offset</div><div className="mt-1 font-data text-[#0F172A]">{Number(datasetTelemetry?.provenance?.original_timestamp ?? seekPosition).toFixed(3)} s</div></div>
        <div><div className="text-[10px] font-bold uppercase text-[#94A3B8]">Display</div><div className="mt-1 font-medium text-[#0F172A]">{frozenData ? 'Frozen for manual inspection' : 'Following replay stream'}</div></div>
      </section>
    </div>
  )
}
