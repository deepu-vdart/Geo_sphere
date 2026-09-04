import { lazy, Suspense } from 'react'
import TopBar from '../components/layout/TopBar'
import LeftSidebar from '../components/layout/LeftSidebar'
import RightPanel from '../components/layout/RightPanel'
import BottomBar from '../components/layout/BottomBar'

import AIAssistantChat from '../components/panels/AIAssistantChat'

// Lazy-load CesiumJS to avoid blocking initial render
const CesiumViewer = lazy(() => import('../components/cesium/CesiumViewer'))

export default function MainPage() {
  return (
    <div className="app-shell">
      <TopBar />
      <LeftSidebar />

      {/* ── 3D Viewer ──────────────────────────────────────────────────── */}
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
        <CesiumViewer />
      </Suspense>

      {/* ── AI Geospatial Assistant Drawer ────────────────────────────── */}
      <AIAssistantChat />

      <RightPanel />
      <BottomBar />
    </div>
  )
}
