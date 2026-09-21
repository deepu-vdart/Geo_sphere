import { useState } from 'react'
import { useAppStore, useViewerStore } from '../../stores'
import { api } from '../../api/client'

export default function TemporalChangePanel() {
  const { datasets, activeDataset } = useAppStore()
  const {
    temporalDiffResult,
    setTemporalDiffResult,
    setTemporalDiffPoints,
  } = useViewerStore()

  const pointCloudDatasets = datasets.filter(
    (d) => d.dataset_type === 'point_cloud' || d.dataset_type === 'gl3d_scene' || d.dataset_type === 'photogrammetry'
  )

  const [baselineId, setBaselineId] = useState<string>(activeDataset?.id || pointCloudDatasets[0]?.id || '')
  const [comparisonId, setComparisonId] = useState<string>(
    pointCloudDatasets[1]?.id || activeDataset?.id || pointCloudDatasets[0]?.id || ''
  )
  const [gridRes, setGridRes] = useState<number>(2.0)
  const [heightThreshold, setHeightThreshold] = useState<number>(0.3)
  const [simulateShift, setSimulateShift] = useState<boolean>(baselineId === comparisonId)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<string>('all')

  const handleRunComparison = async (isDemo = false) => {
    setLoading(true)
    setError(null)
    try {
      let res
      if (isDemo) {
        res = await api.getTemporalDemo()
      } else {
        if (!baselineId) {
          throw new Error('Please select a baseline survey dataset.')
        }
        res = await api.compareTemporalSurveys(
          baselineId,
          comparisonId || baselineId,
          gridRes,
          simulateShift || baselineId === comparisonId
        )
      }

      const data = res.data
      setTemporalDiffResult(data)
      setTemporalDiffPoints(data.difference_samples || [])
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setTemporalDiffResult(null)
    setTemporalDiffPoints(null)
    setError(null)
  }

  const handleFilterChange = (type: string) => {
    setFilterType(type)
    if (!temporalDiffResult || !temporalDiffResult.difference_samples) return
    if (type === 'all') {
      setTemporalDiffPoints(temporalDiffResult.difference_samples)
    } else {
      const filtered = temporalDiffResult.difference_samples.filter((p: any) => p.type === type)
      setTemporalDiffPoints(filtered)
    }
  }

  const metrics = temporalDiffResult?.metrics
  const dist = temporalDiffResult?.distribution

  return (
    <div style={{ padding: '8px 4px', fontSize: 13, color: 'var(--color-text)' }}>
      {/* ── Instructions / Description ──────────────────────────────────── */}
      <div style={{ marginBottom: 12, color: 'var(--color-text-muted)', fontSize: 11, lineHeight: 1.4 }}>
        Compare multi-epoch LiDAR or photogrammetry surveys to detect topographic changes, volumetric cut/fill, and structural developments.
      </div>

      {/* ── Survey Selectors ────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)' }}>
            Baseline Survey (T1 Epoch)
          </label>
          <select
            value={baselineId}
            onChange={(e) => {
              setBaselineId(e.target.value)
              if (e.target.value === comparisonId) setSimulateShift(true)
            }}
            style={{
              width: '100%',
              padding: '6px 8px',
              marginTop: 4,
              borderRadius: 6,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text)',
              fontSize: 12,
            }}
          >
            {pointCloudDatasets.map((d) => (
              <option key={d.id} value={d.id} style={{ background: '#1e293b' }}>
                {d.name}
              </option>
            ))}
            {pointCloudDatasets.length === 0 && (
              <option value="" style={{ background: '#1e293b' }}>
                (No point cloud datasets loaded)
              </option>
            )}
          </select>
        </div>

        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-muted)' }}>
            Comparison Survey (T2 Epoch)
          </label>
          <select
            value={comparisonId}
            onChange={(e) => {
              setComparisonId(e.target.value)
              if (e.target.value === baselineId) setSimulateShift(true)
            }}
            style={{
              width: '100%',
              padding: '6px 8px',
              marginTop: 4,
              borderRadius: 6,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text)',
              fontSize: 12,
            }}
          >
            {pointCloudDatasets.map((d) => (
              <option key={d.id} value={d.id} style={{ background: '#1e293b' }}>
                {d.name} {d.id === baselineId ? '(Same - Shift mode)' : ''}
              </option>
            ))}
            {pointCloudDatasets.length === 0 && (
              <option value="" style={{ background: '#1e293b' }}>
                (Synthetic baseline mode)
              </option>
            )}
          </select>
        </div>
      </div>

      {/* ── Configuration Parameters ────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
        <div>
          <label style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Grid Res (m)</label>
          <select
            value={gridRes}
            onChange={(e) => setGridRes(Number(e.target.value))}
            style={{
              width: '100%',
              padding: '4px 6px',
              marginTop: 2,
              borderRadius: 4,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text)',
              fontSize: 11,
            }}
          >
            <option value={1.0} style={{ background: '#1e293b' }}>1.0 m (High detail)</option>
            <option value={2.0} style={{ background: '#1e293b' }}>2.0 m (Standard)</option>
            <option value={5.0} style={{ background: '#1e293b' }}>5.0 m (Fast coarse)</option>
          </select>
        </div>

        <div>
          <label style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Threshold (m)</label>
          <input
            type="number"
            step="0.1"
            min="0.1"
            max="2.0"
            value={heightThreshold}
            onChange={(e) => setHeightThreshold(Number(e.target.value))}
            style={{
              width: '100%',
              padding: '4px 6px',
              marginTop: 2,
              borderRadius: 4,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text)',
              fontSize: 11,
            }}
          />
        </div>
      </div>

      {/* ── Action Buttons ──────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        <button
          onClick={() => handleRunComparison(false)}
          disabled={loading || (!baselineId && pointCloudDatasets.length === 0)}
          style={{
            flex: 2,
            padding: '8px 12px',
            borderRadius: 6,
            background: 'linear-gradient(135deg, #0ea5e9, #3b82f6)',
            color: '#fff',
            border: 'none',
            cursor: loading ? 'wait' : 'pointer',
            fontWeight: 600,
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          {loading ? '⏳ Computing...' : '🚀 Run Change Detection'}
        </button>

        <button
          onClick={() => handleRunComparison(true)}
          disabled={loading}
          title="Instant demonstration with synthetic excavation & structures"
          style={{
            flex: 1,
            padding: '8px 8px',
            borderRadius: 6,
            background: 'rgba(255, 255, 255, 0.08)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            cursor: loading ? 'wait' : 'pointer',
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          ⚡ Demo
        </button>
      </div>

      {error && (
        <div style={{ padding: '8px', marginBottom: 12, borderRadius: 6, background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', fontSize: 11 }}>
          ⚠️ {error}
        </div>
      )}

      {/* ── Results View ────────────────────────────────────────────────── */}
      {temporalDiffResult && metrics && (
        <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontWeight: 700, fontSize: 12, color: '#38bdf8' }}>
              📊 Change Detection Results
            </span>
            <button
              onClick={handleClear}
              style={{
                fontSize: 10,
                color: 'var(--color-text-muted)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Clear
            </button>
          </div>

          {/* Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 10 }}>
            <div style={{ padding: '8px', borderRadius: 6, background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)' }}>
              <div style={{ fontSize: 10, color: '#f87171' }}>Cut (Erosion/Excavation)</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#ef4444' }}>
                {metrics.cut_volume_m3?.toLocaleString()} m³
              </div>
            </div>

            <div style={{ padding: '8px', borderRadius: 6, background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
              <div style={{ fontSize: 10, color: '#7dd3fc' }}>Fill (Deposition/Fill)</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#38bdf8' }}>
                +{metrics.fill_volume_m3?.toLocaleString()} m³
              </div>
            </div>

            <div style={{ padding: '8px', borderRadius: 6, background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Net Differential</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: metrics.net_volume_m3 >= 0 ? '#38bdf8' : '#ef4444' }}>
                {metrics.net_volume_m3 > 0 ? `+${metrics.net_volume_m3?.toLocaleString()}` : metrics.net_volume_m3?.toLocaleString()} m³
              </div>
            </div>

            <div style={{ padding: '8px', borderRadius: 6, background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>Modified Footprint</div>
              <div style={{ fontSize: 13, fontWeight: 700 }}>
                {metrics.modified_area_m2?.toLocaleString()} m²
              </div>
            </div>
          </div>

          {/* Structure & Surface Dynamics */}
          {dist && (
            <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: 8, borderRadius: 6, marginBottom: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, color: 'var(--color-text-muted)' }}>
                Surface Dynamics
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0' }}>
                <span>🔴 Cut Area:</span>
                <span style={{ fontWeight: 600 }}>{dist.cut_percentage}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0' }}>
                <span>🔵 Fill Area:</span>
                <span style={{ fontWeight: 600 }}>{dist.fill_percentage}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0' }}>
                <span>🟢 Stable Area:</span>
                <span style={{ fontWeight: 600 }}>{dist.stable_percentage}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0' }}>
                <span>🟣 New Structures:</span>
                <span style={{ fontWeight: 600, color: '#c084fc' }}>{dist.new_structures_detected}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0' }}>
                <span>🟠 Demolished:</span>
                <span style={{ fontWeight: 600, color: '#fb923c' }}>{dist.demolished_structures_detected}</span>
              </div>
            </div>
          )}

          {/* 3D Visualizer Filter Buttons */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 6, color: 'var(--color-text-muted)' }}>
              3D Differential Cloud Filter
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {[
                { label: 'All', value: 'all', color: '#94a3b8' },
                { label: 'Cut (Red)', value: 'cut', color: '#ef4444' },
                { label: 'Fill (Blue)', value: 'fill', color: '#38bdf8' },
                { label: 'New Struct', value: 'new_structure', color: '#a855f7' },
                { label: 'Demolished', value: 'demolished', color: '#f97316' },
                { label: 'Stable', value: 'stable', color: '#22c55e' },
              ].map((btn) => (
                <button
                  key={btn.value}
                  onClick={() => handleFilterChange(btn.value)}
                  style={{
                    padding: '3px 6px',
                    fontSize: 10,
                    borderRadius: 4,
                    border: `1px solid ${filterType === btn.value ? btn.color : 'rgba(255,255,255,0.1)'}`,
                    background: filterType === btn.value ? 'rgba(255,255,255,0.1)' : 'transparent',
                    color: btn.color,
                    cursor: 'pointer',
                  }}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
