import os

from databricks import sql
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
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
                SELECT canonical_id, display_name, mapping_version, properties
                FROM ontologysim.graph_ready.nodes
                WHERE node_type = 'ECU'
                ORDER BY canonical_id
                """
        )

        rows = cursor.fetchall()

        print(f"ECUs found: {len(rows)}")

        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
