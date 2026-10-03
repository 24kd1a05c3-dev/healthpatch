export default function ECGLine({ color = '#1A6BCC', height = 80 }: { color?: string; height?: number }) {
  // Two copies of the waveform concatenated for seamless loop
  const wave = `M0,${height / 2}
    L60,${height / 2}
    L80,${height / 2 - 5}
    L95,${height / 2 + 10}
    L105,${height * 0.08}
    L115,${height * 0.92}
    L125,${height / 2}
    L140,${height / 2}
    L155,${height / 2 - 12}
    L165,${height / 2 + 12}
    L175,${height / 2}
    L240,${height / 2}
    L260,${height / 2 - 5}
    L275,${height / 2 + 10}
    L285,${height * 0.08}
    L295,${height * 0.92}
    L305,${height / 2}
    L320,${height / 2}
    L335,${height / 2 - 12}
    L345,${height / 2 + 12}
    L355,${height / 2}
    L420,${height / 2}`

  const totalWidth = 420

  return (
    <div className="overflow-hidden w-full" style={{ height }}>
      <div className="ecg-animate" style={{ display: 'flex', width: '200%' }}>
        <svg width={totalWidth} height={height} viewBox={`0 0 ${totalWidth} ${height}`} preserveAspectRatio="none">
          <defs>
            <linearGradient id="ecg-fade-l" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={color} stopOpacity="0" />
              <stop offset="15%" stopColor={color} stopOpacity="1" />
              <stop offset="100%" stopColor={color} stopOpacity="1" />
            </linearGradient>
          </defs>
          <path d={wave} fill="none" stroke={`url(#ecg-fade-l)`} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <svg width={totalWidth} height={height} viewBox={`0 0 ${totalWidth} ${height}`} preserveAspectRatio="none">
          <path d={wave} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.7" />
        </svg>
      </div>
    </div>
  )
}
