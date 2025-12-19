import glob
import os

from neo4j import GraphDatabase
import networkx as nx


class Neo4jConfig:
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database


def create_driver(config: Neo4jConfig):
    return GraphDatabase.driver(config.uri, auth=(config.username, config.password))


def load_graphml_files(data_dir: str):
    graphml_files = glob.glob(os.path.join(data_dir, "*.graphml"))
    graphs = []
    for file_path in graphml_files:
        graph = nx.read_graphml(file_path)
        graphs.append((graph, os.path.basename(file_path)))
    return graphs


def upload_graph_to_neo4j(driver, graph, filename: str):
    nodes_created = 0
    relationships_created = 0

    with driver.session() as session:
        for node_id, node_data in graph.nodes(data=True):
            clean_node_id = node_id.strip('"')
            properties = {}
            if "entity_type" in node_data:
                properties["entity_type"] = node_data["entity_type"].strip('"')
            if "description" in node_data:
                descriptions = node_data["description"].split("<SEP>")
                properties["description"] = descriptions[0].strip('"')
                if len(descriptions) > 1:
                    properties["additional_descriptions"] = [
                        desc.strip('"') for desc in descriptions[1:]
                    ]
            if "source_id" in node_data:
                properties["source_id"] = node_data["source_id"]

            properties["source_file"] = filename
            properties["node_id"] = clean_node_id

            cypher = """
            MERGE (n:Entity {id: $node_id, source_file: $source_file})
            SET n += $properties
            """

            session.run(
                cypher,
                {
                    "node_id": clean_node_id,
                    "source_file": filename,
                    "properties": properties,
                },
            )

            nodes_created += 1

        for source, target, edge_data in graph.edges(data=True):
            clean_source = source.strip('"')
            clean_target = target.strip('"')
            edge_properties = {}
            if "weight" in edge_data:
                edge_properties["weight"] = float(edge_data["weight"])
            if "description" in edge_data:
                edge_properties["description"] = edge_data["description"].strip('"')
            if "keywords" in edge_data:
                edge_properties["keywords"] = edge_data["keywords"].strip('"')
            if "source_id" in edge_data:
                edge_properties["source_id"] = edge_data["source_id"]

            edge_properties["source_file"] = filename

            cypher = """
            MATCH (a:Entity {id: $source, source_file: $source_file})
            MATCH (b:Entity {id: $target, source_file: $source_file})
            MERGE (a)-[r:RELATED]->(b)
            SET r += $properties
            """

            session.run(
                cypher,
                {
                    "source": clean_source,
                    "target": clean_target,
                    "source_file": filename,
                    "properties": edge_properties,
                },
            )

            relationships_created += 1

    return nodes_created, relationships_created


def import_graphml_directory(config: Neo4jConfig, data_dir: str):
    driver = create_driver(config)
    graphs = load_graphml_files(data_dir)
    if not graphs:
        raise FileNotFoundError(f"No GraphML files found in {data_dir}")

    total_nodes = 0
    total_relationships = 0

    for graph, graph_filename in graphs:
        nodes_created, relationships_created = upload_graph_to_neo4j(
            driver, graph, graph_filename
        )
        total_nodes += nodes_created
        total_relationships += relationships_created

    with driver.session() as session:
        session.run(
            "CREATE INDEX entity_id_index IF NOT EXISTS FOR (n:Entity) ON (n.id)"
        )
        session.run(
            "CREATE INDEX entity_source_file_index IF NOT EXISTS FOR (n:Entity) ON (n.source_file)"
        )

    driver.close()
    return total_nodes, total_relationships, len(graphs)
