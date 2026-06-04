# AetherGraph

A Flask-based web application that extracts and visualizes knowledge graphs from text and documents using Google's Gemini AI. Upload documents, edit text, and watch an interactive network graph of concepts and relationships build in real time.

## Features

- **Knowledge Graph Extraction** — Automatically extracts entities (nodes) and relationships (edges) from text using Google's Gemini AI.
- **Interactive Visualization** — Renders the knowledge graph as an interactive network using [Vis.js](https://visjs.org/).
- **Document Upload** — Supports `.txt`, `.md`, `.csv`, `.json`, and `.pdf` files.
- **Semantic Chat** — Ask questions about your knowledge graph; the AI answers based on extracted concepts.
- **Semantic Search** — Search for nodes by meaning, not just keywords.
- **PDF Export** — Export a styled PDF summary of your workspace, concepts, and relationships.
- **Dynamic Fallback** — When the LLM is unavailable or rate-limited, a rule-based fallback extractor still produces useful results.
- **Document Analysis** — Highlights key concepts, methods, and terms in the source text.

## Tech Stack

- **Backend:** Flask (Python)
- **AI / LLM:** Google Gemini (via `google.genai`)
- **Document NLP:** `langextract`
- **PDF Generation:** ReportLab
- **Frontend:** Vanilla HTML/CSS/JS with Vis.js for graph visualization
- **Schema Validation:** Pydantic

## Prerequisites

- Python 3.10+
- A Google Gemini API key ([get one here](https://aistudio.google.com/app/apikey))

## Installation

1. Clone the repository and navigate into it:

   ```bash
   git clone <repo-url>
   cd knowledge-graph-notebook
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set your Gemini API key:

   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```

   On Windows:

   ```cmd
   set GEMINI_API_KEY=your_api_key_here
   ```

## Running the App

```bash
python3 app.py
```

The application will be available at **http://localhost:5000**.

## Project Structure

```
.
├── app.py                    # Main Flask application (routes, API, fallback logic)
├── core/
│   ├── __init__.py
│   ├── graph_extractor.py    # Gemini-based knowledge graph extraction
│   ├── doc_analyzer.py       # Document analysis and highlighting via langextract
│   └── pdf_generator.py      # PDF summary generation with ReportLab
├── lib/                      # Third-party frontend assets
│   ├── vis-9.1.2/
│   ├── tom-select/
│   └── bindings/
├── templates/                # HTML templates (Jinja2 / plain HTML)
│   ├── home.html
│   ├── workspace.html
│   ├── features.html
│   └── pricing.html
├── static/
│   └── index.css
├── requirements.txt
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` / `/home` | GET | Landing page |
| `/workspace` | GET | Main knowledge graph editor |
| `/features` | GET | Features page |
| `/pricing` | GET | Pricing page |
| `/api/upload` | POST | Upload a file (txt, md, csv, json, pdf) |
| `/api/analyze` | POST | Extract knowledge graph from text |
| `/api/chat` | POST | Ask a question about the current graph |
| `/api/search` | POST | Semantic search within the graph |
| `/api/export-pdf` | POST | Export a PDF summary of the workspace |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key |

## Customizing Extraction

To improve knowledge graph extraction, you can modify:

1. **`app.py` → `RELATION_RULES`** — Add regex patterns for new semantic relationships in the fallback extractor.
2. **`core/graph_extractor.py` → `system_prompt`** — Update the LLM prompt to improve extraction accuracy or add new node/edge categories.
3. **`app.py` → `TECH_TERMS_DICT`** — Add known technical terms for the fallback extractor to recognize.

## License

MIT
