import logging
import json
import traceback
import uuid
import sys
import re
from datetime import datetime

from services import ai_engine, workspace_client, slides_engine, native_slides_engine
from services.simulation_runner import append_event, datastore_client

logger = logging.getLogger(__name__)

def execute_simulation_job(job_id, creds, source_presentation_id, deal_desc, org_filter, method, deal_size_str, risk_flags):
    try:
        append_event(job_id, {"type": "step", "index": 0, "title": "Native Master Template Extraction", "progress": 5})
        append_event(job_id, {"type": "log", "message": "[INFO] Initializing Native Mapping Engine"})
        
        service_slides = slides_engine.get_slides_client(creds)
        service_drive = slides_engine.get_drive_client(creds)
        
        try:
            # We strictly use the authoritative Mega-Template Component Library for generation
            # User provided template ID: 12OiKmHmjkm0ik5PKXZDGrJ9pGlyyBqioPapoEtFkpIQ
            SLIDESHOP_TEMPLATE_ID = '12OiKmHmjkm0ik5PKXZDGrJ9pGlyyBqioPapoEtFkpIQ'
            copied_file = slides_engine.copy_presentation(service_drive, SLIDESHOP_TEMPLATE_ID, 'Native Test Review (PEX BC)')
            presentation_id = copied_file.get('id')
        except Exception as e:
            append_event(job_id, {"type": "log", "message": f"[CRITICAL] Failed to copy slideshop library presentation: {e}"})
            raise e
            
        pres_obj = slides_engine.get_presentation(service_slides, presentation_id)
        available_layouts = native_slides_engine.extract_layouts(pres_obj)
        append_event(job_id, {"type": "log", "message": f"[SUCCESS] Extracted {len(available_layouts)} native Material Master Layouts"})
        
        append_event(job_id, {"type": "step", "index": 1, "title": "Contextual Ingestion", "progress": 15})
        slides_data = slides_engine.extract_presentation_data(service_slides, source_presentation_id)
        append_event(job_id, {"type": "log", "message": f"[SUCCESS] Extracted {len(slides_data)} draft slides from user presentation"})

        append_event(job_id, {"type": "step", "index": 2, "title": "Contextual Semantic Gathering", "progress": 20})
        research_context = ai_engine.run_research_node(deal_desc)
        append_event(job_id, {"type": "log", "message": "[SUCCESS] Live Web Semantic Context Ingested"})
        workspace_context = workspace_client.gather_workspace_context(deal_desc, creds)
        append_event(job_id, {"type": "log", "message": "[SUCCESS] Internal Workspace Drive connected"})
        
        append_event(job_id, {"type": "step", "index": 3, "title": "Executive Review", "progress": 30})
        import rule_engine
        from services.simulation_runner import load_personas_from_json, run_sequential_debate_personas
        active_personas = rule_engine.get_required_personas(deal_desc, org_filter, deal_size_str, risk_flags)
        if not active_personas:
            all_personas = load_personas_from_json()
            active_personas = [p for p in all_personas if p.get('org') == org_filter or org_filter == 'Global'][:2]

        append_event(job_id, {"type": "log", "message": f"[INFO] Orchestrating sequential Agent Debate ({len(active_personas)} personas)"})
        critiques_list_str = run_sequential_debate_personas(active_personas, slides_data, deal_desc, research_context, workspace_context, job_id)
        append_event(job_id, {"type": "log", "message": f"[SUCCESS] Alignment gaps found in Terms ({len(critiques_list_str.split('###')) - 1} critiques generated)"})
        
        append_event(job_id, {"type": "step", "index": 4, "title": "Generative Execution (Layout & Markdown)", "progress": 40})
        append_event(job_id, {"type": "log", "message": "[INFO] Packaging critiques into pristine Review Section..."})
        
        raw_payload = ai_engine.run_native_deck_generation(deal_desc, research_context, workspace_context, available_layouts, critiques_list_str, slides_data)
        
        raw_payload = re.sub(r'```json', '', raw_payload, flags=re.IGNORECASE)
        raw_payload = re.sub(r'```markdown', '', raw_payload, flags=re.IGNORECASE)
        raw_payload = raw_payload.replace('```', '').strip()
        
        try:
            parsed_data = json.loads(raw_payload)
            slides = parsed_data.get('slides', parsed_data) if isinstance(parsed_data, dict) else parsed_data
        except Exception as e:
             append_event(job_id, {"type": "log", "message": f"[CRITICAL] Gemini returned unparsable response: {e}"})
             raise e
             
        append_event(job_id, {"type": "log", "message": f"[SUCCESS] AI completed parsing for {len(slides)} native slides."})     
        append_event(job_id, {"type": "step", "index": 3, "title": "Native Layout Rendering (Pass 1)", "progress": 60})
        
        slide_creation_mapping = []
        pass1_requests = []
        
        for idx, slide_def in enumerate(slides):
            layout_name = slide_def.get('layout_name', 'TITLE_AND_BODY')
            # Attempt to find the specific layout, but fallback to None (Slides API default) if omitted/unmatched to prevent 400 errors
            layout_id = available_layouts.get(layout_name) or available_layouts.get(layout_name.lower()) if available_layouts else None
            
            new_slide_id = f"native_{job_id.replace('-', '')[:10]}_{idx}"
            
            if layout_id:
                pass1_requests.append({
                    'createSlide': {
                        'objectId': new_slide_id,
                        'insertionIndex': str(idx),
                        'slideLayoutReference': {
                            'layoutId': layout_id
                        }
                    }
                })
            else:
                pass1_requests.append({
                    'createSlide': {
                        'objectId': new_slide_id,
                        'insertionIndex': str(idx)
                    }
                })
                
            slide_creation_mapping.append({
                'slide_id': new_slide_id,
                'definition': slide_def
            })
            
        if pass1_requests:
            slides_engine.batch_update_presentation(service_slides, presentation_id, pass1_requests)
            append_event(job_id, {"type": "log", "message": "[SUCCESS] Master Layout skeleton instantiated via Slides API."})
            
        append_event(job_id, {"type": "step", "index": 4, "title": "Rich Content Injection (Pass 2)", "progress": 80})
        append_event(job_id, {"type": "log", "message": "[INFO] Hydrating Placeholders, parsing Markdown Tables, and caching Mermaid SVG/PNGs..."})
        
        service_slides = slides_engine.get_slides_client(creds)
        updated_pres = slides_engine.get_presentation(service_slides, presentation_id)
        
        slide_elements = {}
        for s in updated_pres.get('slides', []):
            slide_elements[s.get('objectId')] = s.get('pageElements', [])
            
        pass2_requests = []
        
        for mapping in slide_creation_mapping:
            s_id = mapping['slide_id']
            s_def = mapping['definition']
            elements = slide_elements.get(s_id, [])
            
            placeholders = s_def.get('placeholders', {})
            mermaid_code = s_def.get('mermaid_code', '').strip()
            
            title_injected = False
            body_injected = False
            
            # Persona Avatar Injection
            title_text = placeholders.get('title') or ''
            body_text = placeholders.get('body') or ''
            combined_text = f"{title_text}\n{body_text}"
            for p in active_personas:
                p_name = p.get('name') or ''
                p_role = p.get('role') or ''
                if ((p_name and p_name in combined_text) or (p_role and p_role in combined_text)) and p.get('avatar_url'):
                    pass2_requests.append({
                        'createImage': {
                            'objectId': f"avatar_{uuid.uuid4().hex[:10]}",
                            'url': p['avatar_url'],
                            'elementProperties': {
                                'pageObjectId': s_id,
                                'size': {'width': {'magnitude': 90, 'unit': 'PT'}, 'height': {'magnitude': 90, 'unit': 'PT'}},
                                'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 580, 'translateY': 30, 'unit': 'PT'}
                            }
                        }
                    })
                    break
            
            # Text + Markdown Tables Injection
            for elem in elements:
                shape = elem.get('shape', {})
                ph = shape.get('placeholder', {})
                ph_type = ph.get('type')
                elem_id = elem.get('objectId')
                
                if not ph_type: continue
                
                content = None
                if ph_type in ['TITLE', 'CENTERED_TITLE'] and 'title' in placeholders:
                    content = placeholders['title']
                elif ph_type in ['SUBTITLE'] and 'subtitle' in placeholders:
                    content = placeholders['subtitle']
                elif ph_type in ['BODY', 'OBJECT'] and 'body' in placeholders:
                    content = placeholders['body']
                    
                if content:
                    clean_text, tables = native_slides_engine.extract_markdown_tables(content)
                    if clean_text:
                        clean_text = clean_text.replace('**', '').replace('*', '').replace('_', '').replace('`', '').replace('### ', '').replace('## ', '').replace('# ', '')
                        pass2_requests.append({
                            'insertText': {
                                'objectId': elem_id,
                                'text': clean_text
                            }
                        })
                        if ph_type in ['TITLE', 'CENTERED_TITLE']: title_injected = True
                        if ph_type in ['BODY', 'OBJECT']: body_injected = True
                        
                    if tables:
                        # Find geometry constraints of original box
                        transform = elem.get('transform', {})
                        scaleY = transform.get('scaleY', 1)
                        translateY = transform.get('translateY', 0)
                        start_y = (translateY * scaleY) + 200 # Push down safely
                        
                        table_reqs = native_slides_engine.build_table_requests(s_id, tables, start_y)
                        pass2_requests.extend(table_reqs)
                        if ph_type in ['BODY', 'OBJECT']: body_injected = True

            # The "Self-Drawing" Fallback for Polished Feedback
            if not title_injected and 'title' in placeholders:
                title_box_id = f"title_{uuid.uuid4().hex[:10]}"
                pass2_requests.append({
                    'createShape': {
                        'objectId': title_box_id,
                        'shapeType': 'TEXT_BOX',
                        'elementProperties': {
                            'pageObjectId': s_id,
                            'size': {'width': {'magnitude': 7700000, 'unit': 'EMU'}, 'height': {'magnitude': 700000, 'unit': 'EMU'}},
                            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 700000, 'translateY': 500000, 'unit': 'EMU'}
                        }
                    }
                })
                pass2_requests.append({'insertText': {'objectId': title_box_id, 'text': placeholders['title']}})

            if not body_injected and 'body' in placeholders:
                body_box_id = f"body_{uuid.uuid4().hex[:10]}"
                pass2_requests.append({
                    'createShape': {
                        'objectId': body_box_id,
                        'shapeType': 'TEXT_BOX',
                        'elementProperties': {
                            'pageObjectId': s_id,
                            'size': {'width': {'magnitude': 7700000, 'unit': 'EMU'}, 'height': {'magnitude': 4500000, 'unit': 'EMU'}},
                            'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 700000, 'translateY': 1300000, 'unit': 'EMU'}
                        }
                    }
                })
                clean_body, tables = native_slides_engine.extract_markdown_tables(placeholders['body'])
                if clean_body:
                    cleaned_body_text = clean_body.replace('**', '').replace('*', '').replace('_', '').replace('`', '').replace('### ', '').replace('## ', '').replace('# ', '')
                    pass2_requests.append({'insertText': {'objectId': body_box_id, 'text': cleaned_body_text}})
                if tables:
                    table_reqs = native_slides_engine.build_table_requests(s_id, tables, 150)
                    pass2_requests.extend(table_reqs)
            
            # Mermaid Ink Rendering Vector Pipeline
            if mermaid_code:
                append_event(job_id, {"type": "log", "message": f"[INFO] Compiling Mermaid schema for Slide Node {s_id}..."})
                image_url = native_slides_engine.render_mermaid_to_image(mermaid_code)
                if image_url:
                    pass2_requests.append({
                        'createImage': {
                            'objectId': f"image_{uuid.uuid4().hex[:10]}",
                            'url': image_url,
                            'elementProperties': {
                                'pageObjectId': s_id,
                                'size': {'width': {'magnitude': 400, 'unit': 'PT'}, 'height': {'magnitude': 300, 'unit': 'PT'}},
                                'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 250, 'translateY': 120, 'unit': 'PT'}
                            }
                        }
                    })
                else:
                    append_event(job_id, {"type": "log", "message": f"[WARNING] Mermaid Ink render failed or timed out. Diagram natively stripped."})
                    
        if pass2_requests:
            slides_engine.batch_update_presentation(service_slides, presentation_id, pass2_requests)
            
        # Hard-delete the original empty slides from the template if we cloned it
        original_slide_ids = [s.get('objectId') for s in pres_obj.get('slides', []) if 'native_' not in s.get('objectId')]
        if original_slide_ids:
             append_event(job_id, {"type": "log", "message": f"[INFO] Purging {len(original_slide_ids)} legacy layout geometries..."})
             delete_reqs = [{'deleteObject': {'objectId': sid}} for sid in original_slide_ids]
             slides_engine.batch_update_presentation(service_slides, presentation_id, delete_reqs)
            
        append_event(job_id, {"type": "step", "index": 5, "title": "Final Payload Complete", "progress": 100})
        append_event(job_id, {"type": "log", "message": "[SUCCESS] Native Gen Architecture V3 compilation and delivery successful."})
        
        url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
        chat_payload = "Native Master Layout generation complete. The Board successfully executed this review directly using native Workspace templates."
        append_event(job_id, {"type": "done", "success": True, "url": url, "payload": chat_payload})
        
        job_key = datastore_client.key('SimulationJob', job_id)
        job = datastore_client.get(job_key)
        if job:
            job['status'] = 'completed'
            datastore_client.put(job)

    except Exception as e:
        traceback.print_exc()
        err_msg = str(e)
        if "Internal error encountered" in err_msg:
             err_msg = f"Slides API 500: Potential Image URL Fetch Failure due to IAP Blocking on Mermaid proxy or GCS. Execution terminated."
        append_event(job_id, {"type": "done", "success": False, "error": err_msg, "message": f"[CRITICAL] Architecture Fault: {err_msg}"})
        job_key = datastore_client.key('SimulationJob', job_id)
        job = datastore_client.get(job_key)
        if job:
            job['status'] = 'failed'
            datastore_client.put(job)
