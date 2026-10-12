from ontologysim.neo4j.config import get_neo4j_config
from ontologysim.neo4j.connection import create_driver


def main() -> None:
    config = get_neo4j_config()
    driver = create_driver(config)

    try:
        records, _, _ = driver.execute_query(
            "RETURN 'Neo4j connection successful' AS message",
            database_=config.database,
        )

        print(records[0]["message"])
    finally:
        driver.close()


if __name__ == "__main__":
    main()
