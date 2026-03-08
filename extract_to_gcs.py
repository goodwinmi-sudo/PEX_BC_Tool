import sys
import json
sys.path.append('/app')
from services import slides_engine
import google.auth
from google.cloud import storage

credentials, project = google.auth.default()
client = slides_engine.get_slides_client(credentials)

try:
    data = slides_engine.extract_presentation_data(client, "12_jvbQgUrU1qZuLaXBZqo7-OXEX7ZzQQEnzJfi3R86g")
    
    storage_client = storage.Client()
    bucket = storage_client.get_bucket("internal-xr-ai-tools-977945-sync-assets")
    blob = bucket.blob("reference_deck_extracted.json")
    blob.upload_from_string(json.dumps(data, indent=2), content_type="application/json")
    print("Success uploading to GCS")
except Exception as e:
    print(f"Failed: {e}")
