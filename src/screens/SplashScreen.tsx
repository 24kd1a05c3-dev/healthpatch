import { useEffect, useState } from 'react'
import { Activity } from 'lucide-react'

interface Props {
  onComplete: () => void
}

export default function SplashScreen({ onComplete }: Props) {
  const [phase, setPhase] = useState(0) // 0=logo, 1=text, 2=arc, 3=done

  useEffect(() => {
    const t1 = setTimeout(() => setPhase(1), 800)
    const t2 = setTimeout(() => setPhase(2), 1400)
    const t3 = setTimeout(() => setPhase(3), 3200)
    const t4 = setTimeout(() => onComplete(), 3600)
    return () => [t1, t2, t3, t4].forEach(clearTimeout)
  }, [onComplete])

  return (
    <div
      className="fixed inset-0 flex flex-col items-center justify-center"
      style={{ background: 'linear-gradient(145deg, #0A1628 0%, #0F172A 50%, #091320 100%)' }}
    >
      {/* Background medical grid */}
      <div className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: 'linear-gradient(#1A6BCC 1px, transparent 1px), linear-gradient(90deg, #1A6BCC 1px, transparent 1px)',
          backgroundSize: '40px 40px'
        }}
      />

      {/* Radial glow */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[600px] h-[600px] rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, #1A6BCC 0%, transparent 70%)' }}
        />
      </div>

      {/* Logo */}
      <div className={`logo-in flex flex-col items-center gap-6 relative z-10`} style={{ animationDelay: '0ms' }}>
        {/* Icon container with arc */}
        <div className="relative w-28 h-28 flex items-center justify-center">
          {/* SVG arc */}
          <svg className="absolute inset-0" viewBox="0 0 120 120" width="120" height="120">
            <circle cx="60" cy="60" r="54" fill="none" stroke="#1E293B" strokeWidth="3" />
            {phase >= 2 && (
              <circle
                cx="60" cy="60" r="54"
                fill="none"
                stroke="url(#arc-grad)"
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray="339"
                className="arc-fill"
                style={{ strokeDashoffset: 339, transformOrigin: '60px 60px', transform: 'rotate(-90deg)' }}
              />
            )}
            <defs>
              <linearGradient id="arc-grad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#1A6BCC" />
                <stop offset="100%" stopColor="#0D9488" />
              </linearGradient>
            </defs>
          </svg>

          {/* Center icon */}
          <div className="w-20 h-20 rounded-[22px] flex items-center justify-center shadow-2xl"
            style={{ background: 'linear-gradient(135deg, #1A6BCC 0%, #0D9488 100%)' }}>
            <Activity size={36} className="text-white" />
          </div>
        </div>

        {/* Brand text */}
        {phase >= 1 && (
          <div className="fade-in-up text-center" style={{ animationDelay: '0ms' }}>
            <div className="text-white text-4xl font-bold tracking-tight">HealthPatch</div>
            <div className="text-[#64748B] text-sm mt-1 tracking-[0.2em] uppercase">Smart Patient Monitoring</div>
          </div>
        )}

        {/* Loading dots */}
        {phase >= 2 && (
          <div className="fade-in-up flex gap-2 mt-2" style={{ animationDelay: '0ms' }}>
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-[#1A6BCC]"
                style={{ animation: `status-pulse 1.2s ease-in-out ${i * 0.2}s infinite` }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Bottom version */}
      {phase >= 1 && (
        <div className="absolute bottom-8 text-[#334155] text-xs fade-in-up" style={{ animationDelay: '200ms' }}>
          v2.4.1 · HIPAA Compliant · FDA Class II
        </div>
      )}

      {/* Transition overlay */}
      {phase === 3 && (
        <div className="absolute inset-0 bg-white"
          style={{ animation: 'logo-in 0.4s ease reverse forwards' }}
        />
      )}
    </div>
  )
}
