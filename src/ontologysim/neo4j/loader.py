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
        source_node_type = row["source_node_type"]
        target_node_type = row["target_node_type"]

        if relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unsupported relationship type: {relationship_type}"
            )

        if source_node_type not in NODE_LABELS:
            raise ValueError(
                f"Unsupported source node type: {source_node_type}"
            )

        if target_node_type not in NODE_LABELS:
            raise ValueError(
                f"Unsupported target node type: {target_node_type}"
            )

        key = (
            relationship_type,
            source_node_type,
            target_node_type,
        )

        grouped[key].append(row)

    for (
        relationship_type,
        source_node_type,
        target_node_type,
    ), relationship_rows in grouped.items():
        source_label = NODE_LABELS[source_node_type]
        target_label = NODE_LABELS[target_node_type]

        query = f"""
        UNWIND $rows AS row

        MATCH (
            source:{source_label} {{
                canonical_id: row.source_node_id
            }}
        )

        MATCH (
            target:{target_label} {{
                canonical_id: row.target_node_id
            }}
        )

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

        total = len(relationship_rows)

        for start in range(0, total, batch_size):
            batch = relationship_rows[start : start + batch_size]

            driver.execute_query(
                query,
                rows=batch,
                database_=database,
            )

            loaded = min(start + len(batch), total)

            if loaded == total or loaded % 10000 == 0:
                print(
                    f"  {relationship_type} "
                    f"{source_label}->{target_label}: "
                    f"{loaded:,}/{total:,}"
                )

        print(
            f"Loaded {total:,} {relationship_type} "
            f"{source_label}->{target_label} relationships"
        )


def load_nodes(
    driver,
    database: str,
    rows: list[dict],
    batch_size: int = 1000,
) -> None:
    grouped = defaultdict(list)

    for row in rows:
        node_type = row["node_type"]

        if node_type not in NODE_LABELS:
            raise ValueError(
                f"Unsupported node type: {node_type}"
            )

        grouped[node_type].append(row)

    for node_type, node_rows in grouped.items():
        label = NODE_LABELS[node_type]

        query = f"""
        UNWIND $rows AS row

        MERGE (n:{label} {{
            canonical_id: row.canonical_id
        }})

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