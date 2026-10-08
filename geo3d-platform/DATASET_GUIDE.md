# Geo3D Platform — Dataset Guide & Data Catalog

This guide provides technical specifications, download sources, licensing, coordinate reference systems (CRS), and ingestion instructions for datasets supported by the **Geo3D Platform**.

---

## 1. Supported Data Modalities & File Formats

| Modality | Formats | Ingestion Engine | Web Output Product |
|---|---|---|---|
| **Airborne / Terrestrial LiDAR** | `.las`, `.laz`, `.ply` | PDAL + Laspy | OGC 3D Tiles (`.pnts`), Potree COPC, DTM/DSM |
| **Elevation Rasters** | `.tif`, `.tiff`, `.dem` | GDAL | Terrain Mesh, Slope/Aspect, Contours, Hillshade |
| **Drone Photogrammetry** | `.jpg`, `.png`, `.zip` | WebODM / NodeODM | Orthophoto GeoTIFF, Textured GLB Mesh, DSM |
| **Vector Layers** | `.geojson`, `.shp` | GeoPandas + Shapely | Cesium Vector Polylines / Polygons |
| **AI Benchmarks** | `.las`, `.laz` | DALES-2 Adapter | 15 Semantic Classes, 3D Bounding Boxes |

---

## 2. Standard Datasets in the Platform

### A. OpenTopography: San Diego Urban Region LiDAR
* **Catalog ID**: `OTLAS.092011.2875.1`
* **Geographic Extent**: San Diego, California (Urban core, Balboa Park, Coronado Bay)
* **Coordinate Reference System (CRS)**: Projected `EPSG:26911` (NAD83 / UTM Zone 11N) with NAVD88 vertical datum
* **Point Density**: 8–12 points/$m^2$
* **Total Points**: ~28,000,000 points across primary tiles
* **Classifications**: ASPRS Standard (1: Unclassified, 2: Ground, 3: Low Veg, 4: Medium Veg, 5: High Veg, 6: Building, 7: Noise)
* **License**: Public Domain (NSF / OpenTopography)
* **Why Selected**: Ideal standard benchmark for testing urban ground filtering (SMRF), building footprint extraction, and elevation profiling across variable slope relief.

### B. DALES-2 Benchmark Dataset (Dayton Annotated LiDAR Earth Scan)
* **Source**: University of Dayton / HuggingFace `mbendjilali/DALES-2`
* **Sensor**: Riegl Q680i airborne scanner
* **CRS**: `EPSG:32616` (WGS 84 / UTM Zone 16N)
* **Resolution**: ~50 points/$m^2$
* **Semantic Classes (15)**:
  1. Ground
  2. Vegetation
  3. Cars
  4. Trucks
  5. Powerlines
  6. Fences
  7. Poles
  8. Buildings
  9. etc.
* **Why Selected**: Real-world airborne LiDAR specifically designed for 3D instance segmentation and 3D bounding box detection without synthetic artifacts.

### C. Drone Photogrammetry: Aukerman & GL3D Datasets
* **Sensors**: DJI Phantom 4 RTK / Sony Alpha
* **Modalities**: High-resolution overlapping RGB aerial nadir/oblique imagery
* **Processing Tool**: WebODM / NodeODM
* **Generated Outputs**:
  * `orthophoto.tif` — 2 cm Ground Sampling Distance (GSD)
  * `textured_mesh.glb` — High-polygon 3D surface model with baked texture atlas
  * `dsm.tif` / `dtm.tif` — High-resolution digital elevation rasters
* **Why Selected**: Validates the end-to-end drone pipeline: image upload $\to$ OpenDroneMap execution $\to$ 3D mesh rendering in CesiumJS.

---

## 3. Data Ingestion Guidelines

### 3.1 Pre-Ingestion Validation Rules
When ingesting any file via the Web UI or API (`POST /api/projects/{id}/datasets`), the platform automatically verifies:
1. **Magic Bytes & Header**: Confirms valid `LASF` signature for LAS/LAZ or GeoTIFF directory tags.
2. **CRS Identification**: Inspects VLR (Variable Length Record) projections; falls back to project CRS if unprojected.
3. **Bounding Extent**: Re-projects native coordinates to WGS84 (`EPSG:4326`) and checks for coordinate flips or polar anomalies.
4. **Point Count & File Size**: Large files (> 1 GB) automatically trigger the chunked streaming pipeline (`iter_point_chunks`) to prevent server memory exhaustion.

### 3.2 Ingesting via CLI Scripts

To ingest benchmark datasets into your local development instance:

```powershell
# Ingest Dayton DALES-2 / San Diego Urban LiDAR
cd backend
.\venv\Scripts\python.exe ..\scripts\setup\ingest_dales2.py

# Verify scene geometry and GLB models
python ..\scripts\verify_scenes.py
```
