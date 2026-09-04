import { useState, useEffect } from 'react'
import { useAppStore, useViewerStore } from '../../stores'
import { api } from '../../api/client'
import ClassificationPanel from '../panels/ClassificationPanel'
import GL3DPanel from '../sidebar/GL3DPanel'

function AITerrainPanel({ datasetId }: { datasetId: string }) {
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetchAI = async () => {
    setLoading(true)
    try {
      const res = await api.getAISummary(datasetId)
      setSummary(res.data)
    } catch (e) {
      console.warn('AI summary fetch failed:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAI()
  }, [datasetId])

  if (loading) {
    return <div style={{ fontSize: 11, color: '#94a3b8', padding: 8 }}>Analyzing terrain structure…</div>
  }

  if (!summary) {
    return (
      <button onClick={fetchAI} className="btn btn--secondary btn--sm w-full" style={{ fontSize: 10 }}>
        🤖 Analyze Terrain
      </button>
    )
  }

  const { structured_metrics, geospatial_insights, development_suitability } = summary

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11, padding: '4px 2px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#38bdf8', fontWeight: 600 }}>Site Suitability:</span>
        <span className="badge badge--success">{development_suitability}</span>
      </div>

      <div style={{ background: 'rgba(255,255,255,0.03)', padding: 6, borderRadius: 4 }}>
        <div style={{ fontWeight: 600, color: '#cbd5e1', marginBottom: 4 }}>Composition:</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: 10, color: '#94a3b8' }}>
          <div>Ground: <span style={{ color: '#f1f5f9' }}>{structured_metrics.composition_percentages.ground}%</span></div>
          <div>Trees: <span style={{ color: '#f1f5f9' }}>{structured_metrics.composition_percentages.vegetation}%</span></div>
          <div>Buildings: <span style={{ color: '#f1f5f9' }}>{structured_metrics.composition_percentages.buildings}%</span></div>
          <div>Relief: <span style={{ color: '#f1f5f9' }}>{structured_metrics.elevation.relief_m}m</span></div>
        </div>
      </div>

      {geospatial_insights && geospatial_insights.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {geospatial_insights.map((insight: string, idx: number) => (
            <div key={idx} style={{ fontSize: 10, lineHeight: 1.4, color: '#93c5fd', background: 'rgba(56,189,248,0.08)', padding: 6, borderRadius: 4 }}>
              💡 {insight}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function LeftSidebar() {
  const {
    projects, activeProject, loadingProjects,
    loadProjects, selectProject, createProject,
    datasets, loadingDatasets, selectDataset, activeDataset,
  } = useAppStore()

  const {
    layers, toggleLayer, activeTool, setActiveTool,
    pointBudget, setPointBudget, tileStreamingProgress,
    setAiDrawerOpen,
    showMapBackground, toggleMapBackground,
    showDroneCameras, toggleDroneCameras,
  } = useViewerStore()

  const [openSections, setOpenSections] = useState({
    project: true,
    layers: true,
    analysis: true,
    ai: false,
    gl3d: false,
    classification: false,
  })

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDesc, setNewProjectDesc] = useState('')
  const [newProjectLoc, setNewProjectLoc] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => { loadProjects() }, [])

  const toggleSection = (key: keyof typeof openSections) =>
    setOpenSections((s) => ({ ...s, [key]: !s[key] }))

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return
    setCreating(true)
    const project = await createProject(newProjectName.trim(), newProjectDesc, newProjectLoc)
    if (project) {
      selectProject(project)
      setShowCreateModal(false)
      setNewProjectName('')
      setNewProjectDesc('')
      setNewProjectLoc('')
    }
    setCreating(false)
  }

  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      validated: 'badge--success',
      pending: 'badge--warning',
      validation_failed: 'badge--error',
      processing: 'badge--info',
    }
    return map[status] || 'badge--neutral'
  }

  const formatBytes = (bytes: number | null) => {
    if (!bytes) return null
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  return (
    <>
      <aside className="sidebar">
        <div className="sidebar__scroll">

          {/* ── Project Section ──────────────────────────────────────── */}
          <div className="sidebar__section">
            <div className="sidebar__section-header" onClick={() => toggleSection('project')}>
              <span className="sidebar__section-title">Project</span>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
                {openSections.project ? '▲' : '▼'}
              </span>
            </div>

            {openSections.project && (
              <>
                <button
                  className="btn btn--primary btn--sm w-full"
                  style={{ marginBottom: 8 }}
                  onClick={() => setShowCreateModal(true)}
                >
                  + New Project
                </button>

                {loadingProjects && (
                  <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 8, fontSize: 11 }}>
                    Loading projects…
                  </div>
                )}

                {projects.length === 0 && !loadingProjects && (
                  <div className="empty-state">
                    <div className="empty-state__icon">📂</div>
                    <div className="empty-state__text">No projects yet.<br/>Create your first project.</div>
                  </div>
                )}

                {projects.map((p) => (
                  <div
                    key={p.id}
                    className={`project-card ${activeProject?.id === p.id ? 'project-card--active' : ''}`}
                    onClick={() => selectProject(p)}
                  >
                    <div className="project-card__name">{p.name}</div>
                    <div className="project-card__meta">
                      {p.dataset_count} dataset{p.dataset_count !== 1 ? 's' : ''}
                      {p.location_name && ` · ${p.location_name}`}
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>

          {/* ── Datasets Section ─────────────────────────────────────── */}
          {activeProject && (
            <div className="sidebar__section">
              <div className="sidebar__section-header">
                <span className="sidebar__section-title">Datasets</span>
                <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
                  {datasets.length}
                </span>
              </div>

              {loadingDatasets && (
                <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 8, fontSize: 11 }}>
                  Loading…
                </div>
              )}

              {!loadingDatasets && datasets.length === 0 && (
                <div className="empty-state">
                  <div className="empty-state__icon">📊</div>
                  <div className="empty-state__text">No datasets.<br/>Upload via the API.</div>
                </div>
              )}

              {datasets.map((d) => (
                <div
                  key={d.id}
                  className={`dataset-item ${activeDataset?.id === d.id ? 'dataset-item--active' : ''}`}
                  onClick={() => selectDataset(d)}
                >
                  <div className="dataset-item__name">{d.name}</div>
                  <div className="dataset-item__meta">
                    <span className={`badge ${getStatusBadge(d.processing_status)}`}>
                      {d.processing_status}
                    </span>
                    <span>{d.dataset_type}</span>
                    {d.file_size_bytes && <span>{formatBytes(d.file_size_bytes)}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Environment & Display Controls ───────────────────────── */}
          <div style={{
            margin: '6px 8px',
            padding: '8px 10px',
            background: 'rgba(255, 255, 255, 0.025)',
            border: '1px solid rgba(255, 255, 255, 0.06)',
            borderRadius: 6,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}>
            {/* Map Background Toggle */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#e2e8f0' }}>
                <span style={{ fontSize: 13 }}>{showMapBackground ? '🛰️' : '⬛'}</span>
                <span style={{ fontWeight: 500 }}>Map Background</span>
              </div>
              <button
                onClick={toggleMapBackground}
                style={{
                  fontSize: 10,
                  padding: '3px 8px',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontWeight: 600,
                  background: showMapBackground ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  color: showMapBackground ? '#38bdf8' : '#94a3b8',
                  border: `1px solid ${showMapBackground ? 'rgba(56, 189, 248, 0.4)' : 'rgba(255, 255, 255, 0.1)'}`,
                  transition: 'all 0.2s ease',
                }}
                title={showMapBackground ? 'Satellite map is ON. Click to remove.' : 'Background map is OFF (clean studio). Click to show.'}
              >
                {showMapBackground ? 'ON' : 'OFF'}
              </button>
            </div>

            {/* Drone Cameras (Blue Dots) Toggle */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#e2e8f0' }}>
                <span style={{ fontSize: 13 }}>📷</span>
                <span style={{ fontWeight: 500 }}>Camera Stations</span>
              </div>
              <button
                onClick={toggleDroneCameras}
                style={{
                  fontSize: 10,
                  padding: '3px 8px',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontWeight: 600,
                  background: showDroneCameras ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                  color: showDroneCameras ? '#38bdf8' : '#94a3b8',
                  border: `1px solid ${showDroneCameras ? 'rgba(56, 189, 248, 0.4)' : 'rgba(255, 255, 255, 0.1)'}`,
                  transition: 'all 0.2s ease',
                }}
                title={showDroneCameras ? 'Camera markers are ON. Click to remove.' : 'Camera markers are OFF. Click to show.'}
              >
                {showDroneCameras ? 'ON' : 'OFF'}
              </button>
            </div>
          </div>

          {/* ── Classification Filter Section ──────────────────────────── */}
          <div className="sidebar__section">
            <div className="sidebar__section-header" onClick={() => toggleSection('layers')}>
              <span className="sidebar__section-title">Point Classes</span>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
                {openSections.layers ? '▲' : '▼'}
              </span>
            </div>

            {openSections.layers && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '4px 2px' }}>
                {[
                  { code: 0, name: 'Ground / Created', color: '#8b5a2b' },
                  { code: 2, name: 'Ground (Classified)', color: '#8b5a2b' },
                  { code: 5, name: 'Trees / High Veg', color: '#228b22' },
                  { code: 4, name: 'Medium Vegetation', color: '#d2691e' },
                  { code: 3, name: 'Low Vegetation', color: '#ffd700' },
                  { code: 6, name: 'Buildings', color: '#dc143c' },
                  { code: 12, name: 'Building Structures', color: '#dc143c' },
                  { code: 9, name: 'Water / Utility Pole', color: '#00ced1' },
                  { code: 7, name: 'Noise / Outlier', color: '#ff1493' },
                ].map((cls) => {
                  const isChecked = useViewerStore.getState().activeClassFilters[cls.code] !== false
                  return (
                    <label
                      key={cls.code}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: 11,
                        cursor: 'pointer',
                        padding: '3px 6px',
                        borderRadius: 4,
                        background: isChecked ? 'rgba(255,255,255,0.03)' : 'transparent'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: cls.color }} />
                        <span>{cls.name}</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => useViewerStore.getState().toggleClassFilter(cls.code)}
                      />
                    </label>
                  )
                })}
              </div>
            )}

            {/* Point Budget Slider */}
            {openSections.layers && (
              <div style={{ padding: '6px 4px 2px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, color: '#94a3b8' }}>LOD Quality</span>
                  <span style={{ fontSize: 10, color: '#38bdf8', fontVariantNumeric: 'tabular-nums' }}>
                    {pointBudget <= 8 ? 'Ultra' : pointBudget <= 16 ? 'High' : pointBudget <= 32 ? 'Medium' : 'Fast'}
                  </span>
                </div>
                <input
                  id="slider-point-budget"
                  type="range" min={4} max={64} step={4}
                  value={pointBudget}
                  onChange={(e) => setPointBudget(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#38bdf8' }}
                />
                {tileStreamingProgress > 0 && tileStreamingProgress < 100 && (
                  <div style={{ marginTop: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#64748b', marginBottom: 2 }}>
                      <span>Streaming tiles…</span>
                      <span>{tileStreamingProgress}%</span>
                    </div>
                    <div style={{ height: 3, background: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${tileStreamingProgress}%`, background: 'linear-gradient(90deg, #38bdf8, #818cf8)', transition: 'width 0.3s' }} />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ── Analysis Section ─────────────────────────────────────── */}
          <div className="sidebar__section">
            <div className="sidebar__section-header" onClick={() => toggleSection('analysis')}>
              <span className="sidebar__section-title">Spatial Analysis</span>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
                {openSections.analysis ? '▲' : '▼'}
              </span>
            </div>

            {openSections.analysis && (
              <>
                {[
                  { id: 'distance', icon: '📏', label: 'Measure Distance', desc: '3D Euclidean & Geodesic' },
                  { id: 'area', icon: '📐', label: 'Measure Area', desc: 'Surface Area & Perimeter' },
                  { id: 'height', icon: '↕️', label: 'Height Difference', desc: 'Vertical Delta Z' },
                  { id: 'profile', icon: '⛰️', label: 'Elevation Profile', desc: 'Transect Line & Chart' },
                  { id: 'slope', icon: '📐', label: 'Slope & Aspect', desc: 'Grade & Facing Analysis' },
                  { id: 'volume', icon: '🗻', label: 'Volume Estimation', desc: 'Cut / Fill Quantities' },
                ].map((item) => {
                  const isActive = activeTool === item.id
                  return (
                    <div
                      key={item.id}
                      className={`analysis-btn ${isActive ? 'analysis-btn--active' : ''}`}
                      onClick={() => setActiveTool(isActive ? 'none' : (item.id as any))}
                      style={{
                        background: isActive ? 'rgba(56, 189, 248, 0.15)' : undefined,
                        borderColor: isActive ? '#38bdf8' : undefined,
                      }}
                    >
                      <span className="analysis-btn__icon">{item.icon}</span>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ color: isActive ? '#38bdf8' : 'inherit', fontWeight: isActive ? 600 : 400 }}>
                          {item.label}
                        </span>
                        <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                          {item.desc}
                        </span>
                      </div>
                      {isActive && (
                        <span
                          style={{
                            marginLeft: 'auto',
                            width: 6,
                            height: 6,
                            borderRadius: '50%',
                            backgroundColor: '#38bdf8',
                          }}
                        />
                      )}
                    </div>
                  )
                })}
              </>
            )}
          </div>

          {/* ── AI Terrain Analyst ─────────────────────────────── */}
          <div className="sidebar__section">
            <div className="sidebar__section-header" onClick={() => toggleSection('ai')}>
              <span className="sidebar__section-title">AI Terrain Analyst</span>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
                {openSections.ai ? '▲' : '▼'}
              </span>
            </div>

            {openSections.ai && activeDataset && (
              <>
                <AITerrainPanel datasetId={activeDataset.id} />
                <button
                  id="btn-sidebar-open-ai-chat"
                  onClick={() => setAiDrawerOpen(true)}
                  className="btn btn--primary btn--sm w-full"
                  style={{
                    marginTop: 6,
                    fontSize: 10,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                    background: 'linear-gradient(135deg, #0284c7, #6366f1)',
                  }}
                >
                  <span>💬</span>
                  <span>Open AI Copilot Chat</span>
                </button>
              </>
            )}
          </div>

          {/* ── GL3D Photogrammetry Scenes ──────────────────────────── */}
          <div className="sidebar__section">
            <div className="sidebar__section-header" onClick={() => toggleSection('gl3d')}>
              <span className="sidebar__section-title">📷 GL3D Scenes</span>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
                {openSections.gl3d ? '▲' : '▼'}
              </span>
            </div>
            {openSections.gl3d && (
              <GL3DPanel />
            )}
          </div>

          {/* ── DALES-2 Classification ──────────────────────────── */}
          {activeDataset?.dataset_type === 'point_cloud' && (
            <div className="sidebar__section">
              <div className="sidebar__section-header" onClick={() => toggleSection('classification')}>
                <span className="sidebar__section-title">🏷️ AI Classification</span>
                <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
                  {openSections.classification ? '▲' : '▼'}
                </span>
              </div>
              {openSections.classification && activeDataset && (
                <ClassificationPanel datasetId={activeDataset.id} />
              )}
            </div>
          )}

        </div>
      </aside>

      {/* ── Create Project Modal ──────────────────────────────────────── */}
      {showCreateModal && (
        <div className="modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal__title">New Project</div>

            <div className="modal__field">
              <label className="modal__label">Project Name *</label>
              <input
                className="input"
                placeholder="My Terrain Survey"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
                autoFocus
              />
            </div>

            <div className="modal__field">
              <label className="modal__label">Location</label>
              <input
                className="input"
                placeholder="e.g. Colorado, USA"
                value={newProjectLoc}
                onChange={(e) => setNewProjectLoc(e.target.value)}
              />
            </div>

            <div className="modal__field">
              <label className="modal__label">Description</label>
              <input
                className="input"
                placeholder="Optional description"
                value={newProjectDesc}
                onChange={(e) => setNewProjectDesc(e.target.value)}
              />
            </div>

            <div className="modal__actions">
              <button className="btn btn--ghost" onClick={() => setShowCreateModal(false)}>
                Cancel
              </button>
              <button
                className="btn btn--primary"
                onClick={handleCreateProject}
                disabled={!newProjectName.trim() || creating}
              >
                {creating ? 'Creating…' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
