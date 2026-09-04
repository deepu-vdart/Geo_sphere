import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import type { GL3DScene } from '../../api/client'
import { useAppStore } from '../../stores'

const CATEGORY_COLORS: Record<string, string> = {
  urban: '#38bdf8',
  scenic: '#a78bfa',
  mixed: '#34d399',
  heritage: '#fbbf24',
  rural: '#fb923c',
  coastal: '#22d3ee',
  object: '#f472b6',
  residential: '#818cf8',
}

const CATEGORY_ICONS: Record<string, string> = {
  urban: '🏙️',
  scenic: '⛰️',
  mixed: '🌍',
  heritage: '🏛️',
  rural: '🌾',
  coastal: '🏖️',
  object: '📦',
  residential: '🏘️',
}

export default function GL3DPanel() {
  const [scenes, setScenes] = useState<GL3DScene[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedScene, setSelectedScene] = useState<string | null>(null)
  const [ingesting, setIngesting] = useState<string | null>(null)
  const [ingestMsg, setIngestMsg] = useState('')
  const { loadProjects } = useAppStore()

  useEffect(() => {
    fetchScenes()
  }, [])

  const fetchScenes = async (query: string = '') => {
    setLoading(true)
    try {
      const res = await api.getGL3DScenes(query)
      setScenes(res.data)
    } catch (e) {
      console.warn('Failed to fetch GL3D scenes:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (q: string) => {
    setSearch(q)
    fetchScenes(q)
  }

  const handleIngest = async (sceneId: string, sceneName: string) => {
    setIngesting(sceneId)
    setIngestMsg('')
    try {
      const res = await api.ingestGL3DScene(sceneId, `GL3D: ${sceneName}`, 200000)
      setIngestMsg(res.data.message)
      // Refresh project list after brief delay
      setTimeout(() => {
        loadProjects()
        setIngestMsg('✓ Scene ingested! Select the GL3D project in the sidebar.')
      }, 3000)
    } catch (e: any) {
      setIngestMsg(`Error: ${e?.response?.data?.detail || e.message}`)
    } finally {
      setIngesting(null)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '2px 0' }}>
      {/* Search Bar */}
      <div style={{ padding: '0 2px' }}>
        <input
          className="input"
          placeholder="Search scenes… (urban, scenic, heritage)"
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          style={{ fontSize: 11, padding: '6px 10px' }}
        />
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: 'center', color: '#94a3b8', padding: 12, fontSize: 11 }}>
          <span style={{ animation: 'pulse 1.5s infinite' }}>Loading GL3D catalog…</span>
        </div>
      )}

      {/* Ingest Status */}
      {ingestMsg && (
        <div style={{
          fontSize: 10,
          padding: '6px 8px',
          borderRadius: 4,
          background: ingestMsg.startsWith('Error')
            ? 'rgba(239,68,68,0.12)'
            : 'rgba(56,189,248,0.12)',
          color: ingestMsg.startsWith('Error') ? '#f87171' : '#38bdf8',
          lineHeight: 1.4,
        }}>
          {ingestMsg}
        </div>
      )}

      {/* Scene Cards */}
      {!loading && scenes.map((scene) => {
        const isSelected = selectedScene === scene.scene_id
        const catColor = CATEGORY_COLORS[scene.category] || '#94a3b8'
        const catIcon = CATEGORY_ICONS[scene.category] || '📷'

        return (
          <div
            key={scene.scene_id}
            onClick={() => setSelectedScene(isSelected ? null : scene.scene_id)}
            style={{
              padding: '8px 10px',
              borderRadius: 6,
              cursor: 'pointer',
              background: isSelected
                ? 'rgba(56, 189, 248, 0.08)'
                : 'rgba(255, 255, 255, 0.02)',
              border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.3)' : 'rgba(255,255,255,0.05)'}`,
              transition: 'all 0.2s ease',
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <span style={{ fontSize: 14 }}>{catIcon}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: '#e2e8f0',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {scene.name}
                </div>
              </div>
              {scene.is_downloaded && (
                <span style={{
                  fontSize: 8,
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'rgba(52,211,153,0.15)',
                  color: '#34d399',
                  fontWeight: 600,
                }}>
                  LOCAL
                </span>
              )}
            </div>

            {/* Meta Row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#94a3b8', flexWrap: 'wrap' }}>
              <span style={{
                padding: '1px 6px',
                borderRadius: 3,
                background: `${catColor}22`,
                color: catColor,
                fontWeight: 600,
                fontSize: 9,
              }}>
                {scene.category_label || scene.category}
              </span>
              <span style={{
                padding: '1px 5px',
                borderRadius: 3,
                background: 'rgba(255,255,255,0.05)',
                color: '#cbd5e1',
                fontSize: 9,
              }}>
                🏛️ 3D Mesh
              </span>
              <span style={{ fontSize: 9, color: '#94a3b8' }}>📸 {scene.image_count}</span>
            </div>

            {/* Expanded Detail */}
            {isSelected && (
              <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                {/* Multi-View Drone Capture Photo Strip (Matches GL3D Paper Layout) */}
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 9, fontWeight: 600, color: '#94a3b8', marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
                    <span>📸 Multi-View Drone Flight Passes:</span>
                    <span style={{ color: '#38bdf8' }}>{scene.category_label}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 4 }}>
                    <div style={{
                      height: 48,
                      borderRadius: 4,
                      background: 'linear-gradient(135deg, rgba(14,165,233,0.15), rgba(99,102,241,0.25))',
                      border: '1px solid rgba(56,189,248,0.2)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 8,
                      color: '#93c5fd',
                      textAlign: 'center',
                      padding: 2,
                    }}>
                      <span>📷 Pass A</span>
                      <span style={{ color: '#64748b', fontSize: 7 }}>Oblique 45°</span>
                    </div>
                    <div style={{
                      height: 48,
                      borderRadius: 4,
                      background: 'linear-gradient(135deg, rgba(168,85,247,0.15), rgba(236,72,153,0.25))',
                      border: '1px solid rgba(168,85,247,0.2)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 8,
                      color: '#d8b4fe',
                      textAlign: 'center',
                      padding: 2,
                    }}>
                      <span>📷 Pass B</span>
                      <span style={{ color: '#64748b', fontSize: 7 }}>Orbit 30°</span>
                    </div>
                    <div style={{
                      height: 48,
                      borderRadius: 4,
                      background: 'linear-gradient(135deg, rgba(34,197,94,0.15), rgba(56,189,248,0.25))',
                      border: '1px solid rgba(34,197,94,0.2)',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 8,
                      color: '#86efac',
                      textAlign: 'center',
                      padding: 2,
                    }}>
                      <span>📷 Pass C</span>
                      <span style={{ color: '#64748b', fontSize: 7 }}>Nadir 90°</span>
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: 10, color: '#cbd5e1', lineHeight: 1.4, marginBottom: 8 }}>
                  {scene.description}
                </div>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 4,
                  fontSize: 9,
                  marginBottom: 8,
                  background: 'rgba(255,255,255,0.02)',
                  padding: 6,
                  borderRadius: 4,
                }}>
                  <div style={{ color: '#64748b' }}>
                    Mesh: <span style={{ color: '#e2e8f0' }}>Solid Triangular Surface</span>
                  </div>
                  <div style={{ color: '#64748b' }}>
                    Shading: <span style={{ color: '#e2e8f0' }}>PBR Clay / Specular</span>
                  </div>
                  <div style={{ color: '#64748b' }}>
                    Coords: <span style={{ color: '#e2e8f0' }}>Local SfM → WGS84</span>
                  </div>
                  <div style={{ color: '#64748b' }}>
                    Source: <span style={{ color: '#e2e8f0' }}>GL3D / Altizure</span>
                  </div>
                </div>

                <button
                  className="btn btn--primary btn--sm w-full"
                  disabled={ingesting === scene.scene_id}
                  onClick={(e) => {
                    e.stopPropagation()
                    handleIngest(scene.scene_id, scene.name)
                  }}
                  style={{
                    fontSize: 10,
                    padding: '6px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    background: ingesting === scene.scene_id
                      ? 'rgba(56,189,248,0.2)'
                      : 'linear-gradient(135deg, #0ea5e9, #6366f1)',
                    opacity: ingesting === scene.scene_id ? 0.7 : 1,
                  }}
                >
                  {ingesting === scene.scene_id ? (
                    <>
                      <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⏳</span>
                      <span>Reconstructing 3D Mesh…</span>
                    </>
                  ) : (
                    <>
                      <span>🏛️</span>
                      <span>Ingest & Render 3D Surface Mesh</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )
      })}

      {/* Empty State */}
      {!loading && scenes.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: 20,
          color: '#64748b',
          fontSize: 11,
        }}>
          <div style={{ fontSize: 24, marginBottom: 6 }}>📷</div>
          <div>No GL3D scenes found.</div>
          <div style={{ fontSize: 10, marginTop: 4 }}>Try a different search query.</div>
        </div>
      )}

      {/* Attribution */}
      <div style={{
        fontSize: 9,
        color: '#475569',
        padding: '4px 6px',
        lineHeight: 1.4,
        borderTop: '1px solid rgba(255,255,255,0.04)',
        marginTop: 4,
      }}>
        GL3D: Shen et al. "Matchable Image Retrieval by Learning from Surface Reconstruction"
        ACCV 2018. 3D reconstructions by Altizure.
      </div>
    </div>
  )
}
