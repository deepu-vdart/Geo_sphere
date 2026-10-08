import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useViewerStore } from '../stores'
import PotreeViewer from '../components/potree/PotreeViewer'
import { useDatasetUrlSync } from '../hooks/useDatasetUrlSync'

export default function PotreeViewerPage() {
  const { activeDataset } = useDatasetUrlSync()
  const {
    potreePointBudget,
    setPotreePointBudget,
    potreeEdlEnabled,
    togglePotreeEdl,
    potreeColorMode,
    setPotreeColorMode,
    potreeActiveTool,
    setPotreeActiveTool,
  } = useViewerStore()

  return (
    <div
      style={{
        height: 'calc(100vh - 48px)',
        width: '100%',
        position: 'relative',
        overflow: 'hidden',
        background: '#040711',
      }}
    >
      {/* ── Potree Viewport ──────────────────────────────────────────────────── */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
        <PotreeViewer />
      </div>

      {/* ── Top Floating Potree Controls ─────────────────────────────────────── */}
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, pointerEvents: 'auto' }}>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              borderRadius: 8,
              padding: '6px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              backdropFilter: 'blur(8px)',
            }}
          >
            <span style={{ fontSize: 13 }}>⚡</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#c084fc' }}>
              Potree 1.8+ / COPC Inspector
            </span>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>
              {activeDataset?.name || 'Aukerman Drone Point Cloud'}
            </span>
          </div>

          {/* Color Mode */}
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
                onClick={() => setPotreeColorMode(mode)}
                style={{
                  background: potreeColorMode === mode ? 'rgba(168, 85, 247, 0.3)' : 'transparent',
                  color: potreeColorMode === mode ? '#c084fc' : '#94a3b8',
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

          {/* EDL Shader Toggle */}
          <button
            onClick={togglePotreeEdl}
            style={{
              background: potreeEdlEnabled ? 'rgba(52, 211, 153, 0.2)' : 'rgba(15, 23, 42, 0.85)',
              border: `1px solid ${potreeEdlEnabled ? 'rgba(52, 211, 153, 0.4)' : 'rgba(255, 255, 255, 0.12)'}`,
              color: potreeEdlEnabled ? '#34d399' : '#94a3b8',
              borderRadius: 8,
              padding: '6px 12px',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              backdropFilter: 'blur(8px)',
            }}
          >
            EDL Shading: {potreeEdlEnabled ? 'ON' : 'OFF'}
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, pointerEvents: 'auto' }}>
          {/* Point Budget Slider */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: 8,
              padding: '4px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 11,
              color: '#94a3b8',
              backdropFilter: 'blur(8px)',
            }}
          >
            <span>Budget:</span>
            <input
              type="range"
              min="500000"
              max="5000000"
              step="500000"
              value={potreePointBudget}
              onChange={(e) => setPotreePointBudget(Number(e.target.value))}
              style={{ width: 80, cursor: 'pointer' }}
            />
            <span style={{ color: '#c084fc', fontWeight: 600 }}>
              {(potreePointBudget / 1000000).toFixed(1)}M pts
            </span>
          </div>

          {/* Cross-section tool button */}
          <button
            onClick={() => setPotreeActiveTool(potreeActiveTool === 'profile' ? 'none' : 'profile')}
            style={{
              background: potreeActiveTool === 'profile' ? 'rgba(56, 189, 248, 0.25)' : 'rgba(15, 23, 42, 0.85)',
              border: `1px solid ${potreeActiveTool === 'profile' ? 'rgba(56, 189, 248, 0.5)' : 'rgba(255, 255, 255, 0.12)'}`,
              color: potreeActiveTool === 'profile' ? '#38bdf8' : '#cbd5e1',
              borderRadius: 8,
              padding: '6px 12px',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              backdropFilter: 'blur(8px)',
            }}
          >
            ✂️ Cross Section
          </button>
        </div>
      </div>
    </div>
  )
}
