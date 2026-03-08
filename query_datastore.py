from google.cloud import datastore
client = datastore.Client()
query = client.query(kind='SimulationJob')
query.order = ['-created_at']
results = list(query.fetch(limit=5))
for res in results:
    print(f"[{res.key.name}] status: {res.get('status')} createdAt: {res.get('created_at')}")
