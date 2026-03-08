import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

import json
import os
import uuid
import requests
import uuid
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, Response
from werkzeug.middleware.proxy_fix import ProxyFix
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.cloud import storage
import subprocess

import test_harness
from services import secrets_manager, ai_engine, workspace_client, simulation_runner

app = Flask(__name__)
app.secret_key = secrets_manager.get_flask_secret_key()
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

RESOLVED_MODEL = ai_engine.get_active_model()
GCP_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945')
GCS_BUCKET_NAME = f"{GCP_PROJECT}-sync-assets"

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/admin.directory.user.readonly'
]
BOT_FILE = 'bot.bgl.json'

def load_bot_data():
    if os.path.exists(BOT_FILE):
        with open(BOT_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_personas():
    """First tries local personas.json, then falls back to dynamic_personas.json from Cloud Storage."""
    if os.path.exists('personas.json'):
        with open('personas.json', 'r') as f:
            try:
                base_personas = json.load(f).get('executives', [])
                if base_personas: return base_personas
            except Exception as e:
                pass
                
    try:
        storage_client = storage.Client(project=GCP_PROJECT)
        bucket = storage_client.get_bucket(GCS_BUCKET_NAME)
        blob = bucket.blob('dynamic_personas.json')
        if blob.exists():
            content = blob.download_as_string()
            data = json.loads(content)
            return data.get('executives', [])
    except Exception as e:
        logger.info(f"Failed to load dynamic_personas from GCS: {e}")
        
    return []

def get_google_credentials():
    if 'credentials' not in session: return None
    creds_data = session['credentials']
    try:
        creds = Credentials.from_authorized_user_info(creds_data)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            session['credentials'] = json.loads(creds.to_json())
            
        return creds
    except Exception as e: # Catching broad Exception from google.auth
        logger.info(f"Auth Error: {e}")
        session.pop('credentials', None)
        return None



from routes import init_app
init_app(app)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
