import { useEffect } from 'react'
import { useAppStore } from '../../stores'

const DALES_COLORS: Record<string, string> = {
  "0": "#8B5A2B",
  "1": "#228B22",
  "2": "#FF4500",
  "3": "#FFD700",
  "4": "#D2691E",
  "5": "#006400",
  "6": "#FF6347",
  "7": "#FF1493",
  "8": "#8A2BE2",
  "9": "#00CED1",
  "10": "#1E90FF",
  "11": "#4169E1",
  "12": "#DC143C",
  "13": "#F0E68C",
  "14": "#A0A0A0",
}

interface ClassEntry {
  class_id: number
  name: string
  color: string
  count: number
  percentage: number
}

export default function ClassificationPanel({ datasetId }: { datasetId: string }) {
  const {
    classificationResult,
    classificationLoading,
    triggerClassification,
    loadClassification,
  } = useAppStore()

  useEffect(() => {
    if (datasetId) {
      loadClassification(datasetId)
    }
  }, [datasetId])

  const isReady = classificationResult?.classification_ready === true
  const classes: ClassEntry[] = isReady
    ? Object.values(classificationResult?.per_class || {})
    : []

  // Sort by count descending
  const sorted = [...classes].sort((a, b) => b.count - a.count)

  if (classificationLoading) {
    return (
      <div style={{ padding: 8, fontSize: 11, color: '#94a3b8' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div className="scene-loading__spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
          Running DALES-2 classifier…
        </div>
      </div>
    )
  }

  if (!isReady) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontSize: 10, color: '#64748b', lineHeight: 1.4 }}>
          Classify this point cloud into 15 DALES-2 semantic classes: ground, buildings, vegetation, poles, wires, vehicles…
        </div>
        <button
          id="btn-run-classification"
          className="btn btn--secondary btn--sm w-full"
          style={{ fontSize: 11, background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(59,130,246,0.2))', borderColor: 'rgba(139,92,246,0.4)' }}
          onClick={() => triggerClassification(datasetId)}
        >
          🤖 Run AI Classification
        </button>
      </div>
    )
  }

  const total = classificationResult?.total_points || 1
  const dominant = classificationResult?.dominant_class || ''

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 10, color: '#94a3b8' }}>
          {total.toLocaleString()} pts · {sorted.length} classes
        </span>
        <span className="badge badge--success" style={{ fontSize: 9 }}>{dominant}</span>
      </div>

      {/* Class bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {sorted.map((cls) => {
          const color = DALES_COLORS[String(cls.class_id)] || cls.color || '#888'
          return (
            <div key={cls.class_id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: color, flexShrink: 0 }} />
                  <span style={{ fontSize: 10, color: '#cbd5e1' }}>{cls.name}</span>
                </div>
                <span style={{ fontSize: 10, color: '#64748b', fontVariantNumeric: 'tabular-nums' }}>
                  {cls.percentage.toFixed(1)}%
                </span>
              </div>
              <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${cls.percentage}%`,
                  background: color,
                  borderRadius: 2,
                  transition: 'width 0.6s ease',
                  opacity: 0.85,
                }} />
              </div>
            </div>
          )
        })}
      </div>

      {/* Re-classify button */}
      <button
        className="btn btn--secondary btn--sm"
        style={{ fontSize: 10, marginTop: 2 }}
        onClick={() => triggerClassification(datasetId)}
      >
        ↻ Re-classify
      </button>
    </div>
  )
}
