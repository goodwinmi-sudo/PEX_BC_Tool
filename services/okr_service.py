import logging

logger = logging.getLogger(__name__)

import os
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import google.auth
import urllib.request
import urllib.parse
import traceback

logger = logging.getLogger(__name__)

CACHE_FILE = 'personas.json'

def get_adc_token():
    try:
        creds, project = google.auth.default()
        if not creds.valid:
            creds.refresh(Request())
        return creds.token
    except Exception as e:
        logger.warning(f"Failed to get ADC credentials: {e}")
        return None

def fetch_okrs_from_api(ldap):
    token = get_adc_token()
    if not token:
        raise Exception("No credentials available to call OKRs API")
    
    # We use REST endpoint mapping for BatchGetTeamOkrs
    # E.g., okrs_team_identifier mapped strictly.
    url = f"https://okrs.corp.googleapis.com/v1/teams:batchGetOkrs?ownerTeamIdentifiers.okrsTeamIdentifier={urllib.parse.quote(ldap)}&periodSelector.mode=FRESH_WITH_FALLBACKS"
    
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return _parse_api_response(data)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        logger.error(f"OKRs API HTTP Error {e.code} for param {ldap}: {body}")
        raise Exception(f"HTTP {e.code}: {body}")
    except Exception as e:
        logger.error(f"OKRs API unknown error for {ldap}: {e}")
        raise e

def _parse_api_response(api_data):
    # Parse the batch get team okrs response
    okrs_text_lines = []
    team_okrs = api_data.get('teamOkrs', [])
    for to in team_okrs:
        objective = to.get('objective', {})
        title = objective.get('title', '')
        if title:
            # Format according to Truth Steward directives (extract and sanitize)
            okrs_text_lines.append(f"- {title}")
    
    if okrs_text_lines:
        return "\n".join(okrs_text_lines)
    return None

def fetch_okrs_from_vision_fallback(ldap):
    """
    Tier 2 Fallback: Multi-Modal OKR Ingestion (Moonshot Proposal)
    Requires user to upload a screenshot to processing queue, processed by Gemini Pro Vision.
    Currently stubbed as Not Implemented to force fallback to Tier 3.
    """
    raise NotImplementedError("Vision fallback requires user screenshot payload")

def fetch_okrs_from_cache(ldap):
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            for p in data.get('executives', []):
                if p.get('ldap') == ldap:
                    return p.get('okrs')
    except Exception as e:
        logger.error(f"Failed to read from cache {CACHE_FILE}: {e}")
    return None

def get_executive_okrs(ldap):
    """
    3-Tier Fallback Strategy for OKRs:
    1. REST API
    2. Vision/Scraping Fallback (Stubbed)
    3. Cached personas.json
    """
    # 1. Try API
    try:
        api_result = fetch_okrs_from_api(ldap)
        if api_result:
            logger.info(f"Successfully fetched OKRs via API for {ldap}")
            return api_result
    except Exception as e:
        logger.warning(f"Tier 1 (API) Fetch Failed for {ldap}: {e}")
        
    # 2. Try Vision/Scraping
    try:
        vision_result = fetch_okrs_from_vision_fallback(ldap)
        if vision_result:
            logger.info(f"Successfully fetched OKRs via Vision for {ldap}")
            return vision_result
    except NotImplementedError:
        pass
    except Exception as e:
        logger.warning(f"Tier 2 (Vision) Fetch Failed for {ldap}: {e}")
        
    # 3. Try Cache
    logger.info(f"Falling back to Tier 3 (Cache) for {ldap}")
    cache_result = fetch_okrs_from_cache(ldap)
    if cache_result:
        return cache_result
        
    return "Error: Could not retrieve OKRs for this persona."

if __name__ == '__main__':
    # Local execution test
    logger.info(get_executive_okrs('kwalker'))
