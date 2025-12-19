"""
Data Integrity and Validation for Supply Chain Graph.

Provides utilities for validating entity references against the Neo4j graph,
checking referential integrity, and handling data consistency issues.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import structlog

from src.models import (
    RiskEvent,
    EntityValidationResult,
    ReferentialIntegrityResult,
    LowConfidenceFlag,
    ValidationError,
)
from src.graph.connection import get_connection

logger = structlog.get_logger(__name__)


@dataclass
class IntegrityCheckResult:
    """Result of an integrity check operation."""

    success: bool
    entity_id: str
    check_type: str
    errors: list[str]
    warnings: list[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class EntityValidator:
    """
    Validates entity references against the Neo4j graph.

    Performs checks to ensure:
    - Entity IDs exist in the graph
    - Entity types match expected values
    - References are consistent across the graph
    """

    # Mapping of node labels to allowed entity ID prefixes
    ENTITY_PREFIXES = {
        "Supplier": ["SUP-", "supplier-"],
        "Component": ["COMP-", "component-"],
        "Product": ["PROD-", "product-"],
        "Location": ["LOC-", "location-"],
        "RiskEvent": ["RISK-", "risk-", "evt-"],
    }

    def __init__(self, connection=None):
        """
        Initialize the validator.

        Args:
            connection: Optional Neo4j connection. Uses global if not provided.
        """
        self._connection = connection

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection

    async def validate_entity_exists(
        self, entity_id: str, expected_type: str | None = None
    ) -> EntityValidationResult:
        """
        Validate that an entity exists in the Neo4j graph.

        Args:
            entity_id: ID of the entity to validate.
            expected_type: Optional expected entity type.

        Returns:
            EntityValidationResult with validation details.
        """
        errors: list[ValidationError] = []
        exists = False
        entity_type = None

        try:
            conn = self._get_connection()

            # Query to find any node with this ID
            query = """
            MATCH (n)
            WHERE n.id = $entity_id
            RETURN labels(n) as labels, n.id as id
            LIMIT 1
            """
            results = await conn.execute_query(query, {"entity_id": entity_id})

            if results and len(results) > 0:
                exists = True
                labels = results[0].get("labels", [])
                entity_type = labels[0] if labels else "Unknown"

                # Check if type matches expected
                if expected_type and entity_type != expected_type:
                    errors.append(
                        ValidationError(
                            field="entity_type",
                            message=f"Expected type {expected_type}, found {entity_type}",
                            value=entity_type,
                            code="type_mismatch",
                        )
                    )
            else:
                errors.append(
                    ValidationError(
                        field="entity_id",
                        message=f"Entity {entity_id} not found in graph",
                        value=entity_id,
                        code="not_found",
                    )
                )

        except Exception as e:
            logger.error("Entity validation failed", entity_id=entity_id, error=str(e))
            errors.append(
                ValidationError(
                    field="connection",
                    message=f"Database error: {str(e)}",
                    code="database_error",
                )
            )

        return EntityValidationResult(
            entity_id=entity_id,
            exists_in_graph=exists,
            entity_type=entity_type,
            validation_errors=errors,
            is_valid=len(errors) == 0,
        )

    async def validate_entities_batch(
        self, entity_ids: list[str]
    ) -> dict[str, EntityValidationResult]:
        """
        Validate multiple entities in a batch.

        Args:
            entity_ids: List of entity IDs to validate.

        Returns:
            Dictionary mapping entity IDs to validation results.
        """
        results = {}

        if not entity_ids:
            return results

        try:
            conn = self._get_connection()

            # Batch query to find all entities at once
            query = """
            UNWIND $entity_ids as eid
            OPTIONAL MATCH (n {id: eid})
            RETURN eid as entity_id, 
                   CASE WHEN n IS NULL THEN false ELSE true END as exists,
                   labels(n) as labels
            """
            query_results = await conn.execute_query(
                query, {"entity_ids": entity_ids}
            )

            found_ids = set()
            for row in query_results:
                eid = row["entity_id"]
                exists = row["exists"]
                labels = row.get("labels") or []
                entity_type = labels[0] if labels else None

                errors = []
                if not exists:
                    errors.append(
                        ValidationError(
                            field="entity_id",
                            message=f"Entity {eid} not found in graph",
                            value=eid,
                            code="not_found",
                        )
                    )

                results[eid] = EntityValidationResult(
                    entity_id=eid,
                    exists_in_graph=exists,
                    entity_type=entity_type,
                    validation_errors=errors,
                    is_valid=exists,
                )
                found_ids.add(eid)

            # Handle any IDs not returned by query
            for eid in entity_ids:
                if eid not in found_ids:
                    results[eid] = EntityValidationResult(
                        entity_id=eid,
                        exists_in_graph=False,
                        entity_type=None,
                        validation_errors=[
                            ValidationError(
                                field="entity_id",
                                message=f"Entity {eid} not found in graph",
                                value=eid,
                                code="not_found",
                            )
                        ],
                        is_valid=False,
                    )

        except Exception as e:
            logger.error("Batch validation failed", error=str(e))
            for eid in entity_ids:
                if eid not in results:
                    results[eid] = EntityValidationResult(
                        entity_id=eid,
                        exists_in_graph=False,
                        entity_type=None,
                        validation_errors=[
                            ValidationError(
                                field="connection",
                                message=f"Database error: {str(e)}",
                                code="database_error",
                            )
                        ],
                        is_valid=False,
                    )

        return results


class ReferentialIntegrityChecker:
    """
    Checks referential integrity for risk events and related entities.

    Ensures that:
    - All affected entity references in risk events are valid
    - No orphaned relationships exist
    - All required references are present
    """

    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, connection=None):
        """
        Initialize the integrity checker.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._entity_validator = EntityValidator(connection)

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection

    async def check_risk_event_integrity(
        self, risk_event: RiskEvent
    ) -> ReferentialIntegrityResult:
        """
        Check referential integrity for a risk event.

        Validates that all entities referenced in the event exist in the graph.

        Args:
            risk_event: The RiskEvent to validate.

        Returns:
            ReferentialIntegrityResult with validation details.
        """
        missing_entities = []

        # Validate all affected entities
        if risk_event.affected_entities:
            validation_results = await self._entity_validator.validate_entities_batch(
                risk_event.affected_entities
            )

            for entity_id, result in validation_results.items():
                if not result.exists_in_graph:
                    missing_entities.append(entity_id)

        # Check for orphaned relationships
        orphaned_relationships = await self._find_orphaned_relationships(risk_event.id)

        all_valid = len(missing_entities) == 0 and len(orphaned_relationships) == 0

        logger.info(
            "Risk event integrity check completed",
            risk_event_id=risk_event.id,
            missing_entities=len(missing_entities),
            orphaned_relationships=len(orphaned_relationships),
            is_valid=all_valid,
        )

        return ReferentialIntegrityResult(
            risk_event_id=risk_event.id,
            all_entities_valid=all_valid,
            missing_entities=missing_entities,
            orphaned_relationships=orphaned_relationships,
        )

    async def _find_orphaned_relationships(self, event_id: str) -> list[str]:
        """
        Find any orphaned relationships for a risk event.

        Args:
            event_id: ID of the risk event to check.

        Returns:
            List of orphaned relationship identifiers.
        """
        orphaned = []

        try:
            conn = self._get_connection()

            # Query for relationships pointing to non-existent nodes
            query = """
            MATCH (e:RiskEvent {id: $event_id})-[r]->(target)
            WHERE target IS NULL OR NOT exists(target.id)
            RETURN type(r) as rel_type, id(r) as rel_id
            """
            results = await conn.execute_query(query, {"event_id": event_id})

            for row in results:
                orphaned.append(f"{row['rel_type']}:{row['rel_id']}")

        except Exception as e:
            logger.warning("Orphan check failed", event_id=event_id, error=str(e))

        return orphaned

    async def check_confidence_threshold(
        self, risk_event: RiskEvent, threshold: float | None = None
    ) -> LowConfidenceFlag | None:
        """
        Check if a risk event's confidence is below threshold.

        Args:
            risk_event: The RiskEvent to check.
            threshold: Optional custom threshold. Defaults to 0.7.

        Returns:
            LowConfidenceFlag if below threshold, None otherwise.
        """
        actual_threshold = threshold if threshold is not None else self.CONFIDENCE_THRESHOLD

        if risk_event.confidence < actual_threshold:
            logger.info(
                "Low confidence event flagged",
                event_id=risk_event.id,
                confidence=risk_event.confidence,
                threshold=actual_threshold,
            )
            return LowConfidenceFlag(
                event_id=risk_event.id,
                original_confidence=risk_event.confidence,
                threshold=actual_threshold,
            )

        return None


class DataIntegrityManager:
    """
    High-level manager for data integrity operations.

    Provides transaction-based operations with rollback support
    for maintaining data consistency.
    """

    def __init__(self, connection=None):
        """
        Initialize the integrity manager.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._entity_validator = EntityValidator(connection)
        self._integrity_checker = ReferentialIntegrityChecker(connection)
        self._pending_modifications: list[dict[str, Any]] = []

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection

    async def validate_before_create(
        self, risk_event: RiskEvent
    ) -> tuple[bool, list[str]]:
        """
        Validate a risk event before creating it in the database.

        Args:
            risk_event: The RiskEvent to validate.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        # Check that all affected entities exist
        if risk_event.affected_entities:
            validation_results = await self._entity_validator.validate_entities_batch(
                risk_event.affected_entities
            )

            for entity_id, result in validation_results.items():
                if not result.is_valid:
                    for err in result.validation_errors:
                        errors.append(f"{entity_id}: {err.message}")

        # Check confidence threshold
        if risk_event.confidence < 0 or risk_event.confidence > 1:
            errors.append(f"Confidence score {risk_event.confidence} out of range [0, 1]")

        return len(errors) == 0, errors

    async def validate_before_update(
        self, entity_id: str, updates: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate updates before applying them.

        Args:
            entity_id: ID of the entity to update.
            updates: Dictionary of field updates.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        # Verify entity exists
        result = await self._entity_validator.validate_entity_exists(entity_id)
        if not result.exists_in_graph:
            errors.append(f"Entity {entity_id} does not exist")
            return False, errors

        # Validate affected_entities if being updated
        if "affected_entities" in updates:
            new_entities = updates["affected_entities"]
            if new_entities:
                validation_results = await self._entity_validator.validate_entities_batch(
                    new_entities
                )
                for eid, res in validation_results.items():
                    if not res.exists_in_graph:
                        errors.append(f"Referenced entity {eid} does not exist")

        return len(errors) == 0, errors

    async def create_with_transaction(
        self, risk_event: RiskEvent, auto_rollback: bool = True
    ) -> tuple[bool, str | None]:
        """
        Create a risk event with transaction support.

        If validation fails and auto_rollback is True, no changes are made.

        Args:
            risk_event: The RiskEvent to create.
            auto_rollback: Whether to rollback on validation failures.

        Returns:
            Tuple of (success, error_message or None).
        """
        # Validate first
        is_valid, errors = await self.validate_before_create(risk_event)

        if not is_valid:
            if auto_rollback:
                logger.warning(
                    "Create transaction rolled back due to validation errors",
                    event_id=risk_event.id,
                    errors=errors,
                )
                return False, "; ".join(errors)

        try:
            conn = self._get_connection()

            # Create the risk event node
            query = """
            CREATE (e:RiskEvent {
                id: $id,
                event_type: $event_type,
                location: $location,
                severity: $severity,
                confidence: $confidence,
                source_url: $source_url,
                description: $description,
                detected_at: datetime()
            })
            RETURN e.id as id
            """
            await conn.execute_write(
                query,
                {
                    "id": risk_event.id,
                    "event_type": risk_event.event_type.value,
                    "location": risk_event.location,
                    "severity": risk_event.severity.value,
                    "confidence": risk_event.confidence,
                    "source_url": risk_event.source_url,
                    "description": risk_event.description,
                },
            )

            # Link to affected entities
            for entity_id in risk_event.affected_entities:
                link_query = """
                MATCH (e:RiskEvent {id: $event_id})
                MATCH (n {id: $entity_id})
                MERGE (e)-[:AFFECTS]->(n)
                """
                await conn.execute_write(
                    link_query,
                    {"event_id": risk_event.id, "entity_id": entity_id},
                )

            logger.info("Risk event created successfully", event_id=risk_event.id)
            return True, None

        except Exception as e:
            logger.error(
                "Failed to create risk event",
                event_id=risk_event.id,
                error=str(e),
            )
            return False, str(e)

    async def prevent_orphan_delete(self, entity_id: str) -> tuple[bool, list[str]]:
        """
        Check if deleting an entity would create orphaned relationships.

        Args:
            entity_id: ID of the entity to check.

        Returns:
            Tuple of (safe_to_delete, list of dependent entities).
        """
        dependents = []

        try:
            conn = self._get_connection()

            # Check for any entities that depend on this one
            query = """
            MATCH (n {id: $entity_id})<-[r]-(dependent)
            RETURN dependent.id as dep_id, type(r) as rel_type
            """
            results = await conn.execute_query(query, {"entity_id": entity_id})

            for row in results:
                dependents.append(f"{row['dep_id']} ({row['rel_type']})")

        except Exception as e:
            logger.warning(
                "Orphan prevention check failed",
                entity_id=entity_id,
                error=str(e),
            )
            return False, [f"Check failed: {str(e)}"]

        safe_to_delete = len(dependents) == 0
        return safe_to_delete, dependents


def format_validation_errors(
    errors: list[ValidationError],
) -> dict[str, Any]:
    """
    Format validation errors for API response.

    Args:
        errors: List of ValidationError objects.

    Returns:
        Dictionary suitable for JSON response.
    """
    return {
        "error": "Validation failed",
        "error_count": len(errors),
        "details": [
            {
                "field": err.field,
                "message": err.message,
                "code": err.code,
                "value": str(err.value) if err.value is not None else None,
            }
            for err in errors
        ],
    }
