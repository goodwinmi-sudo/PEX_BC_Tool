import logging

logger = logging.getLogger(__name__)

import os
import json
import time
import random
from google import genai
from google.genai import types
from services import prompts

import threading

# Singleton Client Architecture
_working_client = None
_resolved_model = None
_resolve_lock = threading.RLock()

def get_gemini_client():
    """
    Returns a singleton instance of the resolved Gemini client (Vertex or AI Studio). 
    This satisfies the CTO's mandate for DRY architecture.
    """
    global _working_client
    if _working_client is not None:
        return _working_client
        
    # Force resolution if not yet resolved
    if _resolved_model is None:
        resolve_vertex_model()
        
    return _working_client

def resolve_vertex_model():
    """
    Resolves the highest capability Gemini model available across providers.
    Caches the result to avoid redundant ping tests on every generation.
    """
    global _resolved_model, _working_client
    with _resolve_lock:
        if _resolved_model is not None:
            return _resolved_model
            
        logger.info("[AI Bouncer] Resolving latest available Gemini Pro model...")
        target_models = ['gemini-3.1-pro-preview', 'gemini-3.0-pro', 'gemini-2.5-pro']
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'internal-xr-ai-tools-977945')
        
        providers = []
        import google.auth.credentials
        import datetime
        import subprocess
        
        class LocalGcloudCredentials(google.auth.credentials.Credentials):
            def __init__(self):
                super().__init__()
                self.token = None
                self.expiry = None
            def refresh(self, request):
                self.token = subprocess.check_output(['/usr/local/google/home/goodwinmi/google-cloud-sdk/bin/gcloud', 'auth', 'print-access-token']).decode('utf-8').strip()
                self.expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                
        is_cloud_environ = os.environ.get('K_SERVICE') is not None
        
        try:
            creds = None if is_cloud_environ else LocalGcloudCredentials()
            for loc in ['global', 'us-central1']:
                providers.append((f"Vertex AI ({loc})", genai.Client(vertexai=True, credentials=creds, project=project_id, location=loc)))
        except Exception as e:
            logger.info(f"[AI Bouncer] Vertex AI init failed: {e}")
        for target in target_models:
            for provider_name, client in providers:
                try:
                    client.models.generate_content(model=target, contents="ping")
                    logger.info(f"[AI Bouncer] SUCCESS: Resolved to {target} via {provider_name} (DRY Compliant)")
                    _resolved_model = target
                    _working_client = client
                    return target
                except Exception as e:
                    # If we hit a quota limit, the model exists and is bleeding edge. We lock onto it.
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e):
                        logger.info(f"[AI Bouncer] SUCCESS (via quota limit verification): Resolved to {target} via {provider_name} (DRY Compliant)")
                        _resolved_model = target
                        _working_client = client
                        return target
                    logger.info(f"[AI Bouncer] Fallback: {target} unavailable via {provider_name}. Reason: {e}")
                
        logger.info("[AI Bouncer] ALL targets failed across all providers. Falling back to default gemini-2.5-pro.")
        _resolved_model = 'gemini-2.5-pro'
        _working_client = providers[0][1] if providers else None
        return _resolved_model

def get_active_model():
    return _resolved_model if _resolved_model else resolve_vertex_model()

def _execute_gemini_with_retry(client, model, contents, config=None, retries=3):
    """Executes Gemini call with exponential backoff on 429s/503s."""
    import threading
    for attempt in range(retries):
        try:
            # Short delay between calls to mitigate burst limits if multiple bots run simultaneously
            threading.Event().wait(0.5) 
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
        except Exception as e:
            if attempt == retries - 1:
                raise e
            wait_time = 2 ** attempt
            logger.warning(f"Gemini API rate limited or unavailable. Retrying in {wait_time}s... Error: {e}")
            threading.Event().wait(wait_time)

def _query_gemini_json_node(contents, temperature=None):
    """DRY Helper to standardize Gemini client resolution and JSON execution."""
    client = get_gemini_client()
    model = get_active_model()
    kwargs = {"response_mime_type": "application/json"}
    if temperature is not None:
        kwargs["temperature"] = temperature
    try:
        res = _execute_gemini_with_retry(
            client=client,
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(**kwargs)
        )
        return res
    except Exception as e:
        logger.error(f"Gemini API JSON execution error: {e}")
        return None

# ==============================================================================
# CORE AI GENERATION NODES
# ==============================================================================

def run_research_node(deal_desc):
    try:
        client = get_gemini_client()
        model = get_active_model()
        prompt = prompts.RESEARCH_NODE_PROMPT.format(deal_desc=deal_desc)
        response = _execute_gemini_with_retry(
            client=client,
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(tools=[{"googleSearch": {}}])
        )
        return response.text
    except Exception as e:
        logger.info(f"Error in run_research_node: {e}")
        return "Market research unavailable. Proceed with caution."

def run_persona_node(persona_data, slides_data, deal_desc, research_context, workspace_context, debate_transcript=None):
    try:
        client = get_gemini_client()
        model = get_active_model()
        contents = prompts.build_persona_prompt(persona_data, deal_desc, research_context, workspace_context, slides_data, debate_transcript)
        critiques = _execute_gemini_with_retry(client=client, model=model, contents=contents).text
        return f"### {persona_data['name']} BOT Critique:\n{critiques}"
    except Exception as e: 
        return f"Failed to generate critique for {persona_data['name']} BOT: {e}"

def format_hardening_directives(slides_data, aggregated_critiques, deal_desc):
    client = get_gemini_client()
    model = get_active_model()
    
    mapping_text = ""
    for idx, slide in enumerate(slides_data):
        mapping_text += f"\n--- SLIDE {idx+1} ({slide['page_id']}) ---\n"
        for obj_id, text in slide['text_boxes'].items():
            mapping_text += f"ObjectID: {obj_id} | Text: {text}\n"

    prompt = prompts.HARDENING_DIRECTIVE_PROMPT.format(
        deal_desc=deal_desc,
        aggregated_critiques=aggregated_critiques,
        mapping_text=mapping_text
    )
    try:
        res = _execute_gemini_with_retry(
            client=client,
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(res.text)
        class DummyDirective:
            def __init__(self, d):
                self.new_terms_block = d.get('new_terms_block', d.get('newTermsBlock', ''))
                self.target_object_id = d.get('target_object_id', d.get('targetObjectId', ''))
                self.rationale = d.get('rationale', '')
        return DummyDirective(data)
    except Exception as e:
        logger.info(f"Hardening Mapping Error: {e}")
        return None

def run_premorteum_node(aggregated_critiques, workspace_context, mapping_text):
    client = get_gemini_client()
    model = get_active_model()
    prompt = prompts.PREMORTEM_PROMPT.format(
        aggregated_critiques=aggregated_critiques,
        workspace_context=workspace_context,
        mapping_text=mapping_text
    )
    res = _query_gemini_json_node(contents=prompt)
    if res: return res.text
    logger.info("Error in run_premorteum_node")
    return "[]"

def run_executive_summary_node(aggregated_critiques):
    prompt = prompts.EXECUTIVE_SUMMARY_PROMPT.format(aggregated_critiques=aggregated_critiques)
    res = _query_gemini_json_node(contents=prompt)
    if res: return res.text
    logger.info("Error in run_executive_summary_node")
    return "[]"

def run_synthesis_coach_node(hostile_critiques, deal_desc):
    prompt = prompts.SYNTHESIS_COACH_PROMPT.format(
        deal_desc=deal_desc,
        hostile_critiques=hostile_critiques
    )
    # This node outputs plain text markdown, not JSON, so we use the raw _execute_gemini_with_retry
    try:
        client = get_gemini_client()
        model = get_active_model()
        res = _execute_gemini_with_retry(
            client=client,
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig()
        )
        return res.text
    except Exception as e:
        logger.error(f"Synthesis Coach Node Error: execution failed -> {e}")
        return hostile_critiques # Fallback to raw critiques if the coach fails

def build_deck_content(deal_desc, research_context, workspace_context, slides_data, previous_critiques=None, iteration=1):
    client = get_gemini_client()
    model = get_active_model()
    
    mapping_text = ""
    for idx, slide in enumerate(slides_data):
        mapping_text += f"\n--- SLIDE {idx+1} ({slide['page_id']}) ---\n"
        for obj_id, text in slide['text_boxes'].items():
            if len(text.strip()) > 0:
                mapping_text += f"ObjectID: {obj_id} | Current Text: {text}\n"

    prompt = prompts.build_deck_content_prompt(
        deal_desc, research_context, workspace_context, 
        mapping_text, iteration, previous_critiques
    )
    
    contents = [prompt]
    for slide in slides_data:
        if slide.get('image_bytes'):
            contents.append(types.Part.from_bytes(data=slide['image_bytes'], mime_type='image/png'))

    res = _query_gemini_json_node(contents=contents)
    if not res:
        logger.info("Deck Gen Error: return None")
        return []
        
    try:
        data = json.loads(res.text)
        reps = data.get('replacements', [])
        
        class DummyReplacement:
            def __init__(self, o, n):
                self.object_id = o
                self.new_text = n
                
        replacements = []
        for r in reps:
            o = r.get('object_id', r.get('objectId'))
            n = r.get('new_text', r.get('newText'))
            if o is not None and n is not None:
                replacements.append(DummyReplacement(o, n))
        return replacements
    except Exception as e:
        logger.info(f"Deck Gen parsing error: {e}")
        return []

def run_ux_redesign_node(raw_json, deal_desc):
    prompt_text = prompts.UX_REDESIGN_PROMPT.format(
        deal_desc=deal_desc,
        raw_json=json.dumps(raw_json, indent=2)
    )
    
    res = _query_gemini_json_node(contents=[prompt_text], temperature=0.4)
    if res:
        return res.text
    logger.error("UX Redesign Node Error: execution failed.")
    return json.dumps(raw_json)

def run_generator_node(deal_desc, research_context, workspace_context):
    prompt_text = prompts.GENERATE_SLIDES_FROM_SCRATCH_PROMPT.format(
        deal_desc=deal_desc,
        research_context=research_context,
        workspace_context=workspace_context
    )
    res = _query_gemini_json_node(contents=[prompt_text], temperature=0.6)
    if res:
        return res.text
    logger.error("Generator Node Error: execution failed.")
    return "{}"

def run_native_deck_generation(deal_desc, research_context, workspace_context, available_layouts, critiques="", slides_data=None):
    mapping_text = ""
    if slides_data:
        for idx, slide in enumerate(slides_data):
            mapping_text += f"\n--- SLIDE {idx+1} ({slide.get('page_id', 'Unknown')}) ---\n"
            for obj_id, text in slide.get('text_boxes', {}).items():
                if len(text.strip()) > 0:
                    mapping_text += f"Text: {text}\n"

    if mapping_text:
        prompt_text = prompts.NATIVE_GENERATOR_PROMPT.format(
            deal_desc=deal_desc,
            research_context=research_context,
            workspace_context=workspace_context,
            available_layouts=json.dumps(available_layouts, indent=2),
            critiques=critiques,
            mapping_text=mapping_text
        )
    else:
        # Fallback to scratch building if no draft deck was provided
        prompt_text = prompts.NATIVE_SCRATCH_PROMPT.format(
            deal_desc=deal_desc,
            research_context=research_context,
            workspace_context=workspace_context,
            available_layouts=json.dumps(available_layouts, indent=2)
        )
        
    res = _query_gemini_json_node(contents=[prompt_text], temperature=0.5)
    if res:
        return res.text
    logger.error("Native Generator Node Error: execution failed.")
    return "{}"


def chat_with_board(prompt, payload_context, history=None):
    """
    Stateful/Stateless Chat interface for the War Room Gem.
    Takes the system payload context and previous history to ground the response.
    """
    client = get_gemini_client()
    model = get_active_model()
    
    # Construct a strong system instruction grounding the AI in the board's persona and the specific deal payload.
    system_instruction = (
        "You are the collective consciousness of the PEX BC (Business Council) Advisory Board. "
        "You speak with the combined authority of the CPO, CRO, CTO, CQO, Head of AI, VP Integrations, UX Designer, and Truth Steward. "
        "Your goal is to harden the user's deal strategy, answer questions about the generated Pre-Mortem, and provide strict, actionable advice. "
        "Do not hallucinate. Base your answers strictly on the executive personas, core business council intent, and the provided War Room Payload.\n\n"
        "--- WAR ROOM PAYLOAD COMMAND CENTER ---\n"
        f"{payload_context}"
    )
    
    # We use a standard generate content call. We can build a text prompt representing history if needed.
    # For now, we'll format the history into the prompt string if provided.
    
    chat_prompt = f"{system_instruction}\n\n"
    if history:
        for turn in history:
            role = turn.get('role', 'user')
            text = turn.get('text', '')
            chat_prompt += f"[{role.upper()}]: {text}\n"
    
    chat_prompt += f"\n[USER]: {prompt}\n[BOARD]:"
    
    try:
        response = _execute_gemini_with_retry(
            client=client,
            model=model,
            contents=chat_prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        return response.text
    except Exception as e:
        logger.info(f"Error in chat_with_board: {e}")
        return "The Board is currently unavailable for deep dives. Please try again later."
