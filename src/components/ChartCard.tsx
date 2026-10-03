import type { ReactNode } from 'react'

interface ChartCardProps {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}

export default function ChartCard({ title, subtitle, actions, children }: ChartCardProps) {
  return (
    <section className="hp-card p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold text-[#0F172A]">{title}</h2>
          {subtitle && <p className="mt-0.5 text-[12px] text-[#94A3B8]">{subtitle}</p>}
        </div>
        {actions && <div className="shrink-0">{actions}</div>}
      </div>
      {children}
    </section>
  )
}
