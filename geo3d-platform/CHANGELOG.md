# Geo3D Platform — Changelog

All notable changes to this project are documented here.

## [0.7.0] — 2026-10-08 — Large Dataset Optimization & OGC 3D Tiles 1.1 Specification (MVP 5)

### Added
- **Chunked Ingestion & Streaming** (`app.processing.pdal_proc.las_processor`):
  - `iter_point_chunks`: Memory-bounded chunk generator streaming binary point records in ~10 MB buffers.
  - `extract_sampled_points`: Streaming strided point extraction to safely process datasets $> 1\,\text{GB}$ with $\le 250\,\text{MB}$ RAM.
- **OGC 3D Tiles 1.1 Specification Compliance** (`app.processing.tiling.tile_generator`):
  - Enforced strict 8-byte boundary alignment across 28-byte `.pnts` header and `FeatureTableJSON`/`FeatureTableBinary` payloads.
  - Hierarchical Octree LOD generation with geometric error calculation and WGS84 bounding regions.
- **High-Performance Tile Server with Caching** (`/api/datasets/{id}/tiles/`):
  - HTTP `ETag` generation, `If-None-Match` checks, and `Cache-Control: public, max-age=604800, immutable` headers.
  - Added `GET /api/datasets/{id}/tiles/stats` telemetry endpoint returning tile counts, total disk MB, and LOD depth.
- **Browser WebGL Memory Protection** (`CesiumViewer.tsx`):
  - Configured `maximumMemoryUsage: 512 MB` to prevent browser tab WebGL out-of-memory crashes.
  - Added progressive resolution and bounding box culling optimizations.
- **Automated Test Suite**:
  - `test_large_dataset_optimization.py` with 5 new unit and benchmark tests (Total test suite: 25/25 passing).

## [0.6.0] — 2026-09-30 — AI Point Cloud Analysis & 3D Object Detection (MVP 6)

### Added
- **DALES-2 Semantic Dataset Adapter** (`app.processing.ai.dales_adapter`):
  - 15 semantic classes: Ground, Vegetation, Cars, Trucks, Vans, Buildings, Utility Poles, Powerlines.
  - Bidirectional translation between DALES-2 and standard ASPRS classes.
- **3D Object Detection & Clustering Engine** (`app.processing.ai.detector`):
  - DBSCAN spatial density clustering and PCA-derived Oriented Bounding Boxes (OBB) & Axis-Aligned Bounding Boxes (AABB).
  - Computes physical metrics: Length $\times$ Width $\times$ Height, bounding volume ($m^3$), heading, and centroid coordinates.
- **CesiumJS 3D Wireframe Rendering** (`CesiumViewer.tsx`):
  - 3D wireframe bounding boxes with category color-coding and distance display conditions.
- **Dual-Tab Classification UI** (`ClassificationPanel.tsx`):
  - 15-class semantic distribution bar charts and interactive 3D Object inventory table with camera focus controls.

## [0.5.0] — 2026-09-21 — Phase 8 Multi-Temporal Change Detection & 3D Difference Visualizer

### Added
- **Multi-Temporal Change Detection Engine** (`app.processing.temporal.change_detection`):
  - Digital Elevation Model of Difference (DoD) algorithm across multi-epoch surveys.
  - Volumetric Cut/Fill analysis computing exact excavation ($m^3$) and deposition ($m^3$) volumes.
  - Structural feature detection isolating newly erected structures and demolished buildings.
  - Dynamic simulation mode synthesizing realistic spatial modifications when single datasets are evaluated.
- **Multi-Temporal REST API** (`/api/temporal/`):
  - `POST /api/temporal/compare` — Comparative DoD execution with optional simulated temporal shift.
  - `GET /api/temporal/demo` — Instant comparison demo across project datasets.
  - `GET /api/temporal/compare/{id}` — Retrieve cached comparison metrics and point clouds.
  - Native support for LAS, LAZ, and PLY point cloud formats via `_extract_dataset_points`.
- **Temporal UI Panel** (`TemporalChangePanel.tsx`):
  - Baseline (T1) vs Comparison (T2) epoch selectors with grid resolution and height threshold controls.
  - Volumetric KPI cards: Cut Volume ($m^3$), Fill Volume ($m^3$), Net Volume ($m^3$), and Modified Footprint ($m^2$).
  - Surface dynamics breakdown: Cut %, Fill %, Stable %, New Structures, and Demolished features.
  - 3D Differential point cloud filter toggles.
- **CesiumJS 3D Difference Visualization** (`CesiumViewer.tsx`):
  - 3D point cloud rendering with dynamic semantic color-coding:
    - 🔴 Cut / Excavation (Red)
    - 🔵 Fill / Deposition (Sky Blue)
    - 🟣 New Structures (Purple)
    - 🟠 Demolished Structures (Orange)
    - 🟢 Stable Terrain (Green)
  - Interactive point inspection showing exact $\Delta Z$, elevation, and classification.
- **Automated Test Suite** (`backend/tests/test_temporal.py`):
  - 4 new unit tests validating cut/fill calculus, thresholding, and simulation mode.

## [0.4.0] — 2026-09-21 — Phase 4 Photogrammetry / WebODM Integration


### Added
- **WebODM REST API Client** (`app.services.odm_service`):
  - Full async client for WebODM authentication, project/task management, and result download.
  - Mock/demo mode when WebODM is not configured — all endpoints return simulated responses.
  - Streaming result download for large assets (orthophoto, DSM, DTM, point cloud, mesh).
- **Photogrammetry Processing Pipeline** (`app.processing.odm_proc.odm_processor`):
  - End-to-end pipeline: image upload → ODM project creation → processing → result download.
  - Auto-import of ODM outputs (orthophoto, DSM, DTM, dense point cloud, textured mesh) into Geo3D catalog.
  - Background task execution with real-time progress tracking (QUEUED → RUNNING → COMPLETED).
- **8 New REST API Endpoints** (`/api/odm/`):
  - `GET /api/odm/health` — WebODM connectivity & node status.
  - `GET /api/odm/nodes` — List processing nodes.
  - `POST /api/odm/projects/{id}/tasks` — Upload images & start photogrammetry.
  - `GET /api/odm/tasks/{id}` — Task status & progress polling.
  - `GET /api/odm/tasks` — List all tasks with filters.
  - `GET /api/odm/tasks/{id}/results` — Available result assets.
  - `POST /api/odm/tasks/{id}/import` — Import results into dataset catalog.
  - `DELETE /api/odm/tasks/{id}` — Cancel & delete tasks.
- **Photogrammetry UI Panel** (`ODMPanel.tsx`):
  - Drag-and-drop drone image upload zone with thumbnail preview.
  - Processing options: quality preset, DSM/DTM toggles.
  - Live task list with status badges, progress bars, and import/delete actions.
  - WebODM connection indicator with node count.
- **Docker Compose WebODM** (optional profile):
  - `docker-compose --profile odm up` starts WebODM + NodeODM alongside the Geo3D stack.
  - Separate volumes for ODM media and processing data.
- **Model & Schema Extensions**:
  - `ProcessingJob.odm_task_id` and `odm_project_id` columns for WebODM task tracking.
  - New Pydantic schemas: `ODMHealthResponse`, `ODMTaskCreate`, `ODMTaskResponse`, `ODMResultsResponse`, `ODMImportResponse`.
- **Config Updates**:
  - `ODM_DIR`, `ODM_UPLOADS_DIR`, `ODM_RESULTS_DIR` storage directories.
  - `ODM_MAX_IMAGES` setting (default: 500).

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
