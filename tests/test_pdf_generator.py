import pytest
import io
from core.pdf_generator import generate_summary_pdf, _esc

def test_esc_helper():
    # Verify unicode replacements and html escaping
    assert _esc("\u2019") == "&#x27;"
    assert _esc("\u201cHello\u201d") == '&quot;Hello&quot;'
    assert _esc("A & B") == "A &amp; B"
    assert _esc(None) == ""

def test_generate_summary_pdf_with_data():
    nodes = [
        {"name": "Concept A", "type": "Concept", "description": "This is concept A."},
        {"name": "Algorithm B", "type": "Algorithm", "description": "This is algorithm B."}
    ]
    edges = [
        {"source": "Concept A", "target": "Algorithm B", "relation": "USES", "confidence": 0.85}
    ]
    documents = [
        {"filename": "doc1.pdf", "timestamp": "2026-06-14 12:00:00", "size": "15 KB"}
    ]

    pdf_buffer = generate_summary_pdf(nodes, edges, documents)
    assert isinstance(pdf_buffer, io.BytesIO)
    pdf_bytes = pdf_buffer.getvalue()
    
    # Check PDF Magic Bytes at the start
    assert pdf_bytes.startswith(b"%PDF")
    # Check that PDF contains some expected structures
    assert len(pdf_bytes) > 1000

def test_generate_summary_pdf_empty_inputs():
    pdf_buffer = generate_summary_pdf([], [], [])
    assert isinstance(pdf_buffer, io.BytesIO)
    pdf_bytes = pdf_buffer.getvalue()
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500
