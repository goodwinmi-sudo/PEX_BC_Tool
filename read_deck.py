import sys
sys.path.append('/app')
from services import slides_engine
import google.auth

credentials, _ = google.auth.default()
client = slides_engine.get_slides_client(credentials)

print("Fetching reference deck...")
try:
    data = slides_engine.extract_presentation_data(client, "12_jvbQgUrU1qZuLaXBZqo7-OXEX7ZzQQEnzJfi3R86g")
    for d in data:
        print(f"--- SLIDE {d['page_id']} ---")
        for k, v in d['text_boxes'].items():
            if v.strip():
                print(v)
except Exception as e:
    print(f"Failed to fetch deck: {e}")
