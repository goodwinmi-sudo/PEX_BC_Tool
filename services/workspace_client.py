import logging

logger = logging.getLogger(__name__)

import os
import time
from googleapiclient.discovery import build
import traceback

def resilient_call(func):
    """
    Decorator for the Liaison's Resilient Facade Pattern. 
    Implements a basic exponential backoff for Google Workspace API calls.
    """
    def wrapper(*args, **kwargs):
        max_retries = 3
        delay = 1
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.info(f"[Liaison] API Call Failed permanently after {max_retries} attempts: {e}")
                    raise
                logger.info(f"[Liaison] API Call Failed: {e}. Retrying in {delay}s...")
                import threading
                threading.Event().wait(delay)
                delay *= 2
    return wrapper

@resilient_call
def _extract_text_from_doc_unsafe(service_docs, doc_id):
    doc = service_docs.documents().get(documentId=doc_id).execute()
    content = doc.get('body').get('content', [])
    text = ""
    for element in content:
        if 'paragraph' in element:
            for elem in element.get('paragraph', {}).get('elements', []):
                 text += elem.get('textRun', {}).get('content', '')
    return text.strip()

@resilient_call
def _fetch_drive_docs_context_unsafe(service_drive, service_docs, query):
    results = service_drive.files().list(
        q=f"fullText contains '{query}' and mimeType='application/vnd.google-apps.document'", 
        spaces='drive', fields='files(id, name)', pageSize=2).execute()
    items = results.get('files', [])
    if not items: return "No matching Docs found."
    context = ""
    for item in items:
        name = item.get('name')
        doc_id = item.get('id')
        text = _extract_text_from_doc_unsafe(service_docs, doc_id)
        if len(text) > 5000: text = text[:5000] + "..."
        context += f"[DOC] Name: {name}\nSnippet: {text}\n\n"
    return context.strip()

@resilient_call
def _fetch_gmail_context_unsafe(service_gmail, query):
    results = service_gmail.users().messages().list(userId='me', q=query, maxResults=5).execute()
    messages = results.get('messages', [])
    if not messages: return "No matching emails found."
    context = ""
    for msg in messages:
        msg_data = service_gmail.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
        headers = msg_data.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        snippet = msg_data.get('snippet', '')
        context += f"[GMAIL] Date: {date} | From: {sender} | Subject: {subject}\nSnippet: {snippet}\n\n"
    return context.strip()

def gather_workspace_context(query, creds):
    """
    Public Contract Layer.
    Wraps the private calls and safely returns context strings instead of throwing.
    """
    if not creds: return "Workspace not connected. No extra context gathered."
    try:
        service_drive = build('drive', 'v3', credentials=creds)
        service_docs = build('docs', 'v1', credentials=creds)
        service_gmail = build('gmail', 'v1', credentials=creds)
        
        try:
            docs_context = "--- DOCS CONTEXT ---\n" + _fetch_drive_docs_context_unsafe(service_drive, service_docs, query)
        except Exception as e:
            docs_context = f"--- DOCS CONTEXT ---\n[Fetch Error: {e}]"
            
        try:
            gmail_context = "--- GMAIL CONTEXT ---\n" + _fetch_gmail_context_unsafe(service_gmail, query)
        except Exception as e:
            gmail_context = f"--- GMAIL CONTEXT ---\n[Fetch Error: {e}]"
            
        return f"{docs_context}\n\n{gmail_context}"
    except Exception as e:
        logger.info(f"Error initializing generic Workspace services: {e}")
        return "Failed to establish Workspace connection."
