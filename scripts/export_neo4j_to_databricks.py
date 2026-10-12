import csv
import os
from pathlib import Path

from databricks import sql
from dotenv import load_dotenv

from ontologysim.neo4j.config import get_neo4j_config
from ontologysim.neo4j.connection import create_driver

load_dotenv()


LABEL_TO_NODE_TYPE = {
    "ECU": "ECU",
    "Component": "COMPONENT",
    "Requirement": "REQUIREMENT",
    "TestCase": "TEST_CASE",
    "TestExecution": "TEST_EXECUTION",
    "Incident": "INCIDENT",
    "Defect": "DEFECT",
}


def main() -> None:
    # -------------------------
    # 1. Read from Neo4j
    # -------------------------
    config = get_neo4j_config()
    driver = create_driver(config)

    try:
        node_records, _, _ = driver.execute_query(
            """
            MATCH (n)
            RETURN
                n.node_id AS node_id,
                labels(n)[0] AS label,
                n.canonical_id AS canonical_id,
                n.display_name AS display_name,
                n.properties_json AS properties,
                n.mapping_version AS mapping_version
            """,
            database_=config.database,
        )

        nodes = [
            (
                r["node_id"],
                LABEL_TO_NODE_TYPE[r["label"]],
                r["canonical_id"],
                r["display_name"],
                r["properties"],
                r["mapping_version"],
            )
            for r in node_records
        ]

        edge_records, _, _ = driver.execute_query(
            """
            MATCH (source)-[r]->(target)
            RETURN
                r.edge_id AS edge_id,
                source.canonical_id AS source_node_id,
                type(r) AS relationship_type,
                target.canonical_id AS target_node_id,
                r.relationship_origin AS relationship_origin,
                r.relationship_status AS relationship_status,
                r.source_family AS source_family,
                r.mapping_version AS mapping_version,
                r.properties_json AS properties
            """,
            database_=config.database,
        )

        edges = [
            (
                r["edge_id"],
                r["source_node_id"],
                r["relationship_type"],
                r["target_node_id"],
                r["relationship_origin"],
                r["relationship_status"],
                r["source_family"],
                r["mapping_version"],
                r["properties"],
            )
            for r in edge_records
        ]

    finally:
        driver.close()

    print(f"Exported from Neo4j: {len(nodes):,} nodes")
    print(f"Exported from Neo4j: {len(edges):,} relationships")

    # -------------------------
    # 2. Write temporary CSVs
    # -------------------------
    export_dir = Path("tmp/neo4j_roundtrip").resolve()
    export_dir.mkdir(parents=True, exist_ok=True)

    nodes_file = export_dir / "nodes.csv"
    edges_file = export_dir / "edges.csv"

    with nodes_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(
            f,
            quoting=csv.QUOTE_ALL,
            doublequote=True,
        )
        writer.writerow(
            [
                "node_id",
                "node_type",
                "canonical_id",
                "display_name",
                "properties",
                "mapping_version",
            ]
        )
        writer.writerows(nodes)

    with edges_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(
            f,
            quoting=csv.QUOTE_ALL,
            doublequote=True,
        )
        writer.writerow(
            [
                "edge_id",
                "source_node_id",
                "relationship_type",
                "target_node_id",
                "relationship_origin",
                "relationship_status",
                "source_family",
                "mapping_version",
                "properties",
            ]
        )
        writer.writerows(edges)

    # -------------------------
    # 3. Upload + COPY INTO
    # -------------------------
    with (
        sql.connect(
            server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
            http_path=os.environ["DATABRICKS_HTTP_PATH"],
            auth_type="databricks-oauth",
            staging_allowed_local_path=str(export_dir),
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("TRUNCATE TABLE ontologysim.neo4j_roundtrip.nodes")
        cursor.execute("TRUNCATE TABLE ontologysim.neo4j_roundtrip.edges")

        cursor.execute(
            f"""
                PUT '{nodes_file.as_posix()}'
                INTO '/Volumes/ontologysim/neo4j_roundtrip/roundtrip_stage/nodes.csv'
                OVERWRITE
                """
        )

        cursor.execute(
            f"""
                PUT '{edges_file.as_posix()}'
                INTO '/Volumes/ontologysim/neo4j_roundtrip/roundtrip_stage/edges.csv'
                OVERWRITE
                """
        )

        print("Files uploaded to Databricks")

        cursor.execute(
            """
                COPY INTO ontologysim.neo4j_roundtrip.nodes
                FROM '/Volumes/ontologysim/neo4j_roundtrip/roundtrip_stage/nodes.csv'
                FILEFORMAT = CSV
                FORMAT_OPTIONS (
                    'header' = 'true',
                    'quote' = '"',
                    'escape' = '"',
                    'multiLine' = 'true'
                )
                COPY_OPTIONS ('force' = 'true')
                """
        )

        cursor.execute(
            """
                COPY INTO ontologysim.neo4j_roundtrip.edges
                FROM '/Volumes/ontologysim/neo4j_roundtrip/roundtrip_stage/edges.csv'
                FILEFORMAT = CSV
                FORMAT_OPTIONS (
                    'header' = 'true',
                    'quote' = '"',
                    'escape' = '"',
                    'multiLine' = 'true'
                )
                COPY_OPTIONS ('force' = 'true')
                """
        )

    print("Neo4j → Databricks export complete")


if __name__ == "__main__":
    main()
