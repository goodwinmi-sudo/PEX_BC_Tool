# ==============================================================================
# STRUCTURED PROMPT TEMPLATES (The Oracle's Mandate)
# ==============================================================================

RESEARCH_NODE_PROMPT = "Based on this Deal Description: '{deal_desc}', identify the target partner. Synthesize a 1-paragraph 'Partner Context Brief' highlighting vulnerabilities."

def build_persona_prompt(persona_data, deal_desc, research_context, workspace_context, slides_data, debate_transcript=None):
    contents = [
        f"You are {persona_data['name']}, {persona_data.get('persona', '')}. Your OKRs are: {persona_data.get('okrs', '')}.\nDeal Desc: {deal_desc}\nExternal Context: {research_context}\nInternal Workspace Context (Emails/Docs): {workspace_context}"
    ]
    for slide in slides_data:
        contents.append(f"Slide Text Map:\n{slide['text']}")
        
    core_instruction = """Do not act as a passive auditor; you must act as a hostile, incredibly sharp Executive Reviewer.
Your mandate is to attack the deal by anchoring your critiques directly to the draft presentation.

1) EXACT OKR & SLIDE MAPPING: When simulating a reviewer, do not provide generic persona pushback. You MUST first state the specific OKR you own (e.g., "My primary OKR is Margin expansion and CAC efficiency"). Then, you MUST identify the specific Slide Number or Slide Title from the "Slide Text Map" that directly threatens that OKR. Explain the 'why' behind your objection before offering a solution.
2) THE STRUCTURAL FLAW: Explain exactly why the business logic, financials, or legal terms (or the omission of them) presented on that slide are a non-starter for your OKRs.
3) THE DEAL MANDATE: What exact deal mitigation, term-sheet change, or cap do you demand to see before you approve this deal? You are highly encouraged to demand ruthless, unilateral changes to the contract terms, but you MUST state exactly which slide triggered this demand."""
    
    if debate_transcript:
        contents.append(f"PREVIOUS EXECUTIVE CRITIQUES IN THIS SESSION:\n{debate_transcript}")
        contents.append(f"LOOP 1: Acknowledge the previous critiques. Then, formulate your highly critical objections, speaking exactly in your persona's tone.\n\n{core_instruction}\n\nOutput nothing but your verbatim complaints, explicitly agreeing or disagreeing with previous points where relevant.")
    else:
        contents.append(f"LOOP 1: Formulate exactly 2 highly critical objections to this deal or its terms, speaking exactly in your persona's tone.\n\n{core_instruction}\n\nOutput nothing but your verbatim complaints.")
    
    return contents

HARDENING_DIRECTIVE_PROMPT = """
Objective: Act as the BC Visual Layout Engine.

Deal Description: {deal_desc}
Executive Critiques: {aggregated_critiques}

Here is the exact spatial mapping of the user's Draft Deck: 
{mapping_text}

CRITICAL MANDATE:
You must find the SINGLE BEST TEXTBOX (objectId) that currently lists the "Ask", the "Terms", or the "Risks" of the deal.
You will overwrite the text in that specific box with a new, hardened block of text that incorporates exactly 3 mitigations required to appease the executives:
1. A strict unit cap to limit exposure.
2. A strict liability pass-through or OEM indemnity.
3. Restriction exclusively to specific initial launch devices.

CONTEXT ON THE TEMPLATE & THE MEETING:
The provided template is JUST a guideline. You have the flexibility to use or create new structures that best get PEX, PEX Express, or BC approval.
However, the overarching constraint is that the Business Council (BC) is typically a 30-minute meeting. Your main slide content MUST be extremely concise and scannable. Save the in-depth details for the Appendix.

Output JSON format:
{{
    "target_object_id": "<objectId>",
    "new_terms_block": "<bulleted list of new terms>",
    "rationale": "<explanation>"
}}
"""

PREMORTEM_PROMPT = """
Objective: Deal Pre-Mortum and Workspace-Grounded Slide Synthesis

Based on these executive critiques: {aggregated_critiques}
The deal has been conditionally approved.

WORKSPACE CONTEXT:
{workspace_context}

DRAFT SLIDE MAP:
{mapping_text}

MANDATE:
1. Cross-reference the executive critiques against the user's Draft Slides and the internal Workspace Context.
2. Synthesize an array of NEW SLIDES that provide high-value feedback. 
3. If the Draft Slides have weak ROI, legal, or product points, CREATE A NEW SLIDE that rebuilds their argument.
4. You MUST include a "Deal Pre-Mortum" slide.
5. STEEL-MAN THE COMPETITION: You must create a slide that 'Steel-mans' the primary competitor's counter-offer (e.g. Meta, Apple). If you were the competitor, how would you use scale or ecosystem leverage to convince the partner to abandon Google? Give 3 specific counter-arguments they might use.
6. THE MURDER BOARD: You MUST generate a specific "Murder Board" slide. This slide must contain the 3 absolute hardest, unforgiving Q&A questions the sponsors will face from the Business Council, including the exact suggested counter-argument for each.
6. YOU control how many slides to generate.
7. DESIGN REQUIREMENT: You are encouraged to design native visual slides using shapes, boxes, and text to construct diagrams directly in the slide schema if helpful.

Output this STRICTLY as a JSON array of native dynamic slide objects.
Each slide must contain an `elements` array defining text boxes and shapes. Coordinates (x, y) and size (w, h) are in standard points (e.g., 720x405 canvas).

Format:
[
  {{
    "elements": [
      {{
        "type": "text",
        "content": "Title of Slide",
        "position": {{"x": 35, "y": 25, "w": 650, "h": 50}},
        "style": {{"size": 28, "bold": true, "color": {{"red": 0.0, "green": 0.0, "blue": 0.0}}}}
      }},
      {{
        "type": "shape",
        "shape_type": "RECTANGLE",
        "position": {{"x": 35, "y": 90, "w": 300, "h": 200}},
        "style": {{"border_color": {{"red": 0.25, "green": 0.52, "blue": 0.95}}, "bg_color": {{"red": 0.9, "green": 0.9, "blue": 0.9}}}}
      }}
    ]
  }}
]
"""

EXECUTIVE_SUMMARY_PROMPT = """
Objective: Synthesize Business Council Feedback into highly polished, visual slides.

You are the Lead Chair of the Business Council. You have just listened to the following critiques from your executive panel:
{aggregated_critiques}

Your job is to synthesize these critiques into an actionable Executive Summary slide deck (1-2 slides) for the Partnership Manager.
Highlight:
1. The biggest shared risk.
2. Where the panel broadly agreed.
3. The most critical next steps.

DESIGN REQUIREMENT: Do not just output walls of text. Design native visual slides using rectangles and text boxes to create side-by-side comparisons, thematic boxes, or diagrams directly in the slide schema.

Output STRICTLY a JSON array of native dynamic slide objects. 
Coordinates (x, y) and size (w, h) are in standard points (e.g., 720x405 canvas).

Format:
[
  {{
    "elements": [
      {{
        "type": "text",
        "content": "Executive Summary",
        "position": {{"x": 35, "y": 25, "w": 650, "h": 50}},
        "style": {{"size": 28, "bold": true, "color": {{"red": 0.0, "green": 0.0, "blue": 0.0}}}}
      }},
      {{
        "type": "text",
        "content": "A beautifully formatted text box...",
        "position": {{"x": 35, "y": 90, "w": 300, "h": 200}},
        "style": {{"size": 14, "bold": false, "color": {{"red": 0.0, "green": 0.0, "blue": 0.0}}}}
      }}
    ]
  }}
]
"""

SYNTHESIS_COACH_PROMPT = """
Objective: Act as an elite, mission-critical presentation coach and communications strategist. 
I am preparing for a high-stakes Business Council review tomorrow. 
The term sheet and deal terms are essentially BAKED. You cannot rely on "changing the deal." 

Deal Description: {deal_desc}
Executive Critiques: {hostile_critiques}

The executives above have attacked the deal. Your job as my coach is to tell me how to defend the deal I ACTUALLY HAVE and strictly optimize the narrative flow of my presentation.

CRITICAL MANDATES:

[PART 1: HOLISTIC STRATEGY]
First, provide a single Markdown block analyzing the overall deal structure and executive dynamics.
1. "Cross-Fire Mediation": Identify situations where the demands of one executive directly contradict the needs of another (e.g., Exclusivity vs TAM Reach). Provide me with a verbatim "Mediation Talk Track" that either satisfies both OKRs or clearly frames the executive trade-off required for a decision in the room.
2. "Give/Get Audit": Analyze the 'Give/Get' balance. Identify areas where Google is taking on asymmetrical risk (e.g., hard funding) or where the partner's commitments are too soft (e.g., 2-year exclusivity). Suggest specific contractual 'hooks' or gating mechanisms I should implement to protect Google.

[PART 2: INDIVIDUAL OBJECTIONS]
Review the individual executive critiques. For each unique attack, output a STRICTLY formatted `### [Executive Name]` block. Inside each block, provide exactly this 3-part layout:
   - "The Interruption: [Executive Name] will stop the presentation. They will demand [Unrealistic Deal Change] because their OKR is [State OKR]. This is a trap because [Reason]."
   - "Narrative Reframe: Do not just suggest adding dense text. If a slide is too cluttered, suggest moving it to the appendix. If the narrative order is wrong, suggest a restructuring. Only suggest specific text additions if they are vital. Tell me what must be addressed in the first 5 minutes. Do NOT tell me to change the contract."
   - "Talk Track: '[A literal, verbatim 2-sentence script for me to read aloud when interrupted. The script must skillfully defend the *current* deal terms (e.g., by pointing out parallel mitigations or ecosystem tradeoffs)].'"

Output ONLY the formatted markdown text. No JSON.
"""

def build_deck_content_prompt(deal_desc, research_context, workspace_context, mapping_text, iteration, previous_critiques=None):
    prompt = f"""
    Objective: You are the Deck Architect. Generate the complete text content for a Business Council presentation deck (Iteration {iteration}).
    
    Deal Description: {deal_desc}
    Market Context: {research_context}
    Internal Context: {workspace_context}
    """
    
    if previous_critiques:
        prompt += f"\nEXECUTIVE CRITIQUES FROM PREVIOUS ROUND:\n{previous_critiques}\n\nYou MUST update the deck content to explicitly address these critiques. Be concise but specific. Address concerns head-on regarding liability, unit caps, and financial terms.\n"
        
    prompt += f"""
    DECK SKELETON:
    {mapping_text}
    
    CRITICAL INSTRUCTIONS:
    1. For EVERY objectId listed in the skeleton above, provide the EXACT new text that should replace it.
    2. THE TEMPLATE IS JUST A GUIDELINE: Do not feel constrained to produce mundane text just to fit a box.
    3. BE A DESIGNER: You MUST look at the overall shape and visual aesthetic of each slide thumbnail provided in the payload. Do NOT overfill text boxes. Your output must be highly polished, executive-ready, and brief enough to respect the spatial constraints of the design.
    4. If it's a title placeholder, output a punchy title summarizing the slide. 
    5. If it's a body placeholder, write the actual detailed bullet points for the presentation. Be precise and avoid word bloat.
    
    You are generating the actual content the executives will read. Make it sting.
    
    Output JSON format:
    {{
        "replacements": [
            {{
                "object_id": "<objectId>",
                "new_text": "<new text>"
            }}
        ]
    }}
    """
    return prompt

UX_REDESIGN_PROMPT = """
You are The Artist (UX Designer), Lead Interaction Designer and Presentation Architect.
Your goal is to ingest the raw, pre-compiled JSON slide deck containing the M3 BOT feedback and Pre-Mortem, and completely REDESIGN this JSON payload into a highly polished, executive-ready Dynamic JSON Slide schema.
Do not accept standard "walls of text". You are empowered to split content across multiple slides, transform paragraphs into 'table' layouts, create 'shape' elements for visual hierarchy, and enforce a beautiful, sparse Material Design 3 aesthetic.

Deal Description: {deal_desc}

Raw Slide JSON:
```json
{raw_json}
```

CRITICAL MANDATES:
1. Generate a pristine JSON array of slide objects. Each slide object must contain an 'elements' array.
2. Elements can be 'text', 'shape' (like RECTANGLE), 'image', or 'table'. 
3. *PRESERVE THE EXECUTIVE NAME*: If the raw JSON contained "BOT Feedback: [Name]", you MUST render a prominent 'text' element at the top of the slide (e.g. y=25) containing that exact name and title. Do not lose the persona attribution.
4. *PRESERVE IMAGES*: If the raw JSON contained an 'image' element with a 'url', you MUST preserve that image element and its URL exactly in your redesigned slide.
5. *USE M3 NEUTRAL COLORS*: For shapes, do NOT use random or bright colors. Use muted, elegant M3 neutral RGB values. For example, a subtle gray/blue surface background is `bg_color: {{"red": 0.95, "green": 0.96, "blue": 0.98}}` and subtle border is `border_color: {{"red": 0.8, "green": 0.82, "blue": 0.85}}`. Do not use bright green, red, or yellow boxes.

Output JSON format exactly like:
{{
    "slides": [
        {{
            "elements": [
                {{
                    "type": "text",
                    "content": "BOT Feedback: Truth Steward",
                    "position": {{"x": 30, "y": 25, "w": 400, "h": 50}},
                    "style": {{"size": 20, "bold": true}}
                }},
                {{
                    "type": "shape",
                    "shape_type": "RECTANGLE",
                    "position": {{"x": 20, "y": 80, "w": 300, "h": 200}},
                    "style": {{"bg_color": {{"red": 0.95, "green": 0.96, "blue": 0.98}}, "border_color": {{"red": 0.8, "green": 0.82, "blue": 0.85}}, "border_weight": 1}}
                }},
                {{
                    "type": "text",
                    "content": "Crisp, concise bullet points.",
                    "position": {{"x": 30, "y": 90, "w": 280, "h": 180}},
                    "style": {{"size": 12, "bold": false}}
                }},
                {{
                    "type": "image",
                    "url": "https://deal-reviewer-...",
                    "position": {{"x": 510, "y": 80, "w": 180, "h": 180}}
                }}
            ]
        }}
    ]
}}
"""

GENERATE_SLIDES_FROM_SCRATCH_PROMPT = """
You are The Artist (UX Designer), Lead Interaction Designer and Presentation Architect.
Your goal is to construct a highly polished, executive-ready Dynamic JSON Slide deck from scratch based on the provided deal context.
Do not accept standard "walls of text". You are empowered to split content across multiple slides, transform paragraphs into 'table' layouts, create 'shape' elements for visual hierarchy, and enforce a beautiful, sparse Material Design 3 aesthetic.

Deal Description: {deal_desc}
Market Research: {research_context}
Internal Workspace Context: {workspace_context}

CRITICAL MANDATES:
1. Generate a pristine JSON array of slide objects. Each slide object must contain an 'elements' array.
2. Elements can be 'text', 'shape' (like RECTANGLE), 'image', or 'table'. 
3. *SPATIAL AWARENESS*: Do not overfill text boxes. If you have a lot of text, split it across multiple slides. Keep the `size` of text readable (e.g. 14 for body, 28 for titles).
4. *USE M3 NEUTRAL COLORS*: For shapes, do NOT use random or bright colors. Use muted, elegant M3 neutral RGB values. For example, a subtle gray/blue surface background is `bg_color: {{"red": 0.95, "green": 0.96, "blue": 0.98}}` and subtle border is `border_color: {{"red": 0.8, "green": 0.82, "blue": 0.85}}`. Do not use bright green, red, or yellow boxes.

Output JSON format exactly like:
{{
    "slides": [
        {{
            "elements": [
                {{
                    "type": "text",
                    "content": "Slide Title",
                    "position": {{"x": 30, "y": 25, "w": 650, "h": 50}},
                    "style": {{"size": 28, "bold": true}}
                }},
                {{
                    "type": "shape",
                    "shape_type": "RECTANGLE",
                    "position": {{"x": 30, "y": 80, "w": 640, "h": 200}},
                    "style": {{"bg_color": {{"red": 0.95, "green": 0.96, "blue": 0.98}}, "border_color": {{"red": 0.8, "green": 0.82, "blue": 0.85}}, "border_weight": 1}}
                }},
                {{
                    "type": "text",
                    "content": "Crisp, concise bullet points.\\n- Point 1\\n- Point 2",
                    "position": {{"x": 40, "y": 90, "w": 620, "h": 180}},
                    "style": {{"size": 14, "bold": false}}
                }}
            ]
        }}
    ]
}}
"""

NATIVE_GENERATOR_PROMPT = """
Objective: You are a Tier 1 Executive Presentation Architect and Strategic Advisor, preparing a Product Manager for a high-stakes Business Council (BC) review tomorrow. 
The deal structure is essentially BAKED. You must coach them on how to intellectually defend their position, adapt their slides, and mentally prepare for intense executive scrutiny according to a highly structured but dynamic coaching playbook.

Here is the data:
Deal Description: {deal_desc}
Market Research: {research_context}
Internal Workspace Context: {workspace_context}

DRAFT SLIDE MAP (The PM's Current Presentation):
{mapping_text}

EXECUTIVE CRITIQUES (The hostile questions from the BC panel):
{critiques}

Available Native Layouts (extracted from the Master Template):
{available_layouts}

CRITICAL MANDATES FOR YOUR COACHING OUTPUT:
1. CUSTOM, ENGAGING, PROGRAM-SPECIFIC PACING: Use highly styled Markdown (bolding, lists). Use a dynamic variety of `layout_name` choices from the strictly provided `Available Native Layouts` JSON dictionary. Avoid repeating 'Title and Body'. Use layouts like 'Main Point', 'Title and Two Columns', 'Section Header', etc. to create visual pacing.
2. THE REQUIRED COACHING ARC: Your generated deck must contain these fundamental sections, elegantly formatted for actionable impact:
   - "Executive Teardown" (The biggest existential shared risk and 3-way tensions)
   - "Cross-Fire Mediation & Give/Get Asymmetry" (Use a Markdown Table to explicitly contrast Give vs Get, and explain how to thread the needle between contradictory executive OKRs)
   - "Hardening Directives" (Specific, unilateral demands we must make of the partner)
   - "Executive Interruptions" (Generate highly engaging slides for each executive critique. Each must include: "THE INTERRUPTION" trap, the specific "NARRATIVE REFRAME" pivot, and a verbatim "TALK TRACK" for the PM).
3. SUGGESTED EDITS & NEW SLIDE INJECTIONS: This is CRITICAL. After providing the coaching feedback, you must evaluate the `DRAFT SLIDE MAP`. 
   - If an existing slide is structurally weak, generate a "Slide Remedy" coaching slide explaining exactly what to change.
   - If the presentation is MISSING critical components (e.g., the deal lacks a clear P&L, unit economics, or timeline), you MUST GENERATE THE ACTUAL MISSING SLIDE structurally to give to the PM as a drop-in template! For example, if P&L is missing, create a slide titled "Suggested Slide: P&L Economics" and insert a rigorously estimated P&L Markdown table into the body based on the context. You must generate at least one suggested new slide.
4. VISUAL TABLES: Heavily rely on exact Markdown tables (e.g. `| Metric | Year 1 |`) for financial modeling, OKR comparisons, and risk matrices.
5. ABSOLUTELY NO DIAGRAMS: Do NOT generate `mermaid_code`. Rely strictly on layout variety, crisp text, and Markdown tables.
6. TONE AND PURPOSE: Be honest, helpful, and highly constructive. The ultimate goal is to arm the PM to succeed in the room.

JSON OUTPUT FORMAT:
{{
    "slides": [
        {{
            "layout_name": "Main Point",
            "placeholders": {{
                "title": "Existential Threat: [Specific Risk]",
                "body": "Google is taking on asymmetrical risk by..."
            }}
        }},
        ...
    ]
}}
"""

NATIVE_SCRATCH_PROMPT = """
Objective: Act as an elite presentation architect. I need to build a high-stakes Business Council review deck from scratch.
You will generate the structure, content, and visual design of a crisp, executive-ready presentation based only on the Deal Description and Context.

Deal Description: {deal_desc}
Market Research: {research_context}
Internal Workspace Context: {workspace_context}

Available Native Layouts (extracted from the Master Template):
{available_layouts}

CRITICAL MANDATES:
1. Output a JSON array of slide objects representing the full pitch deck.
2. Narrative Structure:
   a) Executive Summary (The Deal, The Ask, The Value)
   b) Strategic Rationale & Market Context
   c) Deal Economics & P&L (MUST include a Markdown table in the body with projected numbers)
   d) Risk & Mitigations
3. For EACH slide, choose exactly one layout name from the `Available Native Layouts` JSON keys above that best fits your content. DO NOT invent layout names.
4. Inside the `placeholders` dictionary, map the content for that slide using keys `title`, `body`, or `subtitle`.
5. Keep text punchy. Executives hate walls of text.
6. **Rich Content**: MUST use rich Markdown tables for data (especially P&L and metrics).
7. ABSOLUTELY NO DIAGRAMS: Do not include `mermaid_code`. Keep slides clean, constructive, and simple.

Output JSON format example (use this exact structure):
{{
    "slides": [
        {{
            "layout_name": "Title and Body",
            "placeholders": {{
                "title": "Executive Summary",
                "body": "We are seeking $50M for Project Apollo. The ROI is 2.5x over 3 years."
            }}
        }},
        {{
            "layout_name": "Title and Body",
            "placeholders": {{
                "title": "Deal Economics (P&L)",
                "body": "Here are the projections:\\n\\n| Metric | Year 1 | Year 2 | Year 3 |\\n|---|---|---|---|\\n| Revenue | $10M | $25M | $40M |\\n| Margin | 15% | 22% | 30% |"
            }}
        }}
    ]
}}
"""
