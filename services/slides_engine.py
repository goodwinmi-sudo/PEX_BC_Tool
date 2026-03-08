import logging

logger = logging.getLogger(__name__)

import copy
import requests
import uuid
from googleapiclient.discovery import build
import time

def get_slides_client(creds):
    return build('slides', 'v1', credentials=creds)

def get_drive_client(creds):
    return build('drive', 'v3', credentials=creds)

def _parse_rgb(color_obj, default_rgb=(0, 0, 0)):
    if not isinstance(color_obj, dict):
        return {'red': float(default_rgb[0]), 'green': float(default_rgb[1]), 'blue': float(default_rgb[2])}
    
    def safe_float(val, fallback):
        try:
            if val is None: return float(fallback)
            return float(val)
        except (ValueError, TypeError):
            return float(fallback)

    return {
        'red': safe_float(color_obj.get('red'), default_rgb[0]),
        'green': safe_float(color_obj.get('green'), default_rgb[1]),
        'blue': safe_float(color_obj.get('blue'), default_rgb[2])
    }

def resilient_call(max_retries=3, initial_delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.info(f"[SlidesEngine] API Call Failed permanently after {max_retries} attempts: {e}")
                        raise
                    logger.info(f"[SlidesEngine] API Call Failed: {e}. Retrying in {delay}s...")
                    import threading
                    threading.Event().wait(delay)
                    delay *= 2
        return wrapper
    return decorator

@resilient_call(max_retries=3)
def extract_presentation_data(service_slides, presentation_id):
    """NODE 1: Vision Extraction & exact visual mapping of the slides."""
    try:
        presentation = service_slides.presentations().get(presentationId=presentation_id).execute()
        slides_data = []
        theme_config = {
            'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}}},
            'fontFamily': 'Arial',
            'textColor': {'opaqueColor': {'rgbColor': {'red': 0.0, 'green': 0.0, 'blue': 0.0}}}
        }
        
        is_first_slide = True
        
        for page in presentation.get('slides', []):
            page_id = page.get('objectId')
            
            # Extract theme from the very first slide's background and first text element
            if is_first_slide:
                is_first_slide = False
                props = page.get('pageProperties', {})
                if 'pageBackgroundFill' in props and 'solidFill' in props['pageBackgroundFill']:
                    theme_config['pageBackgroundFill'] = {'solidFill': props['pageBackgroundFill']['solidFill']}
                
            text_boxes = {}
            text_content = ""
            for element in page.get('pageElements', []):
                obj_id = element.get('objectId')
                if 'shape' in element and 'text' in element.get('shape'):
                    raw_text = ""
                    for paragraph in element['shape']['text'].get('textElements', []):
                        if 'textRun' in paragraph:
                            run = paragraph['textRun']
                            raw_text += run.get('content', '')
                            # Opportunistically grab font family and color from the first text run we see on slide 1
                            if len(slides_data) == 0 and 'style' in run:
                                style = run['style']
                                if 'fontFamily' in style:
                                    theme_config['fontFamily'] = style['fontFamily']
                                if 'foregroundColor' in style:
                                    theme_config['textColor'] = style['foregroundColor']
                                    
                    raw_text = raw_text.strip()
                    if raw_text:
                        text_boxes[obj_id] = raw_text
                        text_content += f"[{obj_id}]: {raw_text}\\n"
            try:
                thumbnail = service_slides.presentations().pages().getThumbnail(
                    presentationId=presentation_id, pageObjectId=page_id).execute()
                image_bytes = None
                if thumbnail:
                    resp = requests.get(thumbnail.get('contentUrl'), timeout=10)
                    if resp.status_code == 200:
                        image_bytes = resp.content
            except Exception as e:
                logger.info(f"Thumbnail Error for {page_id}: {e}")
                image_bytes = None
            slides_data.append({
                'page_id': page_id, 
                'text': text_content, 
                'text_boxes': text_boxes, 
                'image_bytes': image_bytes,
                'theme_config': theme_config if len(slides_data) == 0 else None
            })
        return slides_data
    except Exception as e:
        logger.info(f"Extraction Error: {e}")
        return []

def apply_replacements_to_virtual_deck(slides_data, replacements):
    new_slides_data = copy.deepcopy(slides_data)
    rep_dict = {r.object_id: r.new_text for r in replacements}
    for slide in new_slides_data:
        new_text = ""
        for obj_id in slide['text_boxes']:
            if obj_id in rep_dict:
                slide['text_boxes'][obj_id] = rep_dict[obj_id]
            new_text += f"[{obj_id}]: {slide['text_boxes'][obj_id]}\\n"
        slide['text'] = new_text
    return new_slides_data

@resilient_call(max_retries=3)
def copy_presentation(service_drive, source_id, title):
    copy_request = service_drive.files().copy(
        fileId=source_id, 
        body={'name': title},
        supportsAllDrives=True
    )
    if source_id == "12OiKmHmjkm0ik5PKXZDGrJ9pGlyyBqioPapoEtFkpIQ":
        copy_request.headers['X-Goog-Drive-Resource-Keys'] = "12OiKmHmjkm0ik5PKXZDGrJ9pGlyyBqioPapoEtFkpIQ/0-o_iwPnOXkFGMq3N4dWck5g"
    return copy_request.execute()

@resilient_call(max_retries=3)
def create_blank_presentation(service_slides, title):
    return service_slides.presentations().create(body={'title': title}).execute()

@resilient_call(max_retries=3)
def batch_update_presentation(service_slides, presentation_id, requests_payload):
    return service_slides.presentations().batchUpdate(presentationId=presentation_id, body={'requests': requests_payload}).execute()

@resilient_call(max_retries=3)
def get_presentation(service_slides, presentation_id):
    return service_slides.presentations().get(presentationId=presentation_id).execute()

import services.parse_markdown_to_slides_ast as markdown_ast

def calculate_luminance(rgb_color):
    """Calculate relative luminance to determine text contrast"""
    if 'red' not in rgb_color: rgb_color['red'] = 0.0
    if 'green' not in rgb_color: rgb_color['green'] = 0.0
    if 'blue' not in rgb_color: rgb_color['blue'] = 0.0
    
    return (0.299 * rgb_color['red'] + 0.587 * rgb_color['green'] + 0.114 * rgb_color['blue'])

def build_m3_feedback_slide_requests(title_text, body_text, insertion_index=None, theme_config=None):
    """
    Generates a list of Google Slides API requests to create an adaptive, theme-matched feedback slide.
    If insertion_index is None, the slide is appended to the end.
    """
    if theme_config is None:
        theme_config = {
            'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}}},
            'fontFamily': 'Arial',
            'textColor': {'opaqueColor': {'rgbColor': {'red': 0.0, 'green': 0.0, 'blue': 0.0}}}
        }
        
    slide_id = f"s{uuid.uuid4().hex[:10]}"
    
    # IDs for the shapes
    title_box_id = f"title{uuid.uuid4().hex[:10]}"
    body_box_id = f"body{uuid.uuid4().hex[:10]}"
    
    # Base slide creation
    create_slide_req = {
        'objectId': slide_id
    }
    if insertion_index is not None:
        create_slide_req['insertionIndex'] = insertion_index
        
    requests_payload = [
        {
            'createSlide': create_slide_req
        },
        # Slide Background (Adaptive to input deck)
        {
            'updatePageProperties': {
                'objectId': slide_id,
                'pageProperties': {
                    'pageBackgroundFill': theme_config['pageBackgroundFill']
                },
                'fields': 'pageBackgroundFill.solidFill'
            }
        },
        # Title Text Box
        {
            'createShape': {
                'objectId': title_box_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {
                        'width': {'magnitude': 7700000, 'unit': 'EMU'},
                        'height': {'magnitude': 700000, 'unit': 'EMU'}
                    },
                    'transform': {
                        'scaleX': 1, 'scaleY': 1, 'translateX': 700000, 'translateY': 500000, 'unit': 'EMU'
                    }
                }
            }
        },
        {
            'insertText': {
                'objectId': title_box_id,
                'text': title_text
            }
        },
        {
            'updateTextStyle': {
                'objectId': title_box_id,
                'textRange': {'type': 'ALL'},
                'style': {
                    'foregroundColor': theme_config['textColor'],
                    'fontFamily': theme_config['fontFamily'],
                    'fontSize': {'magnitude': 26, 'unit': 'PT'},
                    'bold': True
                },
                'fields': 'foregroundColor,fontFamily,fontSize,bold'
            }
        },
        # Body Text Box Setup
        {
            'createShape': {
                'objectId': body_box_id,
                'shapeType': 'TEXT_BOX',
                'elementProperties': {
                    'pageObjectId': slide_id,
                    'size': {
                        'width': {'magnitude': 7700000, 'unit': 'EMU'},
                        'height': {'magnitude': 3500000, 'unit': 'EMU'}
                    },
                    'transform': {
                        'scaleX': 1, 'scaleY': 1, 'translateX': 700000, 'translateY': 1300000, 'unit': 'EMU'
                    }
                }
            }
        }
    ]
    
    # Process the markdown body text using AST translation
    clean_body_text, markdown_formatting_requests = markdown_ast.parse_markdown_to_requests(body_box_id, body_text, theme_config['textColor'])
    
    # Append the markdown formatting requests 
    requests_payload.extend(markdown_formatting_requests)
    
    # Finally apply base styling to the whole body text
    requests_payload.append(
        {
            'updateTextStyle': {
                'objectId': body_box_id,
                'textRange': {'type': 'ALL'},
                'style': {
                    'fontFamily': theme_config['fontFamily'],
                    # Base font size will not override specific styles previously applied in the markdown AST
                },
                'fields': 'fontFamily'
            }
        }
    )
    
    return requests_payload

def build_dynamic_slide_requests(slide_json, insertion_index=None, theme_config=None):
    if theme_config is None:
        theme_config = {
            'pageBackgroundFill': {'solidFill': {'color': {'rgbColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}}},
            'fontFamily': 'Arial'
        }
        
    slide_id = f"s{uuid.uuid4().hex[:10]}"
    requests = []
    
    create_slide_req = {'objectId': slide_id}
    if insertion_index is not None:
        create_slide_req['insertionIndex'] = insertion_index
        
    requests.append({'createSlide': create_slide_req})
    requests.append({
        'updatePageProperties': {
            'objectId': slide_id,
            'pageProperties': {
                'pageBackgroundFill': theme_config['pageBackgroundFill']
            },
            'fields': 'pageBackgroundFill.solidFill'
        }
    })
    
    def sort_order(el):
        layer_map = {'shape': 0, 'image': 1, 'text': 2}
        return layer_map.get(el.get('type'), 3)
        
    elements = sorted(slide_json.get('elements', []), key=sort_order)
    
    for el in elements:
        obj_id = f"obj_{uuid.uuid4().hex[:10]}"
        pos = el.get('position', {})
        x = int(pos.get('x', 0) * 12700)
        y = int(pos.get('y', 0) * 12700)
        w = int(pos.get('w', 100) * 12700)
        h = int(pos.get('h', 100) * 12700)
        
        style = el.get('style', {})
        
        if el.get('type') == 'text':
            requests.append({
                "createShape": {
                    "objectId": obj_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                        "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}
                    }
                }
            })
            requests.append({
                "insertText": {
                    "objectId": obj_id,
                    "text": el.get('content', ''),
                    "insertionIndex": 0
                }
            })
            
            text_style = {
                'fontFamily': theme_config.get('fontFamily', 'Arial')
            }
            fields = "fontFamily"
            
            if 'size' in style:
                text_style['fontSize'] = {'magnitude': style['size'], 'unit': 'PT'}
                fields += ",fontSize"
            if 'bold' in style:
                text_style['bold'] = style['bold']
                fields += ",bold"
            if 'color' in style:
                c = style['color']
                text_style['foregroundColor'] = {
                    'opaqueColor': {'rgbColor': _parse_rgb(c, (0,0,0))}
                }
                fields += ",foregroundColor"
                
            requests.append({
                "updateTextStyle": {
                    "objectId": obj_id,
                    "textRange": {"type": "ALL"},
                    "style": text_style,
                    "fields": fields
                }
            })
            
        elif el.get('type') == 'shape':
            requests.append({
                "createShape": {
                    "objectId": obj_id,
                    "shapeType": el.get('shape_type', 'RECTANGLE'),
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                        "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}
                    }
                }
            })
            
            shape_props = {}
            fields = ""
            
            if 'bg_color' in style:
                c = style['bg_color']
                shape_props['shapeBackgroundFill'] = {
                    'solidFill': {
                        'color': {'rgbColor': _parse_rgb(c, (1,1,1))}
                    }
                }
                fields += "shapeBackgroundFill.solidFill.color"
                
            if 'border_color' in style:
                c = style['border_color']
                shape_props['outline'] = {
                    'outlineFill': {
                        'solidFill': {
                            'color': {'rgbColor': _parse_rgb(c, (0,0,0))}
                        }
                    },
                    'weight': {'magnitude': float(style.get('border_weight', 1)), 'unit': 'PT'}
                }
                fields += ",outline.outlineFill.solidFill.color,outline.weight" if fields else "outline.outlineFill.solidFill.color,outline.weight"
                
            if shape_props:
                requests.append({
                    "updateShapeProperties": {
                        "objectId": obj_id,
                        "shapeProperties": shape_props,
                        "fields": fields
                    }
                })
                    
        elif el.get('type') == 'image':
            url = el.get('url')
            if url:
                requests.append({
                    "createImage": {
                        "objectId": obj_id,
                        "url": url,
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}
                        }
                    }
                })
                
    return requests

