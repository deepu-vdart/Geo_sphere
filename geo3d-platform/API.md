# Geo3D Platform — REST API Reference

The Geo3D REST API is built with FastAPI and runs at `http://localhost:8000/api`. Interactive Swagger documentation is available at `http://localhost:8000/api/docs`.

---

## 1. System & Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Comprehensive system health check (DB, storage, version, timestamp) |
| `GET` | `/` | API root metadata |

---

## 2. Projects & Datasets

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/projects` | List active projects |
| `POST` | `/api/projects` | Create a new project (name, location, CRS) |
| `GET` | `/api/projects/{id}` | Get project details |
| `DELETE` | `/api/projects/{id}` | Delete project and cascade delete datasets |
| `GET` | `/api/projects/{id}/datasets` | List all datasets in a project |
| `POST` | `/api/projects/{id}/datasets` | Upload a LAS/LAZ/GeoTIFF dataset file |
| `GET` | `/api/datasets/{id}` | Get dataset metadata, bounds, CRS, and status |
| `POST` | `/api/datasets/{id}/process` | Trigger 3D Tiles processing pipeline |
| `GET` | `/api/datasets/{id}/points-sample` | Get sampled points for browser 3D rendering |
| `GET` | `/api/datasets/{id}/tileset.json` | Serve OGC 3D Tiles tileset.json |
| `GET` | `/api/datasets/{id}/tile.pnts` | Stream binary 3D point cloud tile |

---

## 3. Data Providers (OpenTopography & USGS 3DEP)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/providers` | List active remote LiDAR providers |
| `GET` | `/api/providers/search` | Search OpenTopography & USGS 3DEP catalogs by query or bounding box |
| `GET` | `/api/providers/{provider_id}/{dataset_id}` | Fetch detailed remote dataset metadata |

---

## 4. Area of Interest (AOI)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/aoi/estimate` | Validate AOI, compute area ($m^2, ha, km^2$), and estimate point count & memory size |

---

## 5. Terrain Products & Derivatives

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/terrain/datasets/{id}/derivatives` | Generate DTM, DSM, Hillshade, Slope, Aspect, and Roughness |
| `GET` | `/api/terrain/datasets/{id}/contours` | Generate GeoJSON vector contour lines ($0.5m$ to $10m$ interval) |

---

## 6. Spatial Analysis Suite

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analysis/measure-distance` | Calculate 2D geodesic & 3D Euclidean distances with segment breakdowns |
| `POST` | `/api/analysis/measure-area` | Calculate surface area ($m^2, ha, acres, km^2$) & perimeter |
| `POST` | `/api/analysis/measure-height` | Calculate vertical height difference ($\Delta Z$) and 3D direct distance |
| `POST` | `/api/analysis/elevation-profile` | Generate elevation transect profile with slope and relief stats |
| `POST` | `/api/analysis/slope-aspect` | Analyze slope angles and 8-point compass aspect directions |
| `POST` | `/api/analysis/volume` | Calculate cut, fill, and net volume under a 3D polygon |

---

## 7. AI Geospatial Analyst

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/ai/datasets/{id}/summary` | Generate structured AI terrain intelligence and site suitability report |
