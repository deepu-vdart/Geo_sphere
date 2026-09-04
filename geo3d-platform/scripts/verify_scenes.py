import urllib.request
import json

projects_data = json.loads(urllib.request.urlopen("http://localhost:8000/api/projects").read())["projects"]
print(f"Total projects: {len(projects_data)}\n")

for p in projects_data:
    p_id = p["id"]
    p_name = p["name"]
    ds_resp = json.loads(urllib.request.urlopen(f"http://localhost:8000/api/projects/{p_id}/datasets").read())
    datasets = ds_resp["datasets"]
    if not datasets:
        continue
    ds = datasets[0]
    ds_id = ds["id"]
    ds_name = ds["name"]
    meta = ds.get("metadata_json") or {}
    anchor = meta.get("anchor") or {}

    try:
        glb_bytes = len(urllib.request.urlopen(f"http://localhost:8000/api/datasets/{ds_id}/model.glb").read())
    except Exception as e:
        glb_bytes = str(e)

    try:
        pts_data = json.loads(urllib.request.urlopen(f"http://localhost:8000/api/datasets/{ds_id}/points-sample?sample_size=5").read())
        first_pt = pts_data.get("points", [{}])[0]
    except Exception as e:
        first_pt = {}

    cat = meta.get("category")
    tris = meta.get("triangle_count")
    verts = meta.get("vertex_count")

    print(f"Project: {p_name}")
    print(f"  Dataset: {ds_name}")
    print(f"  Category: {cat} | Triangles: {tris} | Vertices: {verts}")
    print(f"  GLB Model Size: {glb_bytes} bytes")
    print(f"  Anchor: Lon={anchor.get('lon')}, Lat={anchor.get('lat')}, Alt={anchor.get('alt')}")
    print(f"  Point 0: Lon={first_pt.get('lon')}, Lat={first_pt.get('lat')}, Alt={first_pt.get('alt')}")
    print("-" * 65)
