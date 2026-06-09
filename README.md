# langextract

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/chandakapu/langextract)

A Flask-based web application that provides a neuro-symbolic knowledge mapping workspace and an interactive visual workbench for Human-in-the-Loop (HITL) text extraction. It leverages Google's Gemini AI to automatically extract concepts and relationships to build an interactive knowledge graph, combined with visual grounding, manual annotation override tools, and action history tracking.

---

## 🌟 Key Features

### 1. Interactive Knowledge Graph & Workspace
- **Knowledge Graph Extraction** — Automatically extracts entities (nodes) and relationships (edges) from text using Google's Gemini AI.
- **Interactive Visualization** — Renders the knowledge graph as a navigable network using a local build of [Vis.js](https://visjs.org/).
- **Document Upload** — Supports `.txt`, `.md`, `.csv`, `.json`, and `.pdf` files.
- **Semantic Chat** — Ask questions about your knowledge base; the AI answers based on extracted concepts.
- **Semantic Search** — Search for nodes in the graph by meaning and relationships, not just exact keywords.
- **PDF Export** — Export a styled PDF summary of your concepts, relationships, and source documents.
- **Dynamic Fallback** — When the LLM is unavailable or rate-limited, a rule-based fallback extractor still produces useful results using sliding-window edge generation for focused, low-noise graphs.

### 2. HCI Extraction Studio (Visual Web Workbench)
- **Explainable AI (XAI) & Grounding** — Direct visual mapping linking extracted structured attributes/entities to their exact source text segment with alignment badges (✅ Solid Match, ⚠️ Partial/Overlapping, ❌ Missing).
- **Human-in-the-Loop (HITL) Agency** — Drag-select raw text to instantly add or override entity labels and key-value attributes.
- **Cognitive Load Reduction** — Pre-populated task templates (Romeo & Juliet character/emotion extraction, medical trial dosage, recipes) and dynamic schema classes builder.
- **Error Prevention & Recovery** — Full undo/redo system for all manual corrections, supported by a visual history panel.
- **Keyboard Shortcuts** — Tactile keys for fast undo (`Ctrl+Z`), redo (`Ctrl+Shift+Z`), saving (`Ctrl+S`), and dismissing popovers (`Escape`).

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python) with modular Blueprint architecture
- **AI / LLM:** Google Gemini (via `google.genai`)
- **Document NLP:** `langextract` library
- **PDF Generation:** ReportLab
- **Frontend:** Vanilla HTML/CSS/JS (Tailwind CSS, local Vis.js, and custom workbench layouts)
- **Schema Validation:** Pydantic

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A Google Gemini API key ([get one here](https://aistudio.google.com/app/apikey))

### Installation

1. Clone the repository and navigate into it:
   ```bash
   git clone https://github.com/chandakapu/langextract.git
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
├── app.py                    # App Factory registering workspace and studio blueprints
├── routes/                   # Modular routes package
│   ├── __init__.py
│   ├── workspace.py          # Workspace view and API endpoints (chat, search, analyze)
│   └── studio.py             # HCI Studio view and API endpoints (templates, extract, save)
├── core/
│   ├── __init__.py
│   ├── graph_extractor.py    # Gemini-based knowledge graph extraction
│   ├── doc_analyzer.py       # Document analysis and highlighting via langextract
│   └── pdf_generator.py      # PDF summary generation with ReportLab
├── lib/                      # Third-party frontend assets
│   ├── vis-9.1.2/            # Local Vis.js build
│   ├── tom-select/
│   └── bindings/
├── templates/                # HTML templates (Jinja2 / plain HTML)
│   ├── home.html             # Landing page
│   ├── workspace.html        # Interactive Knowledge Graph editor
│   ├── studio.html           # HCI Extraction Studio page
│   ├── features.html         # Features detail page
│   └── pricing.html          # Pricing and About page
├── static/
│   ├── utils.js              # Shared utility functions (e.g. escapeHtml)
│   ├── studio.css            # Extraction Studio specific styling
│   └── studio.js             # Client controller for the Visual Studio
├── LICENSE                   # MIT License
├── render.yaml               # Render infrastructure-as-code deployment blueprint
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
| `/api/save` | POST | Convert and download annotated grounded spans as a browser JSONL |

---

## ☁️ Deployment

You can deploy this project for free on **Render** (using the Free Web Service tier).

### One-Click Deploy
Click the button below to start deployment:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/chandakapu/langextract)

### Manual Setup on Render
1. Create a free account on [Render](https://render.com).
2. Click **New** -> **Web Service** and link this GitHub repository.
3. Use the following configuration:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Under **Advanced**, add the environment variable:
   - `GEMINI_API_KEY`: *Your Google Gemini API Key*
5. Click **Create Web Service**.

> [!NOTE]
> **Render Free Tier Cold-Start**: Because of the Render free tier limits, the application spins down after 15 minutes of inactivity. If the service is asleep, loading the page for the first time may take about 50 seconds to boot up.
>
> **Client-side JSONL Exports**: Saving annotations via `/api/save` processes the data in-memory and triggers a direct browser file download. No files are written or saved on the server's ephemeral filesystem, making it fully stateless and safe for multi-user deployment.

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key (used for graph extraction and chat) |
| `LANGEXTRACT_API_KEY` | No | API key override specifically for the LangExtract Studio workbench |

---

## ⚖️ License

MIT License. See [LICENSE](file:///home/chandaka/Documents/ANTIGRAVITY/knowledge-graph-notebook/LICENSE) for details.
