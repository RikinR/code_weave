from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.common import RepositorySummary
from application.repos.repository_service import delete_repository,get_repository_summary,list_repositories

router = APIRouter(prefix="/api/repositories", tags=["repositories"])

@router.get("", response_model=list[RepositorySummary])
def get_repositories(db: Session = Depends(get_db)) -> list[RepositorySummary]:
    return [RepositorySummary(**item) for item in list_repositories(db)]

@router.get("/{repository_id}", response_model=RepositorySummary)
def get_repository(
    repository_id: UUID,
    db: Session = Depends(get_db),
) -> RepositorySummary:
    try:
        return RepositorySummary(**get_repository_summary(db, repository_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.delete("/{repository_id}")
def remove_repository(
    repository_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    result = delete_repository(db, repository_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"deleted": True, **result}
