# Geo3D Platform — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│  OpenTopography · LiDAR (LAS/LAZ) · DEM/DSM/DTM · GeoTIFF         │
│  GeoJSON · Shapefile · Drone Images · WebODM · DALES-2              │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Upload / Ingest
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PROCESSING ENGINE                              │
│  GDAL (raster) · PDAL (point cloud) · Open3D · GeoPandas           │
│  OpenDroneMap / WebODM (photogrammetry)                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      3D DATA PRODUCTS                               │
│  Point Cloud · Terrain Mesh · DTM · DSM · 3D Tiles                 │
│  Textured Mesh · Orthophoto · Hillshade                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │ Stream / Serve
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CESIUMJS VIEWER                              │
│  Interactive 3D Globe · Terrain · Point Clouds · Layers             │
│  Measurements · Object Selection · Camera Controls                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST API
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND                                │
│  /api/projects · /api/datasets · /api/jobs · /api/analysis          │
│  /api/ai (Phase 6) · Background job system                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   POSTGRESQL + POSTGIS                              │
│  projects · datasets · assets · processing_jobs                     │
│  Spatial geometries · CRS metadata · Analysis results               │
└─────────────────────────────────────────────────────────────────────┘
```

## Frontend Architecture

```
src/
├── api/client.ts          Axios API client + TypeScript types
├── stores/index.ts        Zustand: AppStore + ViewerStore
├── components/
│   ├── layout/
│   │   ├── TopBar.tsx     Brand, version, backend status
│   │   ├── LeftSidebar.tsx Projects, datasets, layers, analysis, AI
│   │   ├── RightPanel.tsx  Object inspector, dataset info
│   │   └── BottomBar.tsx   Coordinates, altitude, FPS
│   └── cesium/
│       └── CesiumViewer.tsx CesiumJS globe + controls
└── pages/
    └── MainPage.tsx        App shell layout grid
```

## Backend Architecture

```
app/
├── main.py            FastAPI app, CORS, lifespan, routes
├── config.py          Settings via pydantic-settings
├── database.py        SQLAlchemy async engine + PostGIS init
├── models/            SQLAlchemy ORM
│   ├── project.py     Project + PostGIS geometry
│   ├── dataset.py     Dataset + metadata
│   ├── processing_job.py  Job tracking
│   └── asset.py       Processed 3D outputs
├── schemas/schemas.py  Pydantic request/response types
├── api/routes/         REST endpoints
│   ├── health.py      GET /api/health
│   ├── projects.py    CRUD /api/projects
│   ├── datasets.py    Upload + list /api/datasets
│   └── jobs.py        Job status /api/jobs
└── services/
    └── dataset_service.py  Type inference, validation, processing
```

## Database Schema

```sql
projects     (id UUID PK, name, description, crs, bounding_box GEOMETRY, center_point GEOMETRY, ...)
datasets     (id UUID PK, project_id FK, dataset_type, file_path, extent GEOMETRY, point_count, ...)
processing_jobs (id UUID PK, project_id FK, dataset_id FK, job_type, status, progress, ...)
assets       (id UUID PK, dataset_id FK, asset_type, file_path, url, ...)
```

## API Design

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/health | System health + DB status |
| GET | /api/projects | List projects |
| POST | /api/projects | Create project |
| GET | /api/projects/{id} | Get project |
| PATCH | /api/projects/{id} | Update project |
| DELETE | /api/projects/{id} | Delete project |
| GET | /api/projects/{id}/datasets | List datasets |
| POST | /api/projects/{id}/datasets | Upload dataset |
| GET | /api/datasets/{id} | Get dataset |
| POST | /api/datasets/{id}/process | Trigger processing |
| GET | /api/jobs | List jobs |
| GET | /api/jobs/{id} | Get job status |

## Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| 3D Engine | CesiumJS | Industry-standard, open-source, excellent geospatial support |
| Frontend Framework | React + TypeScript + Vite | Fast HMR, strong types, ecosystem |
| Backend | FastAPI | Async, auto-docs, Pydantic integration |
| ORM | SQLAlchemy 2.x async | Native async, GeoAlchemy2 for PostGIS |
| State Management | Zustand | Lightweight, no boilerplate |
| Database | PostgreSQL + PostGIS | Gold standard for geospatial data |
| Point Cloud Processing | PDAL | Industry standard, supports LAS/LAZ |
| Raster Processing | GDAL | Universal raster standard |
| Point Cloud 3D | Open3D | Modern, fast, Python-native |
| Photogrammetry | OpenDroneMap / WebODM | Open-source, production-grade |
| Job System | FastAPI BackgroundTasks → Celery | Simple now, upgradeable |
| AI | PyTorch | Flexible, widely supported |

## Performance Strategy

- Large point clouds: PDAL → tiling → 3D Tiles streaming → CesiumJS
- Rasters: GDAL → Cloud Optimized GeoTIFF (COG) → tile server
- Never load > 100MB directly into browser
- Level-of-detail (LOD) for close/far viewing
- RequestRenderMode where appropriate in CesiumJS
