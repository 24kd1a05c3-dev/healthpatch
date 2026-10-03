type Severity = 'critical' | 'warning' | 'resolved' | 'info'

interface Props {
  severity: Severity
  label?: string
  dot?: boolean
}

const map = {
  critical: { bg: '#FEE2E2', text: '#DC2626', dot: '#EF4444', label: 'Critical' },
  warning: { bg: '#FEF3C7', text: '#D97706', dot: '#F59E0B', label: 'Warning' },
  resolved: { bg: '#D1FAE5', text: '#059669', dot: '#10B981', label: 'Resolved' },
  info: { bg: '#E8F1FB', text: '#1558AB', dot: '#1A6BCC', label: 'Info' },
}

export default function AlertBadge({ severity, label, dot }: Props) {
  const m = map[severity]
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold"
      style={{ backgroundColor: m.bg, color: m.text }}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: m.dot }} />}
      {label ?? m.label}
    </span>
  )
}
