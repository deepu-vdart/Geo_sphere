# Geo3D Platform — Changelog

All notable changes to this project are documented here.

## [0.3.0] — 2026-08-27 — Phase 3 Spatial Analysis & 3D Interactive Measurements

### Added
- **Elevation Profile Engine & Interactive SVG Chart** (`app.analysis.elevation_profile` + `ElevationProfileChart.tsx`):
  - Polyline path sampling with terrain / point cloud elevation interpolation.
  - Min/Max/Avg elevation, elevation gain/loss, max slope %, and distance breakdown.
  - Interactive SVG area chart with real-time hover pin synced on the 3D Cesium globe.
- **3D Interactive Distance Measurement** (`app.analysis.measurement`):
  - Click-to-draw polyline on globe / point clouds with glowing cyan material and vertex tags.
  - Computes 3D Euclidean distance, 2D geodesic distance, elevation difference ($\Delta Z$), and segment slopes.
- **Polygon Surface Area & Perimeter Tool** (`app.analysis.measurement`):
  - Interactive polygon drawing with translucent green fill and outline.
  - Computes horizontal surface area in $m^2$, hectares, acres, and $km^2$ with perimeter.
- **Vertical Height Tool** (`app.analysis.measurement`):
  - Measure vertical height differences ($\Delta Z$) between points (e.g. building/tree height).
- **Slope & Aspect Analysis** (`app.analysis.slope_aspect`):
  - Slope calculation in degrees and gradient %, aspect azimuth, and 8 cardinal directions.
- **Volumetric Estimation Tool** (`app.analysis.volume`):
  - Calculates Cut Volume ($m^3$), Fill Volume ($m^3$), and Net Volume ($m^3$) under 3D polygon boundaries.
- **Floating Measurement HUD Overlay** (`MeasurementOverlay.tsx`):
  - Real-time metric output cards, instructions, point counter, and clear actions.
- **Spatial Analysis REST API** (`/api/analysis/*`):
  - 6 dedicated endpoints with 11/11 passing pytest tests.

## [0.2.0] — 2026-08-27 — Phase 2 Real Dataset Ingestion & LiDAR Processing

### Added
- **LiDAR LAS/LAZ Processor** (`app.processing.pdal_proc.las_processor.LASProcessor`):
  - Binary LAS 1.0–1.4 reader supporting point formats 0, 1, 2, 3, 4, 5, 6, 7, 8.
  - Coordinate system identification (WKT & GeoKeys) and re-projection to WGS84 (`EPSG:4326`) and ECEF (`EPSG:4978`).
  - Extracted point density, ASPRS classification distribution, elevation bounds, and intensity statistics.
- **OGC 3D Tiles Generation Engine**:
  - Direct compilation of `.pnts` binary tile payloads with `RTC_CENTER` position encoding and feature table headers.
  - Generates OGC 3D Tiles `tileset.json` specifications with bounding volume regions.
- **Raster & DEM Processor** (`app.processing.gdal_proc.raster_processor.RasterProcessor`):
  - GeoTIFF and DEM header tag parsing, resolution, bounding polygon, and elevation range.
- **Backend Asset & Streaming Routes**:
  - `GET /api/datasets/{id}/tileset.json` and `GET /api/datasets/{id}/tile.pnts` for 3D tiles streaming.
  - `GET /api/datasets/{id}/points-sample` for high-speed client-side point cloud sampling.
  - `POST /api/datasets/{id}/process` background processing pipeline.
- **CesiumJS Dynamic Point Cloud Visualizer**:
  - Live point cloud rendering with point budget and size controls.
  - Shader color modes: **Elevation Ramp** (Turbo/Viridis gradient), **ASPRS Classification** (color-coded ground/veg/buildings), and **Intensity**.
  - Camera auto-fly to dataset bounding sphere on dataset selection.
- **Rich Inspector & UI Badges**:
  - ASPRS classification breakdown percentage breakdown in the RightPanel.
  - Point density and elevation span metrics.
- **Testing & Synthetic Data Pipeline**:
  - Python generator `generate_sample_data.py` producing realistic terrain LiDAR point clouds.
  - Comprehensive pytest test suite (`backend/tests/test_processing.py`) with 5/5 passing tests.

## [0.1.0] — 2026-08-27 — Phase 1 Foundation

### Added
- **Monorepo structure** — `geo3d-platform/` with `backend/`, `frontend/`, `infrastructure/`, `data/`, `docs/`, `scripts/`
- **FastAPI backend** — `app/main.py` with CORS, GZip, lifespan, structured logging
- **SQLAlchemy 2.x ORM** — `Project`, `Dataset`, `ProcessingJob`, `Asset` models with PostGIS geometry columns
- **PostGIS support** — `GeoAlchemy2` for spatial geometry storage; `CREATE EXTENSION postgis` on startup
- **Pydantic schemas** — full request/response types for all entities
- **REST API** — health check, project CRUD, dataset upload, processing job status
- **Background job system** — FastAPI `BackgroundTasks` for async validation and processing
- **Dataset validation** — file type checking, size validation, type inference from extension
- **React + TypeScript + Vite frontend** — scaffolded with `create-vite`
- **CesiumJS integration** — globe with OpenStreetMap imagery, no token required
- **Cesium static assets** — via `vite-plugin-static-copy` (Workers, Assets, Widgets)
- **Zustand state stores** — `AppStore` (projects/datasets) + `ViewerStore` (layers/camera/FPS)
- **Professional dark UI** — Inter + JetBrains Mono, dark theme, glassmorphism accents
- **Left sidebar** — project management, dataset listing, layer controls, analysis stubs, AI stubs
- **Right panel** — object inspector + dataset metadata
- **Bottom bar** — cursor coordinates, camera altitude, position, FPS counter
- **Top bar** — brand, backend status indicator, version, live clock
- **Layer toggles** — terrain, point cloud, mesh, buildings, vegetation, roads, imagery, boundaries
- **Docker Compose** — PostgreSQL/PostGIS + backend + frontend services
- **`.env.example`** — all configuration options documented
- **Documentation** — README, PROJECT_STATUS, ROADMAP, ARCHITECTURE, CHANGELOG

### Architecture Decisions
- CesiumJS over custom 3D engine — industry standard, avoids reinventing geospatial rendering
- SQLAlchemy async — matches FastAPI's async nature; PostGIS for all spatial data
- Zustand over Redux — dramatically less boilerplate for this use case
- BackgroundTasks over Celery — sufficient for MVP 1; designed to swap out later
- OSM imagery by default — no Cesium Ion token required for initial development

### Not Yet Implemented (Phase 2+)
- GDAL raster processing
- PDAL point cloud processing
- Open3D 3D processing
- Real terrain display in viewer
- 3D Tiles point cloud display
- WebODM integration
- AI classification
- Spatial analysis tools
