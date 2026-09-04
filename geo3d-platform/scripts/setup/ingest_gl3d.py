"""
GL3D Scene Downloader and Ingestion Script.
Downloads a sample GL3D photogrammetry scene from GitHub,
processes cameras into a 3D point cloud, and ingests it into the Geo3D Platform.

Usage:
  cd backend
  .\\venv\\Scripts\\python.exe ..\\scripts\\setup\\ingest_gl3d.py
"""

import os
import sys
import time
import httpx

BASE_URL = "http://127.0.0.1:8000/api"

# Sample scene to ingest — Scene 2 has ~1013 images and rich geometry
DEFAULT_SCENE_ID = "000000000000000000000002"

GL3D_SCENES = {
    "000000000000000000000000": "GL3D Scene 0 — Urban Building",
    "000000000000000000000002": "GL3D Scene 2 — Scenic Landmark",
    "000000000000000000000005": "GL3D Scene 5 — Dense Urban Area",
    "000000000000000000000008": "GL3D Scene 8 — Mixed Terrain",
    "563de9bfba4f35d92bd2d07e": "GL3D Altizure Scene — Heritage Site",
}


def check_backend():
    """Verify backend API is running."""
    try:
        resp = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[OK] Backend running: {data.get('version', '?')} ({data.get('environment', '?')})")
            return True
    except Exception as e:
        print(f"[ERROR] Cannot reach backend at {BASE_URL}: {e}")
    return False


def list_available_scenes():
    """List available GL3D scenes from the API."""
    try:
        resp = httpx.get(f"{BASE_URL}/gl3d/scenes", timeout=30.0)
        if resp.status_code == 200:
            scenes = resp.json()
            print(f"\n  Available GL3D Scenes ({len(scenes)}):")
            print(f"  {'ID':<30} {'Name':<45} {'Images':>7} {'Downloaded':>12}")
            print(f"  {'─'*30} {'─'*45} {'─'*7} {'─'*12}")
            for s in scenes:
                dl = "✓ Yes" if s["is_downloaded"] else "  No"
                print(f"  {s['scene_id']:<30} {s['name']:<45} {s['image_count']:>7} {dl:>12}")
            return scenes
    except Exception as e:
        print(f"[WARNING] Could not list scenes: {e}")
    return []


def ingest_scene(scene_id: str, project_name: str = None):
    """Trigger GL3D scene ingestion via the API."""
    print(f"\nIngesting GL3D scene: {scene_id}")
    print(f"Project name: {project_name or '(auto)'}")

    client = httpx.Client(base_url=BASE_URL, timeout=120.0)

    # Trigger ingestion
    payload = {}
    if project_name:
        payload["project_name"] = project_name
    payload["max_points"] = 200000

    resp = client.post(f"/gl3d/scenes/{scene_id}/ingest", json=payload)
    if resp.status_code != 200:
        print(f"[ERROR] Ingestion failed: {resp.status_code} — {resp.text}")
        return None

    result = resp.json()
    print(f"[OK] {result['message']}")

    # Poll for scene processing
    print("\nWaiting for processing to complete...")
    for i in range(60):
        time.sleep(2.0)

        # Check scene status
        try:
            scene_resp = client.get(f"/gl3d/scenes/{scene_id}")
            if scene_resp.status_code == 200:
                scene = scene_resp.json()
                if scene.get("is_downloaded"):
                    print(f"\n[SUCCESS] GL3D Scene {scene_id} Ingested!")
                    print(f"  Cameras: {scene.get('camera_count', '?')}")
                    print(f"  Images: {scene.get('image_count', '?')}")
                    print(f"  Has cameras.txt: {scene.get('has_cameras', False)}")
                    return scene_id
        except Exception:
            pass

        if i % 5 == 0:
            print(f"  ... processing ({i*2}s)")

    print("[TIMEOUT] Processing did not complete in 120s. Check backend logs.")
    return scene_id


def main():
    print("=" * 60)
    print("  Geo3D: GL3D Photogrammetry Scene Ingestion")
    print("=" * 60)

    if not check_backend():
        print("\nPlease start the backend first:")
        print("  cd backend && .\\venv\\Scripts\\activate && uvicorn app.main:app --port 8000 --reload")
        sys.exit(1)

    # List scenes
    scenes = list_available_scenes()

    # Select scene
    scene_id = DEFAULT_SCENE_ID
    if len(sys.argv) > 1:
        scene_id = sys.argv[1]
        print(f"\nUsing command-line scene ID: {scene_id}")
    else:
        print(f"\nUsing default scene: {scene_id}")
        print(f"  (Pass a scene_id as argument to ingest a different scene)")

    # Get scene name
    scene_name = GL3D_SCENES.get(scene_id, f"GL3D Scene {scene_id[:12]}…")

    # Ingest
    result = ingest_scene(
        scene_id=scene_id,
        project_name=f"GL3D: {scene_name}",
    )

    if result:
        print(f"\n[DONE] Scene {result} is processing!")
        print(f"       Open http://localhost:5173 — select the GL3D project")
        print(f"       Camera positions will be visualized in the 3D viewer")
    else:
        print("\n[ERROR] Ingestion failed. Check backend logs.")


if __name__ == "__main__":
    main()
