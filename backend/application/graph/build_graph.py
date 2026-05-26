"""Build explorer graph structures from persisted repository metadata.

``build_hierarchy`` assembles folder/file/class/function tree nodes;
``build_architecture_graph`` adds ``calls`` edges from
:class:`infrastructure.db.models.function_calls_model.FunctionCallModel`.
Consumed by graph API routes and cited from RAG via :func:`node_id`.
"""

from __future__ import annotations
from collections import defaultdict
from pathlib import Path, PurePosixPath
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from infrastructure.db.models.class_model import ClassModel
from infrastructure.db.models.file_model import FileModel
from infrastructure.db.models.function_calls_model import FunctionCallModel
from infrastructure.db.models.function_model import FunctionModel
from application.ingestion.path_utils import relative_to_repo
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)
NODE_REPOSITORY = 'repository'
NODE_FOLDER = 'folder'
NODE_FILE = 'file'
NODE_CLASS = 'class'
NODE_FUNCTION = 'function'
NODE_METHOD = 'method'

def node_id(node_type: str, entity_id: UUID | str) -> str:
    """Return the canonical explorer node id (``type:uuid``) used across graph and RAG."""
    return f'{node_type}:{entity_id}'

def _repo_relative_path(file_path: str, repo: RepositoryModel) -> str:
    if not repo.root_path:
        return file_path.replace('\\', '/')
    return relative_to_repo(file_path, repo.root_path, repo.name)

def _folder_path_parts(relative_file_path: str) -> list[str]:
    parent = PurePosixPath(relative_file_path).parent
    if str(parent) in ('.', ''):
        return []
    return list(parent.parts)

def build_hierarchy(session: Session, repository_id: UUID) -> dict:
    """Build folder/file/class/function tree nodes for one repository."""
    repo = session.get(RepositoryModel, repository_id)
    if repo is None:
        return {'root': None, 'nodes': []}
    files = session.query(FileModel).filter_by(repository_id=repository_id).options(joinedload(FileModel.classes), joinedload(FileModel.functions).joinedload(FunctionModel.class_)).all()
    folder_nodes: dict[str, dict] = {}
    nodes: list[dict] = []
    root_id = node_id(NODE_REPOSITORY, repo.id)
    nodes.append({'id': root_id, 'type': NODE_REPOSITORY, 'name': repo.name, 'parent_id': None, 'children': []})
    folder_children: dict[str, list[str]] = defaultdict(list)

    def ensure_folder(parts: list[str]) -> str:
        path_key = '/'.join(parts) if parts else ''
        if path_key in folder_nodes:
            return folder_nodes[path_key]['id']
        fid = node_id(NODE_FOLDER, f'{repo.id}|{path_key}')
        parent_id = root_id
        if parts:
            parent_id = ensure_folder(parts[:-1])
        folder_nodes[path_key] = {'id': fid, 'type': NODE_FOLDER, 'name': parts[-1] if parts else repo.name, 'parent_id': parent_id, 'path': path_key, 'children': []}
        folder_children[parent_id].append(fid)
        return fid
    for file_row in files:
        rel_path = _repo_relative_path(file_row.file_path, repo)
        parts = _folder_path_parts(rel_path)
        parent_id = ensure_folder(parts) if parts else root_id
        file_nid = node_id(NODE_FILE, file_row.id)
        file_name = PurePosixPath(rel_path).name
        file_node = {'id': file_nid, 'type': NODE_FILE, 'name': file_name, 'parent_id': parent_id, 'file_path': rel_path, 'language': file_row.language, 'children': []}
        nodes.append(file_node)
        folder_children[parent_id].append(file_nid)
        class_by_id: dict[UUID, dict] = {}
        for cls in file_row.classes:
            cid = node_id(NODE_CLASS, cls.id)
            class_node = {'id': cid, 'type': NODE_CLASS, 'name': cls.name, 'parent_id': file_nid, 'children': []}
            nodes.append(class_node)
            class_by_id[cls.id] = class_node
            file_node['children'].append(cid)
        for fn in file_row.functions:
            is_method = fn.class_id is not None
            ntype = NODE_METHOD if is_method else NODE_FUNCTION
            fid = node_id(ntype, fn.id)
            parent = class_by_id[fn.class_id]['id'] if fn.class_id in class_by_id else file_nid
            fn_node = {'id': fid, 'type': ntype, 'name': fn.name, 'parent_id': parent, 'function_id': str(fn.id), 'start_line': fn.start_line, 'end_line': fn.end_line, 'children': []}
            nodes.append(fn_node)
            if parent == file_nid:
                file_node['children'].append(fid)
            else:
                class_by_id[fn.class_id]['children'].append(fid)
    for path_key, folder in folder_nodes.items():
        nodes.append(folder)
    for node in nodes:
        nid = node['id']
        node['children'] = folder_children.get(nid, node.get('children', []))
    return {'root_id': root_id, 'nodes': nodes}

def build_architecture_graph(session: Session, repository_id: UUID) -> dict:
    """Build hierarchy nodes plus ``contains`` and ``calls`` edges for the graph canvas."""
    hierarchy = build_hierarchy(session, repository_id)
    nodes = hierarchy['nodes']
    edges: list[dict] = []
    for node in nodes:
        parent_id = node.get('parent_id')
        if parent_id:
            edges.append({'id': f"edge:{parent_id}->{node['id']}", 'source': parent_id, 'target': node['id'], 'kind': 'contains'})
    calls = session.query(FunctionCallModel).join(FunctionModel, FunctionCallModel.caller_function_id == FunctionModel.id).join(FileModel, FunctionModel.file_id == FileModel.id).filter(FileModel.repository_id == repository_id).options(joinedload(FunctionCallModel.caller).joinedload(FunctionModel.file), joinedload(FunctionCallModel.callee).joinedload(FunctionModel.file)).all()
    for call in calls:
        caller = call.caller
        callee = call.callee
        caller_type = NODE_METHOD if caller.class_id else NODE_FUNCTION
        callee_type = NODE_METHOD if callee.class_id else NODE_FUNCTION
        source = node_id(caller_type, caller.id)
        target = node_id(callee_type, callee.id)
        edges.append({'id': f'call:{call.id}', 'source': source, 'target': target, 'kind': 'calls'})
    logger.info('build_graph: repository=%s nodes=%d edges=%d', repository_id, len(nodes), len(edges))
    return {'root_id': hierarchy['root_id'], 'nodes': nodes, 'edges': edges}
