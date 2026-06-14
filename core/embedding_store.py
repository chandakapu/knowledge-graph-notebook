import os
import logging
import numpy as np
from google import genai

logger = logging.getLogger("langextract.embedding_store")

class EmbeddingStore:
    def __init__(self, model_id: str = "models/gemini-embedding-001"):
        self.model_id = model_id
        self._client = None
        # key: lowercase node name, value: {"node": node_dict, "vector": np.ndarray}
        self.store = {}
        # store current list of edges
        self.edges = []

    @property
    def client(self):
        if self._client is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set.")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def clear(self):
        self.store.clear()
        self.edges.clear()

    def get_embedding(self, text: str) -> np.ndarray:
        try:
            res = self.client.models.embed_content(
                model=self.model_id,
                contents=text
            )
            return np.array(res.embeddings[0].values, dtype=np.float32)
        except Exception as e:
            logger.error("Failed to generate embedding: %s", e)
            raise e

    def embed_nodes(self, nodes: list[dict], edges: list[dict] = None):
        """
        Embeds a list of nodes and stores them.
        Each node is expected to be a dict: {"name": str, "type": str, "description": str}
        """
        if edges is not None:
            # Re-sync edges
            self.edges = edges
            
        for node in nodes:
            name = node.get("name", "")
            if not name:
                continue
            key = name.lower()
            text_to_embed = f"[{node.get('type', 'Concept')}] {name}: {node.get('description', '')}"
            
            # Skip if we already embedded the identical node
            if key in self.store:
                old_node = self.store[key]["node"]
                old_text = f"[{old_node.get('type', 'Concept')}] {old_node.get('name', '')}: {old_node.get('description', '')}"
                if text_to_embed == old_text:
                    self.store[key]["node"] = node  # keep metadata fresh
                    continue
            
            try:
                vector = self.get_embedding(text_to_embed)
                self.store[key] = {
                    "node": node,
                    "vector": vector
                }
                logger.info("Embedded node: %s", name)
            except Exception as e:
                logger.error("Error embedding node %s: %s", name, e)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Embeds the query and computes cosine similarity against stored nodes.
        Returns a list of matching nodes sorted by relevance.
        """
        if not self.store:
            return []
        
        try:
            query_vector = self.get_embedding(query)
        except Exception as e:
            logger.error("Search failed to embed query: %s", e)
            return []

        results = []
        for key, val in self.store.items():
            node_vector = val["vector"]
            dot_product = np.dot(query_vector, node_vector)
            norm_q = np.linalg.norm(query_vector)
            norm_n = np.linalg.norm(node_vector)
            if norm_q > 0 and norm_n > 0:
                sim = float(dot_product / (norm_q * norm_n))
            else:
                sim = 0.0
            results.append((sim, val["node"]))

        # Sort by similarity descending
        results.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in results[:top_k]]

    def retrieve_context(self, query: str, top_k: int = 8) -> tuple[list[dict], list[dict]]:
        """
        Given a query, retrieve the top_k most relevant nodes and their corresponding edges.
        Returns (nodes, edges).
        """
        matched_nodes = self.search(query, top_k=top_k)
        matched_names = {n["name"].lower() for n in matched_nodes}

        # Filter edges connecting these nodes
        matched_edges = []
        for edge in self.edges:
            src = edge.get("source", "").lower()
            tgt = edge.get("target", "").lower()
            if src in matched_names and tgt in matched_names:
                matched_edges.append(edge)

        return matched_nodes, matched_edges
