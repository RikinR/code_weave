from __future__ import annotations
from pathlib import Path
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from application.graph.build_graph import NODE_CLASS,NODE_FILE,NODE_FOLDER,NODE_FUNCTION,NODE_METHOD,node_id
from application.ingestion.lookup import get_chunk_by_embedding_index
from infrastructure.db.models.chunk_model import ChunkModel
from infrastructure.db.models.class_model import ClassModel
from infrastructure.db.models.file_model import FileModel
from infrastructure.db.models.function_calls_model import FunctionCallModel
from infrastructure.db.models.function_model import FunctionModel
from infrastructure.db.models.repository_model import RepositoryModel
from application.ingestion.path_utils import relative_to_repo, resolve_repo_path
from infrastructure.file.reader import read_file
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

def parse_node_id(raw: str) -> tuple[str, str] | None:
    if ":" not in raw:
        return None
    node_type, _, entity_key = raw.partition(":")
    if not node_type or not entity_key:
        return None
    return node_type, entity_key

def _display_path(stored_path: str | None, repo: RepositoryModel | None) -> str | None:
    if not stored_path:
        return stored_path
    if repo is None or not repo.root_path:
        return stored_path.replace("\\", "/")
    return relative_to_repo(stored_path, repo.root_path, repo.name)

def get_node_detail(session: Session, raw_node_id: str) -> dict | None:
    parsed = parse_node_id(raw_node_id)
    if parsed is None:
        return None
    node_type, entity_key = parsed

    if node_type == NODE_FILE:
        try:
            return _file_detail(session, UUID(entity_key))
        except ValueError:
            return None
    if node_type == NODE_CLASS:
        try:
            return _class_detail(session, UUID(entity_key))
        except ValueError:
            return None
    if node_type in (NODE_FUNCTION, NODE_METHOD):
        try:
            return _function_detail(session, UUID(entity_key), node_type)
        except ValueError:
            return None
    if node_type == "repository":
        try:
            return _repository_detail(session, UUID(entity_key))
        except ValueError:
            return None
    if node_type == NODE_FOLDER:
        return _folder_detail(session, entity_key)
    return None

def _folder_detail(session: Session, folder_key: str) -> dict | None:
    if "|" not in folder_key:
        return None
    repo_id_str, path_key = folder_key.split("|", 1)
    try:
        repo_uuid = UUID(repo_id_str)
    except ValueError:
        return None
    repo = session.get(RepositoryModel, repo_uuid)
    if repo is None:
        return None
    display_path = path_key or repo.name
    return {
        "id": node_id(NODE_FOLDER, folder_key),
        "type": NODE_FOLDER,
        "name": display_path.split("/")[-1] if path_key else repo.name,
        "file_path": display_path,
        "explanation": f"Folder {display_path} in repository {repo.name}.",
        "code": None,
        "start_line": None,
        "end_line": None,
        "incoming_calls": [],
        "outgoing_calls": [],
        "related_chunks": [],
        "relationships": [],
    }

def _repository_detail(session: Session, repository_id: UUID) -> dict | None:
    repo = session.get(RepositoryModel, repository_id)
    if repo is None:
        return None
    return {
        "id": node_id("repository", repo.id),
        "type": "repository",
        "name": repo.name,
        "file_path": repo.name,
        "explanation": f"Indexed repository {repo.name}.",
        "code": None,
        "start_line": None,
        "end_line": None,
        "incoming_calls": [],
        "outgoing_calls": [],
        "related_chunks": [],
        "relationships": [],
    }

def _file_detail(session: Session, file_id: UUID) -> dict | None:
    file_row = (
        session.query(FileModel)
        .options(joinedload(FileModel.repository))
        .filter_by(id=file_id)
        .one_or_none()
    )
    if file_row is None:
        return None
    repo = file_row.repository
    repo_root = repo.root_path
    display_path = _display_path(file_row.file_path, repo) or ""
    code = _safe_read(file_row.file_path, repo_root)
    return {
        "id": node_id(NODE_FILE, file_row.id),
        "type": NODE_FILE,
        "name": display_path.split("/")[-1],
        "file_path": display_path,
        "language": file_row.language,
        "explanation": f"Source file ({file_row.language or 'unknown'}).",
        "code": code,
        "start_line": 1,
        "end_line": len(code.splitlines()) if code else 0,
        "incoming_calls": [],
        "outgoing_calls": [],
        "related_chunks": [],
        "relationships": [{"kind": "contains", "target_type": "class/function"}],
    }

def _class_detail(session: Session, class_id: UUID) -> dict | None:
    cls = (
        session.query(ClassModel)
        .options(joinedload(ClassModel.file).joinedload(FileModel.repository))
        .filter_by(id=class_id)
        .one_or_none()
    )
    if cls is None:
        return None
    repo = cls.file.repository
    display_path = _display_path(cls.file.file_path, repo) or ""
    return {
        "id": node_id(NODE_CLASS, cls.id),
        "type": NODE_CLASS,
        "name": cls.name,
        "file_path": display_path,
        "language": cls.file.language,
        "explanation": f"Class {cls.name} defined in {display_path}.",
        "code": None,
        "start_line": None,
        "end_line": None,
        "incoming_calls": [],
        "outgoing_calls": [],
        "related_chunks": [],
        "relationships": [],
    }

def _function_detail(session: Session, function_id: UUID, node_type: str) -> dict | None:
    fn = (
        session.query(FunctionModel)
        .options(
            joinedload(FunctionModel.file).joinedload(FileModel.repository),
            joinedload(FunctionModel.class_),
            joinedload(FunctionModel.chunks),
        )
        .filter_by(id=function_id)
        .one_or_none()
    )
    if fn is None:
        return None

    repo = fn.file.repository
    repo_root = repo.root_path if repo else None
    display_path = _display_path(fn.file.file_path, repo) or ""

    chunk = fn.chunks[0] if fn.chunks else None
    code = chunk.content if chunk else _extract_from_file(fn, repo_root)
    incoming = _call_refs(session, fn, repo=repo, incoming=True)
    outgoing = _call_refs(session, fn, repo=repo, incoming=False)
    related = []
    if chunk and chunk.embedding_index is not None:
        ctx = get_chunk_by_embedding_index(
            session, fn.file.repository_id, chunk.embedding_index
        )
        if ctx:
            ctx = dict(ctx)
            ctx["file_path"] = _display_path(ctx.get("file_path"), repo)
            related.append(ctx)

    return {
        "id": node_id(node_type, fn.id),
        "type": node_type,
        "name": fn.name,
        "file_path": display_path,
        "language": fn.file.language,
        "class_name": fn.class_.name if fn.class_ else None,
        "explanation": (
            f"{'Method' if node_type == NODE_METHOD else 'Function'} {fn.name} "
            f"in {display_path}."
        ),
        "code": code,
        "start_line": fn.start_line,
        "end_line": fn.end_line,
        "signature": fn.signature,
        "incoming_calls": incoming,
        "outgoing_calls": outgoing,
        "related_chunks": related,
        "relationships": [
            {"kind": "incoming", "count": len(incoming)},
            {"kind": "outgoing", "count": len(outgoing)},
        ],
        "function_id": str(fn.id),
        "file_id": str(fn.file_id),
    }

def _call_refs(
    session: Session,
    fn: FunctionModel,
    *,
    repo: RepositoryModel | None,
    incoming: bool,
) -> list[dict]:
    load = joinedload(FunctionModel.file).joinedload(FileModel.repository)
    if incoming:
        rows = (
            session.query(FunctionCallModel)
            .options(joinedload(FunctionCallModel.caller).options(load))
            .filter_by(callee_function_id=fn.id)
            .all()
        )
        targets = [r.caller for r in rows]
    else:
        rows = (
            session.query(FunctionCallModel)
            .options(joinedload(FunctionCallModel.callee).options(load))
            .filter_by(caller_function_id=fn.id)
            .all()
        )
        targets = [r.callee for r in rows]

    refs: list[dict] = []
    for other in targets:
        otype = NODE_METHOD if other.class_id else NODE_FUNCTION
        stored = other.file.file_path if other.file else None
        refs.append(
            {
                "node_id": node_id(otype, other.id),
                "name": other.name,
                "file_path": _display_path(stored, repo),
            }
        )
    return refs

def _extract_from_file(fn: FunctionModel, repo_root: str | None) -> str | None:
    text = _safe_read(fn.file.file_path, repo_root)
    if not text or fn.start_line is None or fn.end_line is None:
        return text
    lines = text.splitlines()
    start = max(0, fn.start_line - 1)
    end = min(len(lines), fn.end_line)
    return "\n".join(lines[start:end])

def _safe_read(file_path: str, repo_root: str | None) -> str | None:
    try:
        abs_path = resolve_repo_path(file_path, repo_root) if repo_root else Path(file_path)
        data = read_file(str(abs_path))
        return data.decode("utf-8", errors="replace")
    except Exception:
        logger.warning("node_detail: could not read %s", file_path)
        return None