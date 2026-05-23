from __future__ import annotations
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = "ok"

class RepositorySummary(BaseModel):
    id: str
    name: str
    root_path: str | None = None
    description: str | None = None
    created_at: str | None = None
    file_count: int = 0
    function_count: int = 0
    chunk_count: int = 0

class StageSchema(BaseModel):
    key: str
    label: str
    status: str
    progress: float
    logs: list[str] = Field(default_factory=list)

class JobSnapshot(BaseModel):
    job_id: str
    repository_name: str
    status: str
    repository_id: str | None = None
    error: str | None = None
    created_at: float
    stages: list[StageSchema]

class UploadResponse(BaseModel):
    job_id: str
    repository_name: str

class GraphNode(BaseModel):
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
    id: str
    source: str
    target: str
    kind: str

class ArchitectureGraph(BaseModel):
    root_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]

class HierarchyResponse(BaseModel):
    root_id: str
    nodes: list[GraphNode]

class NodeDetailResponse(BaseModel):
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
    incoming_calls: list[dict] = Field(default_factory=list)
    outgoing_calls: list[dict] = Field(default_factory=list)
    related_chunks: list[dict] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)
    function_id: str | None = None
    file_id: str | None = None

class LanguagesResponse(BaseModel):
    languages: list[str]
    note: str

class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    beginner_mode: bool = False

class ChatCitation(BaseModel):
    chunk_id: str | None = None
    file_path: str | None = None
    function_name: str | None = None
    function_id: str | None = None
    node_id: str | None = None
    score: float | None = None

class ChatCompleteEvent(BaseModel):
    answer: str
    citations: list[ChatCitation]
    highlight_node_ids: list[str]

class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict] = Field(default_factory=list)
    created_at: str | None = None
