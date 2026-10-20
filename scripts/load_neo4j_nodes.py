import os

from databricks import sql
from dotenv import load_dotenv

from ontologysim.neo4j.config import get_neo4j_config
from ontologysim.neo4j.connection import create_driver
from ontologysim.neo4j.loader import load_nodes

load_dotenv()


EXPECTED_COUNTS = {
    "ECU": 3,
    "Component": 1600,
    "Requirement": 8000,
    "TestCase": 16000,
    "TestExecution": 160000,
    "Incident": 160000,
    "Defect": 3200,
}


def main() -> None:
    generation_id = os.environ["GRAPH_GENERATION_ID"]

    print(f"Loading graph generation: {generation_id}")

    # Databricks
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
                node_id,
                node_type,
                canonical_id,
                display_name,
                properties,
                mapping_version
            FROM ontologysim.graph_ready.nodes
            WHERE _generation_id = ?
            """,
            [generation_id],
        )

        rows = [
            {
                "node_id": row[0],
                "node_type": row[1],
                "canonical_id": row[2],
                "display_name": row[3],
                "properties": row[4],
                "mapping_version": row[5],
            }
            for row in cursor.fetchall()
        ]

    print(f"Databricks nodes: {len(rows):,}")

    # Neo4j
    config = get_neo4j_config()
    driver = create_driver(config)

    try:
        load_nodes(driver, config.database, rows)

        records, _, _ = driver.execute_query(
            """
            MATCH (n)
            RETURN labels(n)[0] AS label, count(*) AS count
            ORDER BY label
            """,
            database_=config.database,
        )

        actual = {record["label"]: record["count"] for record in records}

        print("\nNeo4j counts:")

        for label, expected in EXPECTED_COUNTS.items():
            count = actual.get(label, 0)
            status = "PASS" if count == expected else "FAIL"

            print(f"{label:15} {count:>6,} / {expected:>6,}  {status}")

        total = sum(actual.values())

        print(f"\nTotal Neo4j nodes: {total:,}")

        if actual != EXPECTED_COUNTS:
            raise RuntimeError("Neo4j node validation failed")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
