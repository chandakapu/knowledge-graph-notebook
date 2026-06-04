import os
import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from google import genai
from google.genai import types
from pydantic import BaseModel


# --- Pydantic Schemas ---
class Node(BaseModel):
    name: str
    type: str          # e.g. "Method", "Concept", "Algorithm"
    description: str


class Edge(BaseModel):
    source: str
    target: str
    relation: str      # e.g. "USES", "SUBSET_OF", "MINIMIZES"
    confidence: float  # 0.0 – 1.0 AI-generated confidence


class KnowledgeGraph(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


# --- Extractor Class ---
class GraphExtractor:
    def __init__(self, model_id: str = "gemini-2.5-flash", timeout_seconds: int = 60):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Please set it before running."
            )
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=2)

    def extract(self, text: str) -> dict:
        """
        Extract a structured knowledge graph from the given text using Gemini.
        Returns a plain dict with 'nodes' and 'edges' lists.
        """
        print(f"\n[Gemini GraphExtractor] Sending request to Gemini ({self.model_id})...")
        print(f"[Gemini GraphExtractor] Input Text: {text!r}")
        
        system_prompt = """You are an expert knowledge graph construction engine.
Your goal is to extract a highly accurate, structured, and semantically rich knowledge graph from the given text.

Guidelines for Nodes (Entities):
1. Identify all core concepts, algorithms, methods, tools, theories, persons, or applications mentioned in the text.
2. The `name` must be a clean, concise noun phrase in Title Case (e.g., "Backpropagation", "Gradient Descent", "Objective Function"). Never use long sentences, verbs, or pronouns as node names.
3. Classify each node into one of these strict categories:
   - `Concept`: Core ideas, abstractions, data representations, or parameters (e.g., "Weights", "Bias", "Activation").
   - `Method`: Technical procedures, workflows, techniques (e.g., "Supervised Learning", "Data Augmentation").
   - `Algorithm`: Precise mathematical/computational steps or models (e.g., "Stochastic Gradient Descent", "Neural Network").
   - `Tool`: Software, libraries, or hardware platforms (e.g., "PyTorch", "NumPy", "GPU").
   - `Theory`: Mathematical theorems, laws, axioms (e.g., "Bayes' Theorem", "Information Theory").
   - `Person`: Key historical figures or researchers explicitly named (e.g., "Geoffrey Hinton").
   - `Application`: Domains or use cases of these technologies (e.g., "Computer Vision", "Natural Language Processing").
4. Provide a precise, self-contained `description` of the node summarizing its definition, functionality, or context as described in the text.

Guidelines for Edges (Relationships):
1. Connect nodes only if there is a clear semantic relationship mentioned or implied.
2. The `source` and `target` fields must match the extracted node `name` EXACTLY (case-sensitive). Do not introduce phantom nodes that are not in the nodes list.
3. Use specific, uppercase relationship verbs. Preferred verbs include:
   - `USES` / `IMPLEMENTS`: A method/algorithm utilizes a concept/tool.
   - `SOLVES` / `MINIMIZES` / `OPTIMIZES`: An algorithm or method solves a problem or optimizes a function (e.g., "Gradient Descent" -> "MINIMIZES" -> "Loss Function").
   - `PART_OF` / `SUBSET_OF`: Hierarchical relations.
   - `DEFINES` / `DESCRIBES`: Conceptual relationships.
   - `APPLIES_TO`: Usage domains.
   - `CALCULATES`: Math derivation.
   - `TRAINS`: Training processes.
   - `DEPENDS_ON`: Direct dependencies.
   - `INFLUENCES` / `IMPROVES`: Impact relationships.
4. Assign a realistic `confidence` score (0.0 to 1.0) representing the evidence strength:
   - `1.0`: Directly and explicitly stated.
   - `0.8`: Strongly implied or standard textbook knowledge.
   - `0.5`: Suggested or indirectly referenced.
   - `0.2`: Speculative or very weak.

Ensure output is a valid JSON object matching the requested schema.
"""
        try:
            # Use a thread-based timeout to prevent indefinite blocking
            future = self._executor.submit(
                self.client.models.generate_content,
                model=self.model_id,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=KnowledgeGraph,
                    temperature=0.2,
                ),
            )
            response = future.result(timeout=self.timeout_seconds)
            print("[Gemini GraphExtractor] Response received successfully.")
        except FuturesTimeoutError:
            print(f"[Gemini GraphExtractor] API call timed out after {self.timeout_seconds}s")
            raise TimeoutError(
                f"Gemini API call timed out after {self.timeout_seconds} seconds. "
                "The server may be overloaded. Falling back to local extraction."
            )
        except Exception as e:
            print(f"[Gemini GraphExtractor] API Call Failed: {e}")
            raise e

        kg = response.parsed
        if kg is not None:
            return {
                "nodes": [n.model_dump() for n in kg.nodes],
                "edges": [e.model_dump() for e in kg.edges],
            }

        # Fallback: parse manually from response.text if response.parsed is None
        try:
            raw_text = response.text.strip()
            # Clean markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = re.sub(r'^```[a-zA-Z]*\n|```$', '', raw_text, flags=re.MULTILINE).strip()
            parsed_json = json.loads(raw_text)
            
            # Map keys and make sure they exist
            nodes = []
            for n in parsed_json.get("nodes", []):
                nodes.append({
                    "name": str(n.get("name", "")),
                    "type": str(n.get("type", "Concept")),
                    "description": str(n.get("description", ""))
                })
            edges = []
            for e in parsed_json.get("edges", []):
                edges.append({
                    "source": str(e.get("source", "")),
                    "target": str(e.get("target", "")),
                    "relation": str(e.get("relation", "RELATED_TO")),
                    "confidence": float(e.get("confidence", 0.5))
                })
            return {
                "nodes": nodes,
                "edges": edges
            }
        except Exception as pe:
            raise ValueError(f"Failed to parse model response: {response.text}. Error: {pe}")
