from pydantic import BaseModel, Field

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2_000)
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1_000)
    nodes: list[dict] = Field(default_factory=list)

class ExportPdfRequest(BaseModel):
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    documents: list[dict] = Field(default_factory=list)
