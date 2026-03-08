import logging

logger = logging.getLogger(__name__)

import os
import json
import threading
from google.cloud import secretmanager

# GCP Project ID required for Secret Manager
GCP_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945')

_secret_cache = {}
_secret_lock = threading.RLock()

def get_secret(secret_id, version_id="latest"):
    """
    Fetches a secret from Google Cloud Secret Manager.
    Caches the secret payload locally to reduce API latency.
    Returns the string payload of the secret or None if it fails.
    """
    global _secret_cache
    
    cache_key = f"{secret_id}:{version_id}"
    
    if cache_key in _secret_cache:
        return _secret_cache[cache_key]
        
    with _secret_lock:
        if cache_key in _secret_cache:
            return _secret_cache[cache_key]
            
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{GCP_PROJECT}/secrets/{secret_id}/versions/{version_id}"
            response = client.access_secret_version(request={"name": name}, timeout=5.0)
            payload = response.payload.data.decode("UTF-8")
            _secret_cache[cache_key] = payload
            return payload
        except Exception as e:
            logger.info(f"[SecretManager] Failed to fetch secret {secret_id}: {e}")
            return None

def get_oauth_client_secrets():
    """
    Attempts to fetch OAuth client secrets from GCP Secret Manager.
    If it fails, it falls back to the local `client_secrets.json` for development.
    """
    # Prefer Secret Manager (Production)
    secret_payload = get_secret("pex-bc-oauth-client-secrets")
    if secret_payload:
        try:
            return json.loads(secret_payload)
        except json.JSONDecodeError as e:
            logger.info(f"[SecretManager] Invalid JSON in OAuth client secrets: {e}")
    
    # Fallback to local file (Development)
    local_path = "client_secrets.json"
    if os.path.exists(local_path):
        with open(local_path, "r") as f:
            return json.load(f)
            
    logger.info("[SecretManager] CRITICAL: Could not find OAuth client secrets anywhere.")
    return None

def get_gemini_api_key():
    secret_key = get_secret("GEMINI_API_KEY")
    if secret_key: return secret_key
    
    # Cloud Run / Local fallback
    if os.environ.get('GEMINI_API_KEY'):
        return os.environ.get('GEMINI_API_KEY')
        
    try:
        import subprocess
        return subprocess.check_output(['/usr/local/google/home/goodwinmi/google-cloud-sdk/bin/gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=GEMINI_API_KEY', '--project=internal-xr-ai-tools-977945']).decode('utf-8').strip()
    except Exception as e:
        logger.error(f"[SecretManager] Failed to retrieve GEMINI_API_KEY: {e}")
        return None

def get_flask_secret_key():
    """
    Fetches the Flask session secret key from GCP Secret Manager.
    Falls back to environment variable or a default dev key.
    """
    secret_key = get_secret("pex-bc-flask-secret-key")
    if secret_key:
        return secret_key
    return os.environ.get('FLASK_SECRET_KEY', 'pex_bc_tool_persistent_secret_key_2026_dev_fallback')
