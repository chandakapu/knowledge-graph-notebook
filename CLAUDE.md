# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a Flask-based application for extracting and visualizing knowledge graphs from text and PDFs. It comprises two distinct user interfaces, each with its own data pipeline, served by a single Flask app (`app.py`).

### Dual-Mode Application

1.  **Knowledge Graph Workspace** (`/` / `/workspace`): The main interactive graph editor.
    - Users upload text/PDFs.
    - The app extracts entities and relationships and renders them as a navigable Vis.js network.
    - Supports chat, semantic search, and PDF export.
2.  **HCI Extraction Studio** (`/studio`): A schema-constrained visual workbench built around the `langextract` library.
    - Pre-populated templates (e.g., "Clinical Trial", "Recipe") reduce cold-start cognitive load.
    - Visual grounding and alignment badges (✅ Solid Match, ⚠️ Partial/Overlapping, ❌ Missing) link extractions to source text.
    - Full undo/redo system for all manual corrections, backed by a visual history panel.

### Key Backend Components

- **`core/graph_extractor.py` (`GraphExtractor`)**: Wraps the Google `genai` client. It uses a Pydantic schema (`KnowledgeGraph`) to force the Gemini model into returning a strict JSON object of nodes and edges. It also contains a fallback JSON parser to handle raw string responses if the structured output fails.
- **`core/doc_analyzer.py` (`DocAnalyzer`)**: Uses the `langextract` library with few-shot examples to extract key concepts, methods, and terms as span annotations for the frontend to highlight.
- **`core/pdf_generator.py` (`generate_summary_pdf`)**: Uses ReportLab to generate a styled PDF summary of nodes, edges, and source documents. Registers TrueType fonts from `C:/Windows/Fonts`, falling back to Helvetica if not available.
- **`app.py` (Dynamic Fallback Extractor)**: `dynamic_fallback_extract()` is a critical, self-contained fallback module. When the Gemini API is unavailable or returns empty results, this function uses a rule-based system (`STOPWORDS`, `RELATION_RULES`, `TECH_TERMS_DICT`, `COMMON_VERBS`) to produce nodes, edges, and highlights from raw text. Any change to extraction heuristics should be reflected here as well as in the `GraphExtractor` prompt.

### Data Flow

```
Frontend → Flask Route → Service (Gemini/ LangExtract) → Structured JSON
   │
   └── Fallback: dynamic_fallback_extract() (local, no API)
```

Services (`GraphExtractor`, `DocAnalyzer`) are lazy-initialized via `get_graph_extractor()` and `get_doc_analyzer()` globals, not at import time, to avoid failing on missing `GEMINI_API_KEY` during module load.

### Studio Templates

Hardcoded in `app.py` under `TEMPLATES` dict. Adding or modifying a template requires updating the schema, examples, prompt, and default input text in this dictionary.

### Frontend

- **Workspace graph rendering**: Vanilla JS + Vis.js (bundled in `lib/`).
- **Studio interface**: Vanilla JS (`static/studio.js`) with Tailwind CSS (loaded from CDN).
- HTML templates in `templates/` (Jinja2), with Tailwind configured inline in `workspace.html`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key. Used by `GraphExtractor`, `DocAnalyzer`, the chat endpoint, and as the default API key for the Studio. |
| `LANGEXTRACT_API_KEY` | No | Optional override for the `langextract` package in the Studio. Falls back to `GEMINI_API_KEY` if not set. |

## Development Commands

This is a simple Flask application with no build step, test suite, or linting configuration.

```bash
# Run the app
python3 app.py
```
The development server starts on `http://localhost:5000`.

There is currently no test suite, CI, or linting setup. If adding dependencies, update `requirements.txt`.

## Extending Extraction

To improve graph extraction or add new relationship types:

1.  **LLM-based extraction**: Edit the `system_prompt` in `core/graph_extractor.py` and update Pydantic schemas (`Node`, `Edge`, `KnowledgeGraph`).
2.  **Fallback extraction**: Add new relationship regex patterns to `RELATION_RULES` in `app.py`. Add known technical terms and their descriptions to `TECH_TERMS_DICT`.
3.  **Studio templates**: Add new entries to the `TEMPLATES` dictionary in `app.py`.
