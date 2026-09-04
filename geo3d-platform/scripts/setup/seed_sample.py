"""
Seed a demo project and upload sample LAS LiDAR dataset to test the platform.
"""

import httpx
import os
import time

BASE_URL = "http://127.0.0.1:8000/api"
SAMPLE_LAS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "samples", "sample_terrain.las")
)

def main():
    print("Connecting to backend at", BASE_URL)
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 1. Create project
    proj_resp = client.post("/projects", json={
        "name": "Boulder Colorado LiDAR Survey",
        "description": "Demonstration UTM 13N terrain dataset with ground, vegetation, and buildings",
        "location_name": "Boulder, Colorado"
    })
    proj = proj_resp.json()
    project_id = proj["id"]
    print(f"[OK] Created project: {proj['name']} (ID: {project_id})")

    # 2. Upload dataset
    if not os.path.exists(SAMPLE_LAS):
        print("Sample LAS not found at", SAMPLE_LAS)
        return

    with open(SAMPLE_LAS, "rb") as f:
        upload_resp = client.post(
            f"/projects/{project_id}/datasets",
            data={
                "name": "Boulder Terrain Point Cloud (70k pts)",
                "description": "High resolution LiDAR point cloud with ASPRS classes"
            },
            files={"file": ("sample_terrain.las", f, "application/octet-stream")}
        )
    dataset = upload_resp.json()
    dataset_id = dataset["id"]
    print(f"[OK] Uploaded dataset: {dataset['name']} (ID: {dataset_id})")

    # 3. Wait 1 sec for background validation
    time.sleep(1.5)

    # 4. Trigger 3D processing
    proc_resp = client.post(f"/datasets/{dataset_id}/process")
    job = proc_resp.json()
    print(f"[OK] Triggered 3D Processing Job: {job['id']} (Status: {job['status']})")

    # 5. Wait for processing to complete
    for _ in range(10):
        time.sleep(1)
        ds_resp = client.get(f"/datasets/{dataset_id}")
        ds_data = ds_resp.json()
        if ds_data["processing_status"] in ("ready", "validated"):
            print(f"[SUCCESS] Dataset processing complete! Status: {ds_data['processing_status']}")
            print(f"   Points: {ds_data.get('point_count'):,}")
            print(f"   Elevation: {ds_data.get('min_z')}m to {ds_data.get('max_z')}m")
            print(f"   CRS: {ds_data.get('crs')}")
            break

if __name__ == "__main__":
    main()
