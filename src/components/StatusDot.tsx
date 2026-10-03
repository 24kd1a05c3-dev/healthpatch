interface Props {
  status: 'live' | 'offline' | 'warning'
  label?: string
  size?: 'sm' | 'md'
}

const colorMap = {
  live: '#10B981',
  offline: '#94A3B8',
  warning: '#F59E0B',
}

const labelMap = {
  live: 'Live',
  offline: 'Offline',
  warning: 'Warning',
}

export default function StatusDot({ status, label, size = 'md' }: Props) {
  const color = colorMap[status]
  const dotSize = size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'
  const textSize = size === 'sm' ? 'text-[11px]' : 'text-xs'

  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`${dotSize} rounded-full ${status === 'live' ? 'status-dot-live' : ''}`}
        style={{ backgroundColor: color }}
      />
      <span className={`${textSize} font-medium`} style={{ color }}>
        {label ?? labelMap[status]}
      </span>
    </div>
  )
}
