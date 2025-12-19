import argparse
import asyncio
import json
import os

from kg_pipeline.document_parser import extract_text_from_path
from kg_pipeline.neo4j_import import Neo4jConfig, import_graphml_directory
from kg_pipeline.rag_pipeline import (
    build_rag_instance,
    get_graph_snapshot,
    query_rag,
    reload_rag_instance,
)


def build_parser():
    parser = argparse.ArgumentParser(description="PathRAG standalone pipeline")
    parser.add_argument(
        "--working-dir",
        default=os.path.join(os.getcwd(), "data"),
        help="PathRAG working directory",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_cmd = subparsers.add_parser("parse", help="Parse a local file and output text")
    parse_cmd.add_argument("file", help="Path to the file")

    ingest_cmd = subparsers.add_parser("ingest", help="Ingest a file into PathRAG")
    ingest_cmd.add_argument("file", help="Path to the file")

    graph_cmd = subparsers.add_parser("graph", help="Dump knowledge graph as JSON")
    graph_cmd.add_argument("--entity", help="Filter by entity id")

    ask_cmd = subparsers.add_parser("ask", help="Run a RAG question against local data")
    ask_cmd.add_argument("question", help="Question to ask")
    ask_cmd.add_argument(
        "--mode",
        default="hybrid",
        choices=["hybrid", "global"],
        help="Query mode",
    )

    neo4j_cmd = subparsers.add_parser("neo4j-import", help="Import GraphML into Neo4j")
    neo4j_cmd.add_argument("--uri", required=True, help="Neo4j bolt URI")
    neo4j_cmd.add_argument("--username", required=True, help="Neo4j username")
    neo4j_cmd.add_argument("--password", required=True, help="Neo4j password")

    return parser


async def ingest_file(file_path: str, working_dir: str):
    rag = build_rag_instance(working_dir)
    content = extract_text_from_path(file_path)
    await rag.ainsert(content)
    rag = reload_rag_instance(working_dir)
    return rag


def handle_graph(rag, entity: str | None):
    nodes, edges = get_graph_snapshot(rag)
    if entity:
        nodes = [node for node in nodes if node["id"].lower() == entity.lower()]
        node_ids = {node["id"] for node in nodes}
        edges = [edge for edge in edges if edge["source"] in node_ids or edge["target"] in node_ids]
    return {"nodes": nodes, "edges": edges}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "parse":
        text = extract_text_from_path(args.file)
        print(text)
        return

    if args.command == "ingest":
        rag = asyncio.run(ingest_file(args.file, args.working_dir))
        nodes, edges = get_graph_snapshot(rag)
        print(json.dumps({"nodes": len(nodes), "edges": len(edges)}, ensure_ascii=False))
        return

    if args.command == "graph":
        rag = build_rag_instance(args.working_dir)
        payload = handle_graph(rag, args.entity)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "ask":
        rag = build_rag_instance(args.working_dir)
        answer = asyncio.run(query_rag(rag, args.question, mode=args.mode))
        print(answer)
        return

    if args.command == "neo4j-import":
        config = Neo4jConfig(
            uri=args.uri,
            username=args.username,
            password=args.password,
        )
        total_nodes, total_relationships, files_processed = import_graphml_directory(
            config, args.working_dir
        )
        print(
            json.dumps(
                {
                    "nodes": total_nodes,
                    "relationships": total_relationships,
                    "files": files_processed,
                },
                ensure_ascii=False,
            )
        )
        return


if __name__ == "__main__":
    main()
