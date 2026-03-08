import logging
import os
import json
from flask import Blueprint, render_template, request, session, redirect, url_for
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from services import secrets_manager

logger = logging.getLogger(__name__)
views_bp = Blueprint('views', __name__)

from app import load_bot_data, get_google_credentials, RESOLVED_MODEL, GCS_BUCKET_NAME, SCOPES

@views_bp.route('/')
def index():
    bot_data = load_bot_data()
    user_email = request.headers.get('X-Goog-Authenticated-User-Email', '').replace('accounts.google.com:', '')
    if not user_email: user_email = session.get('user_email', request.args.get('user', 'Guest'))
    creds = get_google_credentials()
    access_token = creds.token if creds and creds.token else ""
    return render_template('index.html', version=bot_data.get('bot_metadata', {}).get('version', '10.0.0'), project_id=os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945'), user_email=user_email, access_token=access_token, resolved_model=RESOLVED_MODEL, gcs_bucket=GCS_BUCKET_NAME)

@views_bp.route('/about')
def about():
    bot_data = load_bot_data()
    version = bot_data.get('bot_metadata', {}).get('version', '10.0.0')
    return render_template('about.html', version=version)

@views_bp.route('/login')
def login():
    client_config = secrets_manager.get_oauth_client_secrets()
    if not client_config: return "OAuth configuration not found.", 404
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=url_for('views.callback', _external=True))
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    session['state'] = state
    session['code_verifier'] = getattr(flow, 'code_verifier', None)
    return redirect(authorization_url)

@views_bp.route('/callback')
def callback():
    state = session['state']
    client_config = secrets_manager.get_oauth_client_secrets()
    flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state, redirect_uri=url_for('views.callback', _external=True))
    if session.get('code_verifier'): flow.code_verifier = session['code_verifier']
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session['credentials'] = json.loads(credentials.to_json())
    
    try:
        with open('.cached_creds.json', 'w') as f:
            f.write(credentials.to_json())
    except Exception as e:
        logger.info(f"Error caching credentials: {e}")
        
    service = build('gmail', 'v1', credentials=credentials)
    session['user_email'] = service.users().getProfile(userId='me').execute().get('emailAddress')
    return redirect(url_for('views.index'))

@views_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('views.index'))

@views_bp.route('/avatars/<filename>')
def serve_avatar(filename):
    from flask import send_from_directory
    return send_from_directory(os.path.join(os.getcwd(), 'static', 'avatars'), filename)

@views_bp.route('/board')
def board():
    from datetime import datetime
    return render_template('board.html', timestamp=datetime.now().strftime('%Y-%m-%d'))
