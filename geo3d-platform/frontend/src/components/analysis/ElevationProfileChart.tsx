import { useState, useRef } from 'react'
import { useViewerStore } from '../../stores'

interface ElevationProfileChartProps {
  data: {
    total_distance_m: number
    min_elevation_m: number
    max_elevation_m: number
    avg_elevation_m: number
    elevation_gain_m: number
    elevation_loss_m: number
    max_slope_percent: number
    avg_slope_percent: number
    samples: Array<{
      distance_m: number
      lon: number
      lat: number
      alt: number
      slope_percent: number
    }>
  }
  onClose: () => void
}

export default function ElevationProfileChart({ data, onClose }: ElevationProfileChartProps) {
  const { setHoverProfileDistance } = useViewerStore()
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const { samples, total_distance_m, min_elevation_m, max_elevation_m } = data

  if (!samples || samples.length === 0) return null

  // Chart dimensions
  const width = 680
  const height = 180
  const padding = { top: 20, right: 30, bottom: 30, left: 55 }
  const chartW = width - padding.left - padding.right
  const chartH = height - padding.top - padding.bottom

  const yMin = Math.floor(min_elevation_m - 2)
  const yMax = Math.ceil(max_elevation_m + 2)
  const ySpan = Math.max(1, yMax - yMin)

  const getX = (dist: number) => padding.left + (dist / Math.max(1, total_distance_m)) * chartW
  const getY = (alt: number) => padding.top + chartH - ((alt - yMin) / ySpan) * chartH

  // Build SVG Path
  const pointsString = samples
    .map((s) => `${getX(s.distance_m).toFixed(1)},${getY(s.alt).toFixed(1)}`)
    .join(' ')

  const areaPath = `M ${getX(0)},${padding.top + chartH} L ${pointsString} L ${getX(
    total_distance_m
  )},${padding.top + chartH} Z`
  const linePath = `M ${pointsString}`

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const mouseX = e.clientX - rect.left - padding.left
    const clampedX = Math.max(0, Math.min(chartW, mouseX))
    const ratio = clampedX / chartW
    const targetDist = ratio * total_distance_m

    // Find nearest sample
    let nearestIdx = 0
    let minDiff = Infinity
    for (let i = 0; i < samples.length; i++) {
      const diff = Math.abs(samples[i].distance_m - targetDist)
      if (diff < minDiff) {
        minDiff = diff
        nearestIdx = i
      }
    }

    setHoverIndex(nearestIdx)
    setHoverProfileDistance(samples[nearestIdx].distance_m)
  }

  const handleMouseLeave = () => {
    setHoverIndex(null)
    setHoverProfileDistance(null)
  }

  const activeSample = hoverIndex !== null ? samples[hoverIndex] : null

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 48,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(740px, 92vw)',
        background: 'rgba(15, 19, 32, 0.94)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: 12,
        boxShadow: '0 16px 36px rgba(0, 0, 0, 0.55)',
        zIndex: 50,
        overflow: 'hidden',
        animation: 'slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          background: 'rgba(255, 255, 255, 0.02)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>⛰️</span>
          <span style={{ fontWeight: 600, fontSize: 13, color: '#f0f4f8' }}>
            Elevation Profile Transect
          </span>
          <span
            style={{
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 12,
              background: 'rgba(56, 189, 248, 0.15)',
              color: '#38bdf8',
            }}
          >
            {total_distance_m >= 1000
              ? `${(total_distance_m / 1000).toFixed(2)} km`
              : `${total_distance_m.toFixed(1)} m`}
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--color-text-muted)',
            cursor: 'pointer',
            fontSize: 16,
            padding: 4,
          }}
          title="Close Elevation Profile"
        >
          ✕
        </button>
      </div>

      {/* Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(5, 1fr)',
          gap: 8,
          padding: '8px 16px',
          background: 'rgba(0, 0, 0, 0.2)',
          fontSize: 11,
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
        }}
      >
        <div>
          <div style={{ color: 'var(--color-text-muted)' }}>Min Elev</div>
          <div style={{ fontWeight: 600, color: '#93c5fd' }}>{min_elevation_m.toFixed(1)} m</div>
        </div>
        <div>
          <div style={{ color: 'var(--color-text-muted)' }}>Max Elev</div>
          <div style={{ fontWeight: 600, color: '#f87171' }}>{max_elevation_m.toFixed(1)} m</div>
        </div>
        <div>
          <div style={{ color: 'var(--color-text-muted)' }}>Gain / Loss</div>
          <div style={{ fontWeight: 600, color: '#4ade80' }}>
            +{data.elevation_gain_m.toFixed(1)} / -{data.elevation_loss_m.toFixed(1)} m
          </div>
        </div>
        <div>
          <div style={{ color: 'var(--color-text-muted)' }}>Avg Slope</div>
          <div style={{ fontWeight: 600, color: '#fbbf24' }}>{data.avg_slope_percent.toFixed(1)}%</div>
        </div>
        <div>
          <div style={{ color: 'var(--color-text-muted)' }}>Max Slope</div>
          <div style={{ fontWeight: 600, color: '#f97316' }}>{data.max_slope_percent.toFixed(1)}%</div>
        </div>
      </div>

      {/* SVG Chart */}
      <div style={{ position: 'relative', padding: '6px 8px 10px 8px' }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', display: 'block', cursor: 'crosshair' }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <defs>
            <linearGradient id="elevGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.02" />
            </linearGradient>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="50%" stopColor="#818cf8" />
              <stop offset="100%" stopColor="#f43f5e" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((t) => {
            const y = padding.top + chartH * (1 - t)
            const elevVal = yMin + ySpan * t
            return (
              <g key={t}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={padding.left + chartW}
                  y2={y}
                  stroke="rgba(255,255,255,0.08)"
                  strokeDasharray="4 4"
                />
                <text
                  x={padding.left - 8}
                  y={y + 4}
                  fill="rgba(255,255,255,0.4)"
                  fontSize="10"
                  textAnchor="end"
                >
                  {elevVal.toFixed(0)}m
                </text>
              </g>
            )
          })}

          {/* X Axis labels */}
          {[0, 0.5, 1.0].map((t) => {
            const x = padding.left + chartW * t
            const distVal = total_distance_m * t
            return (
              <text
                key={t}
                x={x}
                y={height - 8}
                fill="rgba(255,255,255,0.4)"
                fontSize="10"
                textAnchor={t === 0 ? 'start' : t === 1.0 ? 'end' : 'middle'}
              >
                {distVal >= 1000 ? `${(distVal / 1000).toFixed(1)} km` : `${distVal.toFixed(0)} m`}
              </text>
            )
          })}

          {/* Filled Area & Line */}
          <path d={areaPath} fill="url(#elevGrad)" />
          <path d={linePath} fill="none" stroke="url(#lineGrad)" strokeWidth="2.5" />

          {/* Hover Crosshair & Circle */}
          {activeSample && (
            <g>
              <line
                x1={getX(activeSample.distance_m)}
                y1={padding.top}
                x2={getX(activeSample.distance_m)}
                y2={padding.top + chartH}
                stroke="rgba(255, 255, 255, 0.7)"
                strokeDasharray="2 2"
                strokeWidth="1.5"
              />
              <circle
                cx={getX(activeSample.distance_m)}
                cy={getY(activeSample.alt)}
                r="5"
                fill="#ffffff"
                stroke="#38bdf8"
                strokeWidth="2.5"
              />
            </g>
          )}
        </svg>

        {/* Floating Tooltip */}
        {activeSample && (
          <div
            style={{
              position: 'absolute',
              top: 14,
              left: `${Math.max(15, Math.min(85, (activeSample.distance_m / total_distance_m) * 100))}%`,
              transform: 'translateX(-50%)',
              background: 'rgba(10, 14, 26, 0.95)',
              border: '1px solid #38bdf8',
              borderRadius: 6,
              padding: '4px 10px',
              fontSize: 11,
              color: '#ffffff',
              pointerEvents: 'none',
              whiteSpace: 'nowrap',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            }}
          >
            <div>
              <strong>Elevation:</strong> {activeSample.alt.toFixed(1)} m
            </div>
            <div style={{ color: '#94a3b8' }}>
              Dist: {activeSample.distance_m.toFixed(1)} m | Slope: {activeSample.slope_percent.toFixed(1)}%
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
