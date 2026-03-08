import json

with open('personas.json', 'r') as f:
    data = json.load(f)

for p in data['executives']:
    if p['name'] == 'Anat Ashkenazi':
        p['okrs'] = p['okrs'] + '\n- Enforce strict Financial Sensitivity: Stress-test "What you need to believe" assumptions. Identify heroic metrics and simulate total-loss scenarios.'
        p['persona'] = p['persona'].replace('Demands bulletproof financial models', 'Demands bulletproof financial models, deeply stressing NPV sensitivity')
        p['persona'] += "\n\nCRITICAL DIRECTIVE: Identify the single most heroic financial assumption and explain how a miss there could trigger a total-loss scenario (e.g. tariff exposure, hardware BOM misses)."
    
    elif p['name'] == 'Don Harrison':
        p['okrs'] = p['okrs'] + '\n- Rigorously evaluate Governance & Control ("Google Gets vs. Google Gives").'
        p['persona'] += "\n\nCRITICAL DIRECTIVE: Do not just list strategic tension. Evaluate the 'Google Gets vs Google Gives'. Identify any 'kingmaker' risk (e.g., giving 2-yr exclusivity). If the partner fails to execute, how difficult is it to pivot? You MUST suggest two additional precise 'Gets' (structuring / IP / data rights) we should negotiate to mitigate this."
        
    elif p['name'] == 'Kent Walker':
        p['persona'] += "\n\nCRITICAL DIRECTIVE: Do not just flag regulatory or structural risk. Propose a specific, contractual carve-out or structural mitigation term that shields us mathematically or legally from catastrophic downside."

with open('personas.json', 'w') as f:
    json.dump(data, f, indent=4)
print("Updated personas.json successfully.")
