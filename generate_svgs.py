import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

import json, os
with open('personas.json', 'r') as f:
    executives = json.load(f).get('executives', [])
os.makedirs('static/moma_images', exist_ok=True)
for i, p in enumerate(executives):
    pid = p.get('id') or f"e{i}"
    # Assign the generated ID back to personas.json to ensure consistency
    p['id'] = pid 
    name = p.get('name', 'User')
    parts = name.split()
    initials = "".join([part[0] for part in parts])[:2].upper() if parts else "U"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" fill="#3b82f6" rx="20"/><text x="50" y="50" font-family="Arial" font-size="40" fill="white" text-anchor="middle" dominant-baseline="central">{initials}</text></svg>'
    with open(f"static/moma_images/{pid}.svg", "w") as out:
        out.write(svg)

with open('personas.json', 'w') as f:
    json.dump({"executives": executives}, f, indent=4)
logger.info("SVGs generated and personas.json updated with IDs if missing.")
