import time
import requests
import sys

BASE_URL = "https://deal-reviewer-401242153647.us-central1.run.app"

def run_headless_iteration(source_deck_id=None, method="template", desc=""):
    print(f"Triggering headless iteration. Mode: {method}, Source Deck: {source_deck_id}")
    
    payload = {
        "source_presentation_id": source_deck_id,
        "dealDesc": desc,
        "orgFilter": "Global",
        "method": method,
        "dealSize": "100M",
        "riskFlags": [],
        "engine": "native"
    }
    import google.auth.transport.requests
    from google.oauth2 import id_token
    request = google.auth.transport.requests.Request()
    token = id_token.fetch_id_token(request, BASE_URL)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/api/headless_trigger", json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Error triggering: {response.status_code} - {response.text}")
        sys.exit(1)
        
    job_data = response.json()
    job_id = job_data.get('job_id')
    print(f"Job triggered successfully. Tracking Job ID: {job_id}")
    
    poll_endpoint = f"{BASE_URL}/api/job/{job_id}"
    last_event_count = 0
    
    while True:
        try:
            r = requests.get(poll_endpoint)
            if r.status_code == 200:
                data = r.json()
                status = data.get('status')
                
                events = data.get('events', [])
                if len(events) > last_event_count:
                    for e in events[last_event_count:]:
                        if e.get('type') == 'step':
                            print(f"\n[{e.get('title')}]")
                        elif e.get('type') == 'log':
                            print(f"  > {e.get('message')}")
                        elif e.get('type') == 'done':
                            print(f"\n[DONE] Pipeline Success!")
                            print(f"Final Presentation URL: {e.get('url')}")
                            print(f"\n--- GENERATED SYSTEM JSON/TEXT ---:\n{e.get('payload')}")
                    last_event_count = len(events)
                    
                if status == 'completed':
                    print("\nJob fully completed on server.")
                    break
                elif status == 'failed':
                    print("\nJob failed on server.")
                    break
                    
        except Exception as e:
            print(f"Polling error: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="template", choices=["clone", "template"])
    parser.add_argument("--source", default=None, help="Source deck ID, e.g. 1h12vgnrSF_5J12Dlj3xpCOFIb7gwt9te4UqiDjsgw94")
    parser.add_argument("--desc", default="MFi Certification and Partnership Deal", help="Deal desc")
    args = parser.parse_args()
    
    run_headless_iteration(source_deck_id=args.source, method=args.mode, desc=args.desc)
