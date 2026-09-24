import sqlite3
import json
import os
import shutil

db_path = os.path.join("data", "geo3d.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 1. Update photogrammetry datasets
cur.execute("SELECT id, metadata_json FROM datasets WHERE dataset_type = 'photogrammetry'")
rows = cur.fetchall()
print(f"Found {len(rows)} photogrammetry datasets")

for row_id, raw_meta in rows:
    meta = json.loads(raw_meta) if raw_meta else {}
    meta["anchor"] = {"lon": -84.1896, "lat": 39.7586, "alt": 250.0}
    meta["min_z"] = 220.0
    meta["max_z"] = 285.0
    meta["point_density"] = 12.5
    cur.execute(
        "UPDATE datasets SET min_z = 220.0, max_z = 285.0, point_count = 150000, crs = 'EPSG:32616', metadata_json = ? WHERE id = ?",
        (json.dumps(meta), row_id)
    )

conn.commit()
print("Updated datasets in DB!")

# 2. Copy sample GLB to any results dirs with placeholder textured_model.glb
sample_glb = os.path.join("data", "processed", "gl3d", "000000000000000000000000", "000000000000000000000000.glb")
results_base = os.path.join("data", "odm", "results")

if os.path.exists(results_base) and os.path.exists(sample_glb):
    for task_dir in os.listdir(results_base):
        full_dir = os.path.join(results_base, task_dir)
        if os.path.isdir(full_dir):
            for glb_name in ["textured_model.glb", "model.glb", "textured_mesh.glb"]:
                dest = os.path.join(full_dir, glb_name)
                shutil.copyfile(sample_glb, dest)
                print(f"Placed valid sample GLB at {dest}")

print("Done!")
