import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useViewerStore } from '../stores'
import CesiumViewer from '../components/cesium/CesiumViewer'
import LeftSidebar from '../components/layout/LeftSidebar'
import RightPanel from '../components/layout/RightPanel'
import BottomBar from '../components/layout/BottomBar'
import { useDatasetUrlSync } from '../hooks/useDatasetUrlSync'

export default function CesiumViewerPage() {
  const { activeDataset } = useDatasetUrlSync()
  const {
    pointCloudColorMode,
    setPointCloudColorMode,
    pointSize,
    setPointSize,
    cameraPosition,
  } = useViewerStore()

  const [showLeftDrawer, setShowLeftDrawer] = useState(false)
  const [showRightDrawer, setShowRightDrawer] = useState(false)

  return (
    <div
      style={{
        height: 'calc(100vh - 48px)',
        width: '100%',
        position: 'relative',
        overflow: 'hidden',
        background: '#070a12',
      }}
    >
      {/* ── Fullscreen Cesium 3D Engine Viewport ──────────────────────────────── */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
        <CesiumViewer />
      </div>

      {/* ── Top Floating Quick Action Bar ────────────────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 12,
          left: 16,
          right: 16,
          zIndex: 10,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pointerEvents: 'none',
        }}
      >
        {/* Left Floating Tool Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, pointerEvents: 'auto' }}>
          <button
            onClick={() => setShowLeftDrawer(!showLeftDrawer)}
            style={{
              background: showLeftDrawer ? 'rgba(56, 189, 248, 0.25)' : 'rgba(15, 23, 42, 0.85)',
              border: `1px solid ${showLeftDrawer ? 'rgba(56, 189, 248, 0.5)' : 'rgba(255, 255, 255, 0.15)'}`,
              color: showLeftDrawer ? '#38bdf8' : '#f1f5f9',
              borderRadius: 8,
              padding: '6px 12px',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              backdropFilter: 'blur(8px)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            }}
          >
            <span>☰</span>
            <span>{showLeftDrawer ? 'Close Layers' : 'Layers & Classification'}</span>
          </button>

          {/* Color Mode Picker */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: 8,
              padding: '2px 4px',
              display: 'flex',
              gap: 2,
              backdropFilter: 'blur(8px)',
            }}
          >
            {(['rgb', 'elevation', 'intensity', 'classification'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setPointCloudColorMode(mode)}
                style={{
                  background: pointCloudColorMode === mode ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
                  color: pointCloudColorMode === mode ? '#38bdf8' : '#94a3b8',
                  border: 'none',
                  borderRadius: 6,
                  padding: '4px 8px',
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  textTransform: 'uppercase',
                }}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* Point Size Adjuster */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: 8,
              padding: '4px 10px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 10,
              color: '#94a3b8',
              backdropFilter: 'blur(8px)',
            }}
          >
            <span>Size:</span>
            <input
              type="range"
              min="1"
              max="12"
              value={pointSize}
              onChange={(e) => setPointSize(Number(e.target.value))}
              style={{ width: 60, cursor: 'pointer' }}
            />
            <span style={{ color: '#38bdf8', fontWeight: 600 }}>{pointSize}px</span>
          </div>
        </div>

        {/* Right Floating Tool Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, pointerEvents: 'auto' }}>
          {activeDataset?.dataset_type === 'photogrammetry' && (
            <Link
              to={`/photogrammetry?dataset=${activeDataset.id}`}
              style={{
                background: 'rgba(56, 189, 248, 0.2)',
                border: '1px solid rgba(56, 189, 248, 0.4)',
                color: '#38bdf8',
                borderRadius: 8,
                padding: '6px 12px',
                fontSize: 11,
                fontWeight: 600,
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                backdropFilter: 'blur(8px)',
              }}
            >
              <span>📸</span>
              <span>Photogrammetry Split View</span>
            </Link>
          )}

          <button
            onClick={() => setShowRightDrawer(!showRightDrawer)}
            style={{
              background: showRightDrawer ? 'rgba(56, 189, 248, 0.25)' : 'rgba(15, 23, 42, 0.85)',
              border: `1px solid ${showRightDrawer ? 'rgba(56, 189, 248, 0.5)' : 'rgba(255, 255, 255, 0.15)'}`,
              color: showRightDrawer ? '#38bdf8' : '#f1f5f9',
              borderRadius: 8,
              padding: '6px 12px',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              backdropFilter: 'blur(8px)',
              boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            }}
          >
            <span>📊</span>
            <span>{showRightDrawer ? 'Hide Inspector' : 'Inspector & Tools'}</span>
          </button>
        </div>
      </div>

      {/* ── Slide-Out Left Drawer (Layers & Classification Filters) ──────────── */}
      {showLeftDrawer && (
        <div
          style={{
            position: 'absolute',
            top: 54,
            left: 16,
            bottom: 40,
            width: 320,
            zIndex: 30,
            background: 'rgba(11, 15, 25, 0.95)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: 10,
            overflowY: 'auto',
            backdropFilter: 'blur(16px)',
            boxShadow: '0 10px 30px rgba(0,0,0,0.6)',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '10px 14px',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 700, color: '#f1f5f9' }}>Layers & Classification</span>
            <button
              onClick={() => setShowLeftDrawer(false)}
              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 14 }}
            >
              ✕
            </button>
          </div>
          <LeftSidebar />
        </div>
      )}

      {/* ── Slide-Out Right Drawer (Spatial Inspector & Analysis) ────────────── */}
      {showRightDrawer && (
        <div
          style={{
            position: 'absolute',
            top: 54,
            right: 16,
            bottom: 40,
            width: 340,
            zIndex: 30,
            background: 'rgba(11, 15, 25, 0.95)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: 10,
            overflowY: 'auto',
            backdropFilter: 'blur(16px)',
            boxShadow: '0 10px 30px rgba(0,0,0,0.6)',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '10px 14px',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 700, color: '#f1f5f9' }}>Inspector & Analysis</span>
            <button
              onClick={() => setShowRightDrawer(false)}
              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 14 }}
            >
              ✕
            </button>
          </div>
          <RightPanel />
        </div>
      )}

      {/* ── Bottom HUD Bar ──────────────────────────────────────────────────── */}
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 10 }}>
        <BottomBar />
      </div>
    </div>
  )
}
