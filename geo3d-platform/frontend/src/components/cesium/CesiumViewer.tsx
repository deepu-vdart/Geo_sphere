import { useEffect, useRef, useState, useCallback } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { useViewerStore, useAppStore } from '../../stores'
import { api } from '../../api/client'
import MeasurementOverlay from '../analysis/MeasurementOverlay'
import ElevationProfileChart from '../analysis/ElevationProfileChart'

// Set CesiumJS base URL
// @ts-expect-error - CESIUM_BASE_URL is defined by Vite
window.CESIUM_BASE_URL = '/cesium'

const CESIUM_TOKEN = import.meta.env.VITE_CESIUM_TOKEN || ''

// Color ramps
function getElevationColor(z: number, minZ: number, maxZ: number): Cesium.Color {
  const norm = Math.max(0, Math.min(1, (z - minZ) / Math.max(1, maxZ - minZ)))
  if (norm < 0.25) {
    const t = norm / 0.25
    return new Cesium.Color(0.1, 0.2 + 0.6 * t, 0.8 + 0.2 * t, 1.0)
  } else if (norm < 0.5) {
    const t = (norm - 0.25) / 0.25
    return new Cesium.Color(0.1 + 0.2 * t, 0.8 + 0.2 * t, 0.8 - 0.6 * t, 1.0)
  } else if (norm < 0.75) {
    const t = (norm - 0.5) / 0.25
    return new Cesium.Color(0.3 + 0.6 * t, 1.0 - 0.1 * t, 0.2 - 0.2 * t, 1.0)
  } else {
    const t = (norm - 0.75) / 0.25
    return new Cesium.Color(0.9 + 0.1 * t, 0.9 - 0.7 * t, 0.0, 1.0)
  }
}

const CLASSIFICATION_CESIUM_COLORS: Record<number, Cesium.Color> = {
  0: Cesium.Color.fromCssColorString('#8b5a2b'), // Ground
  1: Cesium.Color.fromCssColorString('#90ee90'), // Vegetation
  2: Cesium.Color.fromCssColorString('#ff4500'), // Car / Ground
  3: Cesium.Color.fromCssColorString('#ffd700'), // Powerline / Low Veg
  4: Cesium.Color.fromCssColorString('#d2691e'), // Fence / Med Veg
  5: Cesium.Color.fromCssColorString('#228b22'), // Tree / High Veg
  6: Cesium.Color.fromCssColorString('#dc143c'), // Building / Pick-up
  7: Cesium.Color.fromCssColorString('#ff1493'), // Van & Truck / Noise
  8: Cesium.Color.fromCssColorString('#8a2be2'), // Heavy-duty Vehicle
  9: Cesium.Color.fromCssColorString('#00ced1'), // Utility Pole / Water
  10: Cesium.Color.fromCssColorString('#1e90ff'), // Light Pole
  11: Cesium.Color.fromCssColorString('#4169e1'), // Traffic Pole / Road
  12: Cesium.Color.fromCssColorString('#dc143c'), // Building
  13: Cesium.Color.fromCssColorString('#f0e68c'), // Wire / Cable
  14: Cesium.Color.fromCssColorString('#a0a0a0'), // Other
}

export default function CesiumViewer() {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<Cesium.Viewer | null>(null)
  const pointPrimitiveCollectionRef = useRef<Cesium.PointPrimitiveCollection | null>(null)
  const activeTilesetRef = useRef<Cesium.Cesium3DTileset | null>(null)
  const measurementEntitiesRef = useRef<Cesium.Entity[]>([])
  const hoverMarkerEntityRef = useRef<Cesium.Entity | null>(null)
  const aiMarkerPinEntityRef = useRef<Cesium.Entity | null>(null)
  const gl3dCameraEntitiesRef = useRef<Cesium.Entity[]>([])
  const gl3dModelEntityRef = useRef<Cesium.Entity | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const {
    setCameraPosition,
    setCursorCoords,
    setFps,
    setSelectedObject,
    pointCloudColorMode,
    pointSize,
    flyToTarget,
    setFlyToTarget,
    layers,
    activeTool,
    measurementPoints,
    addMeasurementPoint,
    setAnalysisResult,
    analysisResult,
    hoverProfileDistance,
    setActiveTool,
    pointBudget,
    setTileStreamingProgress,
    showMapBackground,
    showDroneCameras,
  } = useViewerStore()

  const activeDataset = useAppStore((s) => s.activeDataset)

  // ── Initialize Cesium Viewer ───────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || viewerRef.current) return

    try {
      if (CESIUM_TOKEN) {
        Cesium.Ion.defaultAccessToken = CESIUM_TOKEN
      }

      // High-resolution satellite imagery (free, CORS-enabled, no API key, no watermark)
      const baseImagery = new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        credit: '© Esri, Maxar, Earthstar Geographics, USDA, USGS',
        maximumLevel: 19,
      })

      const imageryLayer = new Cesium.ImageryLayer(baseImagery)
      imageryLayer.show = false // Background map removed by default

      const viewer = new Cesium.Viewer(containerRef.current, {
        baseLayer: imageryLayer,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        animation: false,
        timeline: false,
        fullscreenButton: false,
        vrButton: false,
        selectionIndicator: false,
        infoBox: false,

        requestRenderMode: false,
        targetFrameRate: 60,
        useBrowserRecommendedResolution: true,

        scene3DOnly: true,
        shadows: false,
        shouldAnimate: true,
      })

      // Clean dark studio background (no background map)
      viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#0b0f19')
      viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#0b0f19')
      viewer.scene.globe.show = false
      viewer.scene.globe.enableLighting = false
      viewer.scene.globe.depthTestAgainstTerrain = false
      viewer.scene.fog.enabled = false
      viewer.scene.screenSpaceCameraController.minimumZoomDistance = 1.0
      viewer.scene.screenSpaceCameraController.maximumZoomDistance = 20000000
      if (viewer.scene.skyAtmosphere) {
        viewer.scene.skyAtmosphere.show = false
      }
      if (viewer.scene.skyBox) {
        viewer.scene.skyBox.show = false
      }
      if (viewer.scene.sun) viewer.scene.sun.show = false
      if (viewer.scene.moon) viewer.scene.moon.show = false

      viewer.scene.renderError.addEventListener((_scene, err) => {
        console.warn('Cesium render warning:', err)
      })

      // Default camera — will auto-fly to dataset center once loaded
      viewer.camera.setView({
        destination: Cesium.Cartesian3.fromDegrees(-84.19, 39.76, 3000),
        orientation: {
          heading: Cesium.Math.toRadians(30),
          pitch: Cesium.Math.toRadians(-30),
          roll: 0,
        },
      })

      // Camera position tracking
      viewer.scene.postRender.addEventListener(() => {
        const cart = viewer.camera.positionCartographic
        if (cart) {
          setCameraPosition({
            lon: Cesium.Math.toDegrees(cart.longitude),
            lat: Cesium.Math.toDegrees(cart.latitude),
            alt: cart.height,
          })
        }
      })

      // Mouse cursor tracking
      const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas)
      handler.setInputAction((movement: { endPosition: Cesium.Cartesian2 }) => {
        const position = viewer.camera.pickEllipsoid(
          movement.endPosition,
          viewer.scene.globe.ellipsoid
        )
        if (position) {
          const carto = Cesium.Cartographic.fromCartesian(position)
          setCursorCoords({
            lon: Cesium.Math.toDegrees(carto.longitude),
            lat: Cesium.Math.toDegrees(carto.latitude),
          })
        } else {
          setCursorCoords(null)
        }
      }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

      // FPS counter
      let frameCount = 0
      let lastTime = performance.now()
      viewer.scene.postRender.addEventListener(() => {
        frameCount++
        const now = performance.now()
        if (now - lastTime >= 1000) {
          setFps(frameCount)
          frameCount = 0
          lastTime = now
        }
      })

      // Click handler (Interactive Tools + Object Selection)
      handler.setInputAction((click: { position: Cesium.Cartesian2 }) => {
        const currentTool = useViewerStore.getState().activeTool

        // If spatial analysis tool is active, pick coordinates and add measurement point
        if (currentTool !== 'none') {
          const ray = viewer.camera.getPickRay(click.position)
          let cartesian: Cesium.Cartesian3 | undefined

          if (ray) {
            cartesian = viewer.scene.globe.pick(ray, viewer.scene)
          }
          if (!cartesian) {
            cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid)
          }

          if (cartesian) {
            const carto = Cesium.Cartographic.fromCartesian(cartesian)
            const lon = Cesium.Math.toDegrees(carto.longitude)
            const lat = Cesium.Math.toDegrees(carto.latitude)
            const alt = carto.height || 1750.0

            useViewerStore.getState().addMeasurementPoint({ lon, lat, alt })
          }
          return
        }

        // Default Point / Object Selection
        const ray = viewer.camera.getPickRay(click.position)
        let cartesian: Cesium.Cartesian3 | undefined
        if (ray) {
          cartesian = viewer.scene.globe.pick(ray, viewer.scene)
        }
        if (!cartesian) {
          cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid)
        }

        if (cartesian && loadedPointsRef.current.length > 0) {
          const carto = Cesium.Cartographic.fromCartesian(cartesian)
          const clickLon = Cesium.Math.toDegrees(carto.longitude)
          const clickLat = Cesium.Math.toDegrees(carto.latitude)

          // Find nearest point within radius
          let nearest = null
          let minDistSq = Infinity

          for (const p of loadedPointsRef.current) {
            const dLon = p.lon - clickLon
            const dLat = p.lat - clickLat
            const distSq = dLon * dLon + dLat * dLat
            if (distSq < minDistSq) {
              minDistSq = distSq
              nearest = p
            }
          }

          if (nearest && Math.sqrt(minDistSq) < 0.005) {  // Within reasonable threshold
            const classNames: Record<number, string> = {
              0: 'Ground / Created',
              1: 'Vegetation / Unclassified',
              2: 'Ground / Car',
              3: 'Low Vegetation / Powerline',
              4: 'Medium Vegetation / Fence',
              5: 'High Tree Vegetation',
              6: 'Building',
              7: 'Noise / Outlier',
              8: 'Heavy Vehicle',
              9: 'Water / Utility Pole',
              10: 'Light Pole',
              11: 'Road / Traffic Pole',
              12: 'Building Structure',
              13: 'Wire / Cable',
              14: 'Other'
            }
            useViewerStore.getState().setPickedPoint({
              ...nearest,
              className: classNames[nearest.classification] || `Class ${nearest.classification}`
            })
          }
        }

        const picked = viewer.scene.pick(click.position)
        if (picked) {
          if (picked.primitive && (picked.primitive as any).datasetInfo) {
            setSelectedObject((picked.primitive as any).datasetInfo)
          } else {
            setSelectedObject({ object: 'Cesium Primitive', detail: String(picked) })
          }
        } else {
          setSelectedObject(null)
        }
      }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

      // Right Click to finish polygon/profile
      handler.setInputAction(() => {
        const currentTool = useViewerStore.getState().activeTool
        if (currentTool === 'area' || currentTool === 'profile' || currentTool === 'volume') {
          // Keep results open
        }
      }, Cesium.ScreenSpaceEventType.RIGHT_CLICK)

      // Point Primitive Collection
      const pointCollection = new Cesium.PointPrimitiveCollection()
      viewer.scene.primitives.add(pointCollection)
      pointPrimitiveCollectionRef.current = pointCollection

      viewerRef.current = viewer
      setLoading(false)
    } catch (err) {
      console.error('CesiumJS initialization error:', err)
      setError(String(err))
      setLoading(false)
    }

    return () => {
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        viewerRef.current.destroy()
        viewerRef.current = null
      }
    }
  }, [])

  // ── Fly To Target ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!viewerRef.current || !flyToTarget) return
    viewerRef.current.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        flyToTarget.lon - 0.004,
        flyToTarget.lat - 0.006,
        flyToTarget.alt + 600
      ),
      orientation: {
        heading: Cesium.Math.toRadians(30),
        pitch: Cesium.Math.toRadians(-25),
        roll: 0,
      },
      duration: 2.0,
    })
    setFlyToTarget(null)
  }, [flyToTarget, setFlyToTarget])

  // ── AI Marker Pin 3D Rendering ─────────────────────────────────────────────
  const aiMarkerPin = useViewerStore((s) => s.aiMarkerPin)

  useEffect(() => {
    if (!viewerRef.current) return
    const viewer = viewerRef.current

    if (aiMarkerPinEntityRef.current) {
      viewer.entities.remove(aiMarkerPinEntityRef.current)
      aiMarkerPinEntityRef.current = null
    }

    if (aiMarkerPin) {
      const pinColor = aiMarkerPin.color
        ? Cesium.Color.fromCssColorString(aiMarkerPin.color)
        : Cesium.Color.fromCssColorString('#ef4444')

      const entity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(
          aiMarkerPin.lon,
          aiMarkerPin.lat,
          aiMarkerPin.alt
        ),
        point: {
          pixelSize: 12,
          color: pinColor,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        label: {
          text: `📍 ${aiMarkerPin.label}`,
          font: 'bold 12px sans-serif',
          fillColor: Cesium.Color.WHITE,
          backgroundColor: Cesium.Color.fromCssColorString('rgba(15, 23, 42, 0.85)'),
          showBackground: true,
          backgroundPadding: new Cesium.Cartesian2(8, 4),
          pixelOffset: new Cesium.Cartesian2(0, -22),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      })
      aiMarkerPinEntityRef.current = entity
    }
  }, [aiMarkerPin])

  const activeClassFilters = useViewerStore((s) => s.activeClassFilters)
  const contoursGeoJson = useViewerStore((s) => s.contoursGeoJson)
  const showContours = useViewerStore((s) => s.showContours)
  const setPickedPoint = useViewerStore((s) => s.setPickedPoint)
  const loadedPointsRef = useRef<Array<{ lon: number; lat: number; alt: number; classification: number; intensity: number }>>([])
  const contoursDataSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null)

  // ── Contours GeoJSON Rendering ─────────────────────────────────────────────
  useEffect(() => {
    if (!viewerRef.current) return
    const viewer = viewerRef.current

    if (contoursDataSourceRef.current) {
      viewer.dataSources.remove(contoursDataSourceRef.current)
      contoursDataSourceRef.current = null
    }

    if (showContours && contoursGeoJson) {
      Cesium.GeoJsonDataSource.load(contoursGeoJson, {
        stroke: Cesium.Color.fromCssColorString('#f59e0b'),
        strokeWidth: 2,
        clampToGround: true,
      }).then((ds) => {
        viewer.dataSources.add(ds)
        contoursDataSourceRef.current = ds
      }).catch((err) => {
        console.warn('Could not load contours GeoJSON:', err)
      })
    }
  }, [showContours, contoursGeoJson])

  // ── Load & Render Point Cloud Dataset ──────────────────────────────────────
  useEffect(() => {
    if (!viewerRef.current || !pointPrimitiveCollectionRef.current) return
    const viewer = viewerRef.current
    const collection = pointPrimitiveCollectionRef.current

    // Clear previous
    collection.removeAll()
    if (activeTilesetRef.current) {
      viewer.scene.primitives.remove(activeTilesetRef.current)
      activeTilesetRef.current = null
    }
    if (gl3dModelEntityRef.current) {
      viewer.entities.remove(gl3dModelEntityRef.current)
      gl3dModelEntityRef.current = null
    }
    setTileStreamingProgress(0)

    const isPointCloudType = activeDataset?.dataset_type === 'point_cloud' || activeDataset?.dataset_type === 'gl3d_scene'
    if (!activeDataset || !isPointCloudType) {
      loadedPointsRef.current = []
      return
    }

    const datasetId = activeDataset.id
    let isSubscribed = true

    // ── GL3D Solid 3D Reconstructed Mesh Loading ──────────────────────────
    if (activeDataset.dataset_type === 'gl3d_scene') {
      const meta = (activeDataset.metadata_json as any) || {}
      const anchor = meta.anchor || { lon: 8.5417, lat: 47.3769, alt: 450.0 }
      const modelUrl = `/api/datasets/${datasetId}/model.glb`

      const position = Cesium.Cartesian3.fromDegrees(anchor.lon, anchor.lat, anchor.alt)

      // Build an East-North-Up (ENU) orientation so the mesh sits upright on the terrain
      const heading = Cesium.Math.toRadians(0)
      const pitch = 0
      const roll = 0
      const hpr = new Cesium.HeadingPitchRoll(heading, pitch, roll)

      const modelEntity = viewer.entities.add({
        name: activeDataset.name,
        position: position,
        orientation: Cesium.Transforms.headingPitchRollQuaternion(position, hpr),
        model: {
          uri: modelUrl,
          minimumPixelSize: 64,
          maximumScale: 200000,
          scale: 1.0,
          shadows: Cesium.ShadowMode.ENABLED,
          silhouetteColor: Cesium.Color.fromCssColorString('#38bdf8'),
          silhouetteSize: 0.5,
        },
      })
      gl3dModelEntityRef.current = modelEntity

      // Fly camera close to the model — position just offset from anchor
      // to show the full reconstruction filling the viewport
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          anchor.lon + 0.0004,
          anchor.lat - 0.0005,
          anchor.alt + 80.0
        ),
        orientation: {
          heading: Cesium.Math.toRadians(320),
          pitch: Cesium.Math.toRadians(-35),
          roll: 0,
        },
        duration: 2.0,
      })
      setTileStreamingProgress(100)
    }

    // ── Strategy 1: Try native Cesium3DTileset (LOD streaming) ──────────────
    const tilesetUrl = `/api/datasets/${datasetId}/tileset.json`

    const tryLoadTileset = async () => {
      try {
        // Quick HEAD check to see if tileset is available
        const resp = await fetch(tilesetUrl, { method: 'HEAD' })
        if (!resp.ok) throw new Error('No tileset yet')

        const tileset = await Cesium.Cesium3DTileset.fromUrl(tilesetUrl, {
          maximumScreenSpaceError: pointBudget,
          skipLevelOfDetail: false,
          preferLeaves: true,
          dynamicScreenSpaceError: true,
          dynamicScreenSpaceErrorDensity: 0.00278,
          dynamicScreenSpaceErrorFactor: 4.0,
        })

        if (!isSubscribed) return

        viewer.scene.primitives.add(tileset)
        activeTilesetRef.current = tileset

        // Track tile streaming progress
        let tilesLoaded = 0
        tileset.tileLoad.addEventListener(() => {
          tilesLoaded++
          const total = Math.max(tilesLoaded, (tileset as any).statistics?.numberOfTilesTotal || tilesLoaded)
          const pct = Math.min(100, Math.round((tilesLoaded / total) * 100))
          setTileStreamingProgress(pct)
        })

        // Fly to tileset bounding sphere
        try {
          await viewer.zoomTo(tileset)
          viewer.camera.flyToBoundingSphere(tileset.boundingSphere, {
            offset: new Cesium.HeadingPitchRange(
              Cesium.Math.toRadians(30),
              Cesium.Math.toRadians(-25),
              tileset.boundingSphere.radius * 3.0,
            ),
            duration: 2.0,
          })
        } catch { /* non-fatal */ }

        setTileStreamingProgress(100)
        return true
      } catch {
        return false
      }
    }

    tryLoadTileset().then((tilesetLoaded) => {
      if (tilesetLoaded || !isSubscribed) return

      // ── Strategy 2: Fallback to points-sample (client-side rendering) ───────
      api
        .getPointsSample(datasetId, 200000)
        .then((res) => {
          if (!isSubscribed) return
          const { points, min_z, max_z } = res.data
          if (!points || points.length === 0) return

          loadedPointsRef.current = points
          const effectiveMinZ = min_z || 240
          const effectiveMaxZ = max_z || 280

          points.forEach((p) => {
            if (activeClassFilters[p.classification] === false) return

            let color: Cesium.Color
            if (pointCloudColorMode === 'elevation') {
              color = getElevationColor(p.alt, effectiveMinZ, effectiveMaxZ)
            } else if (pointCloudColorMode === 'intensity') {
              const intVal = Math.min(1.0, (p.intensity || 0) / 50000)
              color = new Cesium.Color(intVal, intVal, intVal, 1.0)
            } else {
              color = CLASSIFICATION_CESIUM_COLORS[p.classification] || Cesium.Color.fromCssColorString('#8b5a2b')
            }

            collection.add({
              position: Cesium.Cartesian3.fromDegrees(p.lon, p.lat, p.alt),
              color: color,
              pixelSize: pointSize || 5,
            })
          })

          if (points.length > 0) {
            const mid = points[Math.floor(points.length / 2)]
            viewer.camera.flyTo({
              destination: Cesium.Cartesian3.fromDegrees(mid.lon - 0.004, mid.lat - 0.006, mid.alt + 600),
              orientation: { heading: Cesium.Math.toRadians(30), pitch: Cesium.Math.toRadians(-25), roll: 0 },
              duration: 2.0,
            })
          }
          setTileStreamingProgress(100)
        })
        .catch((err) => console.warn('Could not load point cloud sample:', err))
    })

    return () => {
      isSubscribed = false
    }
  }, [activeDataset, pointCloudColorMode, pointSize, activeClassFilters, pointBudget])
 
  // ── Render GL3D Drone Camera Network ──────────────────────────────────────
  useEffect(() => {
    if (!viewerRef.current) return
    const viewer = viewerRef.current

    // Clear existing camera markers
    gl3dCameraEntitiesRef.current.forEach((e) => viewer.entities.remove(e))
    gl3dCameraEntitiesRef.current = []

    if (!activeDataset || activeDataset.dataset_type !== 'gl3d_scene' || !showDroneCameras) return

    const meta = activeDataset.metadata_json as any
    const rawCameras: any[] = meta?.cameras || []
    if (!rawCameras || rawCameras.length === 0) return

    const anchor = meta?.anchor || { lon: 8.5417, lat: 47.3769, alt: 450.0 }
    const anchorLon = anchor.lon
    const anchorLat = anchor.lat
    const anchorAlt = anchor.alt
    const cosLat = Math.cos((anchorLat * Math.PI) / 180)

    // Render drone capture stations
    rawCameras.slice(0, 150).forEach((cam: any) => {
      const center = cam.center || [0, 0, 0]
      const forward = cam.forward || [0, 0, -1]

      const lon = anchorLon + center[0] / (111320 * cosLat)
      const lat = anchorLat + center[1] / 110540
      const alt = anchorAlt + center[2]

      const pos = Cesium.Cartesian3.fromDegrees(lon, lat, alt)

      // Drone station entity
      const camEntity = viewer.entities.add({
        position: pos,
        point: {
          pixelSize: 8,
          color: Cesium.Color.fromCssColorString('#38bdf8'),
          outlineColor: Cesium.Color.fromCssColorString('#0284c7'),
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        label: {
          text: `📷 #${cam.image_id}`,
          font: '10px sans-serif',
          fillColor: Cesium.Color.WHITE,
          showBackground: true,
          backgroundColor: Cesium.Color.fromCssColorString('rgba(15, 23, 42, 0.85)'),
          pixelOffset: new Cesium.Cartesian2(0, -14),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1500),
        },
      })
      ;(camEntity as any).datasetInfo = {
        object: `GL3D Drone Camera #${cam.image_id}`,
        detail: `Focal Length: fx=${cam.fx?.toFixed(1) || 'N/A'} | Local Coords: [${center[0]?.toFixed(1)}, ${center[1]?.toFixed(1)}, ${center[2]?.toFixed(1)}]`,
      }
      gl3dCameraEntitiesRef.current.push(camEntity)

      // Look-at direction ray
      const lookDist = 12.0
      const lookX = center[0] + (forward[0] || 0) * lookDist
      const lookY = center[1] + (forward[1] || 0) * lookDist
      const lookZ = center[2] + (forward[2] || -1) * lookDist

      const lookLon = anchorLon + lookX / (111320 * cosLat)
      const lookLat = anchorLat + lookY / 110540
      const lookAlt = anchorAlt + lookZ

      const rayEntity = viewer.entities.add({
        polyline: {
          positions: [pos, Cesium.Cartesian3.fromDegrees(lookLon, lookLat, lookAlt)],
          width: 1.5,
          material: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.fromCssColorString('rgba(56, 189, 248, 0.7)'),
          }),
        },
      })
      gl3dCameraEntitiesRef.current.push(rayEntity)
    })
  }, [activeDataset, showDroneCameras])


  // ── Render 3D Spatial Measurement Entities ────────────────────────────────
  const updateMeasurementGraphics = useCallback(() => {
    if (!viewerRef.current) return
    const viewer = viewerRef.current

    // Clear previous measurement entities
    measurementEntitiesRef.current.forEach((e) => viewer.entities.remove(e))
    measurementEntitiesRef.current = []

    if (measurementPoints.length === 0 || activeTool === 'none') return

    const cartesians = measurementPoints.map((p) =>
      Cesium.Cartesian3.fromDegrees(p.lon, p.lat, p.alt)
    )

    // 1. Draw Vertex Points
    cartesians.forEach((pos, idx) => {
      const vertexEntity = viewer.entities.add({
        position: pos,
        point: {
          pixelSize: 9,
          color: Cesium.Color.fromCssColorString('#38bdf8'),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        label: {
          text: `P${idx + 1}`,
          font: '11px JetBrains Mono, monospace',
          fillColor: Cesium.Color.WHITE,
          showBackground: true,
          backgroundColor: new Cesium.Color(0.1, 0.1, 0.2, 0.8),
          pixelOffset: new Cesium.Cartesian2(0, -18),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      })
      measurementEntitiesRef.current.push(vertexEntity)
    })

    // 2. Draw Lines for Distance / Profile / Slope
    if (
      (activeTool === 'distance' || activeTool === 'profile' || activeTool === 'slope') &&
      cartesians.length >= 2
    ) {
      const lineEntity = viewer.entities.add({
        polyline: {
          positions: cartesians,
          width: 3.5,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.25,
            color: Cesium.Color.fromCssColorString('#38bdf8'),
          }),
          depthFailMaterial: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.CYAN,
          }),
        },
      })
      measurementEntitiesRef.current.push(lineEntity)
    }

    // 3. Draw Polygon for Area / Volume
    if ((activeTool === 'area' || activeTool === 'volume') && cartesians.length >= 3) {
      const polyEntity = viewer.entities.add({
        polygon: {
          hierarchy: cartesians,
          material: new Cesium.Color(0.2, 0.8, 0.4, 0.35),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString('#4ade80'),
          outlineWidth: 3,
        },
      })
      measurementEntitiesRef.current.push(polyEntity)
    }

    // 4. Draw Vertical Rod for Height Measurement
    if (activeTool === 'height' && cartesians.length >= 2) {
      const p1 = measurementPoints[0]
      const p2 = measurementPoints[1]
      const groundPos = Cesium.Cartesian3.fromDegrees(p2.lon, p2.lat, p1.alt)

      // Vertical line
      const rodEntity = viewer.entities.add({
        polyline: {
          positions: [groundPos, cartesians[1]],
          width: 3,
          material: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.fromCssColorString('#f43f5e'),
            dashLength: 8,
          }),
        },
      })
      measurementEntitiesRef.current.push(rodEntity)

      // Horizontal base line
      const baseLineEntity = viewer.entities.add({
        polyline: {
          positions: [cartesians[0], groundPos],
          width: 2,
          material: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.YELLOW,
          }),
        },
      })
      measurementEntitiesRef.current.push(baseLineEntity)
    }
  }, [measurementPoints, activeTool])

  // Trigger graphics update when points change
  useEffect(() => {
    updateMeasurementGraphics()
  }, [updateMeasurementGraphics])

  // ── Compute Analysis Metrics via Backend API ──────────────────────────────
  useEffect(() => {
    if (measurementPoints.length < 2 || activeTool === 'none') return

    if (activeTool === 'distance') {
      api.measureDistance(measurementPoints).then((res) => setAnalysisResult(res.data))
    } else if (activeTool === 'area' && measurementPoints.length >= 3) {
      api.measureArea(measurementPoints).then((res) => setAnalysisResult(res.data))
    } else if (activeTool === 'height' && measurementPoints.length >= 2) {
      api
        .measureHeight(measurementPoints[0], measurementPoints[1])
        .then((res) => setAnalysisResult(res.data))
    } else if (activeTool === 'profile' && measurementPoints.length >= 2) {
      api
        .getElevationProfile(measurementPoints, activeDataset?.id, 100)
        .then((res) => setAnalysisResult(res.data))
    } else if (activeTool === 'slope' && measurementPoints.length >= 2) {
      api.analyzeSlopeAspect(measurementPoints).then((res) => setAnalysisResult(res.data))
    } else if (activeTool === 'volume' && measurementPoints.length >= 3) {
      api.estimateVolume(measurementPoints).then((res) => setAnalysisResult(res.data))
    }
  }, [measurementPoints, activeTool, activeDataset?.id, setAnalysisResult])

  // ── Synchronize Elevation Profile Hover Marker on Globe ────────────────────
  useEffect(() => {
    if (!viewerRef.current) return
    const viewer = viewerRef.current

    if (hoverMarkerEntityRef.current) {
      viewer.entities.remove(hoverMarkerEntityRef.current)
      hoverMarkerEntityRef.current = null
    }

    if (
      activeTool === 'profile' &&
      analysisResult &&
      analysisResult.samples &&
      hoverProfileDistance !== null
    ) {
      const targetSample = analysisResult.samples.find(
        (s: any) => Math.abs(s.distance_m - hoverProfileDistance) < 5
      )
      if (targetSample) {
        const marker = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(
            targetSample.lon,
            targetSample.lat,
            targetSample.alt + 2
          ),
          point: {
            pixelSize: 14,
            color: Cesium.Color.YELLOW,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
          label: {
            text: `${targetSample.alt.toFixed(1)}m`,
            font: 'bold 12px JetBrains Mono, monospace',
            fillColor: Cesium.Color.YELLOW,
            showBackground: true,
            backgroundColor: new Cesium.Color(0, 0, 0, 0.85),
            pixelOffset: new Cesium.Cartesian2(0, -22),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
        })
        hoverMarkerEntityRef.current = marker
      }
    }
  }, [hoverProfileDistance, activeTool, analysisResult])

  // ── Layer Visibility Sync ──────────────────────────────────────────────────
  useEffect(() => {
    if (!viewerRef.current) return
    const viewer = viewerRef.current

    const imageryVisible = showMapBackground || layers.find((l) => l.id === 'imagery')?.visible === true

    if (viewer.imageryLayers.length > 0) {
      viewer.imageryLayers.get(0).show = imageryVisible
    }

    viewer.scene.globe.show = imageryVisible
    viewer.scene.globe.depthTestAgainstTerrain = imageryVisible
    if (viewer.scene.skyAtmosphere) {
      viewer.scene.skyAtmosphere.show = imageryVisible
    }

    const pcLayer = layers.find((l) => l.id === 'point_cloud')
    if (pcLayer && pointPrimitiveCollectionRef.current) {
      pointPrimitiveCollectionRef.current.show = pcLayer.visible
    }
  }, [layers, showMapBackground])

  return (
    <div className="viewer-container">
      {loading && (
        <div className="scene-loading">
          <div className="scene-loading__spinner" />
          <div className="scene-loading__text">Initializing 3D Scene…</div>
        </div>
      )}
      {error && (
        <div className="scene-loading">
          <div style={{ color: 'var(--color-error)', fontSize: 14 }}>⚠ Viewer Error</div>
          <div className="scene-loading__text">{error}</div>
        </div>
      )}
      <div
        ref={containerRef}
        className="cesium-viewer-wrapper"
        style={{ display: loading || error ? 'none' : 'block' }}
      />

      {/* Measurement HUD Toolbar */}
      <MeasurementOverlay />

      {/* Elevation Profile Modal Chart */}
      {activeTool === 'profile' && analysisResult && analysisResult.samples && (
        <ElevationProfileChart
          data={analysisResult as any}
          onClose={() => setActiveTool('none')}
        />
      )}

      {!loading && !error && <ViewerControls viewer={viewerRef} />}
    </div>
  )
}

// ── Viewer Controls Overlay ─────────────────────────────────────────────────

function ViewerControls({
  viewer,
}: {
  viewer: React.MutableRefObject<Cesium.Viewer | null>
}) {
  const [orbiting, setOrbiting] = useState(false)
  const orbitIntervalRef = useRef<number | null>(null)

  const activeDataset = useAppStore((s) => s.activeDataset)

  const getTargetCenter = () => {
    const meta = activeDataset?.metadata_json as Record<string, any> | null
    const center = meta?.center
    if (center && center.lon && center.lat) {
      return { lon: center.lon, lat: center.lat, alt: center.alt || 250 }
    }
    return { lon: -84.1896, lat: 39.7586, alt: 250 }
  }

  const flyTo3DPerspective = () => {
    if (!viewer.current) return
    const center = getTargetCenter()
    viewer.current.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(center.lon, center.lat - 0.003, center.alt + 320),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-35),
        roll: 0,
      },
      duration: 1.5,
    })
  }

  const flyToStreetLevel = () => {
    if (!viewer.current) return
    const center = getTargetCenter()
    viewer.current.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(center.lon, center.lat - 0.0008, center.alt + 35),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-12),
        roll: 0,
      },
      duration: 1.5,
    })
  }

  const flyToTopDown = () => {
    if (!viewer.current) return
    const center = getTargetCenter()
    viewer.current.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(center.lon, center.lat, center.alt + 800),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-90),
        roll: 0,
      },
      duration: 1.5,
    })
  }

  const toggleOrbit = () => {
    if (!viewer.current) return
    if (orbiting) {
      if (orbitIntervalRef.current) window.clearInterval(orbitIntervalRef.current)
      orbitIntervalRef.current = null
      setOrbiting(false)
    } else {
      setOrbiting(true)
      const center = getTargetCenter()
      const targetCartesian = Cesium.Cartesian3.fromDegrees(center.lon, center.lat, center.alt)
      let heading = viewer.current.camera.heading

      orbitIntervalRef.current = window.setInterval(() => {
        if (!viewer.current) return
        heading += 0.008
        viewer.current.camera.lookAt(
          targetCartesian,
          new Cesium.HeadingPitchRange(heading, Cesium.Math.toRadians(-30), 450)
        )
      }, 30)
    }
  }

  useEffect(() => {
    return () => {
      if (orbitIntervalRef.current) window.clearInterval(orbitIntervalRef.current)
    }
  }, [])

  const showMapBackground = useViewerStore((s) => s.showMapBackground)
  const toggleMapBackground = useViewerStore((s) => s.toggleMapBackground)
  const showDroneCameras = useViewerStore((s) => s.showDroneCameras)
  const toggleDroneCameras = useViewerStore((s) => s.toggleDroneCameras)

  return (
    <div className="viewer-controls" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <button
        className={`viewer-controls__btn ${showDroneCameras ? 'btn--active' : ''}`}
        onClick={toggleDroneCameras}
        title={showDroneCameras ? "Drone Camera Markers: Visible (click to remove)" : "Drone Camera Markers: Removed (click to show)"}
        style={{
          border: showDroneCameras ? '1px solid #38bdf8' : undefined,
          color: showDroneCameras ? '#38bdf8' : '#94a3b8',
        }}
      >
        📷
      </button>
      <button
        className={`viewer-controls__btn ${showMapBackground ? 'btn--active' : ''}`}
        onClick={toggleMapBackground}
        title={showMapBackground ? "Background Map: Visible (click to remove)" : "Background Map: Removed (click to show)"}
        style={{
          border: showMapBackground ? '1px solid #38bdf8' : undefined,
          color: showMapBackground ? '#38bdf8' : '#94a3b8',
        }}
      >
        {showMapBackground ? '🗺️' : '⬛'}
      </button>
      <button className="viewer-controls__btn" onClick={flyTo3DPerspective} title="3D Isometric Perspective">
        🛸
      </button>
      <button className="viewer-controls__btn" onClick={flyToStreetLevel} title="Street / Eye Level View">
        🏙️
      </button>
      <button
        className={`viewer-controls__btn ${orbiting ? 'btn--active' : ''}`}
        onClick={toggleOrbit}
        title={orbiting ? 'Stop 3D Orbit' : 'Orbit 3D Scene'}
        style={{ color: orbiting ? '#38bdf8' : undefined }}
      >
        🔄
      </button>
      <button className="viewer-controls__btn" onClick={flyToTopDown} title="Top-Down 2D Map View">
        🧭
      </button>
    </div>
  )
}
