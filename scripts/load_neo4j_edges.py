import os

from databricks import sql
from dotenv import load_dotenv

from ontologysim.neo4j.config import get_neo4j_config
from ontologysim.neo4j.connection import create_driver
from ontologysim.neo4j.loader import load_relationships

load_dotenv()


EXPECTED_COUNTS = {
    "AFFECTS": 400,
    "EXECUTION_OF": 9700,
    "FOUND_DURING": 184,
    "HOSTS": 100,
    "INVOLVES": 10000,
    "RELATES_TO": 400,
    "TARGETS": 1860,
}


def main() -> None:
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
                    edge_id,
                    source_node_id,
                    relationship_type,
                    target_node_id,
                    relationship_origin,
                    relationship_status,
                    source_family,
                    mapping_version,
                    properties
                FROM ontologysim.graph_ready.edges
                """
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

            print(f"{relationship_type:15} {count:>6,} / {expected:>6,}  {status}")

        total = sum(actual.values())

        print(f"\nTotal Neo4j relationships: {total:,}")

        if actual != EXPECTED_COUNTS:
            raise RuntimeError("Neo4j relationship validation failed")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
