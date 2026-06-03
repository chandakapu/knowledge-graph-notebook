import os
import json
import re
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
    def __init__(self, model_id: str = "gemini-2.5-flash"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Please set it before running."
            )
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id

    def extract(self, text: str) -> dict:
        """
        Extract a structured knowledge graph from the given text using Gemini.
        Returns a plain dict with 'nodes' and 'edges' lists.
        """
        print(f"\n[Gemini GraphExtractor] Sending request to Gemini ({self.model_id})...")
        print(f"[Gemini GraphExtractor] Input Text: {text!r}")
        
        system_prompt = """You are an expert knowledge graph builder.
Given a piece of text, extract all important concepts, methods, and entities as nodes.
Then identify the relationships between those nodes as directed edges.

For EACH edge assign a confidence score (float between 0.0 and 1.0) representing
how strongly the relationship is supported by the text (1.0 = explicitly stated,
0.5 = implied, 0.2 = weakly related).

Node types can be: Concept, Method, Algorithm, Tool, Theory, Person, Application.
Edge relation types can be: USES, SUBSET_OF, SOLVES, FINDS, MINIMIZES, IMPROVES,
RELATED_TO, DEFINED_AS, APPLIES_TO, CALCULATES, TRAINS, DEPENDS_ON.

Return ONLY valid JSON matching the schema. Do not include markdown code fences.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=KnowledgeGraph,
                    temperature=0.2,
                ),
            )
            print("[Gemini GraphExtractor] Response received successfully.")
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
