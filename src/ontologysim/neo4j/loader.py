from collections import defaultdict

NODE_LABELS = {
    "ECU": "ECU",
    "COMPONENT": "Component",
    "REQUIREMENT": "Requirement",
    "TEST_CASE": "TestCase",
    "TEST_EXECUTION": "TestExecution",
    "INCIDENT": "Incident",
    "DEFECT": "Defect",
}


RELATIONSHIP_TYPES = {
    "HOSTS",
    "TARGETS",
    "RELATES_TO",
    "EXECUTION_OF",
    "AFFECTS",
    "FOUND_DURING",
    "INVOLVES",
}


def load_relationships(
    driver,
    database: str,
    rows: list[dict],
    batch_size: int = 1000,
) -> None:
    grouped = defaultdict(list)

    for row in rows:
        relationship_type = row["relationship_type"]

        if relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"Unsupported relationship type: {relationship_type}")

        grouped[relationship_type].append(row)

    for relationship_type, relationship_rows in grouped.items():
        # relationship_type is safe because it was validated
        # against RELATIONSHIP_TYPES above.
        query = f"""
        UNWIND $rows AS row

        MATCH (source {{canonical_id: row.source_node_id}})
        MATCH (target {{canonical_id: row.target_node_id}})

        MERGE (source)-[r:{relationship_type} {{
            edge_id: row.edge_id
        }}]->(target)

        SET
            r.mapping_version = row.mapping_version,
            r.relationship_origin = row.relationship_origin,
            r.relationship_status = row.relationship_status,
            r.source_family = row.source_family,
            r.properties_json = row.properties
        """

        for start in range(0, len(relationship_rows), batch_size):
            batch = relationship_rows[start : start + batch_size]

            driver.execute_query(
                query,
                rows=batch,
                database_=database,
            )

        print(f"Loaded {len(relationship_rows):,} {relationship_type} relationships")


def load_nodes(driver, database: str, rows: list[dict], batch_size: int = 1000) -> None:
    grouped = defaultdict(list)

    for row in rows:
        node_type = row["node_type"]

        if node_type not in NODE_LABELS:
            raise ValueError(f"Unsupported node type: {node_type}")

        grouped[node_type].append(row)

    for node_type, node_rows in grouped.items():
        label = NODE_LABELS[node_type]

        query = f"""
        UNWIND $rows AS row

        MERGE (n:{label} {{canonical_id: row.canonical_id}})

        SET
            n.node_id = row.node_id,
            n.display_name = row.display_name,
            n.mapping_version = row.mapping_version,
            n.properties_json = row.properties
        """

        for start in range(0, len(node_rows), batch_size):
            batch = node_rows[start : start + batch_size]

            driver.execute_query(
                query,
                rows=batch,
                database_=database,
            )

        print(f"Loaded {len(node_rows):,} {node_type} nodes")
