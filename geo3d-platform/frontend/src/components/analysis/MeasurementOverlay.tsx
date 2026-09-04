import { useViewerStore } from '../../stores'

export default function MeasurementOverlay() {
  const {
    activeTool,
    setActiveTool,
    measurementPoints,
    analysisResult,
    clearMeasurements,
  } = useViewerStore()

  if (activeTool === 'none') return null

  const getToolTitle = () => {
    switch (activeTool) {
      case 'distance':
        return { icon: '📏', title: 'Distance Measurement' }
      case 'area':
        return { icon: '📐', title: 'Area & Perimeter Measurement' }
      case 'height':
        return { icon: '📏', title: 'Vertical Height Difference' }
      case 'profile':
        return { icon: '⛰️', title: 'Elevation Profile Transect' }
      case 'slope':
        return { icon: '📐', title: 'Slope & Aspect Analysis' }
      case 'volume':
        return { icon: '🗻', title: 'Volume Estimation' }
      default:
        return { icon: '🔬', title: 'Spatial Tool' }
    }
  }

  const { icon, title } = getToolTitle()
  const ptCount = measurementPoints.length

  return (
    <div
      style={{
        position: 'absolute',
        top: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(580px, 92vw)',
        background: 'rgba(15, 23, 42, 0.92)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(56, 189, 248, 0.3)',
        borderRadius: 12,
        padding: '12px 18px',
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.55)',
        zIndex: 40,
        color: '#f8fafc',
        animation: 'fadeIn 0.2s ease-out',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 18 }}>{icon}</span>
          <span style={{ fontWeight: 600, fontSize: 14, color: '#38bdf8' }}>{title}</span>
          <span
            style={{
              fontSize: 11,
              padding: '2px 8px',
              borderRadius: 10,
              background: 'rgba(255, 255, 255, 0.08)',
              color: 'var(--color-text-secondary)',
            }}
          >
            {ptCount} point{ptCount === 1 ? '' : 's'} placed
          </span>
        </div>

        <div style={{ display: 'flex', gap: 6 }}>
          {ptCount > 0 && (
            <button
              onClick={clearMeasurements}
              className="btn btn--xs btn--secondary"
              style={{ fontSize: 11 }}
            >
              Clear
            </button>
          )}
          <button
            onClick={() => setActiveTool('none')}
            className="btn btn--xs btn--secondary"
            style={{ fontSize: 11 }}
          >
            Done ✕
          </button>
        </div>
      </div>

      {/* Instruction Banner */}
      <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>
        {ptCount === 0 && (
          <span>👆 Click anywhere on the 3D globe / point cloud to place the first point.</span>
        )}
        {ptCount === 1 && activeTool === 'height' && (
          <span>👆 Click the top point to measure vertical height difference.</span>
        )}
        {ptCount > 0 && activeTool !== 'height' && (
          <span>
            Click to add more vertices. Real-time metrics will update automatically below.
          </span>
        )}
      </div>

      {/* Real-time Results Cards */}
      {analysisResult && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: 8,
            padding: '10px 12px',
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: 8,
            border: '1px solid rgba(255, 255, 255, 0.06)',
            fontSize: 11,
          }}
        >
          {/* Distance Metrics */}
          {activeTool === 'distance' && (
            <>
              <div>
                <div style={{ color: '#94a3b8' }}>3D Distance</div>
                <div style={{ fontWeight: 700, fontSize: 14, color: '#38bdf8' }}>
                  {analysisResult.total_3d_distance_m >= 1000
                    ? `${(analysisResult.total_3d_distance_m / 1000).toFixed(2)} km`
                    : `${analysisResult.total_3d_distance_m.toFixed(1)} m`}
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Horizontal Dist</div>
                <div style={{ fontWeight: 600, color: '#f1f5f9' }}>
                  {analysisResult.total_horizontal_distance_m.toFixed(1)} m
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Elevation Diff (ΔZ)</div>
                <div style={{ fontWeight: 600, color: '#a78bfa' }}>
                  {analysisResult.elevation_diff_m.toFixed(1)} m
                </div>
              </div>
            </>
          )}

          {/* Area Metrics */}
          {activeTool === 'area' && (
            <>
              <div>
                <div style={{ color: '#94a3b8' }}>Surface Area</div>
                <div style={{ fontWeight: 700, fontSize: 14, color: '#4ade80' }}>
                  {analysisResult.area_sq_m.toLocaleString()} m²
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Hectares / Acres</div>
                <div style={{ fontWeight: 600, color: '#f1f5f9' }}>
                  {analysisResult.area_hectares} ha / {analysisResult.area_acres} ac
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Perimeter</div>
                <div style={{ fontWeight: 600, color: '#f1f5f9' }}>
                  {analysisResult.perimeter_m.toFixed(1)} m
                </div>
              </div>
            </>
          )}

          {/* Height Metrics */}
          {activeTool === 'height' && (
            <>
              <div>
                <div style={{ color: '#94a3b8' }}>Vertical Height</div>
                <div style={{ fontWeight: 700, fontSize: 14, color: '#f43f5e' }}>
                  {analysisResult.height_delta_z_m} m
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Horizontal Offset</div>
                <div style={{ fontWeight: 600, color: '#f1f5f9' }}>
                  {analysisResult.horizontal_offset_m} m
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Direct 3D Line</div>
                <div style={{ fontWeight: 600, color: '#38bdf8' }}>
                  {analysisResult.direct_distance_3d_m} m ({analysisResult.angle_degrees}°)
                </div>
              </div>
            </>
          )}

          {/* Slope Metrics */}
          {activeTool === 'slope' && (
            <>
              <div>
                <div style={{ color: '#94a3b8' }}>Average Slope</div>
                <div style={{ fontWeight: 700, fontSize: 14, color: '#fbbf24' }}>
                  {analysisResult.average_slope_degrees}° ({analysisResult.average_slope_percent}%)
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Max Slope</div>
                <div style={{ fontWeight: 600, color: '#f87171' }}>
                  {analysisResult.max_slope_degrees}°
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Aspect (Facing)</div>
                <div style={{ fontWeight: 600, color: '#38bdf8' }}>
                  {analysisResult.dominant_aspect?.cardinal} ({analysisResult.dominant_aspect?.compass_heading_deg}°)
                </div>
              </div>
            </>
          )}

          {/* Volume Metrics */}
          {activeTool === 'volume' && (
            <>
              <div>
                <div style={{ color: '#94a3b8' }}>Cut Volume</div>
                <div style={{ fontWeight: 700, fontSize: 14, color: '#f97316' }}>
                  {analysisResult.cut_volume_m3?.toLocaleString()} m³
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Fill Volume</div>
                <div style={{ fontWeight: 600, color: '#38bdf8' }}>
                  {analysisResult.fill_volume_m3?.toLocaleString()} m³
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>Net Volume</div>
                <div style={{ fontWeight: 700, color: '#4ade80' }}>
                  {analysisResult.net_volume_m3?.toLocaleString()} m³
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
