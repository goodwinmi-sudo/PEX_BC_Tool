import re

def parse_markdown_to_requests(object_id, raw_markdown, text_color):
    """
    Parses a markdown string containing ### headers and **bold** text,
    and returns the cleaned string along with a list of Google Slides API requests
    to insert the text and apply the formatting.
    """
    requests = []
    
    clean_text = ""
    current_index = 0
    
    bold_ranges = []
    header_ranges = []
    
    lines = raw_markdown.split('\n')
    for i, line in enumerate(lines):
        clean_line = line
        
        is_header = False
        if clean_line.startswith('### '):
            is_header = True
            clean_line = clean_line[4:]
        elif clean_line.startswith('## '):
            is_header = True
            clean_line = clean_line[3:]
        elif clean_line.startswith('# '):
            is_header = True
            clean_line = clean_line[2:]
            
        line_start_idx = current_index
        
        parts = re.split(r'(\*\*.*?\*\*)', clean_line)
        processed_line = ""
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                bold_text = part[2:-2]
                start_match = current_index + len(processed_line)
                end_match = start_match + len(bold_text)
                bold_ranges.append((start_match, end_match))
                processed_line += bold_text
            else:
                processed_line += part
                
        if is_header:
            header_ranges.append((line_start_idx, line_start_idx + len(processed_line)))
            
        if i < len(lines) - 1:
            processed_line += '\n'
            
        clean_text += processed_line
        current_index += len(processed_line)
        
    requests.append({
        'insertText': {
            'objectId': object_id,
            'text': clean_text,
            'insertionIndex': 0
        }
    })
    
    for start, end in bold_ranges:
        requests.append({
            'updateTextStyle': {
                'objectId': object_id,
                'textRange': {
                    'type': 'FIXED_RANGE',
                    'startIndex': start,
                    'endIndex': end
                },
                'style': {
                    'bold': True
                },
                'fields': 'bold'
            }
        })
        
    for start, end in header_ranges:
        requests.append({
            'updateTextStyle': {
                'objectId': object_id,
                'textRange': {
                    'type': 'FIXED_RANGE',
                    'startIndex': start,
                    'endIndex': end
                },
                'style': {
                    'fontSize': {'magnitude': 14, 'unit': 'PT'},
                    'bold': True,
                    'foregroundColor': text_color
                },
                'fields': 'fontSize,bold,foregroundColor'
            }
        })
        
    return clean_text, requests
