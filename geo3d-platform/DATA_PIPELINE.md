# Geo3D Platform — Data Pipeline Specification

The Geo3D data pipeline ingests raw airborne/terrestrial LiDAR (`.las`/`.laz`) and elevation rasters (`.tif`/`.dem`), performs spatial coordinate transformation, runs classification and filtering pipelines, produces derivative terrain models (DTM, DSM, Hillshade, Slope, Contours), tiles point clouds for OGC 3D Tiles streaming, and feeds structured summaries to the AI geospatial interpretation layer.

---

## 1. End-to-End Pipeline Workflow

```
               ┌────────────────────────┐
               │    Raw LiDAR / LAZ     │
               │ (OpenTopo, USGS, User) │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   1. File Validation   │
               │   & Header Inspection  │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │  2. CRS Transformation │
               │   (Source -> EPSG:4326)│
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   3. Outlier / Noise   │
               │       Filtering        │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │  4. Ground / Building  │
               │     Classification     │
               └─────┬────────────┬─────┘
                     │            │
       ┌─────────────┘            └─────────────┐
       ▼                                        ▼
┌───────────────────────────┐      ┌───────────────────────────┐
│ 5. Terrain Derivatives    │      │ 6. 3D Web Tiling          │
│ - DTM (Ground Only)       │      │ - OGC 3D Tiles (.pnts)    │
│ - DSM (Surface / Max)     │      │ - LOD Spatial Indexing    │
│ - Hillshade (Solar Model) │      │ - RTC Center Transform    │
│ - Slope & Aspect          │      │ - Classification Ramps    │
│ - Roughness (TRI)         │      └─────────────┬─────────────┘
│ - Vector Contours         │                    │
└─────────────┬─────────────┘                    │
              │                                  │
              └──────────────┬───────────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │ 7. CesiumJS 3D Digital Twin │
              │ & Spatial Analysis Suite    │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │ 8. AI Geospatial Analyst    │
              │ (Structured Scene Summary)  │
              └─────────────────────────────┘
```

---

## 2. Pipeline Stages

### Stage 1: Ingestion & Validation
- **Formats**: `.las`, `.laz`, `.ply`, `.tif`, `.geotiff`, `.dem`
- **Validation**: Header signature (`LASF`), offset/scale factors, point record count, bounding box sanity checks.
- **CRS Detection**: Scans VLRs (Record ID 2112 for WKT, Record ID 34735 for GeoKey tags), falls back to provider/project CRS (e.g. `EPSG:32616` UTM 16N or `EPSG:26911` UTM 11N).

### Stage 2: Declarative PDAL Processing
Stored in `processing/pipelines/`:
- `inspect.json`: Reads stats, dimensions, and ASPRS classification histogram.
- `crop.json`: High-speed spatial bounding box and polygon cropper.
- `ground.json`: Simple Morphological Filter (SMRF) ground classification.
- `noise.json`: Statistical outlier removal.
- `dtm.json`: Ground point grid rasterizer using Inverse Distance Weighting (IDW).
- `dsm.json`: Surface point maximum elevation rasterizer.
- `tiles.json`: Subsamples points and converts to OGC 3D Tiles.

### Stage 3: Terrain Derivatives Engine
- **DTM (Digital Terrain Model)**: 1m cell resolution raster generated exclusively from ASPRS Class 2 (Ground) points.
- **DSM (Digital Surface Model)**: 1m cell resolution raster capturing building roofs and tree canopies.
- **Hillshade**: Multi-directional solar illumination model ($Azimuth = 315^\circ$, $Altitude = 45^\circ$).
- **Slope & Aspect**: Horn's method calculating gradient degrees ($0^\circ - 90^\circ$) and compass bearing ($0^\circ - 360^\circ$).
- **Roughness (TRI)**: Terrain Ruggedness Index calculating local standard deviation in 3x3 neighborhoods.
- **Vector Contours**: GeoJSON isolines at configurable $0.5m$, $1m$, $2m$, $5m$, $10m$ intervals.

### Stage 4: 3D Visualization & Streaming
- Converts coordinates to Earth-Centered Earth-Fixed (ECEF `EPSG:4978`).
- Computes `RTC_CENTER` (Relative To Center) for high floating-point precision on the GPU.
- Serves streamable OGC 3D Tiles and downsampled point arrays for real-time 60 FPS in CesiumJS.

### Stage 5: AI Geospatial Analysis Layer
- Synthesizes metrics into structured JSON summaries (relief, mean slope, urban building density, vegetation ratio).
- Generates automated development suitability and hazard recommendations.
