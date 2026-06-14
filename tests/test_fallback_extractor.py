import pytest
from core.fallback_extractor import dynamic_fallback_extract, TECH_TERMS_DICT

def test_empty_or_whitespace_input():
    # Verify that passing an empty string or spaces is handled gracefully
    res = dynamic_fallback_extract("")
    assert res["graph"]["nodes"] == []
    assert res["graph"]["edges"] == []
    assert res["highlights"] == []

    res_spaces = dynamic_fallback_extract("   \n   ")
    assert res_spaces["graph"]["nodes"] == []
    assert res_spaces["graph"]["edges"] == []
    assert res_spaces["highlights"] == []

def test_technical_terms_classification():
    # Verify that a known tech term is classified correctly according to TECH_TERMS_DICT
    text = "Artificial Intelligence is a broad field. Machine learning is a subset of it."
    res = dynamic_fallback_extract(text)
    
    # Check nodes
    nodes = res["graph"]["nodes"]
    node_names = [n["name"] for n in nodes]
    assert "Artificial Intelligence" in node_names
    assert "Machine Learning" in node_names
    
    # Verify exact types from TECH_TERMS_DICT
    ai_node = next(n for n in nodes if n["name"] == "Artificial Intelligence")
    assert ai_node["type"] == TECH_TERMS_DICT["artificial intelligence"][0]
    assert ai_node["description"] == TECH_TERMS_DICT["artificial intelligence"][1]

def test_relationship_rules():
    # Test relationship extraction rules
    # E.g. "Neural network is a computational model."
    # "is" and "a" are in STOPWORDS, separating the terms.
    # The rule matched "is a" from RELATION_RULES.
    text = "Neural network is a computational model."
    res = dynamic_fallback_extract(text)
    
    edges = res["graph"]["edges"]
    assert len(edges) >= 1
    
    # Check if we have an edge with relation SUBSET_OF
    sub_edge = next((e for e in edges if e["relation"] == "SUBSET_OF"), None)
    assert sub_edge is not None
    assert sub_edge["source"].lower() == "neural network"
    assert sub_edge["target"].lower() == "computational model"
    assert sub_edge["confidence"] == 0.8

def test_sliding_window_and_common_verbs():
    # Test relationship fallback to common verbs
    text = "Alice chased Bob."
    res = dynamic_fallback_extract(text)
    
    edges = res["graph"]["edges"]
    assert len(edges) >= 1
    chased_edge = next((e for e in edges if e["relation"] == "CHASED"), None)
    assert chased_edge is not None
    assert chased_edge["source"].lower() == "alice"
    assert chased_edge["target"].lower() == "bob"

def test_highlights():
    # Test highlights detection and ordering
    text = "Neural network is a computational model."
    res = dynamic_fallback_extract(text)
    
    highlights = res["highlights"]
    assert len(highlights) >= 2
    
    # Check ordering is by start index
    starts = [h["start"] for h in highlights]
    assert starts == sorted(starts)
    
    # Verify highlights class mapping
    nn_highlight = next(h for h in highlights if h["text"].lower() == "neural network")
    # type for neural network is Algorithm, which maps to KeyMethod class
    assert nn_highlight["cls"] == "KeyMethod"
