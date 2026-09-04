import { useState } from 'react'
import { useAppStore, useViewerStore, type PointCloudColorMode } from '../../stores'
import { api } from '../../api/client'

const CLASSIFICATION_BADGES: Record<number, { name: string; color: string }> = {
  0: { name: 'Ground / Unclassified', color: '#8b5a2b' },
  1: { name: 'Vegetation', color: '#90ee90' },
  2: { name: 'Ground / Car', color: '#ff4500' },
  3: { name: 'Powerline / Low Veg', color: '#ffd700' },
  4: { name: 'Fence / Med Veg', color: '#d2691e' },
  5: { name: 'Tree / High Veg', color: '#228b22' },
  6: { name: 'Building / Pick-up', color: '#dc143c' },
  7: { name: 'Van & Truck / Noise', color: '#ff1493' },
  8: { name: 'Heavy-duty Vehicle', color: '#8a2be2' },
  9: { name: 'Utility Pole / Water', color: '#00ced1' },
  10: { name: 'Light Pole', color: '#1e90ff' },
  11: { name: 'Traffic Pole / Roads', color: '#4169e1' },
  12: { name: 'Building', color: '#dc143c' },
  13: { name: 'Wire / Cable', color: '#f0e68c' },
  14: { name: 'Other', color: '#a0a0a0' },
}

export default function RightPanel() {
  const { activeDataset, triggerProcessing } = useAppStore()
  const {
    selectedObjectInfo,
    pickedPoint,
    setPickedPoint,
    pointCloudColorMode,
    setPointCloudColorMode,
    pointSize,
    setPointSize,
    showContours,
    setShowContours,
    setContoursGeoJson,
  } = useViewerStore()

  const [terrainData, setTerrainData] = useState<any>(null)
  const [loadingTerrain, setLoadingTerrain] = useState(false)

  const handleGenerateTerrain = async () => {
    if (!activeDataset) return
    setLoadingTerrain(true)
    try {
      const res = await api.getTerrainDerivatives(activeDataset.id)
      setTerrainData(res.data)
      if (res.data.contours) {
        setContoursGeoJson(res.data.contours)
      }
    } catch (e) {
      console.error('Failed to generate terrain derivatives:', e)
    } finally {
      setLoadingTerrain(false)
    }
  }

  const formatBytes = (bytes: number | null) => {
    if (!bytes) return '—'
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  const meta = (activeDataset?.metadata_json as Record<string, any>) || null
  const classBreakdown = meta?.classification_breakdown as Record<string, any> | null

  return (
    <aside className="right-panel">
      <div className="right-panel__header">Inspector & Analysis</div>
      <div className="right-panel__scroll">
        {/* Picked Point Information */}
        {pickedPoint && (
          <div style={{ background: '#182032', padding: 12, borderRadius: 6, margin: '8px 10px', border: '1px solid #2d3748' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontWeight: 600, color: '#38bdf8', fontSize: 12 }}>🎯 Picked Point</span>
              <button
                onClick={() => setPickedPoint(null)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 11 }}
              >
                ✕
              </button>
            </div>
            <div className="info-row">
              <span className="info-row__label">Elevation (Z)</span>
              <span className="info-row__value" style={{ color: '#4ade80', fontWeight: 600 }}>{pickedPoint.alt.toFixed(2)} m</span>
            </div>
            <div className="info-row">
              <span className="info-row__label">Classification</span>
              <span className="info-row__value" style={{ fontWeight: 600 }}>{pickedPoint.className || `Class ${pickedPoint.classification}`}</span>
            </div>
            <div className="info-row">
              <span className="info-row__label">Intensity</span>
              <span className="info-row__value">{pickedPoint.intensity ?? '—'}</span>
            </div>
            <div className="info-row">
              <span className="info-row__label">Longitude</span>
              <span className="info-row__value" style={{ fontSize: 10 }}>{pickedPoint.lon.toFixed(7)}°</span>
            </div>
            <div className="info-row">
              <span className="info-row__label">Latitude</span>
              <span className="info-row__value" style={{ fontSize: 10 }}>{pickedPoint.lat.toFixed(7)}°</span>
            </div>
          </div>
        )}

        {/* Terrain Derivatives Suite */}
        {activeDataset && (
          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--color-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-secondary)' }}>
                🏔️ Terrain Derivatives
              </span>
              <button
                onClick={handleGenerateTerrain}
                disabled={loadingTerrain}
                className="btn btn--secondary btn--sm"
                style={{ fontSize: 10, padding: '2px 8px' }}
              >
                {loadingTerrain ? 'Computing…' : 'Compute DTM/DSM'}
              </button>
            </div>

            {terrainData && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11 }}>
                <div className="info-row">
                  <span className="info-row__label">Mean Slope</span>
                  <span className="info-row__value">{terrainData.slope_aspect_stats?.mean_slope_deg}° (Max {terrainData.slope_aspect_stats?.max_slope_deg}°)</span>
                </div>
                <div className="info-row">
                  <span className="info-row__label">Dominant Aspect</span>
                  <span className="info-row__value">{terrainData.slope_aspect_stats?.dominant_aspect_deg}°</span>
                </div>
                <div className="info-row">
                  <span className="info-row__label">Roughness (TRI)</span>
                  <span className="info-row__value">{terrainData.roughness_stats?.mean} m</span>
                </div>
                <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={showContours}
                      onChange={(e) => setShowContours(e.target.checked)}
                    />
                    <span>Show 2m Vector Contours</span>
                  </label>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Selected Object Info */}
        {selectedObjectInfo ? (
          <>
            <div
              className="right-panel__header"
              style={{
                background: 'var(--color-accent-dim)',
                color: 'var(--color-accent)',
              }}
            >
              Selected Object
            </div>
            {Object.entries(selectedObjectInfo).map(([k, v]) => (
              <div key={k} className="info-row">
                <span className="info-row__label">{k}</span>
                <span className="info-row__value">{String(v)}</span>
              </div>
            ))}
          </>
        ) : !pickedPoint ? (
          <div className="placeholder-message">
            Click any point in the 3D scene to inspect XYZ & classification.
          </div>
        ) : null}

        {/* Active Dataset Info */}
        {activeDataset && (
          <>
            <div className="right-panel__header" style={{ marginTop: 4 }}>
              Dataset Info
            </div>

            <div className="info-row">
              <span className="info-row__label">Name</span>
              <span className="info-row__value" style={{ fontWeight: 600 }}>
                {activeDataset.name}
              </span>
            </div>
            <div className="info-row">
              <span className="info-row__label">Type</span>
              <span className="info-row__value">
                <span
                  className="badge badge--info"
                  style={{ textTransform: 'capitalize' }}
                >
                  {activeDataset.dataset_type.replace('_', ' ')}
                </span>
              </span>
            </div>
            <div className="info-row">
              <span className="info-row__label">Format</span>
              <span className="info-row__value">{activeDataset.file_format?.toUpperCase() || '—'}</span>
            </div>
            <div className="info-row">
              <span className="info-row__label">File Size</span>
              <span className="info-row__value">{formatBytes(activeDataset.file_size_bytes)}</span>
            </div>
            <div className="info-row">
              <span className="info-row__label">CRS</span>
              <span className="info-row__value" style={{ color: 'var(--color-accent)', fontSize: 11 }}>
                {activeDataset.crs || 'EPSG:26913'}
              </span>
            </div>
            <div className="info-row">
              <span className="info-row__label">Status</span>
              <span className="info-row__value">
                <span
                  className={`badge badge--${
                    activeDataset.processing_status === 'ready' ||
                    activeDataset.processing_status === 'validated'
                      ? 'success'
                      : activeDataset.processing_status === 'validation_failed'
                      ? 'error'
                      : 'warning'
                  }`}
                >
                  {activeDataset.processing_status}
                </span>
              </span>
            </div>

            {/* Point Cloud Visual Controls */}
            {activeDataset.dataset_type === 'point_cloud' && (
              <div
                style={{
                  padding: '12px 14px',
                  background: 'rgba(255,255,255,0.03)',
                  borderTop: '1px solid var(--color-border)',
                  borderBottom: '1px solid var(--color-border)',
                  margin: '8px 0',
                }}
              >
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: 'var(--color-accent)',
                    marginBottom: 10,
                  }}
                >
                  🎨 3D Point Styling
                </div>

                {/* Color Mode */}
                <div style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 4 }}>
                    Color Mode
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {(['classification', 'elevation', 'intensity'] as PointCloudColorMode[]).map(
                      (mode) => (
                        <button
                          key={mode}
                          onClick={() => setPointCloudColorMode(mode)}
                          className={`btn btn--xs ${
                            pointCloudColorMode === mode ? 'btn--primary' : 'btn--secondary'
                          }`}
                          style={{ flex: 1, textTransform: 'capitalize', fontSize: 10 }}
                        >
                          {mode}
                        </button>
                      )
                    )}
                  </div>
                </div>

                {/* Point Size Slider */}
                <div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      fontSize: 11,
                      color: 'var(--color-text-muted)',
                      marginBottom: 4,
                    }}
                  >
                    <span>Point Size</span>
                    <span>{pointSize} px</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    value={pointSize}
                    onChange={(e) => setPointSize(Number(e.target.value))}
                    style={{ width: '100%', cursor: 'pointer' }}
                  />
                </div>

                {/* Trigger 3D Processing Button */}
                <div style={{ marginTop: 12 }}>
                  <button
                    onClick={() => triggerProcessing(activeDataset.id)}
                    className="btn btn--secondary"
                    style={{ width: '100%', fontSize: 11 }}
                  >
                    ⚡ Process 3D Tiles
                  </button>
                </div>
              </div>
            )}

            {/* Point Count & Density */}
            {activeDataset.point_count && (
              <>
                <div className="info-row">
                  <span className="info-row__label">Total Points</span>
                  <span className="info-row__value" style={{ fontWeight: 600 }}>
                    {activeDataset.point_count.toLocaleString()}
                  </span>
                </div>
                {activeDataset.point_density && (
                  <div className="info-row">
                    <span className="info-row__label">Point Density</span>
                    <span className="info-row__value">{activeDataset.point_density} pts/m²</span>
                  </div>
                )}
              </>
            )}

            {/* Elevation Range */}
            {activeDataset.min_z != null && (
              <>
                <div className="info-row">
                  <span className="info-row__label">Min Elevation</span>
                  <span className="info-row__value">{activeDataset.min_z.toFixed(2)} m</span>
                </div>
                <div className="info-row">
                  <span className="info-row__label">Max Elevation</span>
                  <span className="info-row__value">{activeDataset.max_z?.toFixed(2)} m</span>
                </div>
                <div className="info-row">
                  <span className="info-row__label">Elevation Span</span>
                  <span className="info-row__value">
                    {((activeDataset.max_z || 0) - activeDataset.min_z).toFixed(2)} m
                  </span>
                </div>
              </>
            )}

            {/* Classification Breakdown */}
            {classBreakdown && Object.keys(classBreakdown).length > 0 && (
              <div style={{ padding: '10px 14px', borderTop: '1px solid var(--color-border)' }}>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--color-text-secondary)',
                    marginBottom: 8,
                  }}
                >
                  ASPRS Classification
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {Object.entries(classBreakdown).map(([codeStr, item]: [string, any]) => {
                    const code = parseInt(codeStr, 10)
                    const badgeInfo = CLASSIFICATION_BADGES[code] || {
                      name: item.name,
                      color: '#888',
                    }
                    return (
                      <div
                        key={code}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: 11,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span
                            style={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              backgroundColor: badgeInfo.color,
                              display: 'inline-block',
                            }}
                          />
                          <span>{badgeInfo.name}</span>
                        </div>
                        <span style={{ color: 'var(--color-text-muted)' }}>
                          {item.count.toLocaleString()} ({item.percentage}%)
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* DALES-2 AI Classification Breakdown */}
            {meta?.dales2_classification?.per_class && (
              <div style={{ padding: '10px 14px', borderTop: '1px solid var(--color-border)' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    🏷️ DALES-2 Semantic Classes
                  </span>
                  <span className="badge badge--success" style={{ fontSize: 9 }}>
                    {meta.dales2_classification.dominant_class}
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {Object.values(meta.dales2_classification.per_class).map((item: any) => (
                    <div
                      key={item.class_id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: 11,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            backgroundColor: item.color || '#888',
                            display: 'inline-block',
                          }}
                        />
                        <span>{item.name}</span>
                      </div>
                      <span style={{ color: 'var(--color-text-muted)' }}>
                        {item.count.toLocaleString()} ({item.percentage}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}


            {/* Raster dimensions */}
            {activeDataset.raster_width && (
              <>
                <div className="info-row">
                  <span className="info-row__label">Dimensions</span>
                  <span className="info-row__value">
                    {activeDataset.raster_width} × {activeDataset.raster_height} px
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-row__label">Bands</span>
                  <span className="info-row__value">
                    {String(activeDataset.metadata_json?.band_count ?? 1)}
                  </span>
                </div>
              </>
            )}

            <div className="info-row">
              <span className="info-row__label">Filename</span>
              <span className="info-row__value" style={{ fontSize: 10 }}>
                {activeDataset.original_filename || '—'}
              </span>
            </div>
            <div className="info-row">
              <span className="info-row__label">Uploaded</span>
              <span className="info-row__value" style={{ fontSize: 10 }}>
                {new Date(activeDataset.created_at).toLocaleString()}
              </span>
            </div>
          </>
        )}

        {/* Phase Status Badges */}
        <div
          style={{
            padding: 'var(--space-4)',
            borderTop: '1px solid var(--color-border)',
            marginTop: 'auto',
          }}
        >
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
            <div
              style={{
                marginBottom: 8,
                fontWeight: 600,
                color: 'var(--color-text-secondary)',
              }}
            >
              🔬 Processing Engine
            </div>
            <div>
              GDAL Raster (GeoTIFF/DEM):{' '}
              <span style={{ color: 'var(--color-success)' }}>✅ Active</span>
            </div>
            <div>
              PDAL/LAS LiDAR Processor:{' '}
              <span style={{ color: 'var(--color-success)' }}>✅ Active</span>
            </div>
            <div>
              OGC 3D Tiles Point Clouds:{' '}
              <span style={{ color: 'var(--color-success)' }}>✅ Active</span>
            </div>
            <div>
              Classification Color Styling:{' '}
              <span style={{ color: 'var(--color-success)' }}>✅ Active</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
