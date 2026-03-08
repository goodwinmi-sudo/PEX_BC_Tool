import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

import json

with open('personas.json', 'r') as f:
    personas_data = json.load(f)

for p in personas_data.get('executives', []):
    track = p.get('track', '')
    roles = []
    
    # Map track to roles array to support rule_engine and matrix
    if track == 'BC':
        roles.append('Approver_BC')
    elif track == 'PEX':
        roles.append('Approver_PEX')
    elif track == 'PEX+':
        roles.append('Approver_PEX+')
        roles.append('Approver_PEX')
    elif track == 'PEXpress':
        roles.append('Approver_PEXExpress')

    p['roles'] = roles

# Save back to dynamic_personas.json since rule_engine uses it
with open('dynamic_personas.json', 'w') as f:
    json.dump(personas_data, f, indent=4)

logger.info("dynamic_personas.json updated successfully with robust profiles & role arrays.")
