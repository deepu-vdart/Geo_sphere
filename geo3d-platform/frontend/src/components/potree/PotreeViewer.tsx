import React, { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useAppStore, useViewerStore } from '../../stores'
import { api, type PotreePoint, type PotreeMetadataResponse } from '../../api/client'
import PotreeProfileWindow from './PotreeProfileWindow'

// Classification Color Palette
const CLS_COLORS: Record<number, [number, number, number]> = {
  0: [0.58, 0.64, 0.72], // Created
  1: [0.80, 0.84, 0.88], // Unclassified
  2: [0.85, 0.47, 0.02], // Ground
  3: [0.52, 0.80, 0.09], // Low veg
  4: [0.13, 0.77, 0.37], // Med veg
  5: [0.08, 0.50, 0.24], // High veg / Tree
  6: [0.94, 0.27, 0.27], // Building
  7: [0.96, 0.62, 0.04], // Noise
  8: [0.92, 0.70, 0.03], // Key-point
  9: [0.22, 0.74, 0.97], // Water
  10: [0.66, 0.33, 0.97], // Rail
  11: [0.39, 0.45, 0.55], // Road
}

// Turbo / Elevation Color Map
function getElevationColor(normZ: number): [number, number, number] {
  const t = Math.max(0, Math.min(1, normZ))
  // Smooth rainbow ramp: Blue -> Cyan -> Green -> Yellow -> Red
  if (t < 0.25) {
    const s = t / 0.25
    return [0.1, 0.2 + 0.6 * s, 0.9]
  } else if (t < 0.5) {
    const s = (t - 0.25) / 0.25
    return [0.1 + 0.1 * s, 0.8, 0.9 - 0.7 * s]
  } else if (t < 0.75) {
    const s = (t - 0.5) / 0.25
    return [0.2 + 0.7 * s, 0.8 + 0.1 * s, 0.1]
  } else {
    const s = (t - 0.75) / 0.25
    return [0.9, 0.9 - 0.7 * s, 0.1]
  }
}

export default function PotreeViewer() {
  const containerRef = useRef<HTMLDivElement>(null)
  const minimapCanvasRef = useRef<HTMLCanvasElement>(null)

  const activeDataset = useAppStore((s) => s.activeDataset)
  const {
    potreeColorMode,
    setPotreeColorMode,
    potreePointBudget,
    setPotreePointBudget,
    potreePointSize,
    setPotreePointSize,
    potreePointSizing,
    setPotreePointSizing,
    potreePointShape,
    setPotreePointShape,
    potreeEdlEnabled,
    togglePotreeEdl,
    potreeEdlRadius,
    setPotreeEdlRadius,
    potreeEdlStrength,
    setPotreeEdlStrength,
    potreeFov,
    setPotreeFov,
    potreeActiveTool,
    setPotreeActiveTool,
    setPotreeProfileOpen,
    setPotreeCrossSectionData,
    potreeCorridorWidth,
    potreeClippingBoxActive,
    setPotreeClippingBoxActive,
    potreeCameraPreset,
    setPotreeCameraPreset,
  } = useViewerStore()

  const [loading, setLoading] = useState<boolean>(true)
  const [pointCount, setPointCount] = useState<number>(0)
  const [datasetCrs, setDatasetCrs] = useState<string>('EPSG:32617')
  const [metadata, setMetadata] = useState<PotreeMetadataResponse | null>(null)
  const [selectedPoint, setSelectedPoint] = useState<PotreePoint | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true)
  const [fps, setFps] = useState<number>(60)

  // Measurement State
  const [measurePoints, setMeasurePoints] = useState<THREE.Vector3[]>([])
  const [measureResult, setMeasureResult] = useState<string | null>(null)

  // Three.js References
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const pointsObjRef = useRef<THREE.Points | null>(null)
  const rawPointsRef = useRef<PotreePoint[]>([])
  const measureLineRef = useRef<THREE.Line | null>(null)
  const clipBoxHelperRef = useRef<THREE.Box3Helper | null>(null)

  // ─── Initialize Three.js Scene ──────────────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const width = container.clientWidth
    const height = container.clientHeight

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a0f1d)
    sceneRef.current = scene

    const camera = new THREE.PerspectiveCamera(potreeFov, width / height, 0.1, 5000)
    camera.position.set(0, -140, 110)
    camera.up.set(0, 0, 1) // Z-up geospatial coordinate convention
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.localClippingEnabled = true
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.screenSpacePanning = false
    controls.maxPolarAngle = Math.PI / 2 + 0.15 // Allow viewing from slightly below horizon
    controlsRef.current = controls

    // Ambient and Directional Lights for surface normals shading
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7)
    scene.add(ambientLight)

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8)
    dirLight.position.set(50, -80, 120)
    scene.add(dirLight)

    // Grid floor helper
    const grid = new THREE.GridHelper(300, 30, 0x334155, 0x1e293b)
    grid.rotation.x = Math.PI / 2
    grid.position.z = -5
    scene.add(grid)

    // FPS Counter & Animation Loop
    let animationId: number
    let lastTime = performance.now()
    let frameCount = 0

    const animate = () => {
      animationId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)

      // Calculate FPS
      frameCount++
      const now = performance.now()
      if (now - lastTime >= 1000) {
        setFps(Math.round((frameCount * 1000) / (now - lastTime)))
        frameCount = 0
        lastTime = now
      }

      // Update minimap
      updateMinimap()
    }
    animate()

    // Handle Window Resize
    const handleResize = () => {
      if (!container || !renderer || !camera) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationId)
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
      renderer.dispose()
    }
  }, [])

  // ─── Fetch Potree Metadata & Point Cloud Data ──────────────────────────────
  const loadPointData = useCallback(async () => {
    if (!activeDataset) return
    setLoading(true)

    try {
      // 1. Fetch metadata
      try {
        const metaRes = await api.getPotreeMetadata(activeDataset.id)
        setMetadata(metaRes.data)
        setDatasetCrs(metaRes.data.projection)
      } catch (err) {
        console.warn('Could not load potree metadata:', err)
      }

      // 2. Fetch high-density stream points
      const res = await api.getPotreePoints(activeDataset.id, potreePointBudget)
      const pts = res.data.points
      rawPointsRef.current = pts
      setPointCount(pts.length)
      if (res.data.crs) setDatasetCrs(res.data.crs)

      // 3. Build Three.js Point Cloud
      updatePointCloudGeometry(pts)
    } catch (err) {
      console.error('Failed to load Potree point cloud:', err)
    } finally {
      setLoading(false)
    }
  }, [activeDataset, potreePointBudget])

  useEffect(() => {
    loadPointData()
  }, [loadPointData])

  // ─── Update Point Cloud Geometry & Shader / Attributes ─────────────────────
  const updatePointCloudGeometry = (points: PotreePoint[]) => {
    const scene = sceneRef.current
    if (!scene) return

    // Remove old point cloud
    if (pointsObjRef.current) {
      scene.remove(pointsObjRef.current)
      pointsObjRef.current.geometry.dispose()
      ;(pointsObjRef.current.material as THREE.Material).dispose()
      pointsObjRef.current = null
    }

    if (points.length === 0) return

    const n = points.length
    const positions = new Float32Array(n * 3)
    const colors = new Float32Array(n * 3)
    const normals = new Float32Array(n * 3)

    // Compute Z range for elevation gradient
    let minZ = Infinity
    let maxZ = -Infinity
    for (let i = 0; i < n; i++) {
      const z = points[i].z
      if (z < minZ) minZ = z
      if (z > maxZ) maxZ = z
    }
    const zRange = Math.max(maxZ - minZ, 1.0)

    for (let i = 0; i < n; i++) {
      const p = points[i]
      const idx = i * 3

      // Position
      positions[idx] = p.x
      positions[idx + 1] = p.y
      positions[idx + 2] = p.z

      // Normal
      normals[idx] = p.nx || 0.0
      normals[idx + 1] = p.ny || 0.0
      normals[idx + 2] = p.nz || 1.0

      // Color based on active potreeColorMode
      let cr = 1, cg = 1, cb = 1
      if (potreeColorMode === 'rgb') {
        cr = p.r / 255
        cg = p.g / 255
        cb = p.b / 255
      } else if (potreeColorMode === 'elevation') {
        const normZ = (p.z - minZ) / zRange
        const [er, eg, eb] = getElevationColor(normZ)
        cr = er; cg = eg; cb = eb
      } else if (potreeColorMode === 'normals') {
        cr = Math.abs(p.nx || 0)
        cg = Math.abs(p.ny || 0)
        cb = Math.abs(p.nz || 1)
      } else if (potreeColorMode === 'classification') {
        const clr = CLS_COLORS[p.classification] || [0.7, 0.7, 0.7]
        cr = clr[0]; cg = clr[1]; cb = clr[2]
      } else if (potreeColorMode === 'intensity') {
        const val = Math.min(1.0, (p.intensity || 128) / 255)
        cr = val; cg = val; cb = val
      }

      // Eye-Dome Lighting (EDL) accentuation
      if (potreeEdlEnabled) {
        const edlFactor = 0.85 + 0.25 * (p.nz || 0.8) * potreeEdlStrength
        cr = Math.min(1.0, cr * edlFactor)
        cg = Math.min(1.0, cg * edlFactor)
        cb = Math.min(1.0, cb * edlFactor)
      }

      colors[idx] = cr
      colors[idx + 1] = cg
      colors[idx + 2] = cb
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
    geometry.computeBoundingBox()

    // Create circular or square point material
    const pointMaterial = new THREE.PointsMaterial({
      size: potreePointSize,
      vertexColors: true,
      sizeAttenuation: potreePointSizing === 'attenuated' || potreePointSizing === 'adaptive',
      transparent: false,
    })

    // Clipping planes if clipping box active
    if (potreeClippingBoxActive) {
      const clipPlanes = [
        new THREE.Plane(new THREE.Vector3(1, 0, 0), 60),
        new THREE.Plane(new THREE.Vector3(-1, 0, 0), 60),
        new THREE.Plane(new THREE.Vector3(0, 1, 0), 50),
        new THREE.Plane(new THREE.Vector3(0, -1, 0), 50),
      ]
      pointMaterial.clippingPlanes = clipPlanes
    }

    const pointsObj = new THREE.Points(geometry, pointMaterial)
    scene.add(pointsObj)
    pointsObjRef.current = pointsObj

    // Center camera on point cloud bounding box
    if (geometry.boundingBox && controlsRef.current && cameraRef.current) {
      const center = new THREE.Vector3()
      geometry.boundingBox.getCenter(center)
      controlsRef.current.target.copy(center)
      cameraRef.current.position.set(center.x, center.y - 120, center.z + 90)
      controlsRef.current.update()
    }
  }

  // Re-color / re-style when visual settings change
  useEffect(() => {
    if (rawPointsRef.current.length > 0) {
      updatePointCloudGeometry(rawPointsRef.current)
    }
  }, [
    potreeColorMode,
    potreePointSize,
    potreePointSizing,
    potreeEdlEnabled,
    potreeEdlStrength,
    potreeClippingBoxActive,
  ])

  // Camera FOV Update
  useEffect(() => {
    if (cameraRef.current) {
      cameraRef.current.fov = potreeFov
      cameraRef.current.updateProjectionMatrix()
    }
  }, [potreeFov])

  // Camera Presets
  const applyCameraPreset = (preset: 'orbit' | 'flight' | 'top' | 'front' | 'isometric') => {
    setPotreeCameraPreset(preset)
    if (!controlsRef.current || !cameraRef.current) return

    const target = controlsRef.current.target
    if (preset === 'top') {
      cameraRef.current.position.set(target.x, target.y, target.z + 160)
    } else if (preset === 'front') {
      cameraRef.current.position.set(target.x, target.y - 160, target.z + 10)
    } else if (preset === 'isometric') {
      cameraRef.current.position.set(target.x - 110, target.y - 110, target.z + 110)
    } else {
      cameraRef.current.position.set(target.x, target.y - 130, target.z + 90)
    }
    controlsRef.current.update()
  }

  // ─── Interactive Mouse Tool Handling ────────────────────────────────────────
  const handleCanvasClick = async (e: React.MouseEvent<HTMLDivElement>) => {
    const container = containerRef.current
    const camera = cameraRef.current
    const pointsObj = pointsObjRef.current
    if (!container || !camera || !pointsObj) return

    const rect = container.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1
    const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1

    const raycaster = new THREE.Raycaster()
    raycaster.params.Points = { threshold: 2.5 }
    raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera)

    const intersects = raycaster.intersectObject(pointsObj)
    if (intersects.length === 0) return

    const hit = intersects[0]
    const idx = hit.index
    if (idx === undefined) return

    const pt = rawPointsRef.current[idx]
    if (!pt) return

    const clickedVec = new THREE.Vector3(pt.x, pt.y, pt.z)

    // 1. Tool: Pick Coordinate
    if (potreeActiveTool === 'pick') {
      setSelectedPoint(pt)
    }

    // 2. Tool: Distance Measurement
    else if (potreeActiveTool === 'distance') {
      const nextPts = [...measurePoints, clickedVec]
      setMeasurePoints(nextPts)

      if (nextPts.length >= 2) {
        let totalDist = 0
        for (let i = 0; i < nextPts.length - 1; i++) {
          totalDist += nextPts[i].distanceTo(nextPts[i + 1])
        }
        setMeasureResult(`3D Distance: ${totalDist.toFixed(2)} m`)
        drawMeasurementLine(nextPts)
      }
    }

    // 3. Tool: Vertical Height (Delta Z)
    else if (potreeActiveTool === 'height') {
      const nextPts = [...measurePoints, clickedVec]
      if (nextPts.length === 1) {
        setMeasurePoints(nextPts)
        setMeasureResult('Click top point...')
      } else if (nextPts.length >= 2) {
        const p1 = nextPts[0]
        const p2 = nextPts[1]
        const deltaZ = Math.abs(p2.z - p1.z)
        const dist = p1.distanceTo(p2)
        setMeasurePoints(nextPts.slice(0, 2))
        setMeasureResult(`Height (ΔZ): ${deltaZ.toFixed(2)} m (3D: ${dist.toFixed(2)} m)`)
        drawMeasurementLine([p1, p2])
      }
    }

    // 4. Tool: 2D Cross Section Profile
    else if (potreeActiveTool === 'profile') {
      const nextPts = [...measurePoints, clickedVec]
      if (nextPts.length === 1) {
        setMeasurePoints(nextPts)
        setMeasureResult('Click second point to slice transect...')
      } else if (nextPts.length >= 2) {
        const p1 = nextPts[0]
        const p2 = nextPts[1]
        setMeasurePoints([p1, p2])
        drawMeasurementLine([p1, p2])

        if (activeDataset) {
          try {
            setMeasureResult('Computing 2D cross-section elevation slice...')
            const res = await api.computePotreeCrossSection(
              activeDataset.id,
              { x: p1.x, y: p1.y, z: p1.z },
              { x: p2.x, y: p2.y, z: p2.z },
              potreeCorridorWidth
            )
            setPotreeCrossSectionData(res.data)
            setPotreeProfileOpen(true)
            setMeasureResult(`Transect Sliced: ${res.data.point_count} points along ${res.data.transect_length_m} m`)
          } catch (err) {
            console.error('Failed to compute cross-section:', err)
            setMeasureResult('Error computing cross-section')
          }
        }
      }
    }
  }

  // Draw 3D measurement indicator line
  const drawMeasurementLine = (pts: THREE.Vector3[]) => {
    const scene = sceneRef.current
    if (!scene) return

    if (measureLineRef.current) {
      scene.remove(measureLineRef.current)
      measureLineRef.current.geometry.dispose()
      ;(measureLineRef.current.material as THREE.Material).dispose()
      measureLineRef.current = null
    }

    const lineGeom = new THREE.BufferGeometry().setFromPoints(pts)
    const lineMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 2.5 })
    const line = new THREE.Line(lineGeom, lineMat)
    scene.add(line)
    measureLineRef.current = line
  }

  const clearTools = () => {
    setPotreeActiveTool('none')
    setMeasurePoints([])
    setMeasureResult(null)
    setSelectedPoint(null)
    const scene = sceneRef.current
    if (scene && measureLineRef.current) {
      scene.remove(measureLineRef.current)
      measureLineRef.current = null
    }
  }

  // ─── 2D Minimap Synchronization ─────────────────────────────────────────────
  const updateMinimap = () => {
    const canvas = minimapCanvasRef.current
    const camera = cameraRef.current
    const controls = controlsRef.current
    if (!canvas || !camera || !controls) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const w = canvas.width
    const h = canvas.height
    ctx.clearRect(0, 0, w, h)

    // Background
    ctx.fillStyle = '#0f172a'
    ctx.fillRect(0, 0, w, h)

    // Boundary frame
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)'
    ctx.strokeRect(10, 10, w - 20, h - 20)

    // Target point (center)
    const target = controls.target
    const mapCenterX = w / 2 + (target.x / 180) * (w / 2 - 20)
    const mapCenterY = h / 2 - (target.y / 160) * (h / 2 - 20)

    // Camera position on minimap
    const camX = w / 2 + (camera.position.x / 180) * (w / 2 - 20)
    const camY = h / 2 - (camera.position.y / 160) * (h / 2 - 20)

    // Draw view frustum line
    ctx.beginPath()
    ctx.moveTo(camX, camY)
    ctx.lineTo(mapCenterX, mapCenterY)
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.7)'
    ctx.lineWidth = 1.5
    ctx.stroke()

    // Draw camera eye
    ctx.beginPath()
    ctx.arc(camX, camY, 4, 0, Math.PI * 2)
    ctx.fillStyle = '#f43f5e'
    ctx.fill()

    // Draw center target dot
    ctx.beginPath()
    ctx.arc(mapCenterX, mapCenterY, 3, 0, Math.PI * 2)
    ctx.fillStyle = '#38bdf8'
    ctx.fill()
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        background: '#0a0f1d',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      {/* 3D WebGL Canvas */}
      <div
        ref={containerRef}
        onClick={handleCanvasClick}
        style={{
          width: '100%',
          height: '100%',
          cursor: potreeActiveTool !== 'none' ? 'crosshair' : 'grab',
        }}
      />

      {/* Loading Overlay */}
      {loading && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(10, 15, 29, 0.85)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(8px)',
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              border: '3px solid rgba(56, 189, 248, 0.2)',
              borderTopColor: '#38bdf8',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              marginBottom: 16,
            }}
          />
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: 14 }}>
            Streaming COPC Octree Point Cloud…
          </div>
          <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 4 }}>
            Eye-Dome Lighting & Normals Shading Initializing
          </div>
        </div>
      )}

      {/* Top HUD Badge: DroneDB / Potree Engine Indicator */}
      <div
        style={{
          position: 'absolute',
          top: 14,
          left: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          borderRadius: 8,
          padding: '6px 14px',
          color: '#f8fafc',
          fontSize: 12,
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
          zIndex: 50,
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#10b981',
            boxShadow: '0 0 8px #10b981',
          }}
        />
        <strong style={{ letterSpacing: '0.02em', color: '#38bdf8' }}>POTREE 1.8+ / COPC INSPECTOR</strong>
        <span style={{ color: '#64748b' }}>|</span>
        <span>{pointCount.toLocaleString()} pts</span>
        <span style={{ color: '#64748b' }}>|</span>
        <span>{datasetCrs}</span>
        <span style={{ color: '#64748b' }}>|</span>
        <span style={{ color: '#a855f7' }}>{fps} FPS</span>
      </div>

      {/* Left Potree Controls Sidebar */}
      <div
        style={{
          position: 'absolute',
          top: 56,
          left: 16,
          width: sidebarOpen ? 270 : 42,
          maxHeight: 'calc(100% - 90px)',
          background: 'rgba(15, 23, 42, 0.92)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: 10,
          boxShadow: '0 12px 32px rgba(0,0,0,0.6)',
          zIndex: 60,
          display: 'flex',
          flexDirection: 'column',
          transition: 'width 0.25s ease',
          overflow: 'hidden',
          color: '#f8fafc',
          fontSize: 11,
        }}
      >
        {/* Sidebar Header & Toggle */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 12px',
            background: 'rgba(30, 41, 59, 0.7)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          {sidebarOpen ? (
            <span style={{ fontWeight: 700, color: '#e2e8f0', letterSpacing: '0.04em' }}>
              POTREE CONTROLS
            </span>
          ) : (
            <span>⚙️</span>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        {sidebarOpen && (
          <div style={{ padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Color Mode */}
            <div>
              <label style={{ display: 'block', fontWeight: 600, color: '#94a3b8', marginBottom: 6 }}>
                COLOR MODE
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 5 }}>
                {[
                  { id: 'rgb', label: 'True RGB' },
                  { id: 'elevation', label: 'Elevation' },
                  { id: 'normals', label: 'Normals' },
                  { id: 'classification', label: 'Classes' },
                  { id: 'intensity', label: 'Intensity' },
                ].map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => setPotreeColorMode(mode.id as any)}
                    style={{
                      padding: '5px 8px',
                      borderRadius: 4,
                      fontSize: 10,
                      fontWeight: 600,
                      cursor: 'pointer',
                      border: potreeColorMode === mode.id ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                      background: potreeColorMode === mode.id ? 'rgba(56, 189, 248, 0.25)' : 'rgba(255,255,255,0.04)',
                      color: potreeColorMode === mode.id ? '#38bdf8' : '#cbd5e1',
                    }}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Eye-Dome Lighting (EDL) */}
            <div style={{ background: 'rgba(255,255,255,0.03)', padding: 8, borderRadius: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontWeight: 600, color: '#94a3b8' }}>EYE-DOME LIGHTING (EDL)</span>
                <input
                  type="checkbox"
                  checked={potreeEdlEnabled}
                  onChange={togglePotreeEdl}
                  style={{ cursor: 'pointer' }}
                />
              </div>
              {potreeEdlEnabled && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748b' }}>
                    <span>EDL Strength</span>
                    <span>{potreeEdlStrength.toFixed(1)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.2"
                    max="2.5"
                    step="0.1"
                    value={potreeEdlStrength}
                    onChange={(e) => setPotreeEdlStrength(parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: '#38bdf8', cursor: 'pointer' }}
                  />
                </div>
              )}
            </div>

            {/* Point Sizing & Budget */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: '#94a3b8' }}>Point Size:</span>
                <strong>{potreePointSize} px</strong>
              </div>
              <input
                type="range"
                min="1"
                max="8"
                step="1"
                value={potreePointSize}
                onChange={(e) => setPotreePointSize(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: '#38bdf8', cursor: 'pointer' }}
              />

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, marginBottom: 4 }}>
                <span style={{ color: '#94a3b8' }}>Point Budget:</span>
                <strong>{(potreePointBudget / 1000).toFixed(0)}k</strong>
              </div>
              <input
                type="range"
                min="30000"
                max="300000"
                step="10000"
                value={potreePointBudget}
                onChange={(e) => setPotreePointBudget(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: '#38bdf8', cursor: 'pointer' }}
              />
            </div>

            {/* Measurement & Inspection Tools */}
            <div>
              <label style={{ display: 'block', fontWeight: 600, color: '#94a3b8', marginBottom: 6 }}>
                MEASUREMENT & TOOLS
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {[
                  { id: 'pick', label: '🎯 Pick Point Coordinate' },
                  { id: 'distance', label: '📏 3D Distance' },
                  { id: 'height', label: '📐 Vertical Delta (ΔZ)' },
                  { id: 'profile', label: '📈 2D Cross Section Profile' },
                ].map((tool) => (
                  <button
                    key={tool.id}
                    onClick={() => {
                      if (potreeActiveTool === tool.id) {
                        clearTools()
                      } else {
                        setPotreeActiveTool(tool.id as any)
                        setMeasurePoints([])
                        setMeasureResult(null)
                      }
                    }}
                    style={{
                      padding: '6px 10px',
                      borderRadius: 4,
                      fontSize: 11,
                      textAlign: 'left',
                      fontWeight: 600,
                      cursor: 'pointer',
                      border: potreeActiveTool === tool.id ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.08)',
                      background: potreeActiveTool === tool.id ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255,255,255,0.02)',
                      color: potreeActiveTool === tool.id ? '#38bdf8' : '#e2e8f0',
                    }}
                  >
                    {tool.label}
                  </button>
                ))}

                {potreeActiveTool !== 'none' && (
                  <button
                    onClick={clearTools}
                    style={{
                      marginTop: 4,
                      padding: '4px',
                      borderRadius: 4,
                      background: 'rgba(239, 68, 68, 0.2)',
                      border: '1px solid #ef4444',
                      color: '#fca5a5',
                      fontSize: 10,
                      cursor: 'pointer',
                    }}
                  >
                    Clear Active Tool
                  </button>
                )}
              </div>
            </div>

            {/* Camera Presets */}
            <div>
              <label style={{ display: 'block', fontWeight: 600, color: '#94a3b8', marginBottom: 6 }}>
                CAMERA PRESETS
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 4 }}>
                {[
                  { id: 'orbit', label: 'Orbit' },
                  { id: 'top', label: 'Top' },
                  { id: 'front', label: 'Front' },
                  { id: 'isometric', label: 'Iso' },
                ].map((cam) => (
                  <button
                    key={cam.id}
                    onClick={() => applyCameraPreset(cam.id as any)}
                    style={{
                      padding: '4px 6px',
                      borderRadius: 4,
                      fontSize: 10,
                      cursor: 'pointer',
                      border: potreeCameraPreset === cam.id ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                      background: 'rgba(255,255,255,0.04)',
                      color: '#cbd5e1',
                    }}
                  >
                    {cam.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Active Measurement Tool Status Banner */}
      {measureResult && (
        <div
          style={{
            position: 'absolute',
            top: 14,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid #38bdf8',
            borderRadius: 8,
            padding: '6px 18px',
            color: '#38bdf8',
            fontWeight: 600,
            fontSize: 12,
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
            zIndex: 80,
          }}
        >
          {measureResult}
        </div>
      )}

      {/* Coordinate Pick Tooltip / Inspector Card */}
      {selectedPoint && (
        <div
          style={{
            position: 'absolute',
            top: 70,
            right: 20,
            width: 250,
            background: 'rgba(15, 23, 42, 0.94)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(56, 189, 248, 0.4)',
            borderRadius: 8,
            padding: 12,
            color: '#f8fafc',
            fontSize: 11,
            boxShadow: '0 12px 30px rgba(0,0,0,0.6)',
            zIndex: 90,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <strong style={{ color: '#38bdf8' }}>Point Coordinate Inspector</strong>
            <button
              onClick={() => setSelectedPoint(null)}
              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div><span style={{ color: '#94a3b8' }}>X (Local): </span>{selectedPoint.x.toFixed(3)} m</div>
            <div><span style={{ color: '#94a3b8' }}>Y (Local): </span>{selectedPoint.y.toFixed(3)} m</div>
            <div><span style={{ color: '#94a3b8' }}>Z (Elev): </span><strong style={{ color: '#38bdf8' }}>{selectedPoint.z.toFixed(3)} m</strong></div>
            {selectedPoint.lon && <div><span style={{ color: '#94a3b8' }}>Lon/Lat: </span>{selectedPoint.lon.toFixed(6)}, {selectedPoint.lat?.toFixed(6)}</div>}
            <div><span style={{ color: '#94a3b8' }}>RGB: </span>rgb({selectedPoint.r}, {selectedPoint.g}, {selectedPoint.b})</div>
            <div><span style={{ color: '#94a3b8' }}>Normal: </span>({selectedPoint.nx?.toFixed(2)}, {selectedPoint.ny?.toFixed(2)}, {selectedPoint.nz?.toFixed(2)})</div>
            <div><span style={{ color: '#94a3b8' }}>Class: </span>{selectedPoint.classification}</div>
          </div>
        </div>
      )}

      {/* Integrated 2D Minimap in bottom right */}
      <div
        style={{
          position: 'absolute',
          bottom: 20,
          right: 20,
          width: 140,
          height: 140,
          background: 'rgba(15, 23, 42, 0.9)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          borderRadius: 8,
          boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
          zIndex: 50,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            padding: '3px 6px',
            background: 'rgba(30, 41, 59, 0.8)',
            color: '#94a3b8',
            letterSpacing: '0.05em',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          2D MINIMAP
        </div>
        <canvas
          ref={minimapCanvasRef}
          width={140}
          height={115}
          style={{ display: 'block', width: '100%', height: '115px' }}
        />
      </div>

      {/* 2D Elevation Cross-Section Profile Window Overlay */}
      <PotreeProfileWindow />
    </div>
  )
}
