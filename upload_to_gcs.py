import os
import json
import subprocess

# Load personas
with open('personas.json', 'r') as f:
    personas = json.load(f).get('executives', [])

name_to_id = {p.get('name', '').lower(): p.get('id', 'default') for p in personas}

bucket_name = os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945') + '-sync-assets'

avatars_dir = 'static/avatars'
for filename in os.listdir(avatars_dir):
    if not (filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg')):
        continue
    
    name = os.path.splitext(filename)[0].lower()
    
    if name in name_to_id:
        pid = name_to_id[name]
        blob_name = f"gs://{bucket_name}/moma_images/{pid}.png"
        
        src_path = os.path.join(avatars_dir, filename)
        
        # Upload using gcloud CLI to bypass missing Workstation oauth scopes
        print(f"Uploading {src_path} -> {blob_name}...")
        subprocess.run(["gcloud", "storage", "cp", src_path, blob_name], check=True)
    else:
        print(f"Warning: Name {name} not found in personas.json")

print("Done uploading avatars to GCS.")
