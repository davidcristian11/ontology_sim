from neo4j import GraphDatabase

from ontologysim.neo4j.config import Neo4jConfig


def create_driver(config: Neo4jConfig):
    driver = GraphDatabase.driver(
        config.uri,
        auth=(config.user, config.password),
    )

    driver.verify_connectivity()

    return driver
