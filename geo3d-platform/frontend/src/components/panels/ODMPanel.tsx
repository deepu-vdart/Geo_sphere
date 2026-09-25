import { useState, useEffect, useCallback, useRef } from 'react'
import { useAppStore, useViewerStore } from '../../stores'
import { api, type ODMTaskResponse } from '../../api/client'

const STATUS_COLORS: Record<string, string> = {
  QUEUED: '#f59e0b',
  RUNNING: '#3b82f6',
  COMPLETED: '#10b981',
  FAILED: '#ef4444',
  CANCELLED: '#6b7280',
}

const STATUS_ICONS: Record<string, string> = {
  QUEUED: '⏳',
  RUNNING: '⚙️',
  COMPLETED: '✅',
  FAILED: '❌',
  CANCELLED: '🚫',
}

export default function ODMPanel() {
  const { activeProject } = useAppStore()
  const {
    odmHealth, odmTasks, odmUploadProgress,
    loadOdmHealth, loadOdmTasks, refreshOdmTask,
    setOdmUploadProgress,
    setSplitCompareMode,
  } = useViewerStore()


  const [dragActive, setDragActive] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [taskName, setTaskName] = useState('Drone Survey')
  const [featureQuality, setFeatureQuality] = useState('high')
  const [generateDsm, setGenerateDsm] = useState(true)
  const [generateDtm, setGenerateDtm] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [loadingPreset, setLoadingPreset] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadOdmHealth()
    if (activeProject) {
      loadOdmTasks(activeProject.id)
    }
  }, [activeProject])

  // Poll running tasks
  useEffect(() => {
    const running = odmTasks.filter((t) => t.status === 'RUNNING' || t.status === 'QUEUED')
    if (running.length === 0) return

    const interval = setInterval(() => {
      running.forEach((t) => refreshOdmTask(t.task_id || t.job_id || ''))
    }, 5000)

    return () => clearInterval(interval)
  }, [odmTasks])

  const handleLoadAukermanPreset = async () => {
    if (!activeProject) {
      setError('Please select or create an active project first.')
      return
    }
    setLoadingPreset(true)
    setError(null)
    try {
      const res = await api.odmLoadAukermanPreset(activeProject.id)
      setSuccess('Loaded DroneDB Aukerman Benchmark dataset!')
      await useAppStore.getState().loadDatasets(activeProject.id)
      const datasets = useAppStore.getState().datasets
      const aukermanDs = datasets.find((d) => d.id === res.data.dataset_id || d.name.includes('Aukerman'))
      if (aukermanDs) {
        useAppStore.getState().selectDataset(aukermanDs)
        useViewerStore.getState().setShowDroneCameras(true)
        useViewerStore.getState().setPointCloudColorMode('rgb')
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load Aukerman preset')
    } finally {
      setLoadingPreset(false)
    }
  }

  const handleViewPointCloud = async (taskId: string) => {
    if (!activeProject) return
    try {
      await useAppStore.getState().loadDatasets(activeProject.id)
      const datasets = useAppStore.getState().datasets
      const ds = datasets.find((d) => {
        const meta = d.metadata_json as any
        return meta?.odm_task_id === taskId || d.name.includes(taskId.substring(0, 6))
      })
      if (ds) {
        useAppStore.getState().selectDataset(ds)
        useViewerStore.getState().setShowDroneCameras(true)
        useViewerStore.getState().setPointCloudColorMode('rgb')
        setSuccess(`Now viewing 3D Point Cloud for ${ds.name}`)
      } else {
        await handleImport(taskId)
      }
    } catch {
      setError('Could not open point cloud viewer')
    }
  }

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      /\.(jpg|jpeg|png|tif|tiff)$/i.test(f.name)
    )
    if (files.length > 0) {
      setSelectedFiles((prev) => [...prev, ...files])
      setError(null)
    }
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length > 0) {
      setSelectedFiles((prev) => [...prev, ...files])
      setError(null)
    }
  }

  const removeFile = (idx: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx))
  }

  const clearFiles = () => {
    setSelectedFiles([])
    setError(null)
    setSuccess(null)
  }

  const handleUpload = async () => {
    if (!activeProject) {
      setError('Select a project first')
      return
    }
    if (selectedFiles.length < 2) {
      setError('At least 2 images are required for photogrammetry')
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(null)
    setOdmUploadProgress(0)

    try {
      const res = await api.odmCreateTask(
        activeProject.id,
        selectedFiles,
        taskName,
        {
          feature_quality: featureQuality,
          generate_dsm: generateDsm,
          generate_dtm: generateDtm,
        }
      )

      setSuccess(`Task created! ID: ${res.data.task_id?.substring(0, 8)}...`)
      setSelectedFiles([])
      setOdmUploadProgress(100)

      // Refresh task list
      setTimeout(() => loadOdmTasks(activeProject.id), 1000)
    } catch (e: any) {
      const detail = e.response?.data?.detail || e.message || 'Upload failed'
      setError(detail)
    } finally {
      setUploading(false)
    }
  }

  const handleImport = async (taskId: string) => {
    try {
      const res = await api.odmImportResults(taskId)
      if (res.data.dataset_id) {
        setSuccess(`Results imported as dataset ${res.data.dataset_id.substring(0, 8)}...`)
        // Refresh datasets
        if (activeProject) {
          useAppStore.getState().loadDatasets(activeProject.id)
        }
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Import failed')
    }
  }

  const handleDelete = async (taskId: string) => {
    try {
      await api.odmDeleteTask(taskId)
      if (activeProject) loadOdmTasks(activeProject.id)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Delete failed')
    }
  }

  const totalSize = selectedFiles.reduce((s, f) => s + f.size, 0)
  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '4px 0' }}>

      {/* ── WebODM Status ────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 8px',
        background: 'rgba(255,255,255,0.03)',
        borderRadius: 6,
        fontSize: 11,
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: odmHealth?.connected ? '#10b981' : odmHealth?.mock_mode ? '#f59e0b' : '#ef4444',
          boxShadow: `0 0 6px ${odmHealth?.connected ? '#10b981' : odmHealth?.mock_mode ? '#f59e0b55' : '#ef444455'}`,
        }} />
        <span style={{ color: '#cbd5e1', flex: 1 }}>
          {odmHealth?.connected ? 'WebODM Connected' : odmHealth?.mock_mode ? 'Demo Mode (Local Photogrammetry)' : 'Disconnected'}
        </span>
        {odmHealth && (
          <span style={{ color: '#64748b', fontSize: 10 }}>
            {odmHealth.node_count} node{odmHealth.node_count !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* ── DroneDB Aukerman Benchmark Preset ────────────── */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(56,189,248,0.12), rgba(99,102,241,0.08))',
        border: '1px solid rgba(56,189,248,0.3)',
        borderRadius: 8,
        padding: '10px 12px',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 16 }}>🛰️</span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
                DroneDB Aukerman Benchmark
              </div>
              <div style={{ fontSize: 10, color: '#94a3b8' }}>
                Cleveland, Ohio Aerial Drone Survey
              </div>
            </div>
          </div>
          <span style={{
            fontSize: 9, fontWeight: 600, color: '#38bdf8',
            background: 'rgba(56,189,248,0.15)', padding: '2px 6px', borderRadius: 4,
          }}>
            Benchmark
          </span>
        </div>

        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4,
          margin: '4px 0', fontSize: 10, textAlign: 'center',
        }}>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: 4 }}>
            <div style={{ color: '#38bdf8', fontWeight: 600 }}>9.48M</div>
            <div style={{ color: '#64748b', fontSize: 9 }}>Points</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: 4 }}>
            <div style={{ color: '#a855f7', fontWeight: 600 }}>77</div>
            <div style={{ color: '#64748b', fontSize: 9 }}>Drone Photos</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '4px', borderRadius: 4 }}>
            <div style={{ color: '#10b981', fontWeight: 600 }}>2.81 cm</div>
            <div style={{ color: '#64748b', fontSize: 9 }}>GSD Res</div>
          </div>
        </div>

        <button
          onClick={handleLoadAukermanPreset}
          disabled={loadingPreset || !activeProject}
          style={{
            background: 'linear-gradient(90deg, #0284c7, #4f46e5)',
            color: 'white',
            border: 'none',
            borderRadius: 6,
            padding: '7px 10px',
            fontSize: 11,
            fontWeight: 600,
            cursor: activeProject && !loadingPreset ? 'pointer' : 'not-allowed',
            opacity: activeProject && !loadingPreset ? 1 : 0.6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
            boxShadow: '0 2px 8px rgba(2,132,199,0.3)',
            transition: 'all 0.2s ease',
          }}
        >
          {loadingPreset ? '⏳ Loading Benchmark...' : '✨ Load DroneDB Aukerman Point Cloud'}
        </button>
      </div>

      {/* ── Image Upload Zone ────────────────────────────── */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragActive ? '#3b82f6' : '#334155'}`,
          borderRadius: 8,
          padding: selectedFiles.length > 0 ? '8px' : '20px 12px',
          textAlign: 'center',
          cursor: 'pointer',
          background: dragActive ? 'rgba(59,130,246,0.08)' : 'rgba(255,255,255,0.02)',
          transition: 'all 0.2s ease',
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.tif,.tiff"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        {selectedFiles.length === 0 ? (
          <>
            <div style={{ fontSize: 24, marginBottom: 6 }}>📸</div>
            <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
              <strong style={{ color: '#cbd5e1' }}>Drop drone images here</strong><br />
              or click to browse<br />
              <span style={{ fontSize: 10, color: '#64748b' }}>JPG, PNG, TIFF • Min 2 images</span>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'left' }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              marginBottom: 6,
            }}>
              <span style={{ fontSize: 11, color: '#38bdf8', fontWeight: 600 }}>
                📸 {selectedFiles.length} image{selectedFiles.length !== 1 ? 's' : ''} • {formatSize(totalSize)}
              </span>
              <button
                onClick={(e) => { e.stopPropagation(); clearFiles() }}
                style={{
                  background: 'none', border: 'none', color: '#94a3b8',
                  cursor: 'pointer', fontSize: 10, padding: '2px 4px',
                }}
              >
                ✕ Clear
              </button>
            </div>
            <div style={{
              maxHeight: 80, overflow: 'auto', display: 'flex', flexWrap: 'wrap', gap: 4,
            }}>
              {selectedFiles.slice(0, 12).map((f, i) => (
                <div
                  key={i}
                  onClick={(e) => { e.stopPropagation(); removeFile(i) }}
                  style={{
                    fontSize: 9, color: '#94a3b8', background: 'rgba(255,255,255,0.05)',
                    padding: '2px 6px', borderRadius: 4, cursor: 'pointer',
                    maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}
                  title={`${f.name} — click to remove`}
                >
                  {f.name}
                </div>
              ))}
              {selectedFiles.length > 12 && (
                <div style={{ fontSize: 9, color: '#64748b', padding: '2px 6px' }}>
                  +{selectedFiles.length - 12} more
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Processing Options ────────────────────────────── */}
      {selectedFiles.length > 0 && (
        <div style={{
          display: 'flex', flexDirection: 'column', gap: 6,
          background: 'rgba(255,255,255,0.03)', borderRadius: 6, padding: 8,
        }}>
          <input
            className="input"
            value={taskName}
            onChange={(e) => setTaskName(e.target.value)}
            placeholder="Task name"
            style={{ fontSize: 11, padding: '4px 8px' }}
            onClick={(e) => e.stopPropagation()}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            <div>
              <label style={{ fontSize: 9, color: '#64748b', display: 'block', marginBottom: 2 }}>
                Quality
              </label>
              <select
                value={featureQuality}
                onChange={(e) => setFeatureQuality(e.target.value)}
                style={{
                  width: '100%', fontSize: 10, padding: '3px 4px', borderRadius: 4,
                  background: 'rgba(255,255,255,0.06)', color: '#e2e8f0',
                  border: '1px solid rgba(255,255,255,0.1)',
                }}
              >
                <option value="ultra">Ultra</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, justifyContent: 'center' }}>
              <label style={{ fontSize: 9, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                <input type="checkbox" checked={generateDsm} onChange={() => setGenerateDsm(!generateDsm)} style={{ accentColor: '#3b82f6' }} />
                DSM
              </label>
              <label style={{ fontSize: 9, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
                <input type="checkbox" checked={generateDtm} onChange={() => setGenerateDtm(!generateDtm)} style={{ accentColor: '#3b82f6' }} />
                DTM
              </label>
            </div>
          </div>

          <button
            className="btn btn--primary btn--sm w-full"
            onClick={(e) => { e.stopPropagation(); handleUpload() }}
            disabled={uploading || selectedFiles.length < 2 || !activeProject}
            style={{
              fontSize: 11, marginTop: 4,
              background: uploading
                ? 'linear-gradient(135deg, #475569, #334155)'
                : 'linear-gradient(135deg, #0ea5e9, #6366f1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            {uploading ? (
              <>
                <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⚙️</span>
                Uploading...
              </>
            ) : (
              <>🚀 Start Processing ({selectedFiles.length} images)</>
            )}
          </button>
        </div>
      )}

      {/* ── Messages ─────────────────────────────────────── */}
      {error && (
        <div style={{
          fontSize: 10, color: '#fca5a5', background: 'rgba(239,68,68,0.1)',
          padding: '6px 8px', borderRadius: 4, lineHeight: 1.4,
        }}>
          ⚠️ {error}
        </div>
      )}
      {success && (
        <div style={{
          fontSize: 10, color: '#86efac', background: 'rgba(16,185,129,0.1)',
          padding: '6px 8px', borderRadius: 4, lineHeight: 1.4,
        }}>
          ✅ {success}
        </div>
      )}

      {/* ── Task List ────────────────────────────────────── */}
      {odmTasks.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5 }}>
            Tasks ({odmTasks.length})
          </div>

          {odmTasks.map((task) => {
            const statusColor = STATUS_COLORS[task.status] || '#6b7280'
            const statusIcon = STATUS_ICONS[task.status] || '❓'

            return (
              <div
                key={task.task_id || task.job_id}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: 6,
                  padding: '8px 10px',
                  borderLeft: `3px solid ${statusColor}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: '#e2e8f0', fontWeight: 500 }}>
                    {statusIcon} {task.task_name || 'Unnamed Task'}
                  </span>
                  <span style={{
                    fontSize: 9, color: statusColor, fontWeight: 600,
                    padding: '1px 6px', borderRadius: 3,
                    background: `${statusColor}15`,
                  }}>
                    {task.status}
                  </span>
                </div>

                <div style={{ fontSize: 10, color: '#94a3b8', display: 'flex', gap: 12, marginBottom: 4 }}>
                  <span>📸 {task.image_count} images</span>
                  {task.processing_time && (
                    <span>⏱ {task.processing_time.toFixed(0)}s</span>
                  )}
                </div>

                {/* Progress Bar */}
                {(task.status === 'RUNNING' || task.status === 'QUEUED') && (
                  <div style={{
                    width: '100%', height: 4, borderRadius: 2,
                    background: 'rgba(255,255,255,0.08)', marginBottom: 4,
                  }}>
                    <div style={{
                      width: `${task.progress}%`, height: '100%', borderRadius: 2,
                      background: `linear-gradient(90deg, #3b82f6, #6366f1)`,
                      transition: 'width 0.3s ease',
                    }} />
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                  {task.status === 'COMPLETED' && (
                    <>
                      <button
                        onClick={() => handleViewPointCloud(task.task_id || task.job_id || '')}
                        style={{
                          fontSize: 9, padding: '2px 8px', borderRadius: 4, cursor: 'pointer',
                          background: 'linear-gradient(90deg, #0284c7, #2563eb)', color: '#ffffff', border: 'none',
                          fontWeight: 600,
                        }}
                        title="View Reconstructed 3D Point Cloud in Cesium"
                      >
                        🎯 3D Point Cloud
                      </button>
                      <button
                        onClick={() => handleImport(task.task_id || task.job_id || '')}
                        style={{
                          fontSize: 9, padding: '2px 8px', borderRadius: 4, cursor: 'pointer',
                          background: 'rgba(16,185,129,0.15)', color: '#34d399', border: 'none',
                        }}
                      >
                        📥 Import Results
                      </button>
                      <button
                        onClick={() => setSplitCompareMode(true)}
                        style={{
                          fontSize: 9, padding: '2px 8px', borderRadius: 4, cursor: 'pointer',
                          background: 'rgba(56,189,248,0.2)', color: '#38bdf8', border: '1px solid rgba(56,189,248,0.4)',
                          fontWeight: 600,
                        }}
                        title="Open Side-by-Side View: Input Images on Left, 3D Output on Right"
                      >
                        🖼️ Split View
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => handleDelete(task.task_id || task.job_id || '')}
                    style={{
                      fontSize: 9, padding: '2px 8px', borderRadius: 4, cursor: 'pointer',
                      background: 'rgba(239,68,68,0.1)', color: '#f87171', border: 'none',
                    }}
                  >
                    🗑️ Delete
                  </button>

                </div>

                {/* Error Message */}
                {task.error_message && (
                  <div style={{
                    fontSize: 9, color: '#fca5a5', marginTop: 4,
                    background: 'rgba(239,68,68,0.08)', padding: '3px 6px', borderRadius: 3,
                  }}>
                    {task.error_message}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── Empty State ──────────────────────────────────── */}
      {odmTasks.length === 0 && selectedFiles.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '12px 8px',
          color: '#64748b', fontSize: 10, lineHeight: 1.5,
        }}>
          No photogrammetry tasks yet.<br />
          Upload drone images above to get started.
        </div>
      )}
    </div>
  )
}
