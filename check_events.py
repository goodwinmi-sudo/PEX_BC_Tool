import os
from google.cloud import datastore

GCP_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945')
datastore_client = datastore.Client(project=GCP_PROJECT)

job_id = '43aff9dd-a427-4a4f-b30b-8370d3acab67'
job_key = datastore_client.key('SimulationJob', job_id)

query = datastore_client.query(kind='SimulationEvent', ancestor=job_key)
query.order = ['timestamp']
events = list(query.fetch())

print(f"Total events found: {len(events)}")
for idx, e in enumerate(events):
    print(f"[{idx}] {e.get('timestamp')}: type={e.get('type')}, msg={e.get('title') or e.get('message') or e.get('error')}")

job = datastore_client.get(job_key)
print(f"Job Status: {job.get('status')} | Error: {job.get('error')}")
