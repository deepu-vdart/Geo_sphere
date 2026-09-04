import { useEffect, useState } from 'react'
import { useAppStore, useViewerStore } from '../../stores'

export default function TopBar() {
  const { backendStatus, backendVersion, checkBackend } = useAppStore()
  const { aiDrawerOpen, setAiDrawerOpen } = useViewerStore()
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

      <div className="topbar__spacer" />

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
