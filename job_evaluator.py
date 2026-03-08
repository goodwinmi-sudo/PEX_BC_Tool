import sys
import os
from google.cloud import storage

print("Dynamically fetching runner script from GCS...")
try:
    client = storage.Client()
    bucket = client.bucket("internal-xr-ai-tools-977945-sync-assets")
    blob = bucket.blob("dynamic_runner.py")
    script_content = blob.download_as_string().decode('utf-8')
    print("Executing dynamic_runner.py...")
    # Add app directory to path for imports
    sys.path.append('/app')
    exec(script_content, globals())
except Exception as e:
    print(f"Failed to execute dynamic runner: {e}")
