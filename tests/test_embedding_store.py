import pytest
import numpy as np
from unittest.mock import MagicMock
from core.embedding_store import EmbeddingStore

def test_clear():
    store = EmbeddingStore()
    store.store = {"test": {"node": {}, "vector": np.array([1, 2, 3])}}
    store.edges = [{"source": "A", "target": "B"}]
    store.clear()
    assert store.store == {}
    assert store.edges == []

def test_embed_nodes_and_deduplication(mock_genai_client):
    # Setup mock embedding return
    mock_res = MagicMock()
    mock_val = MagicMock()
    mock_val.values = [1.0, 0.0, 0.0]
    mock_res.embeddings = [mock_val]
    mock_genai_client.models.embed_content.return_value = mock_res

    store = EmbeddingStore()
    nodes = [
        {"name": "ConceptA", "type": "Concept", "description": "Desc A"},
        {"name": "ConceptB", "type": "Concept", "description": "Desc B"}
    ]
    edges = [{"source": "ConceptA", "target": "ConceptB", "relation": "RELATED_TO"}]
    
    # 1. First embed
    store.embed_nodes(nodes, edges)
    assert len(store.store) == 2
    assert "concepta" in store.store
    assert "conceptb" in store.store
    assert store.edges == edges
    
    # Check that embed_content was called twice
    assert mock_genai_client.models.embed_content.call_count == 2
    
    # Reset call count
    mock_genai_client.models.embed_content.reset_mock()
    
    # 2. Re-embed identical nodes (should skip embed_content API calls)
    store.embed_nodes(nodes, edges)
    assert mock_genai_client.models.embed_content.call_count == 0

    # 3. Modify one node description (should trigger API call for updated node)
    nodes_modified = [
        {"name": "ConceptA", "type": "Concept", "description": "Modified Desc A"},
        {"name": "ConceptB", "type": "Concept", "description": "Desc B"}
    ]
    store.embed_nodes(nodes_modified, edges)
    assert mock_genai_client.models.embed_content.call_count == 1

def test_search_similarity_ranking(mock_genai_client):
    # Setup mock to return specific vectors based on contents
    def embed_side_effect(model, contents):
        mock_res = MagicMock()
        mock_val = MagicMock()
        # If content contains Query, return query vector
        if "Query" in contents:
            mock_val.values = [1.0, 0.0, 0.0]
        # Node A is identical to Query
        elif "NodeA" in contents:
            mock_val.values = [1.0, 0.0, 0.0]
        # Node B is orthogonal
        elif "NodeB" in contents:
            mock_val.values = [0.0, 1.0, 0.0]
        else:
            mock_val.values = [0.0, 0.0, 1.0]
        mock_res.embeddings = [mock_val]
        return mock_res

    mock_genai_client.models.embed_content.side_effect = embed_side_effect

    store = EmbeddingStore()
    nodes = [
        {"name": "NodeA", "type": "Concept", "description": "Node A description"},
        {"name": "NodeB", "type": "Concept", "description": "Node B description"}
    ]
    store.embed_nodes(nodes)

    # Search with "Query"
    results = store.search("Query", top_k=2)
    assert len(results) == 2
    # NodeA should be first because it is identical to Query (sim=1.0 vs sim=0.0)
    assert results[0]["name"] == "NodeA"
    assert results[1]["name"] == "NodeB"

def test_retrieve_context(mock_genai_client):
    # Setup mock embedding
    mock_res = MagicMock()
    mock_val = MagicMock()
    mock_val.values = [0.5, 0.5, 0.5]
    mock_res.embeddings = [mock_val]
    mock_genai_client.models.embed_content.return_value = mock_res

    store = EmbeddingStore()
    nodes = [
        {"name": "A", "type": "Concept", "description": "Node A"},
        {"name": "B", "type": "Concept", "description": "Node B"},
        {"name": "C", "type": "Concept", "description": "Node C"}
    ]
    edges = [
        {"source": "A", "target": "B", "relation": "RELATED_TO"},
        {"source": "B", "target": "C", "relation": "RELATED_TO"},
        {"source": "A", "target": "C", "relation": "RELATED_TO"}
    ]
    store.embed_nodes(nodes, edges)

    # Retrieve top 2 nodes (should return A and B or A and C depending on similarity,
    # but since all embeddings are identical, it returns the first two it finds or all of them.
    # We specify top_k=2)
    matched_nodes, matched_edges = store.retrieve_context("query", top_k=2)
    
    assert len(matched_nodes) == 2
    matched_names = {n["name"].lower() for n in matched_nodes}
    
    # Verify that returned edges only connect the matched nodes
    for edge in matched_edges:
        assert edge["source"].lower() in matched_names
        assert edge["target"].lower() in matched_names
