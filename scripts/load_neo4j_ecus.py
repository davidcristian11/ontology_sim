import os

from databricks import sql
from dotenv import load_dotenv

from ontologysim.neo4j.config import get_neo4j_config
from ontologysim.neo4j.connection import create_driver

load_dotenv()


def main() -> None:
    # Read from Databricks
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
                SELECT canonical_id, display_name, mapping_version
                FROM ontologysim.graph_ready.nodes
                WHERE node_type = 'ECU'
                """
        )

        rows = [
            {
                "canonical_id": row[0],
                "display_name": row[1],
                "mapping_version": row[2],
            }
            for row in cursor.fetchall()
        ]

    # Write to Neo4j
    config = get_neo4j_config()
    driver = create_driver(config)

    try:
        driver.execute_query(
            """
            UNWIND $rows AS row

            MERGE (n:ECU {canonical_id: row.canonical_id})
            SET n.display_name = row.display_name,
                n.mapping_version = row.mapping_version
            """,
            rows=rows,
            database_=config.database,
        )

        records, _, _ = driver.execute_query(
            """
            MATCH (n:ECU)
            RETURN count(n) AS count
            """,
            database_=config.database,
        )

        print(f"Databricks ECUs: {len(rows)}")
        print(f"Neo4j ECUs:      {records[0]['count']}")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
