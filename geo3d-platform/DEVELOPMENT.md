# Geo3D Platform — Developer Guide & Setup Manual

This document details the development environment setup, operating system considerations, testing workflows, and architectural rules for contributing to the **Geo3D Platform**.

---

## 1. Prerequisites

* **Operating System**: Windows 10/11, macOS (Apple Silicon/Intel), or Linux (Ubuntu 22.04 LTS).
* **Python**: 3.11 or 3.12 (with `pip` and virtual environment support).
* **Node.js**: v18.x or v20.x LTS (with `npm`).
* **Docker & Docker Compose**: Optional for containerized deployment (e.g., PostGIS, WebODM).

---

## 2. Local Development Setup (Windows PowerShell)

### 2.1 Backend Setup (FastAPI)
```powershell
# Navigate to backend directory
cd backend

# Create & activate Python virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations / start server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
* API Documentation (Swagger UI): `http://127.0.0.1:8000/docs`
* Health Check: `http://127.0.0.1:8000/api/health`

### 2.2 Frontend Setup (React 18 + Vite + CesiumJS)
```powershell
# In a separate terminal, navigate to frontend
cd frontend

# Install Node modules
npm install

# Start Vite development server
npm run dev
```
* Web Viewer Application: `http://localhost:5173`

---

## 3. Containerized Setup (Docker Compose)

To launch the full stack including PostgreSQL with PostGIS:

```bash
docker compose up -d --build
```

To run with the optional WebODM photogrammetry profile:
```bash
docker compose --profile odm up -d
```

---

## 4. Testing & Verification

### Running the Backend Test Suite
All backend pipelines, PDAL filters, DALES-2 adapters, and 3D tiling logic are tested via the unified runner:

```powershell
cd backend
.\venv\Scripts\python.exe tests\run_tests.py
```
Expected output: **25 PASSED, 0 FAILED**.

### Verifying Frontend TypeScript & Bundle Compilation
```powershell
cd frontend
npm run build
```
Builds production-minified assets with `tsc -b && vite build` and 0 errors.

---

## 5. Architectural Rules & Best Practices

1. **Memory Protection on Large Datasets**:
   - Never load raw files $> 1\,\text{GB}$ directly into memory.
   - Use `LASProcessor.iter_point_chunks()` and `extract_sampled_points()`.
   - Ensure binary 3D Tiles headers are strictly 8-byte aligned.
2. **Coordinate Reference System (CRS) Integrity**:
   - Never assume incoming coordinates are WGS84 (`EPSG:4326`).
   - Parse native coordinate system from file headers and Variable Length Records (VLRs).
   - Project coordinates explicitly via `pyproj.Transformer`.
3. **No Fake Functionality**:
   - Every UI tool must correspond to actual calculation routines or be clearly designated as in development.
