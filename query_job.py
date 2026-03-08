import json
from google.cloud import datastore
import sys

client = datastore.Client(project="internal-xr-ai-tools-977945")
job_key = client.key('SimulationJob', '3f52f811-6b2a-4180-97d1-19313e2506b6')
query = client.query(kind='SimulationEvent', ancestor=job_key)
events = [dict(e) for e in query.fetch()]
for e in events:
    if e.get("type") == "done":
        payload = e.get("payload")
        print(f"DONE EVENT FOUND. Payload exists? {payload is not None}")
        print(f"Success exists? {e.get('success')}")
        print(f"Error: {e.get('error')}")
