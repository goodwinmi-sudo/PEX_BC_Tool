---
description: PEX BC Tool 7-Step Deal Review Architecture
---
# The 7-Step Deal Review Architecture (The LayoutGen Standard)

This workflow defines the authoritative, aggressively polished pipeline for the "Test Review" / Native slides engine. **Do not deviate from these steps.** The goal is to produce breathtaking, Material Design 3 (M3) compliant Google Slides that seamlessly merge the user's original strategic context with ruthless executive feedback.

## 🚀 The 7-Step Execution Workflow

### Step 1: Ingestion (Draft Extraction)
- **Input:** The user provides a `source_presentation_id` (the Draft Deck), the specific "ask" (Deal Description), and the target organization filter.
- **Mechanism:** The `extract_presentation_data` function sweeps the user's current draft, capturing not just text, but established theming properties (like `pageBackgroundFill` and primary `fontFamily` from slide 0) to ensure the generated slides look like native extensions.

### Step 2: External Research (Live Web)
- **Tool:** Gemini equipped with `GoogleSearchRetrieval`.
- **Purpose:** Executes a real-time `run_research_node()` to extract live market intelligence and competitor dynamics, preventing the AI from hallucinating stale financial data.

### Step 3: Internal Intel (Workspace Graph)
- **Tool:** `workspace_client.gather_workspace_context()`
- **Purpose:** Scans Gmail, Google Drive, and Docs for historical deal context, previous P&L spreadsheets, and internal sentiment to ground the executive personas in actual corporate reality.

### Step 4: Panel Assembly (Persona Selection)
- **Mechanism:** The rule engine (`get_required_personas`) dynamically selects the correct Deal Review Personas (e.g., CPO, CRO, Truth Steward) based on the Deal Size and specific Risk Flags (e.g., Security, UX) identified during Ingestion.

### Step 5: Executive Review (Sequential Debate)
- **Mechanism:** Executes `run_sequential_debate_personas()`.
- **Nuance:** This is not a parallel blast. Executives review the ingested context *sequentially*, reading the critiques of their peers. This creates a realistic "debate" where the CPO might push back on a risk the Security lead identified, ending in a holistic view.

### Step 6: Feedback Generation (The Critique Payload)
- **Output:** The executives formulate their critiques using the **Operator Reasoning Framework**:
    1. **War-Game the Hinge:** Identify the single most critical dependency or assumption.
    2. **Forecast the Cascade:** Assume the dependency fails and explicitly describe the domino effect.
    3. **Mandate the Pivot:** Propose a specific, contractual carve-out or fallback.
- **Nuance:** They emphasize the **Conditional Approval Framework**, mandating strategic "Deal 2 Gating Requirements" instead of demanding retroactive, framework-destroying Deal 1 changes.

### Step 7: Presentation Packaging (The "Review Section")
- **The Planner (Gemini):** Ingests the critiques and maps them strictly to a fixed **Master Layout Dictionary** (extracted from a pristine template).
- **The Executor (Python Engine):** Parses the generated JSON to build the final presentation, structurally separating cognitive planning from physical slide rendering.

---

## 🧠 Cognitive Prompting & Feedback Nuance

Our ultimate goal is to provide **highly actionable, high-quality feedback** for the user providing the decks. A "passive auditor" approach (just listing pros and cons) is actively rejected. The tool uses the **Deal Architect Framework** to act as a predictive Operator:

1. **Trade-Off Empathy:** The prompt explicitly instructs the AI to acknowledge competitive tension (e.g., Apple/Meta alternatives) and propose middle-ground concessions instead of binary "No" vetoes.
2. **Proactive Drafting:** For every risk identified, the AI MUST generate exact **'Fallback Proposal'** or **'Counter-Proposal'** language for the deal team to copy-paste.
3. **Stoplight Prioritization System:** Feedback is structurally tagged to prioritize the user's limited time:
    - 🔴 **DEAL KILLER:** Fundamental flaw requiring a *Fallback Proposal*.
    - 🟡 **TRADE-OFF:** Negotiable item requiring a *Trade-Off Path*.
    - 🟢 **STRATEGIC MOAT:** Core strength to be protected.
4. **The Murder Board:** The AI anticipates hostile internal reviews by proactively generating the 3 hardest questions guaranteed to be asked by the Business Council, accompanied by steel-man answers.

---

## 💎 Visual Output Standards & Required Slides

The final packaged presentation **MUST** include:
1. **Summary & Decision Slide:** High-level verdict (BLUF - Bottom Line Up Front).
2. **Required Changes Slide:** The strict mitigations or unit caps.
3. **Persona Feedback Slides:** Dedicated slides highlighting each executive's specific critique.
4. **Custom Financial/Architecture Slides:** Standalone generated slides (like a 3-year P&L Markdown Table, architectural diagrams via Mermaid, or restructured terms).

---

## 🚨 Robustness Guardrails & Hard-Won Architecture Lessons

To preserve system integrity and visual aesthetics, developers MUST adhere to these critical historical lessons learned through extensive dogfooding:

### 1. The Layout Hallucination Trap
Never format system prompts with literal directive markers (e.g., `"<Insert EXACT key>"`) inside the JSON schema example. Structural LLMs will rigidly hallucinate that literal string instead of actively mapping valid Google Slides `layout_name` IDs, causing the engine to default entirely to Blank Slides or crash. **Always use an explicit valid layout string like `"Title Slide"` in the example.**

### 2. M3 Native Table Styling & Geometric Overflow
- **Material 3 UI:** Financial data must be constructed using native API `Table` objects with `#e9f0f8` header fills, bold typography, and 1pt `#ccd1d9` structural borders.
- **The Overflow Trap:** Table Y-Coordinate structural rendering must be strictly constrained using conservative layout intervals. To prevent massive multi-row tables from violently bleeding past the standard 540-PT Slide Canvas threshold, enforce a **14pt baseline**, scaling down to 12pt globally or 10pt locally if necessary.

### 3. Markdown Sanitization Pipeline
Because Google Slides cannot natively parse Markdown, the Python executor **must** run an abstract syntax tree (AST) strip. Raw tokens like `**`, `*`, `_`, and `###` must be regex-stripped from the JSON payload *before* `insertText` is called, applying native `updateTextStyle` boolean flags instead.

### 4. Avatar Layout Isolation Rules (Moma Injection)
Moma Persona injection must organically scan the ENTIRE slide text coordinate matrix (`combined_text = title + body`). Do not strictly tether Avatars only to the `title` element; Gemini unpredictably shifts Executive references into sub-headers or body cells. Always apply DRY truthy null-checks (`p.get('role') or ''`) before applying `in` conditionals to avoid backend `NoneType` Server Crashes.

### 5. Secure Asset Delivery (The Signed URL Fix)
Relying on direct Moma API calls frequently fails due to IAP blocking inside the Google Slides backend renderer (often yielding an `HttpError 500 Invalid JSON payload: solidFill` when shape fills fail). 
- **The Fix:** Avatars must be fetched via the proper Moma Teams Photos API, temporarily staged in a GCS bucket, and injected into the slides using a short-lived **Signed URL**, or fall back to a localized `/static/avatars/` cache to self-heal during network outages.

### 6. The Double-Brace Prompt Protocol
When passing JSON examples within Python string `.format()` calls (specifically inside `prompts.py`), all literal JSON braces MUST be doubled (`{{` and `}}`). Failure to do so results in a `KeyError` as Python attempts to evaluate JSON keys as interpolation variables.

### 7. Serverless CPU Throttling Stalls
When deploying background Python task runners (like our "Fire and Forget" Simulation Runner) to Cloud Run, you MUST attach the `--no-cpu-throttling` flag. Without this, Cloud Run instantly freezes the background threadpool between frontend HTTP polling requests, causing persona simulations to inexplicably pause mid-generation (resulting in UI Timeout errors).

### 8. Queue Starvation / Thread Death
Aggressive frontend API polling concurrent with serial multi-persona Gemini network generation will deadlock the background threadpool. Sequential Gemini node executions must be heavily isolated from Datastore UI polling to prevent 60-second `504 Deadline Exceeded` crashes on fundamental `datastore.get()` functions. 
