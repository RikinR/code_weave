from __future__ import annotations
import argparse
from pathlib import Path
from application.ingestion.index_folder import index_folder
from application.retrieval.query_repository import run_manual_queries
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

DEFAULT_FOLDER = Path("test_data/")
DEFAULT_REPOSITORY = "test_data"

MANUAL_QUERIES = [
    "How does course_to_markdown work?",
    "What does generate_course_structure do?",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Code Weave ingestion and RAG CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    index_cmd = sub.add_parser("index", help="Parse, embed, and index a folder")
    index_cmd.add_argument(
        "folder",
        nargs="?",
        default=str(DEFAULT_FOLDER),
        help="Folder to index (default: test_data/)",
    )
    index_cmd.add_argument(
        "--repository",
        default=DEFAULT_REPOSITORY,
        help="Repository name in Postgres (default: folder name)",
    )

    query_cmd = sub.add_parser("query", help="Run RAG queries against an indexed repository")
    query_cmd.add_argument(
        "queries",
        nargs="*",
        help="Questions to ask (default: built-in MANUAL_QUERIES)",
    )
    query_cmd.add_argument(
        "--repository",
        default=DEFAULT_REPOSITORY,
        help="Indexed repository name",
    )
    query_cmd.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of FAISS hits to retrieve per query",
    )

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.command == "index":
        folder = Path(args.folder)
        logger.info("indexing %s (parse, embed, store)", folder)
        result = index_folder(folder, repository_name=args.repository)
        logger.info("index_folder result: %s", result)
        return

    queries = args.queries if args.queries else MANUAL_QUERIES
    logger.info(
        "running %d query(s) against repository=%s top_k=%d",
        len(queries),
        args.repository,
        args.top_k,
    )
    results = run_manual_queries(
        queries=queries,
        repository_name=args.repository,
        top_k=args.top_k,
    )
    for item in results:
        print("\n" + "=" * 72)
        print(f"Q: {item['query']}")
        print(f"Chunks retrieved: {len(item['chunks'])}")
        for ctx in item["chunks"]:
            print(
                f"  - [{ctx.get('score', 0):.4f}] "
                f"{ctx.get('file_path')} :: {ctx.get('function_name')}"
            )
        print("-" * 72)
        print(item["answer"])
    print("\n" + "=" * 72)


if __name__ == "__main__":
    main()
