# Geo3D Platform — Roadmap

## MVP 1: Interactive 3D Viewer ✅ CURRENT
**Goal:** Working CesiumJS globe with project/dataset management API

- CesiumJS globe in browser
- Project and dataset CRUD
- Layer controls
- Camera, cursor, FPS tracking
- Backend health API
- PostgreSQL + PostGIS

**Done when:** Browser opens, globe renders, API health returns "ok"

---

## MVP 2: LiDAR Processing 🔜 NEXT
**Goal:** Upload a real LAS/LAZ file → see point cloud in CesiumJS

- PDAL integration for LAS/LAZ reading
- Metadata extraction: CRS, bounds, point count
- Point cloud downsampling for web display
- Ground classification (PDAL SMRF)
- CesiumJS 3D Tiles point cloud display
- Sample dataset from OpenTopography (~100 MB)

**Target dataset:** OpenTopography PC19 or USGS 3DEP LiDAR

---

## MVP 3: Terrain and Spatial Analysis
**Goal:** Generate DTM/DSM, display terrain, enable measurements

- GDAL raster reading (GeoTIFF, DEM)
- DTM/DSM generation from point cloud
- Terrain mesh for CesiumJS
- Hillshade generation
- Elevation profile (line → chart)
- Slope + aspect maps
- Distance measurement (2 points)
- Area measurement (polygon)
- Volume estimation (DTM vs DSM)

---

## MVP 4: Photogrammetry / WebODM
**Goal:** Upload drone images → process → display 3D model

- WebODM API client
- Image upload endpoint
- Processing job monitoring
- Point cloud + mesh import from ODM output
- Textured model display in CesiumJS
- Orthophoto overlay
- DSM/DTM from ODM

---

## MVP 5: Large Dataset Optimization
**Goal:** Handle datasets > 1 GB without browser crash

- 3D Tiles specification compliance
- Point cloud tiling pipeline
- LOD generation
- Tile server integration
- Performance benchmarking

---

## MVP 6: AI Point Cloud Analysis
**Goal:** Classify point cloud objects using DALES-2 trained model

- DALES-2 dataset adapter
- Point cloud classification (ground/buildings/vegetation/vehicles/poles)
- PyTorch model training pipeline
- Classified point cloud display
- Object detection and segmentation

---

## MVP 7: AI Geospatial Assistant
**Goal:** Natural language queries grounded in actual geospatial data

- AI tool functions: get_elevation, find_buildings, calculate_area, etc.
- Scene understanding output
- Query → analysis → highlighted result in CesiumJS
- Grounded responses (no hallucination)

---

## MVP 8: Multi-Temporal Change Detection
**Goal:** Compare two surveys, highlight changes

- Dataset registration
- Difference computation
- Changed area highlighting
- New/removed structure detection
- Terrain change analysis
