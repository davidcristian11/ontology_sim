import os

from databricks import sql
from dotenv import load_dotenv

from ontologysim.neo4j.config import get_neo4j_config
from ontologysim.neo4j.connection import create_driver
from ontologysim.neo4j.loader import load_relationships

load_dotenv()


EXPECTED_COUNTS = {
    "AFFECTS": 6400,
    "EXECUTION_OF": 155200,
    "FOUND_DURING": 2947,
    "HOSTS": 1600,
    "INVOLVES": 160000,
    "RELATES_TO": 6400,
    "TARGETS": 47360,
}


def main() -> None:
    generation_id = os.environ["GRAPH_GENERATION_ID"]

    print(f"Loading graph generation: {generation_id}")

    # Read graph-ready edges from Databricks
    with (
        sql.connect(
            server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
            http_path=os.environ["DATABRICKS_HTTP_PATH"],
            auth_type="databricks-oauth",
        ) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            """
            SELECT
                e.edge_id,
                e.source_node_id,
                e.relationship_type,
                e.target_node_id,
                e.relationship_origin,
                e.relationship_status,
                e.source_family,
                e.mapping_version,
                e.properties,
                s.node_type AS source_node_type,
                t.node_type AS target_node_type
            FROM ontologysim.graph_ready.edges e
            JOIN ontologysim.graph_ready.nodes s
                ON e.source_node_id = s.node_id
            AND e._generation_id = s._generation_id
            JOIN ontologysim.graph_ready.nodes t
                ON e.target_node_id = t.node_id
            AND e._generation_id = t._generation_id
            WHERE e._generation_id = ?
            """,
            [generation_id],
        )

        rows = [
            {
                "edge_id": row[0],
                "source_node_id": row[1],
                "relationship_type": row[2],
                "target_node_id": row[3],
                "relationship_origin": row[4],
                "relationship_status": row[5],
                "source_family": row[6],
                "mapping_version": row[7],
                "properties": row[8],
                "source_node_type": row[9],
                "target_node_type": row[10],
            }
            for row in cursor.fetchall()
        ]

    print(f"Databricks relationships: {len(rows):,}")

    config = get_neo4j_config()
    driver = create_driver(config)

    try:
        load_relationships(
            driver,
            config.database,
            rows,
        )

        records, _, _ = driver.execute_query(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS relationship_type,
                   count(*) AS count
            ORDER BY relationship_type
            """,
            database_=config.database,
        )

        actual = {record["relationship_type"]: record["count"] for record in records}

        print("\nNeo4j relationship counts:")

        for relationship_type, expected in EXPECTED_COUNTS.items():
            count = actual.get(relationship_type, 0)
            status = "PASS" if count == expected else "FAIL"

            print(
                f"{relationship_type:15} "
                f"{count:>6,} / {expected:>6,}  {status}"
            )

        total = sum(actual.values())

        print(f"\nTotal Neo4j relationships: {total:,}")

        if actual != EXPECTED_COUNTS:
            raise RuntimeError("Neo4j relationship validation failed")

    finally:
        driver.close()


if __name__ == "__main__":
    main()