import logging
import json
import os
import re
from datetime import datetime
import traceback
from google.cloud import datastore

from services import ai_engine, workspace_client, slides_engine

logger = logging.getLogger(__name__)
GCP_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945')
datastore_client = datastore.Client(project=GCP_PROJECT)

def append_event(job_id, event):
    """Utility to append an event to the Datastore GenerationJob document."""
    try:
        event['timestamp'] = datetime.utcnow().isoformat()
        job_key = datastore_client.key('GenerationJob', job_id)
        
        event_key = datastore_client.key('GenerationEvent', parent=job_key)
        excludes = [k for k, v in event.items() if isinstance(v, str) and len(v.encode('utf-8', errors='ignore')) > 1400]
        event_entity = datastore.Entity(key=event_key, exclude_from_indexes=excludes)
        event_entity.update(event)
        
        datastore_client.put(event_entity)
        
        job = datastore_client.get(job_key)
        if job:
            job['updated_at'] = datetime.utcnow()
            datastore_client.put(job)
            
    except Exception as e:
        logger.info(f"Failed to append event to Datastore for job {job_id}: {e}")

def execute_generation_job(job_id, creds, deal_desc):
    try:
        append_event(job_id, {"type": "step", "index": 0, "title": "Initialization & Research", "progress": 10})
        append_event(job_id, {"type": "log", "message": f"[INFO] Initializing Generation Engine for: {deal_desc}"})
        
        service_slides = slides_engine.get_slides_client(creds)
        
        append_event(job_id, {"type": "log", "message": "[INFO] Executing real-time web semantic search..."})
        research_context = ai_engine.run_research_node(deal_desc)
        append_event(job_id, {"type": "log", "message": "[SUCCESS] Live Market Context Ingested"})

        append_event(job_id, {"type": "step", "index": 1, "title": "Workspace Intel Fetch", "progress": 30})
        append_event(job_id, {"type": "log", "message": "[INFO] Pinging Google Workspace API scopes for Gmail/Drive history..."})
        workspace_context = workspace_client.gather_workspace_context(deal_desc, creds)
        append_event(job_id, {"type": "log", "message": "[SUCCESS] Internal Google Workspace context synced"})
        
        append_event(job_id, {"type": "step", "index": 2, "title": "AI Deck Genesis", "progress": 50})
        append_event(job_id, {"type": "log", "message": "[INFO] Engaging Gemini Pro multimodal model for Ground-Up Generation..."})
        raw_payload = ai_engine.run_generator_node(deal_desc, research_context, workspace_context)

        # Parse JSON
        polished_sjl_payload = re.sub(r'```json', '', raw_payload, flags=re.IGNORECASE)
        polished_sjl_payload = re.sub(r'```markdown', '', polished_sjl_payload, flags=re.IGNORECASE).replace('```', '').strip()
        
        final_dynamic_slides = []
        try:
            parsed_sjl = json.loads(polished_sjl_payload)
            if isinstance(parsed_sjl, dict) and 'slides' in parsed_sjl:
                final_dynamic_slides = parsed_sjl['slides']
            elif isinstance(parsed_sjl, list):
                final_dynamic_slides = parsed_sjl
            append_event(job_id, {"type": "log", "message": f"[SUCCESS] Synthesized {len(final_dynamic_slides)} slide outlines via SJL Layout array"})
        except Exception as e:
            logger.error(f"Failed to parse generated SJL payload: {e}")
            append_event(job_id, {"type": "log", "message": "[CRITICAL] SJL Parsing failed."})
            raise ValueError("AI produced invalid slide schema layout.")

        append_event(job_id, {"type": "step", "index": 3, "title": "Google Slides Assembly", "progress": 80})
        append_event(job_id, {"type": "log", "message": "[INFO] Creating pristine native Google Slides presentation"})
        
        # Create a new blank presentation
        pres_obj = slides_engine.create_blank_presentation(service_slides, f"{deal_desc[:30]} - Auto Generated Deck")
        presentation_id = pres_obj.get('presentationId')
        
        append_event(job_id, {"type": "log", "message": "[INFO] Mapping virtual coordinate layout to Google Slides Batch updates..."})
        
        requests_payload = []
        for slide_json in reversed(final_dynamic_slides):
            requests_payload.extend(
                slides_engine.build_dynamic_slide_requests(
                    slide_json=slide_json,
                    insertion_index=0,
                    theme_config=None
                )
            )
            
        try:
            slides_engine.batch_update_presentation(service_slides, presentation_id, requests_payload)
            # Remove the default empty slide that gets created initially (it will be at the very end since we prepend)
            # Wait, creating a presentation creates exactly 1 empty slide at index 0. If we insert everything before it, 
            # it becomes the last slide. Let's delete the last slide if we want to be clean, or just ignore it.
            # Easiest: The API returns the structural object of the presentation when we create it.
            default_slide_id = pres_obj.get('slides', [{}])[0].get('objectId')
            if default_slide_id:
                cleanup_req = [{'deleteObject': {'objectId': default_slide_id}}]
                slides_engine.batch_update_presentation(service_slides, presentation_id, cleanup_req)

            append_event(job_id, {"type": "log", "message": "[SUCCESS] Slides generated successfully"})
            url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
            chat_payload = f"The independent slide generator has successfully created a structural M3 deck for '{deal_desc}'. The pipeline has completed successfully."
            append_event(job_id, {"type": "done", "success": True, "url": url, "payload": chat_payload})
            
            job_key = datastore_client.key('GenerationJob', job_id)
            job = datastore_client.get(job_key)
            if job:
                job['status'] = 'completed'
                datastore_client.put(job)
        except Exception as e:
            err_msg = str(e)
            logger.info(f"Failed to mutate slide object: {err_msg}")
            append_event(job_id, {"type": "log", "message": f"[CRITICAL] Batch API Error: {err_msg}"})
            raise e
            
    except Exception as e:
        traceback.print_exc()
        append_event(job_id, {"type": "done", "success": False, "error": str(e), "message": f"[CRITICAL] Fatal execution error: {e}"})
        job_key = datastore_client.key('GenerationJob', job_id)
        job = datastore_client.get(job_key)
        if job:
            job['status'] = 'failed'
            datastore_client.put(job)
