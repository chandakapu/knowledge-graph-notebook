# langextract

A Flask-based web application that provides a neuro-symbolic knowledge mapping workspace and an interactive visual workbench for Human-in-the-Loop (HITL) text extraction. It leverages Google's Gemini AI to automatically extract concepts and relationships to build an interactive knowledge graph, combined with visual grounding, manual annotation override tools, and action history tracking.

---

## 🌟 Key Features

### 1. Interactive Knowledge Graph & Workspace
- **Knowledge Graph Extraction** — Automatically extracts entities (nodes) and relationships (edges) from text using Google's Gemini AI.
- **Interactive Visualization** — Renders the knowledge graph as a navigable network using [Vis.js](https://visjs.org/).
- **Document Upload** — Supports `.txt`, `.md`, `.csv`, `.json`, and `.pdf` files.
- **Semantic Chat** — Ask questions about your knowledge base; the AI answers based on extracted concepts.
- **Semantic Search** — Search for nodes in the graph by meaning and relationships, not just exact keywords.
- **PDF Export** — Export a styled PDF summary of your concepts, relationships, and source documents.
- **Dynamic Fallback** — When the LLM is unavailable or rate-limited, a rule-based fallback extractor still produces useful results.

### 2. HCI Extraction Studio (Visual Web Workbench)
- **Explainable AI (XAI) & Grounding** — Direct visual mapping linking extracted structured attributes/entities to their exact source text segment with alignment badges (✅ Solid Match, ⚠️ Partial/Overlapping, ❌ Missing).
- **Human-in-the-Loop (HITL) Agency** — Drag-select raw text to instantly add or override entity labels and key-value attributes.
- **Cognitive Load Reduction** — Pre-populated task templates (Romeo & Juliet character/emotion extraction, medical trial dosage, recipes) and dynamic schema classes builder.
- **Error Prevention & Recovery** — Full undo/redo system for all manual corrections, supported by a visual history panel.
- **Keyboard Shortcuts** — Tactile keys for fast undo (`Ctrl+Z`), redo (`Ctrl+Shift+Z`), saving (`Ctrl+S`), and dismissing popovers (`Escape`).

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **AI / LLM:** Google Gemini (via `google.genai`)
- **Document NLP:** `langextract` library
- **PDF Generation:** ReportLab
- **Frontend:** Vanilla HTML/CSS/JS (Tailwind CSS, Vis.js, and custom workbench layouts)
- **Schema Validation:** Pydantic

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A Google Gemini API key ([get one here](https://aistudio.google.com/app/apikey))

### Installation

1. Clone the repository and navigate into it:
   ```bash
   git clone https://github.com/chandakapu/knowledge-graph-notebook.git
   cd langextract
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
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

### Running the App

```bash
python3 app.py
```
The application will be available at **http://localhost:5000**.

---

## 📂 Project Structure

```
.
├── app.py                    # Main Flask application (routes, API endpoints, templates logic)
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
│   ├── home.html             # Landing page
│   ├── workspace.html        # Interactive Knowledge Graph editor
│   ├── studio.html           # HCI Extraction Studio page
│   ├── features.html         # Features detail page
│   └── pricing.html          # Pricing and About page
├── static/
│   ├── index.css             # Main workspace global stylesheet
│   ├── studio.css            # Extraction Studio specific styling
│   └── studio.js             # Client controller for the Visual Studio
├── gui_exports/              # Saved JSONL annotations and exports
├── requirements.txt
└── README.md
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` / `/home` | GET | Landing page |
| `/workspace` | GET | Main interactive knowledge graph workspace |
| `/studio` | GET | HCI Extraction Studio Visual Workbench |
| `/features` | GET | Features overview page |
| `/pricing` | GET | Pricing and About page |
| `/api/upload` | POST | Upload a file (txt, md, csv, json, pdf) |
| `/api/analyze` | POST | Extract knowledge graph & highlights from text |
| `/api/chat` | POST | Ask a question about the current graph |
| `/api/search` | POST | Semantic search within the graph |
| `/api/export-pdf` | POST | Export a PDF summary of the workspace |
| `/api/templates` | GET | Retrieve pre-configured studio schema templates |
| `/api/extract` | POST | Execute schema-constrained visual extraction |
| `/api/save` | POST | Export annotated grounded spans to a local `.jsonl` file |

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key (used for graph extraction and chat) |
| `LANGEXTRACT_API_KEY` | No | API key override specifically for the LangExtract Studio workbench |

---

## ⚖️ License

MIT
