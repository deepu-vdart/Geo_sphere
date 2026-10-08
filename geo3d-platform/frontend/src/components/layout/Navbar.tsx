import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAppStore, useViewerStore } from '../../stores'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { backendStatus, backendVersion, datasets, activeDataset, selectDataset } = useAppStore()
  const { aiDrawerOpen, setAiDrawerOpen } = useViewerStore()

  const navLinks = [
    { path: '/', label: 'Catalog', icon: '📁' },
    { path: '/viewer', label: '3D Globe', icon: '🌐' },
    { path: '/photogrammetry', label: 'Photogrammetry', icon: '📸' },
    { path: '/potree', label: 'Point Cloud', icon: '⚡' },
    { path: '/dual', label: 'Dual View', icon: '◫' },
    { path: '/analysis', label: 'Analysis', icon: '📊' },
  ]

  const handleDatasetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedId = e.target.value
    const found = datasets.find((d) => d.id === selectedId)
    if (found) {
      selectDataset(found)
      // Retain the current route with the new dataset query parameter
      navigate(`${location.pathname}?dataset=${selectedId}`)
    }
  }

  return (
    <header
      style={{
        height: 48,
        background: 'rgba(11, 15, 25, 0.96)',
        borderBottom: '1px solid rgba(56, 189, 248, 0.18)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        position: 'relative',
        zIndex: 50,
        backdropFilter: 'blur(12px)',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
      }}
    >
      {/* ── Brand Logo ──────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <Link
          to="/"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            textDecoration: 'none',
            color: '#f8fafc',
          }}
        >
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 10px rgba(56, 189, 248, 0.4)',
              fontSize: 16,
            }}
          >
            🌍
          </div>
          <span style={{ fontWeight: 800, fontSize: 14, letterSpacing: -0.3 }}>
            Geo3D Platform
          </span>
          <span
            style={{
              fontSize: 10,
              color: '#64748b',
              background: 'rgba(255, 255, 255, 0.05)',
              padding: '1px 6px',
              borderRadius: 4,
            }}
          >
            v{backendVersion || '0.1.0'}
          </span>
        </Link>

        {/* ── Navigation Links (Clean Dedicated Routes) ───────────────────── */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 12 }}>
          {navLinks.map((item) => {
            const isActive =
              item.path === '/'
                ? location.pathname === '/' || location.pathname === '/projects'
                : location.pathname.startsWith(item.path)

            const targetUrl = activeDataset ? `${item.path}?dataset=${activeDataset.id}` : item.path

            return (
              <Link
                key={item.path}
                to={targetUrl}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '5px 12px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  textDecoration: 'none',
                  transition: 'all 0.15s ease',
                  background: isActive ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                  color: isActive ? '#38bdf8' : '#94a3b8',
                  border: isActive ? '1px solid rgba(56, 189, 248, 0.35)' : '1px solid transparent',
                  boxShadow: isActive ? '0 0 12px rgba(56, 189, 248, 0.2)' : 'none',
                }}
              >
                <span style={{ fontSize: 13 }}>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </div>

      {/* ── Right Status & Controls ────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Active Dataset Dropdown Picker */}
        {datasets.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>
              Dataset:
            </span>
            <select
              value={activeDataset?.id || ''}
              onChange={handleDatasetChange}
              style={{
                background: 'rgba(15, 23, 42, 0.9)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: 6,
                color: '#e2e8f0',
                fontSize: 11,
                padding: '4px 8px',
                outline: 'none',
                maxWidth: 240,
                cursor: 'pointer',
              }}
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.dataset_type})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* AI Copilot Toggle */}
        <button
          onClick={() => setAiDrawerOpen(!aiDrawerOpen)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: aiDrawerOpen ? 'rgba(168, 85, 247, 0.25)' : 'rgba(255, 255, 255, 0.05)',
            border: `1px solid ${aiDrawerOpen ? 'rgba(168, 85, 247, 0.5)' : 'rgba(255, 255, 255, 0.1)'}`,
            borderRadius: 6,
            color: aiDrawerOpen ? '#c084fc' : '#cbd5e1',
            padding: '4px 10px',
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          <span>🤖</span>
          <span>AI Copilot</span>
        </button>

        {/* Backend Connectivity Status Dot */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 8px',
            borderRadius: 12,
            background: 'rgba(255, 255, 255, 0.04)',
            fontSize: 10,
            color: '#94a3b8',
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: backendStatus === 'connected' ? '#34d399' : '#f87171',
              boxShadow: backendStatus === 'connected' ? '0 0 6px #34d399' : 'none',
            }}
          />
          <span>{backendStatus === 'connected' ? 'API Online' : 'API Error'}</span>
        </div>
      </div>
    </header>
  )
}
