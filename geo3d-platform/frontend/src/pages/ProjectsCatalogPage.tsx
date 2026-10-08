import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../stores'
import { type Dataset, type Project } from '../api/client'

export default function ProjectsCatalogPage() {
  const navigate = useNavigate()
  const {
    projects,
    activeProject,
    selectProject,
    datasets,
    activeDataset,
    selectDataset,
    createProject,
    triggerProcessing,
  } = useAppStore()

  const [filterType, setFilterType] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDesc, setNewProjectDesc] = useState('')

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim()) return
    const created = await createProject(newProjectName.trim(), newProjectDesc.trim())
    if (created) {
      selectProject(created)
      setShowNewProjectModal(false)
      setNewProjectName('')
      setNewProjectDesc('')
    }
  }

  const filteredDatasets = datasets.filter((d) => {
    const matchesSearch =
      d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (d.file_format || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (d.dataset_type || '').toLowerCase().includes(searchQuery.toLowerCase())

    if (!matchesSearch) return false
    if (filterType === 'all') return true
    if (filterType === 'photogrammetry') return d.dataset_type === 'photogrammetry' || d.dataset_type === 'gl3d_scene'
    if (filterType === 'point_cloud') return d.dataset_type === 'point_cloud'
    if (filterType === 'raster') return d.dataset_type === 'raster' || d.dataset_type === 'dem'
    return true
  })

  const totalPoints = datasets.reduce((sum, d) => sum + (d.point_count || 0), 0)

  const openViewer = (dataset: Dataset, path: string) => {
    selectDataset(dataset)
    navigate(`${path}?dataset=${dataset.id}`)
  }

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'photogrammetry':
        return { label: 'Drone Photogrammetry', bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', icon: '📸' }
      case 'gl3d_scene':
        return { label: '3D Urban SfM Scene', bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', icon: '🏢' }
      case 'point_cloud':
        return { label: 'LiDAR Point Cloud', bg: 'rgba(52, 211, 153, 0.15)', color: '#34d399', icon: '🛰️' }
      default:
        return { label: type.toUpperCase(), bg: 'rgba(255, 255, 255, 0.1)', color: '#cbd5e1', icon: '📦' }
    }
  }

  return (
    <div
      style={{
        minHeight: 'calc(100vh - 48px)',
        background: '#090d16',
        color: '#f8fafc',
        padding: '24px 32px',
        overflowY: 'auto',
      }}
    >
      {/* ── Top Header & Stats Overview ───────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 24,
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, letterSpacing: -0.5 }}>
            Geospatial Digital Twin Catalog
          </h1>
          <p style={{ margin: '4px 0 0', color: '#94a3b8', fontSize: 13 }}>
            Manage LiDAR point clouds, multi-view drone photogrammetry, and 3D urban models.
          </p>
        </div>

        {/* Global Stats Cards */}
        <div style={{ display: 'flex', gap: 12 }}>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
              borderRadius: 8,
              padding: '8px 16px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 18, fontWeight: 700, color: '#38bdf8' }}>{projects.length}</div>
            <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase' }}>Projects</div>
          </div>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(52, 211, 153, 0.2)',
              borderRadius: 8,
              padding: '8px 16px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 18, fontWeight: 700, color: '#34d399' }}>{datasets.length}</div>
            <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase' }}>Datasets</div>
          </div>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
              borderRadius: 8,
              padding: '8px 16px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 18, fontWeight: 700, color: '#c084fc' }}>
              {(totalPoints / 1_000_000).toFixed(1)}M
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase' }}>Points</div>
          </div>
          <button
            onClick={() => setShowNewProjectModal(true)}
            style={{
              background: 'linear-gradient(135deg, #0284c7, #0ea5e9)',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              padding: '8px 16px',
              fontWeight: 600,
              fontSize: 12,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              boxShadow: '0 0 12px rgba(14, 165, 233, 0.3)',
            }}
          >
            <span>+</span>
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* ── Project Filter Strip ────────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          alignItems: 'center',
          overflowX: 'auto',
          paddingBottom: 12,
          marginBottom: 16,
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', marginRight: 4 }}>
          Project:
        </span>
        {projects.map((p) => {
          const isSelected = activeProject?.id === p.id
          return (
            <button
              key={p.id}
              onClick={() => selectProject(p)}
              style={{
                background: isSelected ? 'rgba(56, 189, 248, 0.2)' : 'rgba(15, 23, 42, 0.6)',
                border: `1px solid ${isSelected ? 'rgba(56, 189, 248, 0.5)' : 'rgba(255, 255, 255, 0.08)'}`,
                color: isSelected ? '#38bdf8' : '#94a3b8',
                borderRadius: 20,
                padding: '4px 12px',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              {p.name}
            </button>
          )
        })}
      </div>

      {/* ── Search & Filter Controls ────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        {/* Type Filter Tabs */}
        <div style={{ display: 'flex', gap: 6 }}>
          {[
            { id: 'all', label: 'All Datasets' },
            { id: 'photogrammetry', label: '📸 Drone & Photogrammetry' },
            { id: 'point_cloud', label: '🛰️ LiDAR Point Cloud' },
            { id: 'raster', label: '🗺️ Raster / DEM' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id)}
              style={{
                background: filterType === tab.id ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                border: `1px solid ${filterType === tab.id ? 'rgba(56, 189, 248, 0.4)' : 'rgba(255, 255, 255, 0.06)'}`,
                color: filterType === tab.id ? '#38bdf8' : '#94a3b8',
                borderRadius: 6,
                padding: '6px 12px',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Bar */}
        <input
          type="text"
          placeholder="🔍 Search datasets by name, format, or type…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            background: 'rgba(15, 23, 42, 0.8)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: 6,
            color: '#f8fafc',
            padding: '6px 14px',
            fontSize: 12,
            width: 280,
            outline: 'none',
          }}
        />
      </div>

      {/* ── Datasets Cards Grid ─────────────────────────────────────────────── */}
      {filteredDatasets.length === 0 ? (
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.4)',
            border: '1px dashed rgba(255, 255, 255, 0.1)',
            borderRadius: 12,
            padding: 48,
            textAlign: 'center',
            color: '#64748b',
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#94a3b8' }}>No datasets found</div>
          <p style={{ fontSize: 12, margin: '4px 0 0' }}>Select another project or adjust your filter query.</p>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
            gap: 20,
          }}
        >
          {filteredDatasets.map((dataset) => {
            const badge = getTypeBadge(dataset.dataset_type)
            const meta = (dataset.metadata_json as any) || {}
            const anchor = meta.anchor || {}
            const isSelected = activeDataset?.id === dataset.id
            const isDrone = dataset.dataset_type === 'photogrammetry' || dataset.dataset_type === 'gl3d_scene'

            return (
              <div
                key={dataset.id}
                style={{
                  background: isSelected ? 'rgba(15, 23, 42, 0.95)' : 'rgba(15, 23, 42, 0.7)',
                  border: isSelected
                    ? '1px solid rgba(56, 189, 248, 0.5)'
                    : '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 10,
                  padding: 18,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 14,
                  boxShadow: isSelected ? '0 0 20px rgba(56, 189, 248, 0.15)' : 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                {/* Header: Title & Badges */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: 4,
                          background: badge.bg,
                          color: badge.color,
                        }}
                      >
                        {badge.icon} {badge.label}
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          padding: '2px 6px',
                          borderRadius: 4,
                          background: 'rgba(255, 255, 255, 0.06)',
                          color: '#94a3b8',
                          fontWeight: 600,
                        }}
                      >
                        {(dataset.file_format || 'MESH').toUpperCase()}
                      </span>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9' }}>
                      {dataset.name}
                    </div>
                  </div>

                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: dataset.processing_status === 'ready' ? '#34d399' : '#f59e0b',
                      flexShrink: 0,
                      marginTop: 4,
                    }}
                    title={`Status: ${dataset.processing_status}`}
                  />
                </div>

                {/* Metadata Details Grid */}
                <div
                  style={{
                    background: 'rgba(0, 0, 0, 0.25)',
                    borderRadius: 6,
                    padding: '10px 12px',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 8,
                    fontSize: 11,
                  }}
                >
                  <div>
                    <span style={{ color: '#64748b' }}>Points: </span>
                    <span style={{ color: '#e2e8f0', fontWeight: 600 }}>
                      {dataset.point_count ? dataset.point_count.toLocaleString() : 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>CRS: </span>
                    <span style={{ color: '#38bdf8', fontWeight: 600 }}>{dataset.crs || 'EPSG:32617'}</span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Elevation: </span>
                    <span style={{ color: '#e2e8f0' }}>
                      {dataset.min_z !== null && dataset.max_z !== null
                        ? `${dataset.min_z.toFixed(0)}m – ${dataset.max_z.toFixed(0)}m`
                        : 'Local SfM'}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: '#64748b' }}>Cameras: </span>
                    <span style={{ color: '#e2e8f0' }}>
                      {meta.camera_count || meta.cameras?.length || (meta.image_count ? `${meta.image_count} photos` : 'Aerial Scan')}
                    </span>
                  </div>
                </div>

                {/* Dedicated Action Buttons */}
                <div style={{ display: 'grid', gridTemplateColumns: isDrone ? '1fr 1fr' : '1fr 1fr', gap: 8, marginTop: 'auto' }}>
                  {isDrone ? (
                    <button
                      onClick={() => openViewer(dataset, '/photogrammetry')}
                      style={{
                        background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(14, 165, 233, 0.35))',
                        border: '1px solid rgba(56, 189, 248, 0.4)',
                        color: '#38bdf8',
                        borderRadius: 6,
                        padding: '7px 10px',
                        fontSize: 11,
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6,
                        boxShadow: '0 0 10px rgba(56, 189, 248, 0.15)',
                      }}
                    >
                      <span>📸</span>
                      <span>Split View (Images ↔ 3D)</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => openViewer(dataset, '/potree')}
                      style={{
                        background: 'rgba(52, 211, 153, 0.15)',
                        border: '1px solid rgba(52, 211, 153, 0.3)',
                        color: '#34d399',
                        borderRadius: 6,
                        padding: '7px 10px',
                        fontSize: 11,
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6,
                      }}
                    >
                      <span>⚡</span>
                      <span>Point Cloud (Potree)</span>
                    </button>
                  )}

                  <button
                    onClick={() => openViewer(dataset, '/viewer')}
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      color: '#f8fafc',
                      borderRadius: 6,
                      padding: '7px 10px',
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6,
                    }}
                  >
                    <span>🌐</span>
                    <span>3D Globe Viewer</span>
                  </button>

                  <button
                    onClick={() => openViewer(dataset, '/dual')}
                    style={{
                      background: 'rgba(168, 85, 247, 0.12)',
                      border: '1px solid rgba(168, 85, 247, 0.25)',
                      color: '#c084fc',
                      borderRadius: 6,
                      padding: '5px 8px',
                      fontSize: 10,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 4,
                    }}
                  >
                    <span>◫</span>
                    <span>Dual Sync View</span>
                  </button>

                  <button
                    onClick={() => openViewer(dataset, '/analysis')}
                    style={{
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      color: '#94a3b8',
                      borderRadius: 6,
                      padding: '5px 8px',
                      fontSize: 10,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 4,
                    }}
                  >
                    <span>📊</span>
                    <span>Terrain Analysis</span>
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── New Project Modal ───────────────────────────────────────────────── */}
      {showNewProjectModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            backdropFilter: 'blur(6px)',
          }}
        >
          <form
            onSubmit={handleCreateProject}
            style={{
              background: '#0f172a',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: 12,
              padding: 24,
              width: 400,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
              boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9' }}>Create New Project</div>
            <div>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Project Name
              </label>
              <input
                type="text"
                required
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="e.g. Alpine Dam Survey 2026"
                style={{
                  width: '100%',
                  background: '#1e293b',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 6,
                  color: '#fff',
                  padding: '8px 12px',
                  fontSize: 12,
                  outline: 'none',
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: 11, color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Description (optional)
              </label>
              <textarea
                value={newProjectDesc}
                onChange={(e) => setNewProjectDesc(e.target.value)}
                rows={3}
                placeholder="Photogrammetry and LiDAR digital twin..."
                style={{
                  width: '100%',
                  background: '#1e293b',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 6,
                  color: '#fff',
                  padding: '8px 12px',
                  fontSize: 12,
                  outline: 'none',
                  resize: 'none',
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
              <button
                type="button"
                onClick={() => setShowNewProjectModal(false)}
                style={{
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.15)',
                  color: '#94a3b8',
                  padding: '6px 14px',
                  borderRadius: 6,
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                style={{
                  background: '#0284c7',
                  border: 'none',
                  color: '#fff',
                  padding: '6px 16px',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Create Project
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
