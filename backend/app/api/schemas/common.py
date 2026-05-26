from __future__ import annotations

"""Pydantic response and request models for the public REST API.

Defines JSON shapes returned to the Flutter client for repositories, ingestion jobs,
architecture graphs, node detail, languages, and RAG chat. Keeps HTTP contracts
separate from SQLAlchemy models in ``infrastructure.db``.
"""
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """Simple health-check payload for ``GET /api/health``."""
    status: str = 'ok'

class RepositorySummary(BaseModel):
    """Indexed repository metadata and aggregate counts shown on the home screen."""
    id: str
    name: str
    root_path: str | None = None
    description: str | None = None
    created_at: str | None = None
    file_count: int = 0
    function_count: int = 0
    chunk_count: int = 0

class StageSchema(BaseModel):
    """One pipeline stage (parse, chunk, embed, etc.) within a job snapshot."""
    key: str
    label: str
    status: str
    progress: float
    logs: list[str] = Field(default_factory=list)

class JobSnapshot(BaseModel):
    """Full ingestion job state streamed to the pipeline UI via polling or SSE."""
    job_id: str
    repository_name: str
    status: str
    repository_id: str | None = None
    error: str | None = None
    created_at: float
    stages: list[StageSchema]

class UploadResponse(BaseModel):
    """Acknowledgement after accepting a ZIP upload and starting background ingestion."""
    job_id: str
    repository_name: str

class GraphNode(BaseModel):
    """Node in the architecture or hierarchy graph (file, class, function, folder)."""
    id: str
    type: str
    name: str
    parent_id: str | None = None
    children: list[str] = Field(default_factory=list)
    file_path: str | None = None
    language: str | None = None
    function_id: str | None = None
    start_line: int | None = None
    end_line: int | None = None

class GraphEdge(BaseModel):
    """Directed relationship between graph nodes (e.g. call or containment)."""
    id: str
    source: str
    target: str
    kind: str

class ArchitectureGraph(BaseModel):
    """Call-aware graph rendered on the explorer canvas."""
    root_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]

class HierarchyResponse(BaseModel):
    """Folder/file tree without call edges, used for tree navigation."""
    root_id: str
    nodes: list[GraphNode]

class AstTreeNodeSchema(BaseModel):
    """Recursive Tree-sitter AST node for the AST panel in the explorer."""
    type: str
    start_line: int | None = None
    end_line: int | None = None
    children: list['AstTreeNodeSchema'] = Field(default_factory=list)

class AstTreePayloadSchema(BaseModel):
    """AST subtree with truncation metadata when the source tree is large."""
    root: AstTreeNodeSchema | dict | None = None
    truncated: bool = False
    node_count: int = 0

class NodeDetailResponse(BaseModel):
    """Rich detail for a selected graph node: code, calls, chunks, and AST preview."""
    id: str
    type: str
    name: str
    file_path: str | None = None
    language: str | None = None
    class_name: str | None = None
    description: str | None = None
    explanation: str | None = None
    code: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    signature: str | None = None
    indexing_mode: str | None = None
    indexing_notice: str | None = None
    ast_tree: dict | None = None
    incoming_calls: list[dict] = Field(default_factory=list)
    outgoing_calls: list[dict] = Field(default_factory=list)
    related_chunks: list[dict] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)
    function_id: str | None = None
    file_id: str | None = None

AstTreeNodeSchema.model_rebuild()

class LanguagesResponse(BaseModel):
    """Languages the ingestion pipeline can parse with Tree-sitter."""
    languages: list[str]
    note: str

class ChatRequest(BaseModel):
    """User question and retrieval options for repository-scoped RAG chat."""
    query: str
    top_k: int = 5
    beginner_mode: bool = False

class ChatCitation(BaseModel):
    """Source chunk linked to an assistant answer for highlighting in the graph."""
    chunk_id: str | None = None
    file_path: str | None = None
    function_name: str | None = None
    function_id: str | None = None
    node_id: str | None = None
    score: float | None = None
    chunk_type: str | None = None
    chunk_strategy: str | None = None

class ChatCompleteEvent(BaseModel):
    """Non-streaming chat completion payload (answer, citations, graph highlights)."""
    answer: str
    citations: list[ChatCitation]
    highlight_node_ids: list[str]

class ChatMessageResponse(BaseModel):
    """Persisted chat message row returned by the message history endpoint."""
    id: str
    role: str
    content: str
    citations: list[dict] = Field(default_factory=list)
    created_at: str | None = None
