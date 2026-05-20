from __future__ import annotations
import hashlib
from pathlib import Path
from uuid import UUID
from sqlalchemy.orm import Session
from application.ingestion.chunk_text import chunk_to_embedding_text
from application.ingestion.path_utils import relative_to_repo, resolve_repo_path
from infrastructure.db.models.chunk_model import ChunkModel
from infrastructure.db.models.class_model import ClassModel
from infrastructure.db.models.file_model import FileModel
from infrastructure.db.models.function_calls_model import FunctionCallModel
from infrastructure.db.models.function_model import FunctionModel
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


def _file_hash(abs_path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(abs_path.read_bytes())
    return digest.hexdigest()


def _first_signature_line(code: str) -> str | None:
    for line in code.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:500]
    return None


def get_or_create_repository(
    session: Session,
    name: str,
    root_path: str | None = None,
    description: str | None = None,
) -> RepositoryModel:
    repo = session.query(RepositoryModel).filter_by(name=name).one_or_none()
    if repo is not None:
        if root_path and repo.root_path != root_path:
            repo.root_path = root_path
        if description is not None and repo.description != description:
            repo.description = description
        return repo

    repo = RepositoryModel(name=name, root_path=root_path, description=description)
    session.add(repo)
    session.flush()
    logger.info("persist: created repository name=%s id=%s", name, repo.id)
    return repo


def _replace_file_row(
    session: Session,
    repository_id: UUID,
    file_path: str,
    language: str | None,
    *,
    repo_root: str | None,
) -> FileModel:
    existing = (
        session.query(FileModel)
        .filter_by(repository_id=repository_id, file_path=file_path)
        .one_or_none()
    )
    if existing is not None:
        session.delete(existing)
        session.flush()
        logger.debug("persist: replaced existing file row path=%s", file_path)

    abs_path = resolve_repo_path(file_path, repo_root) if repo_root else Path(file_path)
    file_row = FileModel(
        repository_id=repository_id,
        file_path=file_path,
        language=language,
        file_hash=_file_hash(abs_path),
    )
    session.add(file_row)
    session.flush()
    return file_row


def _function_for_chunk(
    session: Session,
    file_row: FileModel,
    class_row: ClassModel | None,
    structure: dict,
    chunk: dict,
) -> FunctionModel:
    method_names = set(structure.get("methods") or [])
    class_id = None
    if class_row is not None and chunk["name"] in method_names:
        class_id = class_row.id

    fn = FunctionModel(
        file_id=file_row.id,
        class_id=class_id,
        name=chunk["name"],
        start_line=chunk.get("start_line"),
        end_line=chunk.get("end_line"),
        start_byte=chunk.get("start"),
        end_byte=chunk.get("end"),
        signature=_first_signature_line(chunk.get("code") or ""),
        docstring=None,
    )
    session.add(fn)
    session.flush()
    return fn


def _caller_for_call(
    functions: list[tuple[FunctionModel, dict]], call_start: int
) -> FunctionModel | None:
    for fn, chunk in functions:
        start = chunk.get("start")
        end = chunk.get("end")
        if start is not None and end is not None and start <= call_start < end:
            return fn
    return None


def _resolve_callee(
    callee_name: str,
    file_functions: dict[str, FunctionModel],
    repo_functions: dict[str, list[FunctionModel]],
) -> FunctionModel | None:
    if callee_name in file_functions:
        return file_functions[callee_name]
    candidates = repo_functions.get(callee_name) or []
    return candidates[0] if candidates else None


class _FileIndexState:
    __slots__ = ("file_functions", "fn_chunk_pairs", "calls")

    def __init__(
        self,
        file_functions: dict[str, FunctionModel],
        fn_chunk_pairs: list[tuple[FunctionModel, dict]],
        calls: list[dict],
    ) -> None:
        self.file_functions = file_functions
        self.fn_chunk_pairs = fn_chunk_pairs
        self.calls = calls


class IndexBatch:

    def __init__(self, repository: RepositoryModel) -> None:
        self.repository = repository
        self.pending: list[dict] = []
        self.repo_functions: dict[str, list[FunctionModel]] = {}
        self._file_states: list[_FileIndexState] = []
        self.files_indexed = 0
        self.functions_indexed = 0
        self.classes_indexed = 0
        self.calls_indexed = 0

    def _drop_file_from_function_index(self, session: Session, file_path: str) -> None:
        existing = (
            session.query(FileModel)
            .filter_by(repository_id=self.repository.id, file_path=file_path)
            .one_or_none()
        )
        if existing is None:
            return
        for fn in list(existing.functions):
            names = self.repo_functions.get(fn.name, [])
            names = [item for item in names if item.id != fn.id]
            if names:
                self.repo_functions[fn.name] = names
            else:
                self.repo_functions.pop(fn.name, None)

    def add_file(self, session: Session, file_result: dict) -> None:
        raw_path = file_result["file"]
        file_path = relative_to_repo(
            raw_path,
            self.repository.root_path or "",
            self.repository.name,
        )
        chunks = file_result.get("chunks") or []
        structure = file_result.get("structure") or {}
        calls = file_result.get("calls") or []

        self._drop_file_from_function_index(session, file_path)
        file_row = _replace_file_row(
            session,
            self.repository.id,
            file_path,
            file_result.get("language"),
            repo_root=self.repository.root_path,
        )
        self.files_indexed += 1

        class_row: ClassModel | None = None
        class_name = structure.get("class")
        if class_name:
            class_row = ClassModel(file_id=file_row.id, name=class_name)
            session.add(class_row)
            session.flush()
            self.classes_indexed += 1

        file_functions: dict[str, FunctionModel] = {}
        fn_chunk_pairs: list[tuple[FunctionModel, dict]] = []

        for chunk in chunks:
            fn = _function_for_chunk(session, file_row, class_row, structure, chunk)
            file_functions[fn.name] = fn
            self.repo_functions.setdefault(fn.name, []).append(fn)
            fn_chunk_pairs.append((fn, chunk))
            self.functions_indexed += 1

            self.pending.append(
                {
                    "repository_id": self.repository.id,
                    "file_id": file_row.id,
                    "function_id": fn.id,
                    "chunk": chunk,
                    "text": chunk_to_embedding_text(file_path, chunk),
                    "file_path": file_path,
                }
            )

        self._file_states.append(
            _FileIndexState(file_functions, fn_chunk_pairs, calls)
        )

    def record_all_calls(self, session: Session) -> None:
        for state in self._file_states:
            for call in state.calls:
                caller = _caller_for_call(state.fn_chunk_pairs, call["start"])
                callee = _resolve_callee(
                    call["callee_name"],
                    state.file_functions,
                    self.repo_functions,
                )
                if caller is None or callee is None or caller.id == callee.id:
                    continue
                session.add(
                    FunctionCallModel(
                        caller_function_id=caller.id,
                        callee_function_id=callee.id,
                        call_site_byte=call["start"],
                    )
                )
                self.calls_indexed += 1


def store_chunks_with_embeddings(
    session: Session,
    batch: IndexBatch,
    embedding_indices: list[int],
) -> int:
    if len(embedding_indices) != len(batch.pending):
        raise ValueError(
            f"embedding count {len(embedding_indices)} != pending chunks {len(batch.pending)}"
        )

    for item, embedding_index in zip(batch.pending, embedding_indices, strict=True):
        chunk = item["chunk"]
        session.add(
            ChunkModel(
                repository_id=item["repository_id"],
                file_id=item["file_id"],
                function_id=item["function_id"],
                embedding_index=embedding_index,
                content=chunk["code"],
                start_line=chunk.get("start_line"),
                end_line=chunk.get("end_line"),
                chunk_type="function",
                token_count=None,
            )
        )
        logger.debug(
            "persist: chunk function_id=%s faiss_index=%d file=%s",
            item["function_id"],
            embedding_index,
            item["file_path"],
        )

    return len(batch.pending)
