import json
import time
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

def process_task(url, headers, body, retry_count=0):
    """Simulates async task execution and dispatching with basic retries."""
    # Simulate queue processing delay
    time.sleep(1) 
    print(f"[{time.strftime('%X')}] Emulator dispatching task to {url} (Retry {retry_count})")
    
    try:
        response = requests.post(url, headers=headers, data=body, timeout=30)
        print(f"[{time.strftime('%X')}] Worker responded with status {response.status_code}")
        if response.status_code >= 500 and retry_count < 3:
            print(f"[{time.strftime('%X')}] Retrying task...")
            # Simulate backoff
            time.sleep(2 ** retry_count)
            process_task(url, headers, body, retry_count + 1)
    except Exception as e:
        print(f"[{time.strftime('%X')}] Task dispatch failed: {e}")
        if retry_count < 3:
            print(f"[{time.strftime('%X')}] Retrying task...")
            time.sleep(2 ** retry_count)
            process_task(url, headers, body, retry_count + 1)


@app.route('/enqueue', methods=['POST'])
def enqueue_task():
    try:
        data = request.json
        
        # Validate expected Cloud Tasks payload structure
        task_data = data.get('task', {})
        http_request = task_data.get('http_request', {})
        
        url = http_request.get('url')
        headers = http_request.get('headers', {})
        body = http_request.get('body', {})  # Passed as base64 or raw string from client
        
        if not url:
            return jsonify({"error": "Missing url in http_request"}), 400
            
        print(f"[{time.strftime('%X')}] Task received for {url}. Queuing execution.")

        # Dispatch async thread to simulate Cloud Tasks execution
        threading.Thread(target=process_task, args=(url, headers, body), daemon=True).start()
        
        return jsonify({"name": f"projects/emulator/locations/local/queues/local/tasks/emulated-{time.time()}"}), 200

    except Exception as e:
        print(f"Emulator error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Emulator runs on 8123
    app.run(host='0.0.0.0', port=8123)
