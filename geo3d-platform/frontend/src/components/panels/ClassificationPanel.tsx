import { useEffect, useState } from 'react'
import { useAppStore, useViewerStore } from '../../stores'
import { type Detected3DObject } from '../../api/client'

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
  const [activeTab, setActiveTab] = useState<'classes' | 'objects'>('classes')

  const {
    classificationResult,
    classificationLoading,
    triggerClassification,
    loadClassification,
    detectedObjects,
    detectingObjects,
    detectObjects,
    loadDetectedObjects,
    selectedObjectId,
    selectDetectedObject,
  } = useAppStore()

  const {
    showDetectedBoundingBoxes,
    toggleDetectedBoundingBoxes,
    detectedObjectFilter,
    setDetectedObjectFilter,
  } = useViewerStore()

  useEffect(() => {
    if (datasetId) {
      loadClassification(datasetId)
      loadDetectedObjects(datasetId)
    }
  }, [datasetId])

  const isReady = classificationResult?.classification_ready === true
  const classes: ClassEntry[] = isReady
    ? Object.values(classificationResult?.per_class || {})
    : []

  // Sort classes by count descending
  const sortedClasses = [...classes].sort((a, b) => b.count - a.count)

  const filteredObjects: Detected3DObject[] = (detectedObjects || []).filter((obj) => {
    if (detectedObjectFilter === 'all') return true
    return obj.category === detectedObjectFilter
  })

  // Category counts
  const catCounts = {
    building: (detectedObjects || []).filter(o => o.category === 'building').length,
    vehicle: (detectedObjects || []).filter(o => o.category === 'vehicle').length,
    pole: (detectedObjects || []).filter(o => o.category === 'pole').length,
    tree: (detectedObjects || []).filter(o => o.category === 'tree').length,
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* Tab Switcher */}
      <div style={{
        display: 'flex',
        background: 'rgba(15, 23, 42, 0.6)',
        borderRadius: 6,
        padding: 2,
        border: '1px solid rgba(255,255,255,0.06)'
      }}>
        <button
          className="btn btn--sm"
          style={{
            flex: 1,
            fontSize: 10,
            padding: '4px 6px',
            background: activeTab === 'classes' ? 'rgba(59, 130, 246, 0.25)' : 'transparent',
            color: activeTab === 'classes' ? '#93c5fd' : '#94a3b8',
            borderColor: activeTab === 'classes' ? 'rgba(59, 130, 246, 0.4)' : 'transparent',
            borderRadius: 4
          }}
          onClick={() => setActiveTab('classes')}
        >
          Classes ({sortedClasses.length || 15})
        </button>
        <button
          id="tab-detected-objects"
          className="btn btn--sm"
          style={{
            flex: 1,
            fontSize: 10,
            padding: '4px 6px',
            background: activeTab === 'objects' ? 'rgba(139, 92, 246, 0.25)' : 'transparent',
            color: activeTab === 'objects' ? '#c4b5fd' : '#94a3b8',
            borderColor: activeTab === 'objects' ? 'rgba(139, 92, 246, 0.4)' : 'transparent',
            borderRadius: 4,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4
          }}
          onClick={() => setActiveTab('objects')}
        >
          <span>🎯 3D Objects</span>
          {detectedObjects && detectedObjects.length > 0 && (
            <span style={{
              background: '#8b5cf6',
              color: '#fff',
              fontSize: 9,
              padding: '1px 5px',
              borderRadius: 10,
              fontWeight: 700
            }}>
              {detectedObjects.length}
            </span>
          )}
        </button>
      </div>

      {/* ── TAB 1: Semantic Classes ────────────────────────────────────── */}
      {activeTab === 'classes' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {classificationLoading ? (
            <div style={{ padding: 12, fontSize: 11, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="scene-loading__spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
              Running DALES-2 PointNet / ML classifier…
            </div>
          ) : !isReady ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ fontSize: 10, color: '#64748b', lineHeight: 1.4 }}>
                Classify points into 15 DALES-2 semantic classes: ground, buildings, vegetation, poles, wires, vehicles…
              </div>
              <button
                id="btn-run-classification"
                className="btn btn--secondary btn--sm w-full"
                style={{
                  fontSize: 11,
                  background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(59,130,246,0.2))',
                  borderColor: 'rgba(139,92,246,0.4)'
                }}
                onClick={() => triggerClassification(datasetId)}
              >
                🤖 Run AI Classification
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {/* Header stats */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: '#94a3b8' }}>
                  {(classificationResult?.total_points || 0).toLocaleString()} pts · {sortedClasses.length} classes
                </span>
                <span className="badge badge--success" style={{ fontSize: 9 }}>
                  {classificationResult?.dominant_class || 'Ground'}
                </span>
              </div>

              {/* Class bars */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3, maxHeight: 230, overflowY: 'auto', paddingRight: 2 }}>
                {sortedClasses.map((cls) => {
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

              {/* Actions */}
              <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                <button
                  className="btn btn--secondary btn--sm"
                  style={{ flex: 1, fontSize: 10 }}
                  onClick={() => triggerClassification(datasetId)}
                >
                  ↻ Re-classify
                </button>
                <button
                  className="btn btn--primary btn--sm"
                  style={{
                    flex: 1,
                    fontSize: 10,
                    background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)',
                    borderColor: '#8b5cf6'
                  }}
                  onClick={() => {
                    setActiveTab('objects')
                    if (!detectedObjects || detectedObjects.length === 0) {
                      detectObjects(datasetId)
                    }
                  }}
                >
                  🎯 Detect 3D Objects →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: 3D Objects & Detection ─────────────────────────────── */}
      {activeTab === 'objects' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Action Header / Detect button */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
            <button
              id="btn-detect-3d-objects"
              className="btn btn--primary btn--sm"
              style={{
                flex: 1,
                fontSize: 10,
                background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
                borderColor: '#8b5cf6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6
              }}
              disabled={detectingObjects}
              onClick={() => detectObjects(datasetId)}
            >
              {detectingObjects ? (
                <>
                  <div className="scene-loading__spinner" style={{ width: 10, height: 10, borderWidth: 2 }} />
                  Extracting 3D Objects…
                </>
              ) : (
                <>🎯 {detectedObjects ? 'Re-run 3D Detection' : 'Run 3D Object Detection'}</>
              )}
            </button>

            {detectedObjects && detectedObjects.length > 0 && (
              <button
                className="btn btn--secondary btn--sm"
                style={{
                  fontSize: 10,
                  padding: '4px 8px',
                  background: showDetectedBoundingBoxes ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.06)',
                  color: showDetectedBoundingBoxes ? '#6ee7b7' : '#94a3b8',
                  borderColor: showDetectedBoundingBoxes ? 'rgba(16, 185, 129, 0.4)' : 'rgba(255,255,255,0.1)'
                }}
                title="Toggle 3D Bounding Boxes in Viewer"
                onClick={toggleDetectedBoundingBoxes}
              >
                {showDetectedBoundingBoxes ? '📦 Boxes ON' : '📦 Boxes OFF'}
              </button>
            )}
          </div>

          {/* Category Summary Pills */}
          {detectedObjects && detectedObjects.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 4 }}>
              <div style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: 4,
                padding: '4px 2px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: 9, color: '#f87171' }}>🏢 Bldgs</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#ef4444' }}>{catCounts.building}</div>
              </div>
              <div style={{
                background: 'rgba(249, 115, 22, 0.1)',
                border: '1px solid rgba(249, 115, 22, 0.25)',
                borderRadius: 4,
                padding: '4px 2px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: 9, color: '#fb923c' }}>🚗 Cars</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#f97316' }}>{catCounts.vehicle}</div>
              </div>
              <div style={{
                background: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid rgba(6, 182, 212, 0.25)',
                borderRadius: 4,
                padding: '4px 2px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: 9, color: '#22d3ee' }}>⚡ Poles</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#06b6d4' }}>{catCounts.pole}</div>
              </div>
              <div style={{
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: 4,
                padding: '4px 2px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: 9, color: '#34d399' }}>🌲 Trees</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#10b981' }}>{catCounts.tree}</div>
              </div>
            </div>
          )}

          {/* Category Filter Chips */}
          {detectedObjects && detectedObjects.length > 0 && (
            <div style={{ display: 'flex', gap: 4, overflowX: 'auto', paddingBottom: 2 }}>
              {['all', 'building', 'vehicle', 'pole', 'tree'].map((cat) => (
                <button
                  key={cat}
                  className="btn btn--sm"
                  style={{
                    fontSize: 9,
                    padding: '2px 6px',
                    borderRadius: 12,
                    background: detectedObjectFilter === cat ? 'rgba(139, 92, 246, 0.3)' : 'rgba(255,255,255,0.04)',
                    color: detectedObjectFilter === cat ? '#ddd6fe' : '#64748b',
                    borderColor: detectedObjectFilter === cat ? '#8b5cf6' : 'transparent',
                    textTransform: 'capitalize'
                  }}
                  onClick={() => setDetectedObjectFilter(cat)}
                >
                  {cat === 'all' ? 'All' : cat}
                </button>
              ))}
            </div>
          )}

          {/* Object List */}
          {detectedObjects && detectedObjects.length > 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
              maxHeight: 280,
              overflowY: 'auto',
              paddingRight: 2
            }}>
              {filteredObjects.map((obj) => {
                const isSelected = selectedObjectId === obj.id
                return (
                  <div
                    key={obj.id}
                    style={{
                      background: isSelected ? 'rgba(139, 92, 246, 0.2)' : 'rgba(255,255,255,0.03)',
                      border: `1px solid ${isSelected ? '#8b5cf6' : 'rgba(255,255,255,0.07)'}`,
                      borderRadius: 6,
                      padding: 6,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                    onClick={() => selectDetectedObject(isSelected ? null : obj.id)}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{
                          width: 8,
                          height: 8,
                          borderRadius: 2,
                          background: obj.color,
                          boxShadow: `0 0 6px ${obj.color}`
                        }} />
                        <span style={{ fontSize: 10, fontWeight: 600, color: '#f1f5f9' }}>
                          {obj.subtype}
                        </span>
                      </div>
                      <span style={{
                        fontSize: 9,
                        color: '#94a3b8',
                        background: 'rgba(255,255,255,0.06)',
                        padding: '1px 5px',
                        borderRadius: 3
                      }}>
                        {obj.dimensions.height_m}m H
                      </span>
                    </div>

                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(3, 1fr)',
                      gap: 4,
                      fontSize: 9,
                      color: '#94a3b8'
                    }}>
                      <div>
                        <span style={{ color: '#64748b' }}>Size: </span>
                        {obj.dimensions.length_m}×{obj.dimensions.width_m}m
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Vol: </span>
                        {obj.dimensions.volume_m3 > 1000 ? `${(obj.dimensions.volume_m3 / 1000).toFixed(1)}k` : obj.dimensions.volume_m3}m³
                      </div>
                      <div>
                        <span style={{ color: '#64748b' }}>Conf: </span>
                        {Math.round(obj.confidence * 100)}%
                      </div>
                    </div>

                    {isSelected && (
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 4, marginTop: 2 }}>
                        <button
                          className="btn btn--sm"
                          style={{
                            fontSize: 9,
                            padding: '2px 8px',
                            background: '#8b5cf6',
                            color: '#fff',
                            borderColor: '#8b5cf6'
                          }}
                          onClick={(e) => {
                            e.stopPropagation()
                            selectDetectedObject(obj.id)
                          }}
                        >
                          🔍 Fly to Object
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : !detectingObjects ? (
            <div style={{
              padding: 12,
              textAlign: 'center',
              fontSize: 10,
              color: '#64748b',
              background: 'rgba(255,255,255,0.02)',
              borderRadius: 6,
              border: '1px dashed rgba(255,255,255,0.08)'
            }}>
              Click "Run 3D Object Detection" to cluster and extract 3D bounding boxes for buildings, vehicles, poles, and trees.
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
