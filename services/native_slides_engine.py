import logging
import json
import base64
import requests
import uuid

logger = logging.getLogger(__name__)

def resilient_call(func):
    """Decorator to enforce strict timeouts and gracefully fail external network calls."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[NETWORK VETO] Resilient call failed: {e}")
            return None
    return wrapper

@resilient_call
def render_mermaid_to_image(mermaid_code):
    """
    Renders mermaid code to a URL using mermaid.ink.
    """
    mermaid_code = mermaid_code.strip()
    if mermaid_code.startswith('```mermaid'):
        mermaid_code = mermaid_code[10:]
    if mermaid_code.startswith('```'):
        mermaid_code = mermaid_code[3:]
    if mermaid_code.endswith('```'):
        mermaid_code = mermaid_code[:-3]
    mermaid_code = mermaid_code.strip()
    
    encoded = base64.urlsafe_b64encode(mermaid_code.encode('utf-8')).decode('ascii')
    url = f"https://mermaid.ink/img/{encoded}"
    
    # VP Integrations Mandate: Verify API contract health before committing
    resp = requests.get(url, timeout=3)
    if resp.status_code == 200:
        return url
    else:
        logger.warning(f"Mermaid.ink rejected rendering. Status: {resp.status_code}")
    return None

def extract_layouts(presentation):
    """
    Reads the master slides from a Presentation object and extracts the legal Layout IDs
    so that Gemini does not hallucinate layout names.
    Ensures layouts are scoped to the primary master to prevent 400 Errors on injection.
    """
    masters = presentation.get('masters', [])
    if not masters:
        # User mandate: Do not silently hide problems
        raise ValueError("[extract_layouts] Validation Error: Target presentation contains no master slides.")
        
    slides = presentation.get('slides', [])
    if slides and slides[0].get('slideProperties', {}).get('masterObjectId'):
        primary_master_id = slides[0].get('slideProperties', {}).get('masterObjectId')
    else:
        primary_master_id = masters[0].get('objectId')
        
    layouts_dict = {}
    
    for layout in presentation.get('layouts', []):
        props = layout.get('layoutProperties', {})
        name = props.get('displayName') or props.get('name') or "UNKNOWN"
        obj_id = layout.get('objectId')
        master_id = props.get('masterObjectId')
        if name != "UNKNOWN":
            # Strict layout filtering
            if master_id == primary_master_id:
                layouts_dict[name] = obj_id
                layouts_dict[name.lower()] = obj_id
                
    return layouts_dict

def extract_markdown_tables(text):
    """
    Finds markdown tables in text and returns (clean_text, list_of_tables).
    A table is represented as a list of rows, where each row is a list of cell texts.
    (CQO Mandate: Graceful string parsing stringency).
    """
    if not text:
        return "", []
        
    tables = []
    clean_lines = []
    lines = text.split('\n')
    in_table = False
    current_table = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            in_table = True
            if '---' in stripped:
                continue # Skip separator row
            # Split and remove outer empty strings
            cells = [cell.strip() for cell in stripped.split('|')[1:-1]]
            current_table.append(cells)
        else:
            if in_table:
                tables.append(current_table)
                current_table = []
                in_table = False
            clean_lines.append(line)
            
    if current_table:
        tables.append(current_table)
        
    return '\n'.join(clean_lines).strip(), tables

def build_table_requests(page_id, tables, start_y=200):
    """
    Converts extracted markdown tables into Google Slides API createTable requests,
    and applies highly polished M3 styling (background fills, bold headers, borders).
    """
    requests_payload = []
    current_y = start_y
    
    for table_data in tables:
        rows = len(table_data)
        cols = max(len(row) for row in table_data) if rows > 0 else 0
        if rows == 0 or cols == 0: continue
        
        table_id = f"table_{uuid.uuid4().hex[:10]}"
        requests_payload.append({
            'createTable': {
                'objectId': table_id,
                'elementProperties': {
                    'pageObjectId': page_id,
                    'size': {'width': {'magnitude': 660, 'unit': 'PT'}, 'height': {'magnitude': 25 * rows, 'unit': 'PT'}},
                    'transform': {'scaleX': 1, 'scaleY': 1, 'translateX': 30, 'translateY': current_y, 'unit': 'PT'}
                },
                'rows': rows,
                'columns': cols
            }
        })
        
        # Style the entire table borders
        requests_payload.append({
            'updateTableBorderProperties': {
                'objectId': table_id,
                'borderPosition': 'ALL',
                'tableBorderProperties': {
                    'tableBorderFill': {'solidFill': {'color': {'rgbColor': {'red': 0.8, 'green': 0.82, 'blue': 0.85}}}},
                    'weight': {'magnitude': 1, 'unit': 'PT'}
                },
                'fields': 'tableBorderFill,weight'
            }
        })
        
        # Style the header row background and text
        requests_payload.append({
            'updateTableCellProperties': {
                'objectId': table_id,
                'tableRange': {'location': {'rowIndex': 0, 'columnIndex': 0}, 'rowSpan': 1, 'columnSpan': cols},
                'tableCellProperties': {
                    'tableCellBackgroundFill': {
                        'solidFill': {'color': {'rgbColor': {'red': 0.9, 'green': 0.93, 'blue': 0.96}}}
                    }
                },
                'fields': 'tableCellBackgroundFill.solidFill.color'
            }
        })
        
        for r_idx, row in enumerate(table_data):
            for c_idx, cell_text in enumerate(row):
                if cell_text:
                    # Strip basic markdown before direct Slides API insertion
                    clean_text = cell_text.replace('**', '').replace('*', '').replace('_', '').replace('`', '')
                    requests_payload.append({
                        'insertText': {
                            'objectId': table_id,
                            'cellLocation': {'rowIndex': r_idx, 'columnIndex': c_idx},
                            'text': clean_text
                        }
                    })
                    # Set base font size to prevent chaotic vertical line wrapping
                    requests_payload.append({
                        'updateTextStyle': {
                            'objectId': table_id,
                            'cellLocation': {'rowIndex': r_idx, 'columnIndex': c_idx},
                            'style': {'fontSize': {'magnitude': 14, 'unit': 'PT'}, 'fontFamily': 'Google Sans'},
                            'textRange': {'type': 'ALL'},
                            'fields': 'fontSize,fontFamily'
                        }
                    })
                    if r_idx == 0:
                        # Bold header text
                        requests_payload.append({
                            'updateTextStyle': {
                                'objectId': table_id,
                                'cellLocation': {'rowIndex': r_idx, 'columnIndex': c_idx},
                                'style': {'bold': True, 'fontSize': {'magnitude': 14, 'unit': 'PT'}},
                                'textRange': {'type': 'ALL'},
                                'fields': 'bold,fontSize'
                            }
                        })
                        requests_payload.append({
                            'updateParagraphStyle': {
                                'objectId': table_id,
                                'cellLocation': {'rowIndex': r_idx, 'columnIndex': c_idx},
                                'style': {'alignment': 'CENTER'},
                                'textRange': {'type': 'ALL'},
                                'fields': 'alignment'
                            }
                        })
                        
        current_y += 50 * rows + 40 # Shift down dynamically based on table size
    return requests_payload
