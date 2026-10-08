import React, { useState } from 'react'
import { useAppStore } from '../stores'
import CesiumViewer from '../components/cesium/CesiumViewer'
import RightPanel from '../components/layout/RightPanel'
import TemporalChangePanel from '../components/panels/TemporalChangePanel'
import ClassificationPanel from '../components/panels/ClassificationPanel'
import { useDatasetUrlSync } from '../hooks/useDatasetUrlSync'

export default function AnalysisPage() {
  const { activeDataset } = useDatasetUrlSync()
  const [activeAnalysisTab, setActiveAnalysisTab] = useState<'derivatives' | 'objects' | 'temporal'>('derivatives')

  return (
    <div
      style={{
        height: 'calc(100vh - 48px)',
        width: '100%',
        display: 'flex',
        background: '#090d16',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* ── Left Analytical Controls & Inspector (380px) ──────────────────────── */}
      <div
        style={{
          width: 380,
          height: '100%',
          borderRight: '1px solid rgba(56, 189, 248, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          background: '#0d1322',
          zIndex: 10,
        }}
      >
        {/* Analysis Tool Switcher Tabs */}
        <div
          style={{
            padding: '8px 12px',
            background: 'rgba(15, 23, 42, 0.95)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            gap: 6,
          }}
        >
          {[
            { id: 'derivatives', label: 'Terrain & DTM', icon: '⛰️' },
            { id: 'objects', label: '3D Objects', icon: '🎯' },
            { id: 'temporal', label: 'Temporal Diff', icon: '⏱️' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveAnalysisTab(tab.id as any)}
              style={{
                flex: 1,
                background: activeAnalysisTab === tab.id ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                border: `1px solid ${activeAnalysisTab === tab.id ? 'rgba(56, 189, 248, 0.4)' : 'transparent'}`,
                color: activeAnalysisTab === tab.id ? '#38bdf8' : '#94a3b8',
                borderRadius: 6,
                padding: '6px 8px',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 4,
              }}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {activeAnalysisTab === 'derivatives' && <RightPanel />}
          {activeAnalysisTab === 'objects' && <ClassificationPanel datasetId={activeDataset?.id || ''} />}
          {activeAnalysisTab === 'temporal' && <TemporalChangePanel />}
        </div>
      </div>

      {/* ── Right 3D Visualizer Viewport ─────────────────────────────────────── */}
      <div style={{ flex: 1, height: '100%', position: 'relative' }}>
        <div
          style={{
            position: 'absolute',
            top: 10,
            left: 10,
            zIndex: 10,
            background: 'rgba(15, 23, 42, 0.85)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: 6,
            padding: '4px 10px',
            fontSize: 11,
            color: '#38bdf8',
            fontWeight: 700,
            pointerEvents: 'none',
          }}
        >
          {activeDataset ? `Interactive 3D Analytical Surface • ${activeDataset.name}` : '3D Analytical Surface'}
        </div>
        <CesiumViewer />
      </div>
    </div>
  )
}
