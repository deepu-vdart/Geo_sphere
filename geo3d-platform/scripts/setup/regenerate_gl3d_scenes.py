"""
Regenerate GL3D Sample Scene 3D Models & Point Clouds.
Rebuilds unique .glb, .obj, and .ply files for every scene in data/processed/gl3d/
and updates data/geo3d.db SQLite database records with unique anchors and metadata.

Usage:
  cd backend
  .\\venv\\Scripts\\python.exe ..\\scripts\\setup\\regenerate_gl3d_scenes.py
"""

import os
import sys
import json
import sqlite3
import logging

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.providers.gl3d import GL3D_SAMPLE_SCENES, GL3DProvider
from app.processing.gl3d_proc.gl3d_processor import GL3DProcessor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_GL3D_DIR = os.path.join(ROOT_DIR, "data", "processed", "gl3d")
DB_PATH = os.path.join(ROOT_DIR, "data", "geo3d.db")


def main():
    print("=" * 70)
    print("  Regenerating GL3D 3D Models and Point Clouds (Unique per Scene)")
    print("=" * 70)

    provider = GL3DProvider()

    # Map scene_id -> scene info
    scene_lookup = {s["scene_id"]: s for s in GL3D_SAMPLE_SCENES}

    # Find existing processed scene directories or process all sample scenes
    existing_dirs = []
    if os.path.isdir(PROCESSED_GL3D_DIR):
        existing_dirs = [d for d in os.listdir(PROCESSED_GL3D_DIR)
                         if os.path.isdir(os.path.join(PROCESSED_GL3D_DIR, d))]

    target_scene_ids = list(set(existing_dirs + [s["scene_id"] for s in GL3D_SAMPLE_SCENES[:5]]))
    print(f"Target scenes to regenerate: {len(target_scene_ids)}")

    processed_results = {}

    for scene_id in target_scene_ids:
        scene_info = scene_lookup.get(scene_id, {})
        category = scene_info.get("category", "urban")
        name = scene_info.get("name", f"GL3D Scene {scene_id[:8]}")
        anchor = scene_info.get("anchor", {"lon": 8.5417, "lat": 47.3769, "alt": 450.0})

        print(f"\n[Processing] {name}")
        print(f"  ID:       {scene_id}")
        print(f"  Category: {category}")
        print(f"  Anchor:   Lon {anchor['lon']}, Lat {anchor['lat']}, Alt {anchor['alt']}m")

        scene_dir = provider.get_scene_data_dir(scene_id)
        os.makedirs(scene_dir, exist_ok=True)

        output_dir = os.path.join(PROCESSED_GL3D_DIR, scene_id)
        os.makedirs(output_dir, exist_ok=True)

        processor = GL3DProcessor(scene_dir, max_total_points=200000, category=category)
        metadata = processor.process(output_dir)

        # Attach unique anchor & center
        metadata["anchor"] = anchor
        metadata["center"] = {
            "lon": anchor["lon"],
            "lat": anchor["lat"],
            "alt": anchor["alt"],
        }
        metadata["name"] = name
        metadata["description"] = scene_info.get("description", "")

        processed_results[scene_id] = metadata

        glb_size = os.path.getsize(metadata["glb_path"]) if os.path.exists(metadata.get("glb_path", "")) else 0
        ply_size = os.path.getsize(metadata["ply_path"]) if os.path.exists(metadata.get("ply_path", "")) else 0
        print(f"  [Output] GLB: {glb_size / 1024:.1f} KB, PLY: {ply_size / 1024:.1f} KB ({metadata['point_count']} pts)")
        print(f"  [Triangles] {metadata.get('triangle_count', '?')}, Vertices: {metadata.get('vertex_count', '?')}")

    # Update SQLite database if present
    if os.path.exists(DB_PATH):
        print(f"\nUpdating database at {DB_PATH}...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check datasets joined with projects
        cursor.execute("""
            SELECT d.id, d.name, d.file_path, p.id, p.name
            FROM datasets d
            JOIN projects p ON d.project_id = p.id
            WHERE d.dataset_type = 'gl3d_scene' OR d.file_format = 'ply'
        """)
        rows = cursor.fetchall()
        print(f"Found {len(rows)} GL3D/PLY dataset records in database.")

        updated_count = 0
        for ds_id, ds_name, ds_path, proj_id, proj_name in rows:
            matched_scene_id = None

            p_lower = (proj_name or "").lower()
            if "scene 2" in p_lower or "pagoda" in p_lower:
                matched_scene_id = "000000000000000000000002"
            elif "scene 16" in p_lower or "bronze" in p_lower or "ding" in p_lower:
                matched_scene_id = "000000000000000000000010"
            elif "scene 5" in p_lower or "dense urban" in p_lower:
                matched_scene_id = "000000000000000000000005"
            elif "desert" in p_lower or "coastal" in p_lower:
                matched_scene_id = "56d73ba74bd29b8c35abade2"
            elif "heritage" in p_lower or "kiln" in p_lower:
                matched_scene_id = "563de9bfba4f35d92bd2d07e"
            elif "rural" in p_lower or "terrace" in p_lower:
                matched_scene_id = "000000000000000000000008"
            elif "scene 0" in p_lower or "high-rise" in p_lower or "urban" in p_lower:
                matched_scene_id = "000000000000000000000000"

            if matched_scene_id and matched_scene_id in processed_results:
                meta = processed_results[matched_scene_id]
                ply_path = meta["ply_path"]
                file_size = os.path.getsize(ply_path) if os.path.exists(ply_path) else 0
                cam_count = meta.get("camera_count", 120)
                new_ds_name = f"GL3D Scene {matched_scene_id[:8]}… ({cam_count} cameras)"
                anchor = meta["anchor"]

                cursor.execute("""
                    UPDATE datasets
                    SET name = ?,
                        metadata_json = ?,
                        file_path = ?,
                        file_size_bytes = ?,
                        point_count = ?,
                        min_z = ?,
                        max_z = ?
                    WHERE id = ?
                """, (
                    new_ds_name,
                    json.dumps(meta),
                    ply_path,
                    file_size,
                    meta["point_count"],
                    meta.get("extent", {}).get("min_z", 0.0),
                    meta.get("extent", {}).get("max_z", 50.0),
                    ds_id,
                ))

                new_loc = f"{meta['category'].capitalize()} · Lat {anchor['lat']:.4f}°, Lon {anchor['lon']:.4f}°"
                cursor.execute("UPDATE projects SET location_name = ? WHERE id = ?", (new_loc, proj_id))

                updated_count += 1
                print(f"  Linked Project '{proj_name}' -> Scene {matched_scene_id[:8]} ({meta['name']}) [Anchor: {anchor['lat']}, {anchor['lon']}]")

        conn.commit()
        conn.close()
        print(f"[SUCCESS] Correctly mapped and updated {updated_count} project-dataset records in database.")
    else:
        print(f"[NOTE] Database {DB_PATH} not found. File generation complete.")

    print("\n[COMPLETE] All scenes regenerated with unique models, point clouds, and anchors!")


if __name__ == "__main__":
    main()
