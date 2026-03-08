import logging
from flask import Blueprint, jsonify, request, session
from services import workspace_client, ai_engine
import test_harness
from datetime import datetime
import os
import io
from flask import send_file, redirect
from google.cloud import storage

storage_client = storage.Client()
logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

@api_bp.route('/api/personas')
def get_personas():
    from app import load_personas
    return jsonify(load_personas())

@api_bp.route('/api/collect_context', methods=['POST'])
def api_collect_context():
    from app import get_google_credentials
    creds = get_google_credentials()
    return jsonify({"context": workspace_client.gather_workspace_context(request.json.get('query', 'General Deal'), creds)})

@api_bp.route('/api/avatar/<pid>')
def get_avatar(pid):
    """
    Serves a publicly accessible avatar for the Google Slides API.
    Since Google Slides API evaluates image URLs from its backend,
    it cannot access internal Moma URLs or SVGs. 
    This proxy returns the cached JPG, or a PNG from ui-avatars.
    """
    try:
        bucket_name = os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945') + '-sync-assets'
        bucket = storage_client.bucket(bucket_name)
        
        blob = bucket.blob(f"moma_images/{pid}.png")
        if blob.exists():
            image_bytes = blob.download_as_bytes()
            return send_file(io.BytesIO(image_bytes), mimetype='image/png')
        else:
            return redirect("https://www.gstatic.com/images/branding/product/2x/avatar_square_blue_120dp.png")

    except Exception as e:
        logger.error(f"Failed to stream GCS URL for avatar proxy: {e}")
        return redirect("https://www.gstatic.com/images/branding/product/2x/avatar_square_blue_120dp.png")

@api_bp.route('/api/board/health')
def board_health():
    success, errors, warnings = test_harness.run_tests()
    return jsonify({
        "status": "PASS" if success else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@api_bp.route('/api/simulate', methods=['POST'])
def simulate():
    return jsonify({"status": "success", "step": request.json.get('step', 0)})

@api_bp.route('/api/board_chat', methods=['POST'])
def board_chat():
    from app import get_google_credentials
    creds = get_google_credentials()
    if not creds: return jsonify({"error": "Unauthorized"}), 401
    
    prompt = request.json.get('prompt')
    payload_context = request.json.get('payload_context', '')
    history = request.json.get('history', [])
    
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
        
    try:
        response_text = ai_engine.chat_with_board(prompt, payload_context, history)
        return jsonify({"response": response_text})
    except Exception as e:
        logger.info(f"Chat error: {e}")
        return jsonify({"error": "Internal server error during chat"}), 500
