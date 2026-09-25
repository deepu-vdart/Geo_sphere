import React, { useState } from 'react'
import { useViewerStore } from '../../stores'
import { type CrossSectionPoint } from '../../api/client'

const CLASS_NAMES: Record<number, { name: string; color: string }> = {
  0: { name: 'Created / Unassigned', color: '#94a3b8' },
  1: { name: 'Unclassified', color: '#cbd5e1' },
  2: { name: 'Ground', color: '#d97706' },
  3: { name: 'Low Veg', color: '#84cc16' },
  4: { name: 'Med Veg', color: '#22c55e' },
  5: { name: 'High Veg / Tree', color: '#15803d' },
  6: { name: 'Building', color: '#ef4444' },
  7: { name: 'Low Point / Noise', color: '#f59e0b' },
  8: { name: 'Model Key-point', color: '#eab308' },
  9: { name: 'Water', color: '#38bdf8' },
  10: { name: 'Rail / Road', color: '#a855f7' },
  11: { name: 'Road Surface', color: '#64748b' },
  12: { name: 'Wire Guard', color: '#ec4899' },
}

export default function PotreeProfileWindow() {
  const {
    potreeProfileOpen,
    setPotreeProfileOpen,
    potreeCrossSectionData,
    potreeCorridorWidth,
    setPotreeCorridorWidth,
  } = useViewerStore()

  const [hoveredPoint, setHoveredPoint] = useState<CrossSectionPoint | null>(null)

  if (!potreeProfileOpen || !potreeCrossSectionData) {
    return null
  }

  const {
    transect_length_m,
    corridor_width_m,
    point_count,
    min_elevation,
    max_elevation,
    delta_elevation,
    points,
  } = potreeCrossSectionData

  // SVG dimensions
  const svgWidth = 760
  const svgHeight = 220
  const padLeft = 60
  const padRight = 30
  const padTop = 25
  const padBottom = 35

  const plotWidth = svgWidth - padLeft - padRight
  const plotHeight = svgHeight - padTop - padBottom

  const maxDist = Math.max(transect_length_m, 1.0)
  const elevSpan = Math.max(max_elevation - min_elevation, 1.0)
  const elevMargin = elevSpan * 0.15
  const yMin = min_elevation - elevMargin
  const yMax = max_elevation + elevMargin
  const yRange = yMax - yMin

  const getX = (dist: number) => padLeft + (dist / maxDist) * plotWidth
  const getY = (elev: number) => padTop + plotHeight - ((elev - yMin) / yRange) * plotHeight

  // Generate grid ticks
  const xTickCount = 6
  const xTicks = Array.from({ length: xTickCount + 1 }, (_, i) => (maxDist / xTickCount) * i)

  const yTickCount = 4
  const yTicks = Array.from({ length: yTickCount + 1 }, (_, i) => yMin + (yRange / yTickCount) * i)

  return (
    <div
      id="potree_profile_window"
      style={{
        position: 'absolute',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(940px, 92vw)',
        background: 'rgba(15, 23, 42, 0.94)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(56, 189, 248, 0.35)',
        borderRadius: 12,
        boxShadow: '0 20px 45px rgba(0, 0, 0, 0.65), 0 0 25px rgba(56, 189, 248, 0.2)',
        zIndex: 900,
        overflow: 'hidden',
        color: '#f8fafc',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          background: 'linear-gradient(90deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.95))',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16 }}>📈</span>
          <span style={{ fontWeight: 700, fontSize: 13, letterSpacing: '0.03em' }}>
            POTREE 2D ELEVATION CROSS-SECTION PROFILE
          </span>
          <span
            style={{
              fontSize: 10,
              padding: '2px 8px',
              borderRadius: 20,
              background: 'rgba(56, 189, 248, 0.2)',
              color: '#38bdf8',
              fontWeight: 600,
            }}
          >
            {point_count.toLocaleString()} Sliced Points
          </span>
        </div>

        {/* Corridor Width & Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
            <span style={{ color: 'var(--color-text-muted, #94a3b8)' }}>Corridor Width:</span>
            {[0.5, 1.0, 2.0, 5.0].map((w) => (
              <button
                key={w}
                onClick={() => setPotreeCorridorWidth(w)}
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: potreeCorridorWidth === w ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                  background: potreeCorridorWidth === w ? 'rgba(56, 189, 248, 0.25)' : 'rgba(255,255,255,0.04)',
                  color: potreeCorridorWidth === w ? '#38bdf8' : '#94a3b8',
                }}
              >
                {w}m
              </button>
            ))}
          </div>

          <button
            onClick={() => setPotreeProfileOpen(false)}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: 16,
              padding: '0 4px',
              lineHeight: 1,
            }}
            title="Close 2D Cross Section"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 8,
          padding: '8px 16px',
          background: 'rgba(15, 23, 42, 0.6)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          fontSize: 11,
        }}
      >
        <div>
          <span style={{ color: '#94a3b8' }}>Transect Length: </span>
          <strong style={{ color: '#38bdf8' }}>{transect_length_m.toFixed(1)} m</strong>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Min Elevation: </span>
          <strong style={{ color: '#34d399' }}>{min_elevation.toFixed(1)} m</strong>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Max Elevation: </span>
          <strong style={{ color: '#f87171' }}>{max_elevation.toFixed(1)} m</strong>
        </div>
        <div>
          <span style={{ color: '#94a3b8' }}>Elevation Delta (ΔZ): </span>
          <strong style={{ color: '#fbbf24' }}>{delta_elevation.toFixed(1)} m</strong>
        </div>
      </div>

      {/* Interactive 2D Profile Canvas */}
      <div style={{ position: 'relative', padding: '12px 16px 8px 16px' }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
        >
          {/* Background grid */}
          <rect
            x={padLeft}
            y={padTop}
            width={plotWidth}
            height={plotHeight}
            fill="rgba(10, 15, 30, 0.7)"
            stroke="rgba(255, 255, 255, 0.08)"
          />

          {/* Horizontal grid lines & Y labels */}
          {yTicks.map((yVal, idx) => {
            const yPos = getY(yVal)
            return (
              <g key={idx}>
                <line
                  x1={padLeft}
                  y1={yPos}
                  x2={padLeft + plotWidth}
                  y2={yPos}
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeDasharray="3 3"
                />
                <text
                  x={padLeft - 8}
                  y={yPos + 3}
                  textAnchor="end"
                  fontSize="10"
                  fill="#94a3b8"
                >
                  {yVal.toFixed(1)}m
                </text>
              </g>
            )
          })}

          {/* Vertical grid lines & X labels */}
          {xTicks.map((xVal, idx) => {
            const xPos = getX(xVal)
            return (
              <g key={idx}>
                <line
                  x1={xPos}
                  y1={padTop}
                  x2={xPos}
                  y2={padTop + plotHeight}
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeDasharray="3 3"
                />
                <text
                  x={xPos}
                  y={padTop + plotHeight + 16}
                  textAnchor="middle"
                  fontSize="10"
                  fill="#94a3b8"
                >
                  {xVal.toFixed(0)}m
                </text>
              </g>
            )
          })}

          {/* Sliced 3D points in 2D profile */}
          {points.map((pt, idx) => {
            const cx = getX(pt.distance)
            const cy = getY(pt.elevation)
            const clsInfo = CLASS_NAMES[pt.classification] || { name: 'Other', color: '#cbd5e1' }
            const ptColor = `rgb(${pt.r}, ${pt.g}, ${pt.b})`

            return (
              <circle
                key={idx}
                cx={cx}
                cy={cy}
                r="2.2"
                fill={ptColor}
                stroke={clsInfo.color}
                strokeWidth="0.6"
                style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                onMouseEnter={() => setHoveredPoint(pt)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
            )
          })}

          {/* Active Hover Point Highlight */}
          {hoveredPoint && (
            <g>
              <line
                x1={getX(hoveredPoint.distance)}
                y1={padTop}
                x2={getX(hoveredPoint.distance)}
                y2={padTop + plotHeight}
                stroke="#38bdf8"
                strokeWidth="1.2"
                strokeDasharray="2 2"
              />
              <circle
                cx={getX(hoveredPoint.distance)}
                cy={getY(hoveredPoint.elevation)}
                r="5"
                fill="#38bdf8"
                stroke="#ffffff"
                strokeWidth="1.5"
              />
            </g>
          )}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredPoint && (
          <div
            style={{
              position: 'absolute',
              top: 18,
              right: 28,
              background: 'rgba(15, 23, 42, 0.95)',
              border: '1px solid #38bdf8',
              borderRadius: 6,
              padding: '6px 12px',
              fontSize: 11,
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              display: 'flex',
              gap: 12,
              alignItems: 'center',
            }}
          >
            <div>
              <span style={{ color: '#94a3b8' }}>Distance: </span>
              <strong>{hoveredPoint.distance.toFixed(1)} m</strong>
            </div>
            <div>
              <span style={{ color: '#94a3b8' }}>Elevation: </span>
              <strong style={{ color: '#38bdf8' }}>{hoveredPoint.elevation.toFixed(2)} m</strong>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: CLASS_NAMES[hoveredPoint.classification]?.color || '#94a3b8',
                }}
              />
              <span>{CLASS_NAMES[hoveredPoint.classification]?.name || 'Point'}</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer Classification Palette Legend */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 12,
          padding: '6px 16px 10px 16px',
          background: 'rgba(15, 23, 42, 0.85)',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          fontSize: 10,
          color: '#94a3b8',
        }}
      >
        <span style={{ fontWeight: 600, color: '#e2e8f0' }}>Legend:</span>
        {[2, 3, 4, 5, 6, 9].map((c) => {
          const info = CLASS_NAMES[c]
          return (
            <div key={c} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: info.color,
                }}
              />
              <span>{info.name}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
