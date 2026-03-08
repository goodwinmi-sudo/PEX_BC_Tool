import logging
import os
import json
import uuid
import requests
import queue
import threading
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from google.cloud import datastore
from google.oauth2.credentials import Credentials
from services import secrets_manager, simulation_runner, generator_runner, native_runner

logger = logging.getLogger(__name__)
tasks_bp = Blueprint('tasks', __name__)

from app import GCP_PROJECT, get_google_credentials
from services.simulation_runner import datastore_client

# Instantiate the thread-safe global staging queue for concurrent users
simulation_queue = queue.Queue()

def _background_worker():
    """
    A continuous daemon thread that reads from the internal staging queue sequentially.
    This guarantees that the container never attempts to process 100 simulations
    simultaneously, preventing CPU throttling or Gunicorn worker exhaustion.
    """
    logger.info("[Background Worker] Starting continuous PEX Simulation staging queue processing.")
    
    # --- ORPHAN SWEEPER & QUEUE REHYDRATION (Executes ONCE on container boot) ---
    try:
        now_naive = datetime.utcnow()
        from datetime import timedelta
        fifteen_mins_ago = now_naive - timedelta(minutes=15)
        
        # 1. Rehydrate 'queued' jobs that were dropped during SIGTERM
        job_query = datastore_client.query(kind='SimulationJob')
        job_query.add_filter('status', '=', 'queued')
        queued_jobs = list(job_query.fetch(limit=50))
        
        for job in queued_jobs:
            payload_str = job.get('payload')
            if payload_str:
                logger.info(f"[Background Worker] Rehydrating queued Job {job.key.name} from Datastore state.")
                simulation_queue.put(json.loads(payload_str))
                
        # 2. Rehydrate 'processing' orphans that hung for > 15 minutes
        orphan_query = datastore_client.query(kind='SimulationJob')
        orphan_query.add_filter('status', '=', 'processing')
        orphans = list(orphan_query.fetch(limit=20))
        
        for orphan in orphans:
            updated_at = orphan.get('updated_at') or orphan.get('created_at')
            if updated_at:
                if hasattr(updated_at, 'tzinfo') and updated_at.tzinfo:
                    updated_at = updated_at.replace(tzinfo=None)
                if updated_at < fifteen_mins_ago:
                    payload_str = orphan.get('payload')
                    if payload_str:
                        logger.warning(f"[Background Worker] Orphan Sweeper: Rehydrating hung Job {orphan.key.name} back to queue.")
                        orphan.update({'status': 'queued', 'updated_at': now_naive})
                        datastore_client.put(orphan)
                        simulation_queue.put(json.loads(payload_str))
    except Exception as e:
        logger.error(f"[Background Worker] Failed to execute boot-time queue rehydration: {e}")
    # --- END ORPHAN SWEEPER ---

    while True:
        try:
            # Block until a job payload is dropped into the queue by the frontend
            payload_data = simulation_queue.get()
            job_id = payload_data.get('job_id')
            
            logger.info(f"[Background Worker] Picking up Job {job_id} from staging queue. Processing...")
            
            # Immediately lock status in Datastore and update timestamps
            job_key = datastore_client.key('SimulationJob', job_id)
            job = datastore_client.get(job_key)
            if job:
                job.update({'status': 'processing', 'updated_at': datetime.utcnow()})
                datastore_client.put(job)
            
            # Rehydrate credentials from the user's secure HTTP session state
            creds_data = payload_data.get('creds_json')
            if not creds_data:
                logger.error(f"[Background Worker] Critical Failure: No credentials found for Job {job_id}.")
                if job:
                    job.update({'status': 'failed', 'error': 'No credentials found', 'updated_at': datetime.utcnow()})
                    job.pop('payload', None)
                    datastore_client.put(job)
                simulation_queue.task_done()
                continue
                
            creds = Credentials.from_authorized_user_info(creds_data)
            
            # Execute the heavy AI simulation payload synchronously (it blocks this background thread only)
            # The native engine has been fully deprecated in favor of the Mission Critical Coach (Legacy Injection).
            engine_choice = payload_data.get('engine', 'legacy')
            
            if payload_data.get('method') == 'template':
                native_runner.execute_simulation_job(
                    job_id, 
                    creds, 
                    payload_data.get('source_presentation_id'), 
                    payload_data['dealDesc'], 
                    payload_data['orgFilter'], 
                    payload_data['method'], 
                    payload_data['dealSize'], 
                    payload_data['riskFlags']
                )
            else:
                simulation_runner.execute_simulation_job(
                    job_id, 
                    creds, 
                    payload_data['source_presentation_id'], 
                    payload_data['dealDesc'], 
                    payload_data['orgFilter'], 
                    payload_data['method'], 
                    payload_data['dealSize'], 
                    payload_data['riskFlags']
                )
            
            logger.info(f"[Background Worker] Successfully finished processing Job {job_id}.")
            
            # Clean up securely (CRO dictates ephemeral datastore token presence)
            final_job = datastore_client.get(job_key)
            if final_job:
                final_job.update({'status': 'done', 'updated_at': datetime.utcnow()})
                final_job.pop('payload', None)
                datastore_client.put(final_job)
            
        except Exception as e:
            logger.error(f"[Background Worker] Unhandled execution crash for Job {job_id}: {e}")
        finally:
            # Always mark the queue item as complete to allow graceful shutdown tracking
            simulation_queue.task_done()

# Fire and forget the background daemon exactly once upon Blueprint loading
threading.Thread(target=_background_worker, daemon=True).start()


@tasks_bp.route('/api/headless_trigger', methods=['POST'])
def headless_trigger():
    # Fetch latest completed job to steal credentials for the headless run
    query = datastore_client.query(kind='SimulationJob')
    query.add_filter('status', '=', 'completed')
    query.order = ['-created_at']
    jobs = list(query.fetch(limit=1))
    
    if not jobs:
        return jsonify({"error": "No previous job credentials found in Datastore"}), 500
        
    last_job = datastore_client.get(jobs[0].key)
    payload_str = last_job.get('payload')
    if not payload_str:
        return jsonify({"error": "No payload in previous job"}), 500
        
    import json
    old_payload = json.loads(payload_str)
    creds_json = old_payload.get('creds_json')
    if not creds_json:
        return jsonify({"error": "No creds_json in previous job"}), 500
        
    source_presentation_id = request.json.get('source_presentation_id')
    deal_desc = request.json.get('dealDesc', 'Headless Iteration Deal')
    org_filter = request.json.get('orgFilter', 'Platforms & Devices')
    method = request.json.get('method', 'template')
    deal_size_str = request.json.get('dealSize', '100M')
    risk_flags = request.json.get('riskFlags', [])
    engine = request.json.get('engine', 'native')

    job_id = str(uuid.uuid4())
    payload_data = {
        'job_id': job_id,
        'source_presentation_id': source_presentation_id,
        'dealDesc': deal_desc,
        'orgFilter': org_filter,
        'method': method,
        'dealSize': deal_size_str,
        'riskFlags': risk_flags,
        'engine': engine,
        'creds_json': creds_json 
    }

    key = datastore_client.key('SimulationJob', job_id)
    job_entity = datastore.Entity(key=key, exclude_from_indexes=['payload'])
    job_entity.update({
        'status': 'queued',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'payload': json.dumps(payload_data)
    })
    datastore_client.put(job_entity)
    simulation_queue.put(payload_data)
    return jsonify({"job_id": job_id})

@tasks_bp.route('/api/generate_slides', methods=['POST'])
def generate_slides():
    creds = get_google_credentials()
    if not creds: return jsonify({"error": "Unauthorized. Please click 'Connect' to authenticate with your Google Workspace first."}), 401
    
    source_presentation_id = request.json.get('source_presentation_id')
    deal_desc = request.json.get('dealDesc', 'General Deal')
    org_filter = request.json.get('orgFilter', 'Platforms & Devices')
    method = request.json.get('method', 'clone')
    deal_size_str = request.json.get('dealSize', '0M')
    risk_flags = request.json.get('riskFlags', [])
    engine = request.json.get('engine', 'legacy')
    
    if method == 'clone' and not source_presentation_id:
        return jsonify({"error": "Review my Deck requires a source presentation."}), 400
    if method == 'template' and not source_presentation_id:
        source_presentation_id = "12OiKmHmjkm0ik5PKXZDGrJ9pGlyyBqioPapoEtFkpIQ" # Use user-provided template

    job_id = str(uuid.uuid4())
    payload_data = {
        'job_id': job_id,
        'source_presentation_id': source_presentation_id,
        'dealDesc': deal_desc,
        'orgFilter': org_filter,
        'method': method,
        'dealSize': deal_size_str,
        'riskFlags': risk_flags,
        'engine': engine,
        'creds_json': session.get('credentials') 
    }

    try:
        # Initialize Datastore Entity for the Job with state-hydrated payload
        key = datastore_client.key('SimulationJob', job_id)
        # Exclude payload from indexes since it contains a JSON blob which can be over 1500 bytes and cause errors
        job_entity = datastore.Entity(key=key, exclude_from_indexes=['payload'])
        job_entity.update({
            'status': 'queued',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'payload': json.dumps(payload_data)
        })
        datastore_client.put(job_entity)

        # Explicit strict environment detection
        is_production = 'K_SERVICE' in os.environ or 'GAE_ENV' in os.environ or 'GAE_APPLICATION' in os.environ

        try:
            # Drop the job into the internal memory queue
            # The background thread will pick it up and process it sequentially
            simulation_queue.put(payload_data)
            
            # Calculate the user's position in the queue
            # This consists of jobs actively in the memory queue + the 1 job currently running
            queue_position = simulation_queue.qsize()
            
            # We don't have a reliable way to know if a job is actively running without complex locks,
            # but the active queue size is a safe, conservative estimate of how many people are in front of them.
            if queue_position == 0:
                logger.info(f"[{'PROD' if is_production else 'LOCAL'}] User bypassed queue. Dispatching {job_id} to background thread immediately.")
            else:
                logger.info(f"[{'PROD' if is_production else 'LOCAL'}] High Concurrency: Staged job {job_id} at queue position {queue_position}.")
            
        except Exception as e:
            logger.error(f"[FATAL] Failed to enqueue simulation job in internal queue: {e}")
            return jsonify({"error": "Failed to enqueue simulation job due to an internal threading error"}), 500
                
        return jsonify({
            "job_id": job_id, 
            "status": "queued",
            "queue_position": queue_position
        })
    except Exception as e:
        logger.info(f"Failed to process simulation request: {e}")
        return jsonify({"error": "Failed to process simulation request"}), 500


@tasks_bp.route('/api/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    try:
        key = datastore_client.key('SimulationJob', job_id)
        job_entity = datastore_client.get(key)
        if job_entity:
            data = dict(job_entity)
            if 'created_at' in data and data['created_at']:
                data['created_at'] = str(data['created_at'])
            
            # Fetch events as child entities without Datastore-native sorting to avoid 
            # requiring a composite index allocation in production.
            query = datastore_client.query(kind='SimulationEvent', ancestor=key)
            events = [dict(e) for e in query.fetch()]
            
            # Perform a fast in-memory chronological sort 
            events.sort(key=lambda x: x.get('timestamp', ''))
            data['events'] = events
            
            logger.info(f"[DIAGNOSTICS] /api/job/{job_id} returning. Job State: {data.get('status')}. Events fetched: {len(events)}.")
            if len(events) == 0:
                logger.info(f"[DIAGNOSTICS] Datastore query returned NO events for ancestor {job_id}")

            return jsonify(data)
        else:
            logger.info(f"[DIAGNOSTICS] Job {job_id} not found in Datastore")
            return jsonify({"error": "Job not found"}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# =====================================================================
# GENERATION SERVICE (Standalone/Parallel Pipeline)
# =====================================================================

generation_queue = queue.Queue()

def _generator_worker():
    logger.info("[Generator Worker] Starting continuous AI Deck Generation processing.")
    # Boot-time rehydration for GenerationJob
    try:
        now_naive = datetime.utcnow()
        from datetime import timedelta
        fifteen_mins_ago = now_naive - timedelta(minutes=15)
        
        job_query = datastore_client.query(kind='GenerationJob')
        job_query.add_filter('status', '=', 'queued')
        queued_jobs = list(job_query.fetch(limit=50))
        for job in queued_jobs:
            payload_str = job.get('payload')
            if payload_str:
                logger.info(f"[Generator Worker] Rehydrating queued Job {job.key.name}")
                generation_queue.put(json.loads(payload_str))
                
        orphan_query = datastore_client.query(kind='GenerationJob')
        orphan_query.add_filter('status', '=', 'processing')
        orphans = list(orphan_query.fetch(limit=20))
        for orphan in orphans:
            updated_at = orphan.get('updated_at') or orphan.get('created_at')
            if updated_at:
                if hasattr(updated_at, 'tzinfo') and updated_at.tzinfo:
                    updated_at = updated_at.replace(tzinfo=None)
                if updated_at < fifteen_mins_ago:
                    payload_str = orphan.get('payload')
                    if payload_str:
                        logger.warning(f"[Generator Worker] Sweeper: Rehydrating hung Job {orphan.key.name}")
                        orphan.update({'status': 'queued', 'updated_at': now_naive})
                        datastore_client.put(orphan)
                        generation_queue.put(json.loads(payload_str))
    except Exception as e:
        logger.error(f"[Generator Worker] Failed boot rehydration: {e}")

    while True:
        try:
            payload_data = generation_queue.get()
            job_id = payload_data.get('job_id')
            logger.info(f"[Generator Worker] Processing Job {job_id}...")
            
            job_key = datastore_client.key('GenerationJob', job_id)
            job = datastore_client.get(job_key)
            if job:
                job.update({'status': 'processing', 'updated_at': datetime.utcnow()})
                datastore_client.put(job)
            
            creds_data = payload_data.get('creds_json')
            if not creds_data:
                logger.error(f"[Generator Worker] No credentials for Job {job_id}.")
                if job:
                    job.update({'status': 'failed', 'error': 'No credentials', 'updated_at': datetime.utcnow()})
                    job.pop('payload', None)
                    datastore_client.put(job)
                generation_queue.task_done()
                continue
                
            creds = Credentials.from_authorized_user_info(creds_data)
            
            # Execute Generation
            generator_runner.execute_generation_job(
                job_id, 
                creds, 
                payload_data['dealDesc']
            )
            
            final_job = datastore_client.get(job_key)
            if final_job:
                final_job.update({'status': 'done', 'updated_at': datetime.utcnow()})
                final_job.pop('payload', None)
                datastore_client.put(final_job)
            
        except Exception as e:
            logger.error(f"[Generator Worker] Unhandled crash for Job {job_id}: {e}")
        finally:
            generation_queue.task_done()

threading.Thread(target=_generator_worker, daemon=True).start()

@tasks_bp.route('/api/generate_deck_from_scratch', methods=['POST'])
def generate_deck_from_scratch():
    creds = get_google_credentials()
    if not creds: return jsonify({"error": "Unauthorized. Please connect."}), 401
    
    deal_desc = request.json.get('dealDesc', 'General Deal')
    job_id = str(uuid.uuid4())
    
    payload_data = {
        'job_id': job_id,
        'dealDesc': deal_desc,
        'creds_json': session.get('credentials') 
    }

    try:
        key = datastore_client.key('GenerationJob', job_id)
        job_entity = datastore.Entity(key=key, exclude_from_indexes=['payload'])
        job_entity.update({
            'status': 'queued',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'payload': json.dumps(payload_data)
        })
        datastore_client.put(job_entity)

        generation_queue.put(payload_data)
        queue_position = generation_queue.qsize()
        
        return jsonify({
            "job_id": job_id, 
            "status": "queued",
            "queue_position": queue_position
        })
    except Exception as e:
        logger.info(f"Failed to enqueue generator: {e}")
        return jsonify({"error": "Failed to process generator request"}), 500

@tasks_bp.route('/api/generation_job/<job_id>', methods=['GET'])
def get_generation_job_status(job_id):
    try:
        key = datastore_client.key('GenerationJob', job_id)
        job_entity = datastore_client.get(key)
        if job_entity:
            data = dict(job_entity)
            if 'created_at' in data and data['created_at']:
                data['created_at'] = str(data['created_at'])
            
            query = datastore_client.query(kind='GenerationEvent', ancestor=key)
            events = [dict(e) for e in query.fetch()]
            events.sort(key=lambda x: x.get('timestamp', ''))
            data['events'] = events
            return jsonify(data)
        else:
            return jsonify({"error": "Job not found"}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

