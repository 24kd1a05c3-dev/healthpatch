import { Activity, Battery, Database, Radio, ShieldCheck, Wifi } from 'lucide-react'
import patchImage from '../assets/healthpatch-device.png'

type Props = {
  source: 'dataset' | 'synthetic'
  replayState: any
  telemetry: any
  deviceStatus: any
}

export default function DigitalTwinPanel({ source, replayState, telemetry, deviceStatus }: Props) {
  const dataset = source === 'dataset'
  const stale = !telemetry?.timestamp || Date.now() - Date.parse(telemetry.timestamp) > 15000
  const state = dataset ? (replayState?.state ?? 'STOPPED') : (stale ? 'NO RECENT DATA' : 'RECEIVING')
  const active = !stale && ['CONNECTED', 'PLAYING', 'READY', 'RECEIVING'].includes(state)
  const twinId = telemetry?.device_id ?? 'No active source'
  const signal = telemetry?.signal_quality == null ? null : Math.round(telemetry.signal_quality * 100)
  const battery = dataset ? null : (deviceStatus?.battery ?? null)

  return (
    <section className="relative min-h-[430px] overflow-hidden rounded-lg bg-[#07111F] text-white border border-[#17283D]" aria-label="Digital twin">
      <div className="absolute inset-0 twin-grid opacity-30" />
      <div className="relative z-10 p-5 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] font-semibold text-[#5EEAD4] uppercase"><Activity size={13} />Digital Twin</div>
          <h2 className="mt-1 text-xl font-semibold">HealthPatch · HP-01</h2>
          <div className="mt-1 font-data text-[11px] text-[#7F94AA]">{twinId}</div>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-[11px] font-semibold border ${active ? 'border-[#14B8A6]/40 bg-[#14B8A6]/10 text-[#5EEAD4]' : 'border-[#F59E0B]/40 bg-[#F59E0B]/10 text-[#FCD34D]'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-[#2DD4BF] twin-pulse' : 'bg-[#F59E0B]'}`} />{state}
        </div>
      </div>

      <div className="relative z-10 h-[255px] flex items-center justify-center">
        <div className={`absolute w-56 h-56 rounded-full border ${active ? 'border-[#2DD4BF]/25 twin-orbit' : 'border-[#334155]'}`} />
        <div className={`absolute w-72 h-72 rounded-full border border-dashed ${active ? 'border-[#38BDF8]/15 twin-orbit-reverse' : 'border-[#1E293B]'}`} />
        <img src={patchImage} alt="HealthPatch wearable sensor digital twin" className="relative z-10 w-[360px] max-w-[82%] object-contain drop-shadow-[0_24px_34px_rgba(0,0,0,0.45)]" />
        <span className="absolute left-[16%] top-[28%] text-[10px] font-data text-[#5EEAD4] border-l border-[#2DD4BF] pl-2">PPG SENSOR</span>
        <span className="absolute right-[13%] bottom-[24%] text-[10px] font-data text-[#7DD3FC] border-r border-[#38BDF8] pr-2">ECG CONTACT</span>
      </div>

      <div className="relative z-10 px-5 py-2 border-t border-[#17283D] bg-[#091522] flex items-center gap-2 text-[10px] text-[#7F94AA]"><Radio size={12} />Last sync {telemetry?.timestamp ? new Date(telemetry.timestamp).toLocaleTimeString() : 'awaiting telemetry'}</div>

      <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 border-t border-[#17283D] bg-[#0A1727]/85">
        <Metric icon={<Database size={14} />} label="Source" value={!telemetry ? 'WAITING' : dataset ? 'BIDMC REPLAY' : 'SIMULATED DATA'} />
        <Metric icon={<Wifi size={14} />} label="Signal" value={signal === null ? 'UNKNOWN' : `${signal}%`} />
        <Metric icon={<Battery size={14} />} label="Battery" value={battery === null ? 'N/A' : `${Math.round(battery)}%`} />
        <Metric icon={<ShieldCheck size={14} />} label="Provenance" value={dataset ? (telemetry?.provenance?.record_id ?? 'WAITING') : 'TAGGED'} />
      </div>
    </section>
  )
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="px-4 py-3 border-r border-[#17283D] last:border-r-0 min-w-0"><div className="flex items-center gap-1.5 text-[#6F8499] text-[10px] uppercase">{icon}{label}</div><div className="mt-1 font-data text-[12px] text-[#DCEAF5] truncate">{value}</div></div>
}
