import os
import sys
import uuid
import json
import time

# Ensure we can import from PEX_BC_Tool
sys.path.append('/usr/local/google/home/goodwinmi/PEX_BC_Tool')
from google.cloud import datastore
from google.oauth2.credentials import Credentials

from services import native_runner
from services import ai_engine

GCP_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945')
datastore_client = datastore.Client(project=GCP_PROJECT)

def get_credentials_from_datastore():
    query = datastore_client.query(kind='SimulationJob')
    query.add_filter('status', '=', 'completed')
    query.order = ['-created_at']
    jobs = list(query.fetch(limit=1))
    
    if not jobs:
        print("No completed jobs to pull credentials from.")
        return None
        
    job_key = jobs[0].key
    job = datastore_client.get(job_key)
    payload_str = job.get('payload')
    
    if not payload_str:
        return None
        
    payload = json.loads(payload_str)
    creds_json = payload.get('creds_json')
    if creds_json:
        return Credentials.from_authorized_user_info(creds_json)
    return None

def test_headless_native(source_deck_id=None, method="template"):
    print("Extracting user credentials from Datastore...")
    creds = get_credentials_from_datastore()
    if not creds:
        print("Failed to acquire credentials.")
        return
        
    job_id = str(uuid.uuid4())
    print(f"Executing HEADLESS SIMULATION LOCAL. Job ID: {job_id}")
    
    deal_desc = "Project Velocity - Autonomous Vehicles Compute Partnership. Asking for 3yr 100M commit for exclusivity."
    org_filter = "Global"
    deal_size_str = "100M"
    risk_flags = []
    
    # Run the native generation directly
    try:
        native_runner.execute_simulation_job(
            job_id,
            creds,
            source_deck_id,
            deal_desc,
            org_filter,
            method,
            deal_size_str,
            risk_flags
        )
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="template", choices=["clone", "template"])
    parser.add_argument("--source", default=None, help="Source deck ID")
    args = parser.parse_args()
    
    test_headless_native(source_deck_id=args.source, method=args.mode)
