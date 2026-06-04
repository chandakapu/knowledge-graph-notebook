# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This repository contains a Flask-based application for extracting and visualizing knowledge graphs from text and documents.

*   **`app.py`**: The central Flask application. It defines routes, handles API requests (upload, analyze, chat, search, export), and coordinates between the extraction logic and the LLM. It includes dynamic fallback mechanisms for extraction when the LLM service is unavailable or returns empty results.
*   **`core/`**:
    *   **`graph_extractor.py`**: Handles structured knowledge graph extraction using Google GenAI (Gemini). Uses Pydantic for schema validation of nodes and edges.
    *   **`doc_analyzer.py`**: Performs document analysis (likely highlighting/tagging).
    *   **`pdf_generator.py`**: Generates PDF summaries from the extracted knowledge graph data.
*   **`lib/`**: Contains third-party frontend dependencies, specifically Vis.js for network visualization and Tom Select for dropdown interaction.

## Common Development Tasks

### Environment Configuration
The application requires a `GEMINI_API_KEY` environment variable to function, as it is used by the `GraphExtractor` to communicate with Google's GenAI models.

### Running the Application
The app is a standard Flask application. It can be run using the following command from the root directory:

```bash
python3 app.py
```

This starts the development server (configured with `debug=True`) on port 5000.

### Adding New Extraction Rules
If you need to improve the graph extraction, focus on these areas:

1.  **`app.py` -> `RELATION_RULES`**: Add regex patterns here to identify new types of semantic relationships during the fallback extraction process.
2.  **`core/graph_extractor.py` -> `GraphExtractor`**: Update the `system_prompt` to improve LLM-based extraction accuracy or node/edge classification schema.
3.  **`app.py` -> `TECH_TERMS_DICT`**: Add known technical terms and their descriptions to the lookup dictionary for the fallback extractor.
