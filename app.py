import os
import re
import json
import traceback
from flask import Flask, render_template, request, jsonify, send_file
from pydantic import BaseModel
from google.genai import types

from core.graph_extractor import GraphExtractor
from core.doc_analyzer import DocAnalyzer
from core.pdf_generator import generate_summary_pdf
from core.fallback_extractor import dynamic_fallback_extract
from core.studio_templates import TEMPLATES

class ChatResponse(BaseModel):
    answer: str
    related_nodes: list[str]

class SearchResponse(BaseModel):
    matched_nodes: list[str]
    reason: str

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# Lazy-initialise services (they check for the API key at runtime)            #
# --------------------------------------------------------------------------- #
_graph_extractor: GraphExtractor | None = None
_doc_analyzer: DocAnalyzer | None = None


def get_graph_extractor() -> GraphExtractor:
    global _graph_extractor
    if _graph_extractor is None:
        _graph_extractor = GraphExtractor()
    return _graph_extractor


def get_doc_analyzer() -> DocAnalyzer:
    global _doc_analyzer
    if _doc_analyzer is None:
        _doc_analyzer = DocAnalyzer()
    return _doc_analyzer


# --------------------------------------------------------------------------- #
# Routes                                                                        #
# --------------------------------------------------------------------------- #

@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")


@app.route("/workspace")
def workspace():
    return render_template("workspace.html")


@app.route("/features")
def features():
    return render_template("features.html")


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
        
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        file_bytes = file.read()
        extracted_text = ""
        
        if ext in [".txt", ".md", ".csv", ".json"]:
            extracted_text = file_bytes.decode("utf-8", errors="ignore")
        elif ext == ".pdf":
            import pypdf
            from io import BytesIO
            reader = pypdf.PdfReader(BytesIO(file_bytes))
            pages_text = []
            for page in reader.pages:
                pages_text.append(page.extract_text() or "")
            extracted_text = "\n".join(pages_text)
        else:
            return jsonify({"error": f"Unsupported file extension: {ext}"}), 400
            
        extracted_text = extracted_text.strip()
        if not extracted_text:
            return jsonify({"error": "The uploaded file is empty or no text could be extracted."}), 400
            
        print(f"\n[Flask API] File uploaded successfully: {filename} ({len(file_bytes)} bytes)")
        print(f"[Flask API] Extracted text length: {len(extracted_text)} characters")
        
        return jsonify({
            "filename": filename,
            "text": extracted_text
        })
        
    except Exception as e:
        print(f"[Flask API] Error parsing uploaded file {filename}: {e}")
        return jsonify({"error": f"Failed to parse file: {str(e)}"}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Expects JSON: { "text": "..." }
    Returns JSON:
    {
        "graph": { "nodes": [...], "edges": [...] },
        "highlights": [ { "text", "start", "end", "cls" }, ... ]
    }
    """
    body = request.get_json(force=True)
    text: str = (body or {}).get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided."}), 400

    errors = []

    # --- Knowledge Graph via google.genai ---
    graph_data = {"nodes": [], "edges": []}
    try:
        extractor = get_graph_extractor()
        graph_data = extractor.extract(text)
    except ValueError as ve:
        print(f"[Flask API] Graph extraction skipped (value error): {ve}")
        errors.append(f"Graph extraction skipped: {ve}")
    except Exception as e:
        print(f"[Flask API] Graph extraction failed: {e}")
        errors.append(f"Graph extraction error: {e}")

    # Fallback if graph is empty (e.g. rate limit)
    if not graph_data.get("nodes"):
        print("[Flask API] Graph empty or API error. Invoking dynamic fallback extractor for graph...")
        fallback_data = dynamic_fallback_extract(text)
        graph_data = fallback_data["graph"]
        errors.append("Using fallback graph data due to API error or empty result.")
    else:
        fallback_data = None

    # --- Document Analysis via langextract ---
    highlights = []
    try:
        analyzer = get_doc_analyzer()
        highlights = analyzer.analyze(text)
    except Exception as e:
        print(f"[Flask API] Doc analysis failed: {e}")
        errors.append(f"Doc analysis error: {e}")

    # Fallback if highlights are empty
    if not highlights:
        print("[Flask API] Highlights empty or API error. Invoking dynamic fallback extractor for highlights...")
        if fallback_data is None:
            fallback_data = dynamic_fallback_extract(text)
        highlights = fallback_data["highlights"]

    response = {
        "graph": graph_data,
        "highlights": highlights,
    }
    if errors:
        response["warnings"] = errors

    return jsonify(response)


@app.route("/api/export-pdf", methods=["POST"])
def export_pdf():
    """
    Expects JSON:
    {
        "nodes": [...],
        "edges": [...],
        "documents": [...]
    }
    Generates and returns the PDF summary as a file download.
    """
    body = request.get_json(force=True) or {}
    nodes = body.get("nodes", [])
    edges = body.get("edges", [])
    documents = body.get("documents", [])
    
    try:
        pdf_buffer = generate_summary_pdf(nodes, edges, documents)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="langextract_summary.pdf"
        )
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[Flask API] PDF Export Failed:\n{tb}")
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500




@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Expects JSON:
    {
        "question": "What is gradient descent?",
        "nodes": [...],   # current graph nodes from the frontend
        "edges": [...]    # current graph edges from the frontend
    }
    Returns JSON: { "answer": "...", "related_nodes": [...] }
    """
    body = request.get_json(force=True) or {}
    question: str = (body.get("question") or "").strip()
    nodes: list   = body.get("nodes", [])
    edges: list   = body.get("edges", [])

    if not question:
        return jsonify({"error": "No question provided."}), 400

    # ── Build a concise knowledge-base summary from the graph ─────────────────
    kb_lines = []
    for n in nodes:
        name  = n.get("name", "")
        ntype = n.get("type", "Concept")
        desc  = n.get("description", "")
        if name:
            kb_lines.append(f"- [{ntype}] {name}: {desc}")

    for e in edges:
        src = e.get("source", "")
        rel = e.get("relation", "RELATED_TO")
        tgt = e.get("target", "")
        if src and tgt:
            kb_lines.append(f"- {src} --[{rel}]--> {tgt}")

    kb_text = "\n".join(kb_lines) if kb_lines else "(No knowledge graph data available yet.)"

    # ── Local fallback keyword matching (always run first, or keep as fallback) ─
    q_words = set(re.findall(r'\b\w+\b', question.lower()))
    fallback_related_nodes = []
    for n in nodes:
        name_words = set(re.findall(r'\b\w+\b', (n.get("name") or "").lower()))
        desc_words = set(re.findall(r'\b\w+\b', (n.get("description") or "").lower()))
        if q_words & (name_words | desc_words):
            fallback_related_nodes.append(n.get("name", ""))

    answer = ""
    related_nodes = []

    # ── Try Gemini for structured answer and semantic search by meaning and relationships ──
    try:
        extractor = get_graph_extractor()
        
        system_prompt = """You are langextract AI Assistant — an expert research assistant in a knowledge-graph workspace.
Your task is to answer user questions using the provided knowledge graph (nodes and edges) as your primary context, and identify which nodes are semantically relevant to the query based on their meaning and relationships.

Instructions:
1. Examine the provided knowledge graph context (nodes and edges).
2. Answer the question clearly, concisely, and accurately based on the graph.
3. If the graph does not contain the answer, state that clearly, then provide a general answer based on your broader knowledge.
4. "Search by meaning and relationships": Analyze the semantic meaning of the question and the relationships in the graph. List up to 5 node names from the graph that are semantically related to the question or its answer (even if they don't share exact words). Do not invent names; select only from the provided graph node names.
5. Return the result strictly in the requested JSON format containing:
   - `answer`: your text response (use **bold** for key terms, keep under 200 words).
   - `related_nodes`: list of related node names found in the graph.
"""

        prompt = f"""Knowledge Graph Data:
{kb_text}

User Question: {question}
"""
        response = extractor.client.models.generate_content(
            model=extractor.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=ChatResponse,
                temperature=0.3,
            )
        )
        
        chat_data = response.parsed
        if chat_data is not None:
            answer = chat_data.answer
            related_nodes = chat_data.related_nodes
            print(f"[Flask /api/chat] Structured Gemini response received. Related nodes: {related_nodes}")
        else:
            # Fallback parse from raw text
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r'^```[a-zA-Z]*\n|```$', '', raw_text, flags=re.MULTILINE).strip()
            parsed_json = json.loads(raw_text)
            answer = parsed_json.get("answer", "")
            related_nodes = parsed_json.get("related_nodes", [])
            print(f"[Flask /api/chat] Parsed raw JSON Gemini response. Related nodes: {related_nodes}")

    except Exception as e:
        print(f"[Flask /api/chat] Gemini unavailable or failed: {e}. Using local keyword fallback.")
        traceback.print_exc()

    # ── Fallback if API call failed ──
    if not answer:
        related_nodes = fallback_related_nodes
        if related_nodes:
            matched = []
            for n in nodes:
                if n.get("name") in related_nodes:
                    matched.append(f"**{n['name']}** ({n.get('type','Concept')}): {n.get('description','')}")
            answer = (
                "Based on your knowledge graph, here's what I found:\n\n"
                + "\n\n".join(matched[:5])
            )
        else:
            answer = (
                "I couldn't find specific information about that in your current knowledge graph. "
                "Try adding more notes or uploading documents related to this topic — "
                "I'll be able to give a better answer once the graph has more context."
            )

    # Clean up related_nodes: ensure they actually exist in the graph (case-insensitive match)
    existing_names = {n.get("name", "").lower(): n.get("name", "") for n in nodes}
    cleaned_related_nodes = []
    for rn in related_nodes:
        if rn.lower() in existing_names:
            cleaned_related_nodes.append(existing_names[rn.lower()])
    
    # If cleaned is empty but we have fallback matches, use fallback matches
    if not cleaned_related_nodes and fallback_related_nodes:
        cleaned_related_nodes = fallback_related_nodes[:5]

    return jsonify({"answer": answer, "related_nodes": cleaned_related_nodes})


@app.route("/api/search", methods=["POST"])
def search():
    """
    Expects JSON:
    {
        "query": "minimizing loss function",
        "nodes": [...]  # list of current nodes
    }
    Returns JSON: { "matched_nodes": ["Gradient Descent", "Objective Function"], "reason": "..." }
    """
    body = request.get_json(force=True) or {}
    query: str = (body.get("query") or "").strip()
    nodes: list = body.get("nodes", [])

    if not query:
        return jsonify({"matched_nodes": [], "reason": ""})

    if not nodes:
        return jsonify({"matched_nodes": [], "reason": "Graph is empty."})

    # Prepare node context
    node_desc = []
    for n in nodes:
        name = n.get("name", "")
        ntype = n.get("type", "Concept")
        desc = n.get("description", "")
        node_desc.append(f"- [{ntype}] {name}: {desc}")
    nodes_text = "\n".join(node_desc)

    try:
        extractor = get_graph_extractor()
        system_prompt = """You are langextract Semantic Search Engine.
Given a user query and a list of nodes with descriptions, identify which nodes are semantically relevant to the query based on their meaning, concepts, and descriptions.
Rank them in order of relevance.
List up to 3 node names. The names must match the node names in the list EXACTLY.
Return the result strictly as JSON matching the schema:
- `matched_nodes`: list of matching node names in order of relevance.
- `reason`: a brief 1-sentence description of the match connection.
"""
        prompt = f"""Nodes list:
{nodes_text}

Query: {query}
"""
        response = extractor.client.models.generate_content(
            model=extractor.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=SearchResponse,
                temperature=0.1,
            )
        )
        search_data = response.parsed
        if search_data is not None:
            matched_nodes = search_data.matched_nodes
            reason = search_data.reason
        else:
            # Fallback parse from raw text
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r'^```[a-zA-Z]*\n|```$', '', raw_text, flags=re.MULTILINE).strip()
            parsed_json = json.loads(raw_text)
            matched_nodes = parsed_json.get("matched_nodes", [])
            reason = parsed_json.get("reason", "")
    except Exception as e:
        print(f"[Flask /api/search] Semantic search failed: {e}. Using local keyword fallback.")
        # Local keyword match fallback
        q_words = set(re.findall(r'\b\w+\b', query.lower()))
        matched_nodes = []
        for n in nodes:
            name_words = set(re.findall(r'\b\w+\b', (n.get("name") or "").lower()))
            desc_words = set(re.findall(r'\b\w+\b', (n.get("description") or "").lower()))
            if q_words & (name_words | desc_words):
                matched_nodes.append(n.get("name", ""))
        reason = "Matched by keywords."

    # Validate names
    existing_names = {n.get("name", "").lower(): n.get("name", "") for n in nodes}
    cleaned_matches = []
    for m in matched_nodes:
        if m.lower() in existing_names:
            cleaned_matches.append(existing_names[m.lower()])

    return jsonify({"matched_nodes": cleaned_matches, "reason": reason})


# --------------------------------------------------------------------------- #


@app.route("/studio")
def studio():
    return render_template("studio.html")


@app.route("/api/templates", methods=["GET"])
def get_templates():
    """Retrieve all pre-configured prompt, schema, and example templates."""
    return jsonify(TEMPLATES)


@app.route("/api/extract", methods=["POST"])
def run_extraction():
    """Execute LangExtract using the live Python package."""
    try:
        import langextract as lx
        
        request_data = request.get_json(force=True) or {}
        text = request_data.get("text", "").strip()
        prompt_description = request_data.get("prompt_description", "").strip()
        examples = request_data.get("examples", [])
        model_id = request_data.get("model_id", "gemini-2.5-flash")
        api_key = request_data.get("api_key") or os.environ.get("LANGEXTRACT_API_KEY") or os.environ.get("GEMINI_API_KEY")
        temperature = request_data.get("temperature")
        if temperature is not None:
            try:
                temperature = max(0.0, min(2.0, float(temperature)))
            except (TypeError, ValueError):
                temperature = None
        
        if not text:
            return jsonify({"error": "Please enter a target document first!"}), 400
        if not prompt_description:
            return jsonify({"error": "Extraction instructions cannot be empty!"}), 400
            
        if not api_key and "gemini" in model_id.lower():
            return jsonify({
                "error": "A Gemini API Key is required for cloud-hosted Gemini models. Please enter your API Key in the settings sidebar."
            }), 400

        # Prepare example data structure
        lx_examples = []
        for ex in examples:
            lx_extractions = []
            for ext in ex.get("extractions", []):
                lx_extractions.append(
                    lx.data.Extraction(
                        extraction_class=ext.get("extraction_class"),
                        extraction_text=ext.get("extraction_text"),
                        attributes=ext.get("attributes", {})
                    )
                )
            lx_examples.append(
                lx.data.ExampleData(
                    text=ex.get("text"),
                    extractions=lx_extractions
                )
            )
            
        print(f"\n[Flask /api/extract] Running extract with model: {model_id}")
        
        # Invoke LangExtract
        result = lx.extract(
            text_or_documents=text,
            prompt_description=prompt_description,
            examples=lx_examples,
            model_id=model_id,
            api_key=api_key,
            temperature=temperature,
            show_progress=False
        )
        
        # Parse output into clean JSON serializable response
        serialized_extractions = []
        for ext in result.extractions:
            char_interval = None
            if ext.char_interval:
                char_interval = {
                    "start_pos": ext.char_interval.start_pos,
                    "end_pos": ext.char_interval.end_pos
                }
            
            serialized_extractions.append({
                "extraction_class": ext.extraction_class,
                "extraction_text": ext.extraction_text,
                "char_interval": char_interval,
                "alignment_status": ext.alignment_status.value if ext.alignment_status else None,
                "extraction_index": ext.extraction_index,
                "attributes": ext.attributes or {}
            })
            
        return jsonify({
            "document_id": result.document_id,
            "text": result.text,
            "extractions": serialized_extractions
        })

    except ImportError as e:
        print(f"[Flask /api/extract] ImportError during extract: {e}")
        return jsonify({
            "error": "Failed to load LangExtract package. Ensure that dependencies are fully installed in the environment."
        }), 500
    except Exception as e:
        print(f"[Flask /api/extract] Exception during extraction run: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/save", methods=["POST"])
def save_extraction():
    """Save the annotated document (including user edits) to a local JSONL file."""
    try:
        import langextract as lx
        
        request_data = request.get_json(force=True) or {}
        text = request_data.get("text")
        document_id = request_data.get("document_id")
        extractions = request_data.get("extractions", [])
        filename = request_data.get("filename", "custom_extraction.jsonl")
        
        # Convert requests annotations to lx.data.Extraction format
        lx_extractions = []
        for idx, ext in enumerate(extractions):
            char_interval = None
            if ext.get("char_interval"):
                char_interval = lx.data.CharInterval(
                    start_pos=ext["char_interval"]["start_pos"],
                    end_pos=ext["char_interval"]["end_pos"]
                )
            
            lx_extractions.append(
                lx.data.Extraction(
                    extraction_class=ext["extraction_class"],
                    extraction_text=ext["extraction_text"],
                    char_interval=char_interval,
                    extraction_index=ext.get("extraction_index", idx),
                    attributes=ext.get("attributes", {})
                )
            )
            
        annotated_doc = lx.data.AnnotatedDocument(
            document_id=document_id,
            text=text,
            extractions=lx_extractions
        )
        
        # Ensure target file name is secure and written within workspace
        filename = os.path.basename(filename)
        if not filename.endswith(".jsonl"):
            filename += ".jsonl"
            
        current_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(current_dir, "gui_exports")
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        lx.io.save_annotated_documents([annotated_doc], output_name=filename, output_dir=output_dir)
        
        return jsonify({
            "status": "success",
            "filepath": filepath,
            "message": f"Successfully exported extraction document to {filepath}"
        })
        
    except Exception as e:
        print(f"[Flask /api/save] Failed to save document: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)
