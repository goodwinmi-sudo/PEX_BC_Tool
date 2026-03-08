import os
os.environ['GOOGLE_CLOUD_PROJECT'] = 'internal-xr-ai-tools-977945'
from google.cloud import datastore

client = datastore.Client()
key = client.key('Job', '8d5c2aff-32cc-4de9-b00f-57d30f2c72dc')
job = client.get(key)

if job and 'events' in job:
    events = job['events']
    print(f"Total events: {len(events)}")
    for i, event in enumerate(events[-30:]):  # print last 30
        print(f"[{len(events) - 30 + i}] {event.get('type')}: {event.get('message', event.get('title', 'NO CONTENT'))}")
else:
    print("Job not found or no events")
