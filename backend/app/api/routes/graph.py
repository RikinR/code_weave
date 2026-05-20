from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.common import ArchitectureGraph, HierarchyResponse, NodeDetailResponse
from application.graph.build_graph import build_architecture_graph, build_hierarchy
from application.graph.node_detail import get_node_detail

router = APIRouter(tags=["graph"])

@router.get("/api/repositories/{repository_id}/hierarchy", response_model=HierarchyResponse)
def repository_hierarchy(
    repository_id: UUID,
    db: Session = Depends(get_db),
) -> HierarchyResponse:
    data = build_hierarchy(db, repository_id)
    if not data.get("root_id"):
        raise HTTPException(status_code=404, detail="Repository not found")
    return HierarchyResponse(**data)


@router.get("/api/repositories/{repository_id}/graph", response_model=ArchitectureGraph)
def repository_graph(
    repository_id: UUID,
    db: Session = Depends(get_db),
) -> ArchitectureGraph:
    data = build_architecture_graph(db, repository_id)
    if not data.get("root_id"):
        raise HTTPException(status_code=404, detail="Repository not found")
    return ArchitectureGraph(**data)


@router.get("/api/nodes/{node_id:path}", response_model=NodeDetailResponse)
def node_detail(
    node_id: str,
    db: Session = Depends(get_db),
) -> NodeDetailResponse:
    detail = get_node_detail(db, node_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return NodeDetailResponse(**detail)
