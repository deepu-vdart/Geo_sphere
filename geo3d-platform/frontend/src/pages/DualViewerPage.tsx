import React from 'react'
import CesiumViewer from '../components/cesium/CesiumViewer'
import PotreeViewer from '../components/potree/PotreeViewer'
import { useDatasetUrlSync } from '../hooks/useDatasetUrlSync'

export default function DualViewerPage() {
  const { activeDataset } = useDatasetUrlSync()

  return (
    <div
      style={{
        height: 'calc(100vh - 48px)',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: '#090d16',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* ── Top Dual Compare Header Bar ───────────────────────────────────────── */}
      <div
        style={{
          height: 38,
          background: 'rgba(15, 23, 42, 0.95)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          zIndex: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 13 }}>◫</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#f1f5f9' }}>
            Dual Synchronized Comparison
          </span>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>
            {activeDataset?.name || 'Dataset'}
          </span>
        </div>

        <div style={{ display: 'flex', gap: 20, fontSize: 11, fontWeight: 600 }}>
          <span style={{ color: '#38bdf8' }}>◀ Left: Cesium 3D Globe</span>
          <span style={{ color: '#c084fc' }}>Right: Potree 1.8+ Point Cloud ▶</span>
        </div>
      </div>

      {/* ── Main Dual 50 / 50 Panes ───────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', position: 'relative', overflow: 'hidden' }}>
        {/* Left: Cesium 3D Globe */}
        <div
          style={{
            flex: 1,
            height: '100%',
            position: 'relative',
            borderRight: '2px solid rgba(56, 189, 248, 0.3)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 10,
              zIndex: 10,
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              borderRadius: 6,
              padding: '3px 8px',
              fontSize: 10,
              color: '#38bdf8',
              fontWeight: 700,
              pointerEvents: 'none',
            }}
          >
            CESIUM 3D GLOBE
          </div>
          <CesiumViewer />
        </div>

        {/* Right: Potree Point Cloud */}
        <div
          style={{
            flex: 1,
            height: '100%',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 10,
              zIndex: 10,
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              borderRadius: 6,
              padding: '3px 8px',
              fontSize: 10,
              color: '#c084fc',
              fontWeight: 700,
              pointerEvents: 'none',
            }}
          >
            POTREE 1.8+ / COPC INSPECTOR
          </div>
          <PotreeViewer />
        </div>
      </div>
    </div>
  )
}
