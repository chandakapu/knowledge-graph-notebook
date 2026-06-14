import os
import pytest
from unittest.mock import MagicMock
from concurrent.futures import TimeoutError as FuturesTimeoutError
from core.graph_extractor import GraphExtractor, KnowledgeGraph, Node, Edge

def test_missing_api_key(mocker):
    # Remove key temporarily to verify ValueError
    mocker.patch.dict(os.environ, {}, clear=True)
    with pytest.raises(ValueError, match="GEMINI_API_KEY environment variable not set"):
        GraphExtractor()

def test_extract_success_parsed(mock_genai_client):
    # Setup mock return value with parsed Pydantic KnowledgeGraph
    mock_kg = KnowledgeGraph(
        nodes=[Node(name="Gradient Descent", type="Algorithm", description="An optimization algorithm")],
        edges=[Edge(source="Gradient Descent", target="Loss Function", relation="MINIMIZES", confidence=0.9)]
    )
    mock_response = MagicMock()
    mock_response.parsed = mock_kg
    mock_genai_client.models.generate_content.return_value = mock_response

    extractor = GraphExtractor()
    result = extractor.extract("some text")

    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["name"] == "Gradient Descent"
    assert result["nodes"][0]["type"] == "Algorithm"
    assert len(result["edges"]) == 1
    assert result["edges"][0]["relation"] == "MINIMIZES"

def test_extract_fallback_raw_json(mock_genai_client):
    # Setup response with parsed=None but valid JSON text
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = """
    ```json
    {
        "nodes": [{"name": "SGD", "type": "Algorithm", "description": "Stochastic GD"}],
        "edges": [{"source": "SGD", "target": "Loss", "relation": "MINIMIZES", "confidence": 0.85}]
    }
    ```
    """
    mock_genai_client.models.generate_content.return_value = mock_response

    extractor = GraphExtractor()
    result = extractor.extract("some text")

    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["name"] == "SGD"
    assert len(result["edges"]) == 1
    assert result["edges"][0]["relation"] == "MINIMIZES"
    assert result["edges"][0]["confidence"] == 0.85

def test_extract_fallback_invalid_json(mock_genai_client):
    # Setup response with parsed=None and invalid JSON text
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = "invalid json response"
    mock_genai_client.models.generate_content.return_value = mock_response

    extractor = GraphExtractor()
    with pytest.raises(ValueError, match="Failed to parse model response"):
        extractor.extract("some text")

def test_extract_api_timeout(mock_genai_client, mocker):
    # Mock future.result to raise FuturesTimeoutError
    mock_future = MagicMock()
    mock_future.result.side_effect = FuturesTimeoutError()
    
    # We patch ThreadPoolExecutor.submit to return our mock future
    mocker.patch("concurrent.futures.ThreadPoolExecutor.submit", return_value=mock_future)

    extractor = GraphExtractor()
    with pytest.raises(TimeoutError, match="Gemini API call timed out"):
        extractor.extract("some text")
