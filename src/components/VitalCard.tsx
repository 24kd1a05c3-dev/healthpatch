import type { ReactNode } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  unit: string
  icon: ReactNode
  trend?: 'up' | 'down' | 'stable'
  trendValue?: string
  status?: 'normal' | 'warning' | 'critical'
  color?: 'blue' | 'teal' | 'emerald' | 'red' | 'amber' | 'slate'
  subtitle?: string
  large?: boolean
}

const colorMap = {
  blue: { bg: '#E8F1FB', icon: '#1A6BCC', text: '#1A6BCC', border: '#BFDBFE' },
  teal: { bg: '#CCFBF1', icon: '#0D9488', text: '#0D9488', border: '#99F6E4' },
  emerald: { bg: '#D1FAE5', icon: '#10B981', text: '#10B981', border: '#6EE7B7' },
  red: { bg: '#FEE2E2', icon: '#EF4444', text: '#EF4444', border: '#FCA5A5' },
  amber: { bg: '#FEF3C7', icon: '#F59E0B', text: '#F59E0B', border: '#FDE68A' },
  slate: { bg: '#F1F5F9', icon: '#64748B', text: '#64748B', border: '#CBD5E1' },
}

const statusMap = {
  normal: { dot: '#10B981', label: 'Normal' },
  warning: { dot: '#F59E0B', label: 'Warning' },
  critical: { dot: '#EF4444', label: 'Critical' },
}

export default function VitalCard({ label, value, unit, icon, trend, trendValue, status = 'normal', color = 'blue', subtitle, large }: Props) {
  const c = colorMap[color]
  const s = statusMap[status]

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor = trend === 'up' ? '#10B981' : trend === 'down' ? '#EF4444' : '#94A3B8'

  return (
    <div className="hp-card p-5 flex flex-col gap-3 hover:shadow-lg transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ backgroundColor: c.bg }}
        >
          <span style={{ color: c.icon }}>{icon}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="status-dot-live inline-block w-2 h-2 rounded-full" style={{ backgroundColor: s.dot }} />
          <span className="text-[11px] font-medium" style={{ color: s.dot }}>{s.label}</span>
        </div>
      </div>

      <div>
        <div className="flex items-end gap-1.5">
          <span className={`font-data font-medium leading-none ${large ? 'text-4xl' : 'text-3xl'}`} style={{ color: c.text }}>
            {value}
          </span>
          <span className="text-sm text-[#94A3B8] mb-0.5">{unit}</span>
        </div>
        <div className="mt-1 text-[13px] font-medium text-[#0F172A]">{label}</div>
        {subtitle && <div className="text-[11px] text-[#94A3B8] mt-0.5">{subtitle}</div>}
      </div>

      {trend && trendValue && (
        <div className="flex items-center gap-1 pt-1 border-t border-[#F1F5F9]">
          <TrendIcon size={12} style={{ color: trendColor }} />
          <span className="text-[11px] font-medium" style={{ color: trendColor }}>{trendValue}</span>
          <span className="text-[11px] text-[#94A3B8]">vs last hour</span>
        </div>
      )}
    </div>
  )
}
