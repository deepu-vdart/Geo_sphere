import { create } from 'zustand'
import { api, type Project, type Dataset, type ProcessingJob } from '../api/client'

// ─── App Store ────────────────────────────────────────────────────────────────

interface AppState {
  // Backend connectivity
  backendStatus: 'unknown' | 'connected' | 'error'
  backendVersion: string | null

  // Projects
  projects: Project[]
  activeProject: Project | null
  loadingProjects: boolean

  // Datasets
  datasets: Dataset[]
  activeDataset: Dataset | null
  loadingDatasets: boolean

  // Jobs
  activeJobs: ProcessingJob[]

  // Classification
  classificationResult: Record<string, any> | null
  classificationLoading: boolean

  // Actions
  checkBackend: () => Promise<void>
  loadProjects: () => Promise<void>
  selectProject: (project: Project | null) => void
  loadDatasets: (projectId: string) => Promise<void>
  selectDataset: (dataset: Dataset | null) => void
  refreshDataset: (datasetId: string) => Promise<void>
  triggerProcessing: (datasetId: string) => Promise<void>
  createProject: (name: string, description?: string, locationName?: string) => Promise<Project | null>
  triggerClassification: (datasetId: string) => Promise<void>
  loadClassification: (datasetId: string) => Promise<void>
}

export const useAppStore = create<AppState>((set, get) => ({
  backendStatus: 'unknown',
  backendVersion: null,
  projects: [],
  activeProject: null,
  loadingProjects: false,
  datasets: [],
  activeDataset: null,
  loadingDatasets: false,
  activeJobs: [],
  classificationResult: null,
  classificationLoading: false,

  checkBackend: async () => {
    try {
      const res = await api.health()
      set({ backendStatus: 'connected', backendVersion: res.data.version })
    } catch {
      set({ backendStatus: 'error', backendVersion: null })
    }
  },

  loadProjects: async () => {
    set({ loadingProjects: true })
    try {
      const res = await api.getProjects()
      const projects = res.data.projects
      set({ projects, loadingProjects: false })

      // Auto-select DALES-2 or first project if none selected
      if (!get().activeProject && projects.length > 0) {
        const dalesProj = projects.find((p) => p.name.includes('DALES') || p.name.includes('Dayton'))
        const defaultProj = dalesProj || projects[0]
        get().selectProject(defaultProj)
      }
    } catch {
      set({ loadingProjects: false })
    }
  },

  selectProject: (project) => {
    set({ activeProject: project, datasets: [], activeDataset: null })
    if (project) {
      get().loadDatasets(project.id)
    }
  },

  loadDatasets: async (projectId: string) => {
    set({ loadingDatasets: true })
    try {
      const res = await api.getDatasets(projectId)
      const datasets = res.data.datasets
      set({ datasets, loadingDatasets: false })

      // Auto-select first active dataset
      if (!get().activeDataset && datasets.length > 0) {
        const readyDs = datasets.find((d) => d.processing_status === 'ready') || datasets[0]
        get().selectDataset(readyDs)
      }
    } catch {
      set({ loadingDatasets: false })
    }
  },

  selectDataset: (dataset) => {
    set({ activeDataset: dataset })
    if (dataset) {
      const meta = dataset.metadata_json as Record<string, any> | null
      const center = meta?.center || null
      if (center && center.lon && center.lat) {
        useViewerStore.getState().setFlyToTarget({
          lon: center.lon,
          lat: center.lat,
          alt: center.alt || 250,
        })
      }
    }
  },

  refreshDataset: async (datasetId: string) => {
    try {
      const res = await api.getDataset(datasetId)
      const updated = res.data
      set((state) => ({
        datasets: state.datasets.map((d) => (d.id === datasetId ? updated : d)),
        activeDataset: state.activeDataset?.id === datasetId ? updated : state.activeDataset,
      }))
    } catch (e) {
      console.error('Failed to refresh dataset:', e)
    }
  },

  triggerProcessing: async (datasetId: string) => {
    try {
      await api.processDataset(datasetId)
      setTimeout(() => get().refreshDataset(datasetId), 2000)
      setTimeout(() => get().refreshDataset(datasetId), 6000)
    } catch (e) {
      console.error('Failed to trigger processing:', e)
    }
  },

  createProject: async (name, description, locationName) => {
    try {
      const res = await api.createProject({ name, description, location_name: locationName })
      const project = res.data
      set((state) => ({ projects: [project, ...state.projects] }))
      return project
    } catch {
      return null
    }
  },

  triggerClassification: async (datasetId: string) => {
    set({ classificationLoading: true })
    try {
      await api.triggerClassification(datasetId)
      // Poll after 2s for fast results
      setTimeout(async () => {
        try {
          const res = await api.getClassifications(datasetId)
          if (res.data.classification_ready) {
            set({ classificationResult: res.data, classificationLoading: false })
          } else {
            // Poll again after 4 more seconds
            setTimeout(async () => {
              try {
                const res2 = await api.getClassifications(datasetId)
                set({ classificationResult: res2.data, classificationLoading: false })
              } catch { set({ classificationLoading: false }) }
            }, 4000)
          }
        } catch { set({ classificationLoading: false }) }
      }, 2500)
    } catch {
      set({ classificationLoading: false })
    }
  },

  loadClassification: async (datasetId: string) => {
    try {
      const res = await api.getClassifications(datasetId)
      set({ classificationResult: res.data })
    } catch {
      set({ classificationResult: null })
    }
  },
}))

// ─── Viewer Store ─────────────────────────────────────────────────────────────

interface Layer {
  id: string
  label: string
  visible: boolean
  type: 'terrain' | 'point_cloud' | 'mesh' | 'buildings' | 'vegetation' | 'roads' | 'imagery' | 'boundaries'
  icon: string
}

export type PointCloudColorMode = 'classification' | 'elevation' | 'intensity' | 'rgb'
export type ActiveAnalysisTool = 'none' | 'distance' | 'area' | 'height' | 'profile' | 'slope' | 'volume'

interface ViewerState {
  layers: Layer[]
  selectedObjectInfo: Record<string, unknown> | null
  pickedPoint: { lon: number; lat: number; alt: number; classification?: number; intensity?: number; className?: string } | null
  cameraPosition: { lon: number; lat: number; alt: number } | null
  fps: number
  cursorCoords: { lon: number; lat: number } | null

  // Point Cloud Visual Options
  pointCloudColorMode: PointCloudColorMode
  pointSize: number
  flyToTarget: { lon: number; lat: number; alt: number } | null
  activeClassFilters: Record<number, boolean>

  // Contours & Derivatives
  contoursGeoJson: Record<string, any> | null
  showContours: boolean

  // Spatial Analysis Tools
  activeTool: ActiveAnalysisTool
  measurementPoints: Array<{ lon: number; lat: number; alt: number }>
  analysisResult: Record<string, any> | null
  hoverProfileDistance: number | null

  // AOI
  aoiMetrics: Record<string, any> | null

  // 3D Tiles Streaming Progress
  tileStreamingProgress: number  // 0-100
  pointBudget: number            // max screen-space error budget (8 = high quality, 32 = performance)

  toggleLayer: (id: string) => void
  setSelectedObject: (info: Record<string, unknown> | null) => void
  setPickedPoint: (pt: { lon: number; lat: number; alt: number; classification?: number; intensity?: number; className?: string } | null) => void
  setCameraPosition: (pos: { lon: number; lat: number; alt: number }) => void
  setCursorCoords: (coords: { lon: number; lat: number } | null) => void
  setFps: (fps: number) => void
  setPointCloudColorMode: (mode: PointCloudColorMode) => void
  setPointSize: (size: number) => void
  setFlyToTarget: (target: { lon: number; lat: number; alt: number } | null) => void
  toggleClassFilter: (classCode: number) => void
  setContoursGeoJson: (geojson: Record<string, any> | null) => void
  setShowContours: (show: boolean) => void
  setAoiMetrics: (metrics: Record<string, any> | null) => void

  // Analysis actions
  setActiveTool: (tool: ActiveAnalysisTool) => void
  addMeasurementPoint: (pt: { lon: number; lat: number; alt: number }) => void
  setMeasurementPoints: (pts: Array<{ lon: number; lat: number; alt: number }>) => void
  setAnalysisResult: (res: Record<string, any> | null) => void
  setHoverProfileDistance: (dist: number | null) => void
  clearMeasurements: () => void

  // 3D Tiles streaming
  setTileStreamingProgress: (pct: number) => void
  setPointBudget: (budget: number) => void

  // AI Geospatial Assistant (MVP 7)
  aiDrawerOpen: boolean
  setAiDrawerOpen: (open: boolean) => void
  aiChatMessages: Array<{ role: 'user' | 'assistant'; content: string; toolCalled?: string; action?: any }>
  addAiChatMessage: (msg: { role: 'user' | 'assistant'; content: string; toolCalled?: string; action?: any }) => void
  clearAiChat: () => void
  aiMarkerPin: { lon: number; lat: number; alt: number; label: string; color?: string } | null
  setAiMarkerPin: (pin: { lon: number; lat: number; alt: number; label: string; color?: string } | null) => void

  // Multi-Temporal Change Detection (MVP 8)
  temporalModalOpen: boolean
  setTemporalModalOpen: (open: boolean) => void
  temporalDiffResult: Record<string, any> | null
  setTemporalDiffResult: (res: Record<string, any> | null) => void
  temporalDiffPoints: Array<{ lon: number; lat: number; alt: number; color: string; delta_z: number; type: string }> | null
  setTemporalDiffPoints: (pts: Array<{ lon: number; lat: number; alt: number; color: string; delta_z: number; type: string }> | null) => void

  // Background map visibility (remove background map)
  showMapBackground: boolean
  setShowMapBackground: (show: boolean) => void
  toggleMapBackground: () => void

  // Drone cameras visibility (blue dots above 3D model)
  showDroneCameras: boolean
  setShowDroneCameras: (show: boolean) => void
  toggleDroneCameras: () => void
}

export const useViewerStore = create<ViewerState>((set) => ({
  showMapBackground: false,
  setShowMapBackground: (show) => set({ showMapBackground: show }),
  toggleMapBackground: () => set((state) => ({ showMapBackground: !state.showMapBackground })),

  showDroneCameras: false,
  setShowDroneCameras: (show) => set({ showDroneCameras: show }),
  toggleDroneCameras: () => set((state) => ({ showDroneCameras: !state.showDroneCameras })),

  layers: [
    { id: 'terrain', label: 'Terrain', visible: false, type: 'terrain', icon: '🏔️' },
    { id: 'point_cloud', label: 'Point Cloud', visible: true, type: 'point_cloud', icon: '⬛' },
    { id: 'mesh', label: 'Mesh', visible: false, type: 'mesh', icon: '🔷' },
    { id: 'buildings', label: 'Buildings', visible: true, type: 'buildings', icon: '🏗️' },
    { id: 'vegetation', label: 'Vegetation', visible: true, type: 'vegetation', icon: '🌿' },
    { id: 'roads', label: 'Roads', visible: true, type: 'roads', icon: '🛣️' },
    { id: 'imagery', label: 'Satellite Map', visible: false, type: 'imagery', icon: '🛰️' },
    { id: 'boundaries', label: 'Boundaries', visible: false, type: 'boundaries', icon: '📐' },
  ],
  selectedObjectInfo: null,
  pickedPoint: null,
  cameraPosition: null,
  fps: 0,
  cursorCoords: null,

  pointCloudColorMode: 'classification',
  pointSize: 4,
  flyToTarget: null,
  activeClassFilters: {
    0: true,  // Ground / Created
    1: true,  // Vegetation / Unclassified
    2: true,  // Ground / Car
    3: true,  // Low veg / Powerline
    4: true,  // Med veg / Fence
    5: true,  // Tree
    6: true,  // Building
    7: true,  // Noise
    8: true,  // Heavy
    9: true,  // Water / Pole
    10: true, // Light pole
    11: true, // Traffic pole
    12: true, // Building
    13: true, // Wire
    14: true, // Other
  },

  contoursGeoJson: null,
  showContours: false,
  aoiMetrics: null,
  tileStreamingProgress: 0,
  pointBudget: 16,

  // Spatial Analysis initial state
  activeTool: 'none',
  measurementPoints: [],
  analysisResult: null,
  hoverProfileDistance: null,

  toggleLayer: (id) =>
    set((state) => ({
      layers: state.layers.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)),
    })),

  setSelectedObject: (info) => set({ selectedObjectInfo: info }),
  setPickedPoint: (pt) => set({ pickedPoint: pt }),
  setCameraPosition: (pos) => set({ cameraPosition: pos }),
  setCursorCoords: (coords) => set({ cursorCoords: coords }),
  setFps: (fps) => set({ fps }),
  setPointCloudColorMode: (mode) => set({ pointCloudColorMode: mode }),
  setPointSize: (size) => set({ pointSize: size }),
  setFlyToTarget: (target) => set({ flyToTarget: target }),
  toggleClassFilter: (code) =>
    set((state) => ({
      activeClassFilters: {
        ...state.activeClassFilters,
        [code]: state.activeClassFilters[code] === undefined ? false : !state.activeClassFilters[code]
      }
    })),
  setContoursGeoJson: (geojson) => set({ contoursGeoJson: geojson }),
  setShowContours: (show) => set({ showContours: show }),
  setAoiMetrics: (metrics) => set({ aoiMetrics: metrics }),

  setActiveTool: (tool) =>
    set({
      activeTool: tool,
      measurementPoints: [],
      analysisResult: null,
      hoverProfileDistance: null,
    }),

  addMeasurementPoint: (pt) =>
    set((state) => ({
      measurementPoints: [...state.measurementPoints, pt],
    })),

  setMeasurementPoints: (pts) => set({ measurementPoints: pts }),
  setAnalysisResult: (res) => set({ analysisResult: res }),
  setHoverProfileDistance: (dist) => set({ hoverProfileDistance: dist }),
  clearMeasurements: () =>
    set({
      measurementPoints: [],
      analysisResult: null,
      hoverProfileDistance: null,
    }),

  setTileStreamingProgress: (pct) => set({ tileStreamingProgress: pct }),
  setPointBudget: (budget) => set({ pointBudget: budget }),

  // AI Assistant initial state & actions
  aiDrawerOpen: false,
  setAiDrawerOpen: (open) => set({ aiDrawerOpen: open }),
  aiChatMessages: [
    {
      role: 'assistant',
      content: 'Hello! I am your AI Geospatial Assistant. Ask me questions about terrain, highest/lowest elevations, building counts, or ask me to fly to specific features.',
    },
  ],
  addAiChatMessage: (msg) => set((s) => ({ aiChatMessages: [...s.aiChatMessages, msg] })),
  clearAiChat: () => set({ aiChatMessages: [] }),
  aiMarkerPin: null,
  setAiMarkerPin: (pin) => set({ aiMarkerPin: pin }),

  // Temporal comparison initial state & actions
  temporalModalOpen: false,
  setTemporalModalOpen: (open) => set({ temporalModalOpen: open }),
  temporalDiffResult: null,
  setTemporalDiffResult: (res) => set({ temporalDiffResult: res }),
  temporalDiffPoints: null,
  setTemporalDiffPoints: (pts) => set({ temporalDiffPoints: pts }),
}))
