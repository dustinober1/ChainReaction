"""
Neo4j Database Connection and Utilities.

Provides connection management, query execution, and schema validation
for the ChainReaction knowledge graph.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError

from src.config import get_settings

logger = structlog.get_logger(__name__)


class Neo4jConnection:
    """
    Manages Neo4j database connection with async support.

    This class provides a singleton-like pattern for database connections
    with proper connection pooling and error handling.
    """

    _driver: AsyncDriver | None = None
    _instance: "Neo4jConnection | None" = None

    def __new__(cls) -> "Neo4jConnection":
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        """
        Establish connection to Neo4j database.

        Raises:
            ConnectionError: If connection cannot be established.
        """
        if self._driver is not None:
            return

        settings = get_settings()

        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j.uri,
                auth=(
                    settings.neo4j.username,
                    settings.neo4j.password.get_secret_value(),
                ),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
            )

            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info(
                "Connected to Neo4j",
                uri=settings.neo4j.uri,
                database=settings.neo4j.database,
            )

        except AuthError as e:
            logger.error("Neo4j authentication failed", error=str(e))
            raise ConnectionError(f"Neo4j authentication failed: {e}") from e
        except ServiceUnavailable as e:
            logger.error("Neo4j service unavailable", error=str(e))
            raise ConnectionError(f"Neo4j service unavailable: {e}") from e
        except Exception as e:
            logger.error("Failed to connect to Neo4j", error=str(e))
            raise ConnectionError(f"Failed to connect to Neo4j: {e}") from e

    async def close(self) -> None:
        """Close the database connection."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    @property
    def driver(self) -> AsyncDriver:
        """Get the Neo4j driver instance."""
        if self._driver is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._driver

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session as async context manager.

        Yields:
            AsyncSession: Neo4j async session.
        """
        settings = get_settings()
        async with self.driver.session(database=settings.neo4j.database) as session:
            yield session

    async def execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string.
            parameters: Optional query parameters.

        Returns:
            List of result records as dictionaries.
        """
        async with self.session() as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a write query and return summary.

        Args:
            query: Cypher write query.
            parameters: Optional query parameters.

        Returns:
            Query execution summary.
        """
        async with self.session() as session:

            async def _write_tx(tx):
                result = await tx.run(query, parameters or {})
                summary = await result.consume()
                return {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                }

            return await session.execute_write(_write_tx)


# Singleton instance
_connection: Neo4jConnection | None = None


async def get_connection() -> Neo4jConnection:
    """
    Get the Neo4j connection instance.

    Returns:
        Neo4jConnection: The database connection.
    """
    global _connection
    if _connection is None:
        _connection = Neo4jConnection()
        await _connection.connect()
    return _connection


async def close_connection() -> None:
    """Close the global database connection."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None


# =============================================================================
# Schema Management
# =============================================================================

# Cypher statements for creating constraints and indexes
SCHEMA_CONSTRAINTS = [
    # Unique constraints for node IDs
    "CREATE CONSTRAINT supplier_id IF NOT EXISTS FOR (s:Supplier) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT component_id IF NOT EXISTS FOR (c:Component) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.id IS UNIQUE",
    "CREATE CONSTRAINT risk_event_id IF NOT EXISTS FOR (r:RiskEvent) REQUIRE r.id IS UNIQUE",
]

SCHEMA_INDEXES = [
    # Indexes for common query patterns
    "CREATE INDEX supplier_name IF NOT EXISTS FOR (s:Supplier) ON (s.name)",
    "CREATE INDEX supplier_location IF NOT EXISTS FOR (s:Supplier) ON (s.location)",
    "CREATE INDEX component_name IF NOT EXISTS FOR (c:Component) ON (c.name)",
    "CREATE INDEX component_category IF NOT EXISTS FOR (c:Component) ON (c.category)",
    "CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name)",
    "CREATE INDEX product_line IF NOT EXISTS FOR (p:Product) ON (p.product_line)",
    "CREATE INDEX location_country IF NOT EXISTS FOR (l:Location) ON (l.country)",
    "CREATE INDEX location_region IF NOT EXISTS FOR (l:Location) ON (l.region)",
    "CREATE INDEX risk_event_type IF NOT EXISTS FOR (r:RiskEvent) ON (r.event_type)",
    "CREATE INDEX risk_event_location IF NOT EXISTS FOR (r:RiskEvent) ON (r.location)",
]


async def setup_schema(connection: Neo4jConnection | None = None) -> dict[str, int]:
    """
    Set up database schema with constraints and indexes.

    Args:
        connection: Optional connection instance. If None, uses global connection.

    Returns:
        Dictionary with counts of created constraints and indexes.
    """
    if connection is None:
        connection = await get_connection()

    created = {"constraints": 0, "indexes": 0}

    for constraint in SCHEMA_CONSTRAINTS:
        try:
            await connection.execute_write(constraint)
            created["constraints"] += 1
            logger.debug("Created constraint", query=constraint[:50])
        except Exception as e:
            # Constraint may already exist
            logger.debug("Constraint exists or failed", error=str(e))

    for index in SCHEMA_INDEXES:
        try:
            await connection.execute_write(index)
            created["indexes"] += 1
            logger.debug("Created index", query=index[:50])
        except Exception as e:
            # Index may already exist
            logger.debug("Index exists or failed", error=str(e))

    logger.info(
        "Schema setup complete",
        constraints_created=created["constraints"],
        indexes_created=created["indexes"],
    )

    return created


async def validate_schema(connection: Neo4jConnection | None = None) -> dict[str, list[str]]:
    """
    Validate that all expected schema elements exist.

    Args:
        connection: Optional connection instance.

    Returns:
        Dictionary with lists of existing constraints and indexes.
    """
    if connection is None:
        connection = await get_connection()

    # Get existing constraints
    constraints_result = await connection.execute_query("SHOW CONSTRAINTS")
    constraints = [r.get("name", "") for r in constraints_result]

    # Get existing indexes
    indexes_result = await connection.execute_query("SHOW INDEXES")
    indexes = [r.get("name", "") for r in indexes_result]

    return {
        "constraints": constraints,
        "indexes": indexes,
    }


async def clear_database(connection: Neo4jConnection | None = None) -> dict[str, int]:
    """
    Clear all data from the database (use with caution!).

    Args:
        connection: Optional connection instance.

    Returns:
        Summary of deleted nodes and relationships.
    """
    if connection is None:
        connection = await get_connection()

    logger.warning("Clearing all data from database")

    result = await connection.execute_write(
        "MATCH (n) DETACH DELETE n"
    )

    logger.info(
        "Database cleared",
        nodes_deleted=result["nodes_deleted"],
        relationships_deleted=result["relationships_deleted"],
    )

    return result
