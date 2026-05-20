from __future__ import annotations
from fastapi import APIRouter
from app.api.schemas.common import LanguagesResponse
from infrastructure.parser.language_specs import LANGUAGE_REGISTRY

router = APIRouter(prefix="/api/languages", tags=["languages"])

@router.get("/supported", response_model=LanguagesResponse)
def supported_languages() -> LanguagesResponse:
    languages = sorted(
        lang
        for lang, spec in LANGUAGE_REGISTRY.items()
        if spec.queries.get("functions")
    )
    return LanguagesResponse(
        languages=languages,
        note=(
            "Parsing uses Tree-sitter grammars. Only listed languages are processed; "
            "other files are skipped during ingestion."
        ),
    )
