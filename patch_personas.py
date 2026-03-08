import json

with open('personas.json', 'r') as f:
    data = json.load(f)

for p in data['executives']:
    # Initialize roles if not present
    if 'roles' not in p:
        p['roles'] = []

    name = p['name']
    
    # Map Global PEX+
    if name == 'Rick Osterloh':
        p['roles'] = ['Approver_PEX+']
        p['org'] = 'Global'
    
    # Map Global PEX
    elif name in ['Sameer Samat', 'Cristina Bita', 'Marc Ellenbogen']:
        p['roles'] = ['Approver_PEX']
        p['org'] = 'Global'
    
    # Map Specific PEXpress
    elif name == 'Kara Bailey': p['roles'] = ['Approver_PEXExpress']; p['org'] = 'Android OS'
    elif name == 'Patrick Brady': p['roles'] = ['Approver_PEXExpress']; p['org'] = 'Android Auto'
    elif name == 'Shalini GovilPai': p['roles'] = ['Approver_PEXExpress']; p['org'] = 'Android TV'
    elif name == 'Sam Bright': p['roles'] = ['Approver_PEXExpress']; p['org'] = 'Google Play'
    elif name == 'Mike Torres': p['roles'] = ['Approver_PEXExpress']; p['org'] = 'Chrome Browser'
    
    # Let Architect and Artist be Global PEX
    elif name in ['The Architect', 'The Artist']:
        p['roles'] = ['Approver_PEX']
        p['org'] = 'Global'

# Add Android XR specific personas
new_personas = [
    {
        "name": "Shahram Izadi",
        "ldap": "shahrami",
        "track": "PEXpress",
        "org": "Android XR",
        "okrs": "- Build the spatial computing ecosystem for Android.\n- Partner with OEMs for XR headsets.",
        "persona": "Role: VP, AR/XR.\n\nCommunication Style: Visionary but highly technical.\n\nStrategic Focus: Spatial computing, 3D ecosystems.",
        "refinements": [],
        "quarter": "2026-Q1",
        "last_updated": "2026-03-05T00:00:00Z",
        "id": "e16",
        "roles": ["Approver_PEXExpress"]
    },
    {
        "name": "Christian Cramer",
        "ldap": "ccramer",
        "track": "PEXpress",
        "org": "Global",
        "okrs": "- P&D financial discipline for PEXpress deals.",
        "persona": "Role: Finance Director.\n\nCommunication Style: Strict on margins and deal economics.",
        "refinements": [],
        "quarter": "2026-Q1",
        "last_updated": "2026-03-05T00:00:00Z",
        "id": "e17",
        "roles": ["Approver_PEXExpress"]
    },
    {
        "name": "Rina Shah",
        "ldap": "rinashah",
        "track": "PEXpress",
        "org": "Android XR",
        "okrs": "- Legal risk mitigation for emerging platforms like XR and TV.",
        "persona": "Role: Legal Counsel.\n\nCommunication Style: Risk-averse, focuses on data privacy and IP.",
        "refinements": [],
        "quarter": "2026-Q1",
        "last_updated": "2026-03-05T00:00:00Z",
        "id": "e18",
        "roles": ["Approver_PEXExpress"]
    }
]

# Ensure we don't add duplicates
existing_names = [p['name'] for p in data['executives']]
for np in new_personas:
    if np['name'] not in existing_names:
        data['executives'].append(np)

with open('personas.json', 'w') as f:
    json.dump(data, f, indent=4)

print("Patched personas.json successfully.")
