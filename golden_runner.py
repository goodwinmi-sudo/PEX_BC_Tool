import json
import logging
from google.cloud import storage
from services import slides_engine
import google.auth

logger = logging.getLogger(__name__)

credentials, project = google.auth.default()
client = slides_engine.get_slides_client(credentials)

print("Extracting PEX/BC Golden Presentation...")
try:
    data = slides_engine.extract_presentation_data(client, "12_jvbQgUrU1qZuLaXBZqo7-OXEX7ZzQQEnzJfi3R86g")
    
    # Store the output back into GCS
    storage_client = storage.Client()
    bucket = storage_client.get_bucket("internal-xr-ai-tools-977945-sync-assets")
    blob = bucket.blob("golden_deck_extract.json")
    blob.upload_from_string(json.dumps(data, indent=2), content_type="application/json")
    print("Success. Golden deck JSON uploaded to GCS.")
except Exception as e:
    print(f"Extraction failed: {e}")
