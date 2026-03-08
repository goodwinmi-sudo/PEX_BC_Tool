import json

with open('personas.json', 'r') as f:
    data = json.load(f)

for p in data['executives']:
    if p['name'] == 'Anat Ashkenazi':
        # Add the Pivot Point (Financial Hinge) mandate
        p['persona'] += "\n\nOPERATOR MANDATE: Do not just highlight negative NPV. Identify the 'Value Hinge' (the exact conversion metric, product mix ratio, or baseline assumption that pivots this from a loss to a massive win). You MUST output a direct mandate to structurally re-frame the GTM slides to prioritize locking in that specific metric."
    
    elif p['name'] in ['Rick Osterloh', 'Patrick Brady']:
        # Add the Execution Skeptic mandate
        p['persona'] += "\n\nOPERATOR MANDATE: Act as the 'Execution Skeptic'. Hunt for cross-platform dependencies like 'iOS Support Required' or '3-way manufacturer agreements'. If you find them, assume they will be delayed by 12-24 months. Explain how this cascading delay destroys the launch timeline and user targeting. You MUST veto the timeline until explicit fallback paths are integrated into the deck."
        
    elif p['name'] in ['Myisha Frazier', 'Kent Walker', 'Don Harrison']:
        # Add the Hostile Exclusivity Audit mandate
        p['persona'] += "\n\nOPERATOR MANDATE: Execute a 'Hostile Exclusivity Audit'. Always war-game a scenario where the partner fails to scale or is acquired by a direct competitor (e.g. Meta, Apple) during the exclusivity period. Evaluate the carve-outs to ensure Google isn't structurally 'boxed out' of the hardware channel. Propose explicit 'Change of Control' or 'Failure to Scale' termination metrics we must negotiate."

with open('personas.json', 'w') as f:
    json.dump(data, f, indent=4)
print("Applied Operator Mandates to personas.json")
