import { X, CheckCircle, AlertTriangle, AlertCircle, Info } from 'lucide-react'

export interface Toast {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  title: string
  message?: string
}

const iconMap = {
  success: <CheckCircle size={16} className="text-[#10B981]" />,
  warning: <AlertTriangle size={16} className="text-[#F59E0B]" />,
  error: <AlertCircle size={16} className="text-[#EF4444]" />,
  info: <Info size={16} className="text-[#1A6BCC]" />,
}

const borderMap = {
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#1A6BCC',
}

interface Props {
  toasts: Toast[]
  onDismiss: (id: string) => void
}

export default function ToastContainer({ toasts, onDismiss }: Props) {
  return (
    <div className="fixed bottom-6 left-6 z-50 flex flex-col gap-2" style={{ maxWidth: 340 }}>
      {toasts.map(t => (
        <div
          key={t.id}
          className="toast-in hp-card flex items-start gap-3 p-4 shadow-lg"
          style={{ borderLeft: `3px solid ${borderMap[t.type]}` }}
        >
          <span className="mt-0.5 shrink-0">{iconMap[t.type]}</span>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-[#0F172A] leading-tight">{t.title}</div>
            {t.message && <div className="text-xs text-[#64748B] mt-0.5">{t.message}</div>}
          </div>
          <button onClick={() => onDismiss(t.id)} className="shrink-0 text-[#94A3B8] hover:text-[#64748B]">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  )
}
