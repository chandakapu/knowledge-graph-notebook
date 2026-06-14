import os
import pytest
from unittest.mock import MagicMock

# Ensure GEMINI_API_KEY is present for all tests
os.environ["GEMINI_API_KEY"] = "fake-gemini-api-key"

@pytest.fixture
def sample_nodes():
    return [
        {
            "name": "Artificial Intelligence",
            "type": "Concept",
            "description": "The simulation of human intelligence processes by machines, especially computer systems."
        },
        {
            "name": "Gradient Descent",
            "type": "Algorithm",
            "description": "An optimization algorithm used to minimize some function by iteratively moving in the direction of steepest descent."
        }
    ]

@pytest.fixture
def sample_edges():
    return [
        {
            "source": "Gradient Descent",
            "target": "Artificial Intelligence",
            "relation": "USES",
            "confidence": 0.9
        }
    ]

@pytest.fixture
def mock_genai_client(mocker):
    mock_client = MagicMock()
    # Patch the Client constructor in both modules that import it
    mocker.patch("core.graph_extractor.genai.Client", return_value=mock_client)
    mocker.patch("core.embedding_store.genai.Client", return_value=mock_client)
    return mock_client
