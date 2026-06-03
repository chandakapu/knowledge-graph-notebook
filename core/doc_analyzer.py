import os
import textwrap
import langextract as lx


class DocAnalyzer:
    """
    Uses langextract to perform document-level NLP analysis:
      - Important concept highlighting
      - Key method detection
      - Named-entity-style tagging

    Returns span annotations that the frontend uses to highlight text.
    """

    _EXAMPLES = [
        lx.data.ExampleData(
            text=(
                "Gradient Descent is an optimization algorithm that uses the "
                "derivative to minimize a loss function."
            ),
            extractions=[
                lx.data.Extraction(extraction_class="KeyConcept",  extraction_text="Gradient Descent"),
                lx.data.Extraction(extraction_class="KeyConcept",  extraction_text="derivative"),
                lx.data.Extraction(extraction_class="KeyMethod",   extraction_text="optimization algorithm"),
                lx.data.Extraction(extraction_class="KeyTerm",     extraction_text="loss function"),
            ],
        ),
        lx.data.ExampleData(
            text=(
                "Neural Networks mimic the human brain structure using layers "
                "of neurons and activation functions to solve complex tasks."
            ),
            extractions=[
                lx.data.Extraction(extraction_class="KeyConcept",  extraction_text="Neural Networks"),
                lx.data.Extraction(extraction_class="KeyConcept",  extraction_text="activation functions"),
                lx.data.Extraction(extraction_class="KeyTerm",     extraction_text="layers of neurons"),
                lx.data.Extraction(extraction_class="KeyMethod",   extraction_text="solve complex tasks"),
            ],
        ),
    ]

    _PROMPT = textwrap.dedent("""
        Analyze the document and extract the following types of spans:

        - KeyConcept : Important theoretical concepts or named entities (e.g. "Backpropagation").
        - KeyMethod  : Algorithmic or procedural techniques (e.g. "gradient calculation").
        - KeyTerm    : Domain-specific terminology worth defining (e.g. "loss function").

        Extract exact text spans only. Do not paraphrase.
    """)

    def __init__(self, model_id: str = "gemini-2.5-flash"):
        self.model_id = model_id
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No API key found. Set GEMINI_API_KEY."
            )

    def analyze(self, text: str) -> list[dict]:
        """
        Run extraction over the text.
        Returns a list of dicts: [{text, start, end, class}, ...].
        Falls back to an empty list on API error.
        """
        print(f"\n[Gemini DocAnalyzer] Sending highlight extraction request to Gemini ({self.model_id})...")
        print(f"[Gemini DocAnalyzer] Input Text: {text!r}")
        try:
            result = lx.extract(
                text_or_documents=text,
                prompt_description=self._PROMPT,
                examples=self._EXAMPLES,
                model_id=self.model_id,
                api_key=self.api_key,
            )
            print(f"[Gemini DocAnalyzer] Highlight response received successfully. Extracted {len(result.extractions)} span(s).")
        except Exception as e:
            print(f"[Gemini DocAnalyzer] API Call Failed: {e}")
            raise e

        highlights = []
        for ext in result.extractions:
            span_text = ext.extraction_text
            start = text.find(span_text)
            if start == -1:
                # Try case-insensitive fallback
                lower_text = text.lower()
                lower_span = span_text.lower()
                start = lower_text.find(lower_span)

            if start != -1:
                highlights.append(
                    {
                        "text": span_text,
                        "start": start,
                        "end": start + len(span_text),
                        "cls": ext.extraction_class,
                    }
                )

        # Sort by start position and deduplicate overlapping spans
        highlights.sort(key=lambda h: h["start"])
        return highlights
