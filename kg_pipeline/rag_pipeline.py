import os

from PathRAG import PathRAG, QueryParam
from PathRAG.llm import openai_complete


def build_rag_instance(working_dir: str) -> PathRAG:
    os.makedirs(working_dir, exist_ok=True)
    return PathRAG(
        working_dir=working_dir,
        llm_model_func=openai_complete,
    )


def reload_rag_instance(working_dir: str) -> PathRAG:
    return build_rag_instance(working_dir)


def get_graph_snapshot(rag: PathRAG):
    graph = rag.chunk_entity_relation_graph
    nodes = []
    edges = []

    for node_id in graph._graph.nodes():
        node_data = graph._graph.nodes[node_id]
        nodes.append(
            {
                "id": node_id,
                "type": node_data.get("entity_type", "Unknown"),
                "description": node_data.get("description", ""),
            }
        )

    for source, target, data in graph._graph.edges(data=True):
        edges.append(
            {
                "source": source,
                "target": target,
                "description": data.get("description", ""),
                "weight": data.get("weight", 1.0),
            }
        )

    return nodes, edges


async def query_rag(rag: PathRAG, question: str, mode: str = "hybrid") -> str:
    return await rag.aquery(question, param=QueryParam(mode=mode))
