from ontologysim.neo4j.config import get_neo4j_config
from ontologysim.neo4j.connection import create_driver

EXPECTED_NODES = {
    "ECU": 3,
    "Component": 100,
    "Requirement": 500,
    "TestCase": 1000,
    "TestExecution": 10000,
    "Incident": 10000,
    "Defect": 200,
}

EXPECTED_RELATIONSHIPS = {
    "AFFECTS": 400,
    "EXECUTION_OF": 9700,
    "FOUND_DURING": 184,
    "HOSTS": 100,
    "INVOLVES": 10000,
    "RELATES_TO": 400,
    "TARGETS": 1860,
}


def scalar(driver, database, query):
    records, _, _ = driver.execute_query(
        query,
        database_=database,
    )
    return records[0]["count"]


def main() -> None:
    config = get_neo4j_config()
    driver = create_driver(config)

    try:
        checks = {
            "missing canonical_id": scalar(
                driver,
                config.database,
                """
                MATCH (n)
                WHERE n.canonical_id IS NULL
                RETURN count(n) AS count
                """,
            ),
            "duplicate canonical_id": scalar(
                driver,
                config.database,
                """
                MATCH (n)
                WITH n.canonical_id AS id, count(*) AS occurrences
                WHERE occurrences > 1
                RETURN count(*) AS count
                """,
            ),
            "missing node mapping_version": scalar(
                driver,
                config.database,
                """
                MATCH (n)
                WHERE n.mapping_version IS NULL
                RETURN count(n) AS count
                """,
            ),
            "missing edge_id": scalar(
                driver,
                config.database,
                """
                MATCH ()-[r]->()
                WHERE r.edge_id IS NULL
                RETURN count(r) AS count
                """,
            ),
            "duplicate edge_id": scalar(
                driver,
                config.database,
                """
                MATCH ()-[r]->()
                WITH r.edge_id AS id, count(*) AS occurrences
                WHERE occurrences > 1
                RETURN count(*) AS count
                """,
            ),
            "missing relationship mapping_version": scalar(
                driver,
                config.database,
                """
                MATCH ()-[r]->()
                WHERE r.mapping_version IS NULL
                RETURN count(r) AS count
                """,
            ),
        }

        print("Integrity checks:")
        for name, count in checks.items():
            status = "PASS" if count == 0 else "FAIL"
            print(f"{name:38} {count:>6}  {status}")

        node_records, _, _ = driver.execute_query(
            """
            MATCH (n)
            RETURN labels(n)[0] AS label, count(*) AS count
            """,
            database_=config.database,
        )

        actual_nodes = {record["label"]: record["count"] for record in node_records}

        rel_records, _, _ = driver.execute_query(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(*) AS count
            """,
            database_=config.database,
        )

        actual_relationships = {record["type"]: record["count"] for record in rel_records}

        print("\nNode counts:")
        for label, expected in EXPECTED_NODES.items():
            actual = actual_nodes.get(label, 0)
            status = "PASS" if actual == expected else "FAIL"
            print(f"{label:15} {actual:>6,} / {expected:>6,}  {status}")

        print("\nRelationship counts:")
        for rel_type, expected in EXPECTED_RELATIONSHIPS.items():
            actual = actual_relationships.get(rel_type, 0)
            status = "PASS" if actual == expected else "FAIL"
            print(f"{rel_type:15} {actual:>6,} / {expected:>6,}  {status}")

        unexpected_nodes = set(actual_nodes) - set(EXPECTED_NODES)
        unexpected_relationships = set(actual_relationships) - set(EXPECTED_RELATIONSHIPS)

        print(f"\nUnexpected labels: {unexpected_nodes or 'none'}")
        print(f"Unexpected relationship types: {unexpected_relationships or 'none'}")

        valid = (
            all(value == 0 for value in checks.values())
            and actual_nodes == EXPECTED_NODES
            and actual_relationships == EXPECTED_RELATIONSHIPS
        )

        print(f"\nNeo4j V1 validation: {'PASS' if valid else 'FAIL'}")

        if not valid:
            raise RuntimeError("Neo4j validation failed")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
