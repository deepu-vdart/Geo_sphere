import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// ─── Types ───────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  version: string
  environment: string
  database: string
  timestamp: string
}

export interface Project {
  id: string
  name: string
  description: string | null
  location_name: string | null
  crs: string | null
  min_elevation: number | null
  max_elevation: number | null
  status: string
  created_at: string
  updated_at: string
  dataset_count: number
}

export interface ProjectCreate {
  name: string
  description?: string
  location_name?: string
  crs?: string
}

export interface Dataset {
  id: string
  project_id: string
  name: string
  description: string | null
  dataset_type: string
  file_format: string | null
  file_size_bytes: number | null
  original_filename: string | null
  crs: string | null
  min_z: number | null
  max_z: number | null
  point_count: number | null
  point_density: number | null
  resolution_x: number | null
  resolution_y: number | null
  raster_width: number | null
  raster_height: number | null
  processing_status: string
  status: string
  metadata_json: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ProcessingJob {
  id: string
  project_id: string
  dataset_id: string | null
  job_type: string
  status: string
  progress: number
  parameters: Record<string, unknown> | null
  output_assets: unknown[] | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  created_at: string
}

// ─── GL3D Types ──────────────────────────────────────────────────────────────

export interface GL3DScene {
  scene_id: string
  name: string
  description: string
  category: string
  category_label?: string
  mesh_type?: string
  image_count: number
  is_downloaded: boolean
}

export interface GL3DCamera {
  image_id: number
  center: [number, number, number]
  forward: [number, number, number]
  up: [number, number, number]
  fx: number
  fy: number
}

export interface GL3DSceneDetail extends GL3DScene {
  camera_count: number
  has_cameras: boolean
  has_depths: boolean
  has_images: boolean
  cameras: GL3DCamera[] | null
  metadata: Record<string, unknown> | null
}

export interface GL3DCameraResponse {
  scene_id: string
  total_cameras: number
  returned: number
  extent: Record<string, number>
  cameras: GL3DCamera[]
}

export interface GL3DIngestResponse {
  status: string
  scene_id: string
  project_id: string | null
  dataset_id: string | null
  message: string
}

// ─── API Functions ────────────────────────────────────────────────────────────

export const api = {
  // Health
  health: () => apiClient.get<HealthResponse>('/health'),

  // Projects
  getProjects: () => apiClient.get<{ total: number; projects: Project[] }>('/projects'),
  createProject: (data: ProjectCreate) => apiClient.post<Project>('/projects', data),
  getProject: (id: string) => apiClient.get<Project>(`/projects/${id}`),
  deleteProject: (id: string) => apiClient.delete(`/projects/${id}`),

  // Datasets
  getDatasets: (projectId: string) =>
    apiClient.get<{ total: number; datasets: Dataset[] }>(`/projects/${projectId}/datasets`),
  uploadDataset: (projectId: string, file: File, name: string, description?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('name', name)
    form.append('description', description || '')
    return apiClient.post<Dataset>(`/projects/${projectId}/datasets`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getDataset: (id: string) => apiClient.get<Dataset>(`/datasets/${id}`),
  processDataset: (id: string) => apiClient.post<ProcessingJob>(`/datasets/${id}/process`),
  getPointsSample: (id: string, sampleSize: number = 15000) =>
    apiClient.get<{
      dataset_id: string
      point_count: number
      sample_count: number
      crs: string
      min_z: number
      max_z: number
      points: Array<{ lon: number; lat: number; alt: number; classification: number; intensity: number }>
    }>(`/datasets/${id}/points-sample?sample_size=${sampleSize}`),
  getTilesetUrl: (id: string) => `${BASE_URL}/api/datasets/${id}/tileset.json`,

  // Spatial Analysis
  measureDistance: (points: Array<{ lon: number; lat: number; alt?: number }>) =>
    apiClient.post('/analysis/measure-distance', { points }),
  measureArea: (points: Array<{ lon: number; lat: number; alt?: number }>) =>
    apiClient.post('/analysis/measure-area', { points }),
  measureHeight: (basePoint: { lon: number; lat: number; alt: number }, topPoint: { lon: number; lat: number; alt: number }) =>
    apiClient.post('/analysis/measure-height', { base_point: basePoint, top_point: topPoint }),
  getElevationProfile: (points: Array<{ lon: number; lat: number; alt?: number }>, datasetId?: string, numSamples: number = 100) =>
    apiClient.post('/analysis/elevation-profile', { points, dataset_id: datasetId, num_samples: numSamples }),
  analyzeSlopeAspect: (points: Array<{ lon: number; lat: number; alt?: number }>) =>
    apiClient.post('/analysis/slope-aspect', { points }),
  estimateVolume: (points: Array<{ lon: number; lat: number; alt?: number }>, baseElevation?: number) =>
    apiClient.post('/analysis/volume', { points, base_elevation: baseElevation }),

  // Jobs
  getJob: (id: string) => apiClient.get<ProcessingJob>(`/jobs/${id}`),
  getJobs: (params?: { project_id?: string; dataset_id?: string; status?: string }) =>
    apiClient.get<ProcessingJob[]>('/jobs', { params }),

  // AOI
  estimateAOI: (data: { dataset_id?: string; bbox?: number[]; polygon?: Array<{ lon: number; lat: number }> }) =>
    apiClient.post('/aoi/estimate', data),

  // Terrain Products & Derivatives
  getTerrainDerivatives: (datasetId: string, gridResolution: number = 1.0) =>
    apiClient.get(`/terrain/datasets/${datasetId}/derivatives?grid_resolution=${gridResolution}`),
  getContours: (datasetId: string, interval: number = 2.0) =>
    apiClient.get(`/terrain/datasets/${datasetId}/contours?interval=${interval}`),

  // AI Geospatial Analysis
  getAISummary: (datasetId: string) =>
    apiClient.get(`/ai/datasets/${datasetId}/summary`),


  // Data Providers
  getProviders: () => apiClient.get('/providers'),
  searchProviders: (query: string = '') => apiClient.get(`/providers/search?q=${encodeURIComponent(query)}`),

  // DALES-2 AI Classification
  triggerClassification: (datasetId: string) =>
    apiClient.post(`/classification/datasets/${datasetId}/classify`),
  getClassifications: (datasetId: string) =>
    apiClient.get(`/classification/datasets/${datasetId}/classifications`),

  // AI Geospatial Assistant (MVP 7)
  chatWithAI: (datasetId: string, query: string) =>
    apiClient.post('/ai/chat', { dataset_id: datasetId, query }),

  // Multi-Temporal Change Detection (MVP 8)
  compareTemporalSurveys: (baselineId: string, comparisonId: string, gridRes: number = 2.0) =>
    apiClient.post('/temporal/compare', {
      baseline_dataset_id: baselineId,
      comparison_dataset_id: comparisonId,
      grid_resolution: gridRes,
    }),

  // GL3D Photogrammetry Scenes
  getGL3DScenes: (query: string = '') =>
    apiClient.get<GL3DScene[]>(`/gl3d/scenes?q=${encodeURIComponent(query)}`),
  getGL3DScene: (sceneId: string) =>
    apiClient.get<GL3DSceneDetail>(`/gl3d/scenes/${sceneId}`),
  getGL3DCameras: (sceneId: string, limit: number = 100) =>
    apiClient.get<GL3DCameraResponse>(`/gl3d/scenes/${sceneId}/cameras?limit=${limit}`),
  getGL3DImages: (sceneId: string, limit: number = 20) =>
    apiClient.get<{ scene_id: string; total_images: number; images: string[] }>(`/gl3d/scenes/${sceneId}/images?limit=${limit}`),
  ingestGL3DScene: (sceneId: string, projectName?: string, maxPoints: number = 250000) =>
    apiClient.post<GL3DIngestResponse>(`/gl3d/scenes/${sceneId}/ingest`, {
      project_name: projectName,
      max_points: maxPoints,
    }),
}
