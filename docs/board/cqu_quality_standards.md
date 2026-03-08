# CQU Quality Standards: UCE & Regression

As the CQU (Chief Quality Underminer/Understander), my role is to maintain the User Centered Excellence (UCE) standards and prevent regressions.

## UCE Standards

1. **Accuracy**: AI-generated suggestions must be technically sound and contextually relevant.
2. **Robustness**: The tool must handle edge cases in deal structures without crashing.
3. **Consistency**: The UI must follow the established BD design language.
4. **DRY (Don't Repeat Yourself)**: Every past bug is a test case in our harness.
5. **Transparency**: The About page (`templates/about.html`) MUST be kept up to date with the current bot version before every deployment.
6. **M3 Integrity**: HTML files must strongly prefer M3 components (`<md-`) over legacy HTML elements (like vanilla `<button>` or `<input>`).
7. **Security**: The codebase must never contain hardcoded API keys or secrets (e.g., `AIza...` for Google API).
8. **Data Integrity**: `personas.json` must be strictly validated. Every persona must have a `name`, `org`, `persona`, and `okrs`, and there must be at least 15 executives.
9. **Dark Mode Enforcement**: Every top-level template must explicitly declare `<html class="dark">` to ensure the War Room aesthetic is strictly maintained.
10. **Endpoint/Template Mapping**: Every `render_template` call in `app.py` must point to an existing file in `templates/`.
11. **PEX Document Sync**: The deployment must verify that `personas.json` is fresh and up-to-date with the live Google Sheets for Deal Criteria and PEX Approval Flow.

## Regression Log (Past Issues)

- Issue #001: JSON parsing error in `bot.bgl.json` when certain fields are null.
- Issue #002: Tailwind CSS not loading in the HTML dashboard view.
- Issue #003: "Launch simulation" button not responding in some viewports.

> [!WARNING]
> The Test Harness MUST be Updated daily and run before every deployment.
