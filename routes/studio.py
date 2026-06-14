import os
import logging
import traceback
import json
from flask import Blueprint, render_template, request, jsonify, Response
from core.studio_templates import TEMPLATES

studio_bp = Blueprint("studio", __name__)
logger = logging.getLogger("langextract.routes.studio")


@studio_bp.route("/studio")
def studio():
    return render_template("studio.html")


@studio_bp.route("/api/templates", methods=["GET"])
def get_templates():
    """Retrieve all pre-configured prompt, schema, and example templates."""
    return jsonify(TEMPLATES)


@studio_bp.route("/api/extract", methods=["POST"])
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
            
        logger.info("Running extract with model: %s", model_id)
        
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
        logger.error("ImportError during extract: %s", e)
        return jsonify({
            "error": "Failed to load LangExtract package. Ensure that dependencies are fully installed in the environment."
        }), 500
    except Exception as e:
        logger.exception("Exception during extraction run: %s", e)
        return jsonify({"error": str(e)}), 500


@studio_bp.route("/api/save", methods=["POST"])
def save_extraction():
    """Convert the annotated document (including user edits) to JSONL and return as a file download."""
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
        
        # Ensure target file name is secure
        filename = os.path.basename(filename)
        if not filename.endswith(".jsonl"):
            filename += ".jsonl"
            
        doc_dict = lx.io.data_lib.annotated_document_to_dict(annotated_doc)
        jsonl_str = json.dumps(doc_dict, ensure_ascii=False) + '\n'
        
        return Response(
            jsonl_str,
            mimetype="application/jsonl",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.exception("Failed to save document: %s", e)
        return jsonify({"error": str(e)}), 500
