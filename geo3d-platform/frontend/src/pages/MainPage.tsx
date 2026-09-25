import { lazy, Suspense } from 'react'
import TopBar from '../components/layout/TopBar'
import LeftSidebar from '../components/layout/LeftSidebar'
import RightPanel from '../components/layout/RightPanel'
import BottomBar from '../components/layout/BottomBar'

import AIAssistantChat from '../components/panels/AIAssistantChat'
import PhotogrammetrySplitView from '../components/panels/PhotogrammetrySplitView'
import { useViewerStore } from '../stores'

// Lazy-load 3D Viewers to avoid blocking initial bundle render
const CesiumViewer = lazy(() => import('../components/cesium/CesiumViewer'))
const PotreeViewer = lazy(() => import('../components/potree/PotreeViewer'))

export default function MainPage() {
  const viewerMode = useViewerStore((s) => s.viewerMode)

  return (
    <div className="app-shell">
      <TopBar />
      <LeftSidebar />

      {/* ── 3D Viewer Container (Cesium / Potree / Dual Split) ─────────────── */}
      <Suspense
        fallback={
          <div className="viewer-container">
            <div className="scene-loading">
              <div className="scene-loading__spinner" />
              <div className="scene-loading__text">Loading 3D Engine…</div>
            </div>
          </div>
        }
      >
        {viewerMode === 'cesium' && (
          <PhotogrammetrySplitView>
            <CesiumViewer />
          </PhotogrammetrySplitView>
        )}

        {viewerMode === 'potree' && (
          <div className="viewer-container" style={{ position: 'relative', width: '100%', height: '100%' }}>
            <PotreeViewer />
          </div>
        )}

        {viewerMode === 'dual' && (
          <div
            className="viewer-container"
            style={{
              display: 'flex',
              width: '100%',
              height: '100%',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* Left Pane: Cesium 3D Globe with Orthophoto & Terrain */}
            <div
              style={{
                flex: 1,
                height: '100%',
                position: 'relative',
                borderRight: '2px solid rgba(56, 189, 248, 0.4)',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  top: 10,
                  left: 10,
                  zIndex: 20,
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

            {/* Right Pane: Potree 1.8+ Ultra-Dense Point Cloud with EDL */}
            <div style={{ flex: 1, height: '100%', position: 'relative' }}>
              <div
                style={{
                  position: 'absolute',
                  top: 10,
                  left: 10,
                  zIndex: 20,
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
                POTREE COPC INSPECTOR
              </div>
              <PotreeViewer />
            </div>
          </div>
        )}
      </Suspense>

      {/* ── AI Geospatial Assistant Drawer ────────────────────────────── */}
      <AIAssistantChat />

      <RightPanel />
      <BottomBar />
    </div>
  )
}
