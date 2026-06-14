import pytest
from unittest.mock import MagicMock
from app import app
from routes.workspace import get_graph_extractor, get_doc_analyzer

@pytest.fixture
def client():
    app.config["TESTING"] = True
    # Disable rate limiting for testing routes easily
    app.config["RATELIMIT_ENABLED"] = False
    with app.test_client() as client:
        yield client

def test_home_and_workspace_routes(client):
    res = client.get("/workspace")
    assert res.status_code == 200
    assert b"Workspace" in res.data or b"workspace" in res.data

def test_analyze_validation(client):
    # Missing required 'text' field
    res = client.post("/api/analyze", json={})
    assert res.status_code == 422
    assert b"Validation failed" in res.data

    # Valid request but mocking extractors
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = {"nodes": [], "edges": []}
    
    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = []
    
    # Patch the lazy initialization getters
    import routes.workspace
    routes.workspace._graph_extractor = mock_extractor
    routes.workspace._doc_analyzer = mock_analyzer

    res_valid = client.post("/api/analyze", json={"text": "Hello world"})
    assert res_valid.status_code == 200
    data = res_valid.get_json()
    assert "graph" in data
    assert "highlights" in data

def test_chat_validation(client):
    # Missing required 'question' field
    res = client.post("/api/chat", json={})
    assert res.status_code == 422

    # Valid request
    res_valid = client.post("/api/chat", json={
        "question": "test question",
        "nodes": [],
        "edges": []
    })
    assert res_valid.status_code == 200
    data = res_valid.get_json()
    assert "answer" in data
    assert "related_nodes" in data

def test_search_validation(client):
    # Missing required 'query' field
    res = client.post("/api/search", json={})
    assert res.status_code == 422

    # Empty graph
    res_empty_graph = client.post("/api/search", json={
        "query": "query",
        "nodes": []
    })
    assert res_empty_graph.status_code == 200
    assert res_empty_graph.get_json()["reason"] == "Graph is empty."
