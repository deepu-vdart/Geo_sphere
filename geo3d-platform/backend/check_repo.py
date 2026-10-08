import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
req = urllib.request.Request(
    'https://api.github.com/repos/OpenDroneMap/odm_data_aukerman/contents/images',
    headers={'User-Agent': 'Mozilla/5.0'}
)
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        data = json.loads(response.read().decode())
        print(f"Total images found: {len(data)}")
        for item in data[:10]:
            print(f"- {item['name']} ({item.get('size', 0)} bytes, download: {item.get('download_url')})")
except Exception as e:
    print("Error:", e)
