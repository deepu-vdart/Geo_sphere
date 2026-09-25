import { useEffect, useState } from 'react'
import { useAppStore, useViewerStore } from '../../stores'

export default function TopBar() {
  const { backendStatus, backendVersion, checkBackend } = useAppStore()
  const {
    viewerMode,
    setViewerMode,
    aiDrawerOpen,
    setAiDrawerOpen,
    splitCompareMode,
    setSplitCompareMode,
  } = useViewerStore()
  const activeDataset = useAppStore((s) => s.activeDataset)

  const [time, setTime] = useState(new Date())

  useEffect(() => {
    checkBackend()
    const interval = setInterval(() => {
      checkBackend()
      setTime(new Date())
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <header className="topbar">
      {/* Brand */}
      <div className="topbar__brand">
        <div className="topbar__logo">🌍</div>
        <span className="topbar__title">Geo3D Platform</span>
      </div>

      <div className="topbar__divider" />

      {/* Version */}
      <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
        v{backendVersion || '…'}
      </span>

      {/* 3D Engine Mode Selector: Cesium Globe vs Potree Point Cloud vs Dual View */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          background: 'rgba(15, 23, 42, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: 8,
          padding: 2,
          gap: 2,
          marginLeft: 16,
        }}
      >
        <button
          id="btn-viewer-mode-cesium"
          onClick={() => setViewerMode('cesium')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '4px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            background: viewerMode === 'cesium' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
            color: viewerMode === 'cesium' ? '#38bdf8' : '#94a3b8',
            boxShadow: viewerMode === 'cesium' ? '0 0 10px rgba(56, 189, 248, 0.3)' : 'none',
            transition: 'all 0.15s ease',
          }}
          title="CesiumJS Global 3D Globe with Multi-Layer Geospatial Context"
        >
          <span>🌐</span>
          <span>Cesium Globe</span>
        </button>

        <button
          id="btn-viewer-mode-potree"
          onClick={() => setViewerMode('potree')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '4px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            background: viewerMode === 'potree' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
            color: viewerMode === 'potree' ? '#38bdf8' : '#94a3b8',
            boxShadow: viewerMode === 'potree' ? '0 0 10px rgba(56, 189, 248, 0.3)' : 'none',
            transition: 'all 0.15s ease',
          }}
          title="Potree 1.8+ Ultra-Dense Point Cloud Inspector with Eye-Dome Lighting (EDL)"
        >
          <span>⚡</span>
          <span>Potree COPC</span>
        </button>

        <button
          id="btn-viewer-mode-dual"
          onClick={() => setViewerMode('dual')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '4px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            background: viewerMode === 'dual' ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.3), rgba(168, 85, 247, 0.35))' : 'transparent',
            color: viewerMode === 'dual' ? '#c084fc' : '#94a3b8',
            boxShadow: viewerMode === 'dual' ? '0 0 10px rgba(168, 85, 247, 0.35)' : 'none',
            transition: 'all 0.15s ease',
          }}
          title="Dual Split View: Cesium 3D Globe (Left) + Potree Point Cloud (Right)"
        >
          <span>🔀</span>
          <span>Dual View</span>
        </button>
      </div>

      <div className="topbar__spacer" />

      {/* Photogrammetry Split View (Input Images ↔ 3D Output) */}
      <button
        id="btn-split-compare-toggle"
        onClick={() => setSplitCompareMode(!splitCompareMode)}
        className="btn"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 11,
          padding: '4px 12px',
          borderRadius: 6,
          background: splitCompareMode
            ? 'linear-gradient(135deg, rgba(14, 165, 233, 0.3), rgba(99, 102, 241, 0.4))'
            : 'rgba(255, 255, 255, 0.05)',
          border: splitCompareMode
            ? '1px solid #38bdf8'
            : '1px solid rgba(255, 255, 255, 0.12)',
          color: splitCompareMode ? '#38bdf8' : '#e2e8f0',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          boxShadow: splitCompareMode ? '0 0 14px rgba(56, 189, 248, 0.35)' : 'none',
          marginRight: 8,
        }}
        title="Toggle Split View: Left = Input Drone Images, Right = Reconstructed 3D Output (Paper Style)"
      >
        <span>🖼️</span>
        <span style={{ fontWeight: 600 }}>Split View (Images ↔ 3D)</span>
        {splitCompareMode && (
          <span
            style={{
              fontSize: 9,
              background: '#38bdf8',
              color: '#0f172a',
              fontWeight: 700,
              padding: '1px 5px',
              borderRadius: 10,
            }}
          >
            ACTIVE
          </span>
        )}
      </button>

      {/* AI Assistant Copilot Toggle */}

      <button
        id="btn-ai-copilot-toggle"
        onClick={() => setAiDrawerOpen(!aiDrawerOpen)}
        className="btn"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 11,
          padding: '4px 10px',
          borderRadius: 6,
          background: aiDrawerOpen
            ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(129, 140, 248, 0.35))'
            : 'rgba(255, 255, 255, 0.05)',
          border: aiDrawerOpen
            ? '1px solid #38bdf8'
            : '1px solid rgba(255, 255, 255, 0.1)',
          color: aiDrawerOpen ? '#38bdf8' : '#e2e8f0',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          boxShadow: aiDrawerOpen ? '0 0 12px rgba(56, 189, 248, 0.3)' : 'none',
        }}
        title="Toggle AI Geospatial Assistant (Natural Language Query & Scene Actions)"
      >
        <span>🤖</span>
        <span style={{ fontWeight: 600 }}>AI Copilot</span>
        {aiDrawerOpen && (
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              backgroundColor: '#38bdf8',
              boxShadow: '0 0 6px #38bdf8',
            }}
          />
        )}
      </button>

      <div className="topbar__divider" />

      {/* Time */}
      <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
        {time.toLocaleTimeString()}
      </span>

      <div className="topbar__divider" />

      {/* Backend status */}
      <div className="topbar__status">
        <div className={`status-dot status-dot--${backendStatus}`} />
        <span>
          {backendStatus === 'connected' ? 'API Connected' :
           backendStatus === 'error' ? 'API Offline' : 'Connecting…'}
        </span>
      </div>
    </header>
  )
}
