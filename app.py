import os
import re
from flask import Flask, render_template, request, jsonify

from core.graph_extractor import GraphExtractor
from core.doc_analyzer import DocAnalyzer

app = Flask(__name__)

# --------------------------------------------------------------------------- #
# Dynamic Fallback Extraction Configuration & Logic                          #
# --------------------------------------------------------------------------- #
STOPWORDS = {
    "the", "a", "an", "it", "this", "they", "we", "he", "she", "you", "i", 
    "in", "on", "at", "by", "for", "with", "to", "from", "and", "or", "but", 
    "if", "then", "else", "when", "where", "why", "how", "all", "any", "both", 
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", 
    "only", "own", "same", "so", "than", "too", "very", "is", "are", "was", 
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "of",
    "what", "which", "who", "whom", "whose", "whosever", "whichever", "that", "these", "those",
    "necessary", "unnecessary", "important", "unimportant", "general", "specific", 
    "main", "major", "minor", "simple", "complex", "basic", "advanced", "good", "bad",
    "something", "anything", "nothing", "someone", "anyone", "everyone", "noone", 
    "somebody", "anybody", "everybody", "nobody", "everything", "here", "there",
    "also", "just", "even", "still", "yet", "already", "never", "always", 
    "sometimes", "often", "usually", "seldom", "rarely", "about", "above", 
    "across", "after", "against", "along", "among", "around", "before", "behind", 
    "below", "beneath", "beside", "between", "beyond", "during", "except", 
    "inside", "into", "near", "off", "outside", "over", "past", "through", 
    "throughout", "under", "until", "up", "upon", "within", "without",
    "part", "parts", "example", "examples", "thing", "things", "way", "ways", 
    "use", "uses", "used", "using", "user", "users", "note", "notes", "detail", "details",
    "information", "info", "data", "result", "results", "output", "input", "process"
}

RELATION_RULES = [
    (r"\b(is a|is an|are|was a|were|defined as|refers to)\b", "SUBSET_OF"),
    (r"\b(uses|using|use|utilized|utilizes|employs)\b", "USES"),
    (r"\b(minimize|minimizes|minimizing|reduce|reduces|reducing|reduction)\b", "MINIMIZES"),
    (r"\b(improve|improves|improving|optimize|optimizes|optimizing)\b", "IMPROVES"),
    (r"\b(solve|solves|solving)\b", "SOLVES"),
    (r"\b(works at|work at|employed by|works in)\b", "WORKS_AT"),
    (r"\b(located in|lives in|situated in|based in)\b", "LOCATED_IN"),
    (r"\b(depends on|depend on|dependent on)\b", "DEPENDS_ON"),
    (r"\b(trains|training|trained by)\b", "TRAINS"),
    (r"\b(calculates|calculating|calculate|derived from)\b", "CALCULATES"),
    (r"\b(implements|implementing|implemented by)\b", "IMPLEMENTS"),
    (r"\b(supports|supporting)\b", "SUPPORTS"),
    (r"\b(generates|generating|created by|creates)\b", "CREATES"),
]

TECH_TERMS_DICT = {
    "artificial intelligence": ("Concept", "The simulation of human intelligence processes by machines, especially computer systems."),
    "machine learning": ("Concept", "A type of artificial intelligence (AI) that allows software applications to become more accurate at predicting outcomes without being explicitly programmed."),
    "deep learning": ("Concept", "A subset of machine learning, which is essentially a neural network with three or more layers."),
    "neural network": ("Algorithm", "A computational model inspired by the structure and function of biological neural networks."),
    "gradient descent": ("Algorithm", "An optimization algorithm used to minimize some function by iteratively moving in the direction of steepest descent."),
    "backpropagation": ("Method", "An algorithm used to calculate the gradient of the loss function with respect to the weights in a neural network."),
    "loss function": ("Theory", "A method of evaluating how well your specific algorithm models the given data."),
    "derivative": ("Concept", "The rate of change of a function with respect to a variable."),
    "optimization": ("Method", "The process of making something as fully perfect, functional, or effective as possible."),
    "tensor": ("Concept", "A mathematical object represented by an array of components that are functions of coordinates of a space."),
    "weights": ("Concept", "The learnable parameters in a neural network that scale the input data."),
    "bias": ("Concept", "An additional parameter in a neural network used to adjust the output along with the weighted sum of inputs."),
    "activation function": ("Method", "A mathematical formula that determines the output of a neural network node."),
    "supervised learning": ("Concept", "A machine learning paradigm where the model is trained on labeled data."),
    "unsupervised learning": ("Concept", "A machine learning paradigm where the model learns patterns from unlabeled data."),
    "reinforcement learning": ("Concept", "An area of machine learning concerned with how intelligent agents ought to take actions in an environment to maximize cumulative reward."),
    "natural language processing": ("Concept", "A subfield of computer science, information engineering, and artificial intelligence concerned with the interactions between computers and human languages."),
    "computer vision": ("Concept", "An interdisciplinary scientific field that deals with how computers can gain high-level understanding from digital images or videos."),
}

COMMON_VERBS = {
    "chased", "chase", "ran", "run", "saw", "see", "likes", "like", "hates", "hate",
    "loves", "love", "plays", "play", "works", "work", "located", "locate", "knows",
    "know", "helps", "help", "creates", "create", "makes", "make", "built", "build",
    "finds", "find", "owns", "own", "has", "have", "had", "is", "was", "are", "were",
    "need", "needs", "needed", "want", "wants", "wanted", "must", "should", "would",
    "could", "can", "may", "might", "make", "makes", "making", "made", "take", "takes",
    "taking", "took", "taken", "get", "gets", "getting", "got", "gotten", "go", "goes",
    "going", "went", "gone", "come", "comes", "coming", "came", "give", "gives", "giving",
    "gave", "given", "find", "finds", "finding", "found"
}

def clean_term(t: str) -> str:
    return re.sub(r'^[^\w]+|[^\w]+$', '', t).strip()

def dynamic_fallback_extract(text: str) -> dict:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    nodes = []
    edges = []
    highlights = []
    
    node_set = {}  # lowercase -> {name, type, description}
    edge_set = set() # (source, target, relation)
    
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
            
        # Tokenize sentence into words with start and end indices
        words = []
        for m in re.finditer(r'\b\w+\b', sent):
            w = m.group(0)
            words.append({
                "word": w,
                "start": m.start(),
                "end": m.end()
            })
            
        candidates = []
        i = 0
        while i < len(words):
            w_info = words[i]
            w_lower = w_info["word"].lower()
            
            # Skip stopwords, common verbs, and very short words
            if w_lower in STOPWORDS or w_lower in COMMON_VERBS or len(w_lower) <= 1:
                i += 1
                continue
                
            # Group consecutive non-stopwords/non-verbs
            group = [w_info]
            j = i + 1
            while j < len(words):
                next_w = words[j]
                next_lower = next_w["word"].lower()
                if next_lower not in STOPWORDS and next_lower not in COMMON_VERBS and len(next_lower) > 1:
                    group.append(next_w)
                    j += 1
                else:
                    break
                    
            term = sent[group[0]["start"]:group[-1]["end"]]
            candidates.append({
                "term": term,
                "start": group[0]["start"],
                "end": group[-1]["end"]
            })
            i = j
            
        # Add candidates to node_set
        for c in candidates:
            name = c["term"]
            name_lower = name.lower()
            
            # Check if it is a known technical term
            if name_lower in TECH_TERMS_DICT:
                node_type, desc = TECH_TERMS_DICT[name_lower]
                name = name_lower.title()
                if name_lower in ["artificial intelligence", "supervised learning", "unsupervised learning", "reinforcement learning", "natural language processing", "computer vision"]:
                    name = " ".join([w.capitalize() for w in name_lower.split()])
            else:
                # General heuristics
                node_type = "Concept"
                desc = f"Entity extracted from the context: \"{sent}\""
                
                # Check suffix-based rules
                if re.search(r'\b(algorithm|sort|search|tree|net)\b', name, re.I):
                    node_type = "Algorithm"
                elif re.search(r'\b(method|process|descent|propagation|training)\b', name, re.I):
                    node_type = "Method"
                elif re.search(r'\b(theory|law|function|model)\b', name, re.I):
                    node_type = "Theory"
                    
            if name_lower not in node_set:
                node_set[name_lower] = {
                    "name": name,
                    "type": node_type,
                    "description": desc
                }
            else:
                if "Entity extracted" in node_set[name_lower]["description"] and "Entity extracted" not in desc:
                    node_set[name_lower]["description"] = desc
                    node_set[name_lower]["type"] = node_type
                    
        # Find relationships
        for idx in range(len(candidates)):
            for jdx in range(idx + 1, len(candidates)):
                c1 = candidates[idx]
                c2 = candidates[jdx]
                
                between = sent[c1["end"]:c2["start"]]
                
                relation = "RELATED_TO"
                confidence = 0.5
                
                # Look for relation rules first
                matched_rule = False
                for pattern, rel_type in RELATION_RULES:
                    if re.search(pattern, between, re.I):
                        relation = rel_type
                        confidence = 0.8
                        matched_rule = True
                        break
                        
                if not matched_rule:
                    for verb in COMMON_VERBS:
                        if re.search(r'\b' + re.escape(verb) + r'\b', between, re.I):
                            relation = verb.upper()
                            confidence = 0.8
                            break
                            
                edge_sig = (c1["term"].lower(), c2["term"].lower(), relation)
                if edge_sig not in edge_set:
                    edge_set.add(edge_sig)
                    edges.append({
                        "source": node_set[c1["term"].lower()]["name"],
                        "target": node_set[c2["term"].lower()]["name"],
                        "relation": relation,
                        "confidence": confidence
                    })

    nodes = list(node_set.values())
    
    # Highlights
    sorted_node_names = sorted(nodes, key=lambda x: len(x["name"]), reverse=True)
    matched_ranges = []
    
    for node in sorted_node_names:
        name = node["name"]
        cls = "KeyConcept"
        if node["type"] in ["Algorithm", "Method"]:
            cls = "KeyMethod"
        elif node["type"] == "Theory":
            cls = "KeyTerm"
            
        for m in re.finditer(r'\b' + re.escape(name) + r'\b', text, re.I):
            start = m.start()
            end = m.end()
            
            overlap = False
            for rs, re_end in matched_ranges:
                if not (end <= rs or start >= re_end):
                    overlap = True
                    break
            if not overlap:
                matched_ranges.append((start, end))
                highlights.append({
                    "text": text[start:end],
                    "start": start,
                    "end": end,
                    "cls": cls
                })
                
    highlights.sort(key=lambda h: h["start"])
    
    if not nodes and text.strip():
        single_node = text.strip()[:30]
        if len(text.strip()) > 30:
            single_node += "..."
        nodes = [{
            "name": single_node,
            "type": "Concept",
            "description": f"Notes snippet: \"{text}\""
        }]
        highlights = [{
            "text": text,
            "start": 0,
            "end": len(text),
            "cls": "KeyConcept"
        }]
        
    return {
        "graph": {
            "nodes": nodes,
            "edges": edges
        },
        "highlights": highlights
    }


# --------------------------------------------------------------------------- #
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
def index():
    return render_template("index.html")


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
