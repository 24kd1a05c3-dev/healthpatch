import { Bell } from 'lucide-react'
import type { Screen } from './Sidebar'
import { useAuth } from '../context/AuthContext'

const screenTitles: Record<string, { title: string; sub: string }> = {
  dashboard: { title: 'Dashboard', sub: 'Patient overview & vitals' },
  live: { title: 'Patch Digital Twin', sub: 'Source, state, signals, and replay controls' },
  signals: { title: 'Signal Lab', sub: 'Recorded waveform inspection and replay controls' },
  insights: { title: 'Statistical Observations', sub: 'Within-stream baseline and deviation' },
  simulator: { title: 'Research Simulator', sub: 'Explicitly synthetic scenario stream' },
  alerts: { title: 'Alert Center', sub: 'Critical notifications' },
  history: { title: 'Health History', sub: 'Trends & analysis' },
  profile: { title: 'Patient Profile', sub: 'Personal & medical info' },
  doctor: { title: 'Doctor Dashboard', sub: 'Patient management' },
  pairing: { title: 'Device Pairing', sub: 'ESP32 & sensor setup' },
  settings: { title: 'Settings', sub: 'Preferences & configuration' },
}

interface Props {
  current: Screen
  alertCount?: number
  onNavigate: (screen: Screen) => void
}

export default function TopBar({ current, alertCount = 0, onNavigate }: Props) {
  const { user } = useAuth()
  const info = screenTitles[current] ?? { title: 'HealthPatch', sub: '' }
  const initials = user?.full_name
    ? user.full_name.split(' ').map((part: string) => part[0]).join('').slice(0, 2).toUpperCase()
    : 'HP'

  return (
    <header className="h-16 bg-white border-b border-[#E2E8F0] flex items-center pl-16 pr-4 md:px-6 gap-4 shrink-0 sticky top-0 z-20">
      <div className="flex-1 min-w-0">
        <h1 className="text-[17px] font-semibold text-[#0F172A] leading-tight truncate">{info.title}</h1>
        <p className="text-[12px] text-[#94A3B8] leading-tight">{info.sub}</p>
      </div>

      {/* Alerts bell */}
      <button onClick={() => onNavigate('alerts')} title="Open alerts" aria-label="Open alerts" className="relative w-9 h-9 shrink-0 rounded-lg bg-[#F5F8FC] border border-[#E2E8F0] flex items-center justify-center text-[#64748B] hover:text-[#1A6BCC] transition-colors">
        <Bell size={16} />
        {alertCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-[#EF4444] rounded-full text-white text-[9px] font-bold flex items-center justify-center">
            {alertCount}
          </span>
        )}
      </button>

      {/* User */}
      <button onClick={() => onNavigate('profile')} title="Open profile" aria-label="Open profile" className="flex shrink-0 items-center gap-2.5 pl-3 border-l border-[#E2E8F0]">
        <div className="w-8 h-8 rounded-full overflow-hidden bg-gradient-to-br from-[#1A6BCC] to-[#0D9488] flex items-center justify-center">
          <span className="text-white text-xs font-bold">{initials}</span>
        </div>
        <div className="hidden md:block text-left">
          <div className="text-[13px] font-semibold text-[#0F172A] leading-tight">{user?.full_name || 'HealthPatch User'}</div>
          <div className="text-[11px] text-[#94A3B8] leading-tight capitalize">{user?.role || 'patient'}</div>
        </div>
      </button>
    </header>
  )
}
