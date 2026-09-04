# Geo3D LiDAR Digital Twin & Terrain Analysis Platform

A web-based 3D geospatial digital twin and LiDAR processing platform for terrain analysis, point cloud classification, and digital elevation modeling.

Built with **FastAPI**, **CesiumJS**, **PDAL**, **GDAL**, **React 18**, and **TypeScript**.

---

## 🌟 Key Features

1. **Multi-Source LiDAR Ingestion**:
   - **OpenTopography**: Seamless catalog discovery including *2005 San Diego Urban Region LiDAR* (`OTLAS.092011.2875.1`).
   - **USGS 3DEP**: Integration with public-domain 3D Elevation Program point clouds.
   - **User File Ingestion**: Drag-and-drop `.las`, `.laz`, and GeoTIFF datasets.
2. **PDAL Pipeline Architecture**:
   - Declarative JSON pipelines in `processing/pipelines/` for inspection, cropping, ground classification (SMRF), outlier noise filtering, and DTM/DSM generation.
3. **Terrain Derivatives Engine**:
   - **DTM** (Digital Terrain Model) & **DSM** (Digital Surface Model)
   - **Hillshade** (Multi-directional solar illumination)
   - **Slope & Aspect** (Horn's gradient method in degrees & 8-point compass facing)
   - **Roughness** (Terrain Ruggedness Index / TRI)
   - **Vector Contours** (GeoJSON isolines at 0.5m, 1m, 2m, 5m, 10m intervals)
4. **Interactive CesiumJS 3D Viewer**:
   - High-density point cloud rendering (200,000+ points at 60 FPS).
   - Dynamic coloring: **Elevation Ramp**, **ASPRS Classification**, **Intensity**, and **RGB**.
   - Point classification filtering (Ground, Buildings, Trees, Water, Poles, Noise).
   - **True Point Picking**: Click any point in the 3D scene to inspect exact XYZ coordinates, classification, and intensity.
5. **Spatial Analysis & Measurement Suite**:
   - **3D Distance**: 2D geodesic & 3D Euclidean distances with segment breakdowns.
   - **Surface Area**: Polygon area in $m^2$, hectares, acres, and $km^2$.
   - **Height Difference**: Vertical $\Delta Z$ altitude rods.
   - **Elevation Profile**: Interactive SVG transect chart with slope/relief stats and 3D hover sync.
   - **Cut-Fill Volume**: Volumetric estimation under 3D polygons.
6. **AI Geospatial Analyst**:
   - Structured terrain metric summarization, site suitability scoring, and actionable geospatial insights.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Node.js** (v18+)
- **Python** (3.11 or 3.12)
- **Docker & Docker Compose** (optional for containerized setup)

### 2. Running Locally

#### Backend (FastAPI)
```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```
API runs at `http://localhost:8000/api` (Swagger UI at `/api/docs`).

#### Frontend (React + Vite + CesiumJS)
```powershell
cd frontend
npm install
npm run dev
```
Viewer runs at `http://localhost:5173`.

#### Ingest Sample LiDAR (Dayton DALES-2 / San Diego)
```powershell
cd backend
.\venv\Scripts\python.exe ..\scripts\setup\ingest_dales2.py
```

---

## 🧪 Testing

Run unit and integration test suite:
```powershell
cd backend
pytest tests/ -v
```

Verify frontend build:
```powershell
cd frontend
npm run build
```

---

## 📚 Documentation

- [Architecture Guide](file:///c:/project/geo3d-platform/ARCHITECTURE.md)
- [Data Pipeline Specification](file:///c:/project/geo3d-platform/DATA_PIPELINE.md)
- [REST API Reference](file:///c:/project/geo3d-platform/API.md)
- [Project Status & Checklist](file:///c:/project/geo3d-platform/PROJECT_STATUS.md)
