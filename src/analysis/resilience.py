"""
Resilience Scoring Engine for Supply Chain Analysis.

Provides multi-level resilience calculations for components, products, and portfolios.
Implements redundancy-based scoring with historical tracking and trend analysis.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog

from src.models import (
    ResilienceScore,
    ResilienceMetrics,
    HistoricalResilienceScore,
)
from src.graph.connection import get_connection

logger = structlog.get_logger(__name__)


@dataclass
class RedundancyInfo:
    """Information about supplier redundancy for a component."""

    component_id: str
    component_name: str
    supplier_count: int
    primary_supplier_id: str | None
    backup_suppliers: list[str]
    has_redundancy: bool


class ResilienceScorer:
    """
    Calculates multi-level resilience scores for supply chain entities.

    Resilience scoring is based on:
    - Supplier redundancy (number of alternative suppliers)
    - Geographic diversity (suppliers in different locations)
    - Lead time buffers
    - Historical reliability
    """

    # Weights for resilience factors
    REDUNDANCY_WEIGHT = 0.40
    DIVERSITY_WEIGHT = 0.25
    RELIABILITY_WEIGHT = 0.20
    LEAD_TIME_WEIGHT = 0.15

    # Thresholds for scoring
    MIN_REDUNDANCY_FOR_HIGH_SCORE = 3
    SINGLE_POINT_OF_FAILURE_PENALTY = 25

    def __init__(self, connection=None):
        """
        Initialize the resilience scorer.

        Args:
            connection: Optional Neo4j connection. Uses global if not provided.
        """
        self._connection = connection
        self._history_cache: dict[str, list[HistoricalResilienceScore]] = {}

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection

    async def calculate_component_resilience(
        self, component_id: str
    ) -> ResilienceScore:
        """
        Calculate resilience score for a single component.

        The score is based on:
        - Number of suppliers (redundancy)
        - Geographic diversity of suppliers
        - Supplier reliability history

        Args:
            component_id: ID of the component to score.

        Returns:
            ResilienceScore for the component.
        """
        try:
            conn = self._get_connection()

            # Get component and its suppliers
            query = """
            MATCH (c:Component {id: $component_id})
            OPTIONAL MATCH (s:Supplier)-[:SUPPLIES]->(c)
            OPTIONAL MATCH (s)-[:LOCATED_IN]->(l:Location)
            RETURN c.id as component_id, 
                   c.name as component_name,
                   collect(DISTINCT {
                       supplier_id: s.id, 
                       supplier_name: s.name,
                       location: l.name,
                       country: l.country,
                       risk_score: s.risk_score
                   }) as suppliers
            """
            results = await conn.execute_query(query, {"component_id": component_id})

            if not results:
                logger.warning("Component not found", component_id=component_id)
                return ResilienceScore(
                    entity_id=component_id,
                    entity_type="component",
                    score=0.0,
                    redundancy_factor=0.0,
                )

            row = results[0]
            suppliers = [s for s in row.get("suppliers", []) if s.get("supplier_id")]

            # Calculate redundancy factor (0-1)
            supplier_count = len(suppliers)
            if supplier_count == 0:
                redundancy_factor = 0.0
            elif supplier_count == 1:
                redundancy_factor = 0.3
            elif supplier_count == 2:
                redundancy_factor = 0.6
            else:
                redundancy_factor = min(1.0, 0.6 + (supplier_count - 2) * 0.1)

            # Calculate geographic diversity (0-1)
            unique_countries = set(
                s.get("country") for s in suppliers if s.get("country")
            )
            if len(unique_countries) == 0:
                diversity_score = 0.0
            elif len(unique_countries) == 1:
                diversity_score = 0.4
            else:
                diversity_score = min(1.0, 0.4 + (len(unique_countries) - 1) * 0.2)

            # Calculate reliability from supplier risk scores (invert: low risk = high reliability)
            avg_risk = 0.0
            if suppliers:
                risk_scores = [
                    s.get("risk_score", 50) for s in suppliers if s.get("supplier_id")
                ]
                avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 50
            reliability_score = max(0, (100 - avg_risk)) / 100

            # Calculate overall score
            score = (
                self.REDUNDANCY_WEIGHT * redundancy_factor * 100
                + self.DIVERSITY_WEIGHT * diversity_score * 100
                + self.RELIABILITY_WEIGHT * reliability_score * 100
                + self.LEAD_TIME_WEIGHT * 75  # Default lead time buffer score
            )

            # Apply single point of failure penalty
            if supplier_count <= 1:
                score = max(0, score - self.SINGLE_POINT_OF_FAILURE_PENALTY)

            logger.debug(
                "Component resilience calculated",
                component_id=component_id,
                score=score,
                redundancy_factor=redundancy_factor,
                supplier_count=supplier_count,
            )

            return ResilienceScore(
                entity_id=component_id,
                entity_type="component",
                score=score,
                redundancy_factor=redundancy_factor,
            )

        except Exception as e:
            logger.error(
                "Failed to calculate component resilience",
                component_id=component_id,
                error=str(e),
            )
            return ResilienceScore(
                entity_id=component_id,
                entity_type="component",
                score=0.0,
                redundancy_factor=0.0,
            )

    async def calculate_product_resilience(
        self, product_id: str
    ) -> ResilienceMetrics:
        """
        Calculate resilience score for a product (aggregated from components).

        Args:
            product_id: ID of the product to score.

        Returns:
            ResilienceMetrics for the product with component breakdown.
        """
        try:
            conn = self._get_connection()

            # Get all components for the product
            query = """
            MATCH (p:Product {id: $product_id})
            OPTIONAL MATCH (c:Component)-[:PART_OF]->(p)
            RETURN p.id as product_id, 
                   p.name as product_name,
                   collect(DISTINCT c.id) as component_ids
            """
            results = await conn.execute_query(query, {"product_id": product_id})

            if not results:
                logger.warning("Product not found", product_id=product_id)
                return ResilienceMetrics(
                    entity_id=product_id,
                    level="product",
                    overall_score=0.0,
                )

            row = results[0]
            component_ids = [cid for cid in row.get("component_ids", []) if cid]

            # Calculate resilience for each component
            component_scores: list[ResilienceScore] = []
            for comp_id in component_ids:
                score = await self.calculate_component_resilience(comp_id)
                component_scores.append(score)

            # Calculate aggregate metrics
            if component_scores:
                total_score = sum(s.score for s in component_scores)
                overall_score = total_score / len(component_scores)
                
                # Redundancy coverage: % of components with backup suppliers
                with_redundancy = sum(
                    1 for s in component_scores if s.redundancy_factor > 0.5
                )
                redundancy_coverage = with_redundancy / len(component_scores)
                
                # Count single points of failure
                single_points = sum(
                    1 for s in component_scores if s.redundancy_factor < 0.4
                )
            else:
                overall_score = 0.0
                redundancy_coverage = 0.0
                single_points = 0

            logger.info(
                "Product resilience calculated",
                product_id=product_id,
                overall_score=overall_score,
                component_count=len(component_scores),
                single_points=single_points,
            )

            return ResilienceMetrics(
                entity_id=product_id,
                level="product",
                overall_score=overall_score,
                component_scores=component_scores,
                redundancy_coverage=redundancy_coverage,
                single_points_of_failure=single_points,
            )

        except Exception as e:
            logger.error(
                "Failed to calculate product resilience",
                product_id=product_id,
                error=str(e),
            )
            return ResilienceMetrics(
                entity_id=product_id,
                level="product",
                overall_score=0.0,
            )

    async def calculate_portfolio_resilience(self) -> ResilienceMetrics:
        """
        Calculate portfolio-level resilience across all products.

        Returns:
            ResilienceMetrics for the entire portfolio.
        """
        try:
            conn = self._get_connection()

            # Get all products
            query = """
            MATCH (p:Product)
            RETURN collect(p.id) as product_ids
            """
            results = await conn.execute_query(query)

            if not results or not results[0].get("product_ids"):
                return ResilienceMetrics(
                    entity_id=None,
                    level="portfolio",
                    overall_score=0.0,
                )

            product_ids = results[0]["product_ids"]

            # Calculate resilience for each product
            all_component_scores: list[ResilienceScore] = []
            total_single_points = 0
            product_scores = []

            for prod_id in product_ids:
                metrics = await self.calculate_product_resilience(prod_id)
                all_component_scores.extend(metrics.component_scores)
                total_single_points += metrics.single_points_of_failure
                product_scores.append(metrics.overall_score)

            # Calculate portfolio aggregate
            if product_scores:
                overall_score = sum(product_scores) / len(product_scores)
            else:
                overall_score = 0.0

            if all_component_scores:
                with_redundancy = sum(
                    1 for s in all_component_scores if s.redundancy_factor > 0.5
                )
                redundancy_coverage = with_redundancy / len(all_component_scores)
            else:
                redundancy_coverage = 0.0

            logger.info(
                "Portfolio resilience calculated",
                overall_score=overall_score,
                product_count=len(product_scores),
                total_single_points=total_single_points,
            )

            return ResilienceMetrics(
                entity_id=None,
                level="portfolio",
                overall_score=overall_score,
                component_scores=all_component_scores,
                redundancy_coverage=redundancy_coverage,
                single_points_of_failure=total_single_points,
            )

        except Exception as e:
            logger.error(
                "Failed to calculate portfolio resilience",
                error=str(e),
            )
            return ResilienceMetrics(
                entity_id=None,
                level="portfolio",
                overall_score=0.0,
            )


class ResilienceHistoryTracker:
    """
    Tracks historical resilience scores for trend analysis.

    Stores scores over time and calculates trend metrics.
    """

    # History retention period
    DEFAULT_RETENTION_DAYS = 90

    def __init__(self, connection=None):
        """
        Initialize the history tracker.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._scorer = ResilienceScorer(connection)

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection

    async def record_score(
        self, entity_id: str, score: float, factors: dict[str, float] | None = None
    ) -> HistoricalResilienceScore:
        """
        Record a resilience score for trend tracking.

        Args:
            entity_id: ID of the entity.
            score: Current resilience score.
            factors: Contributing factors and their values.

        Returns:
            HistoricalResilienceScore record.
        """
        record = HistoricalResilienceScore(
            entity_id=entity_id,
            score=score,
            factors=factors or {},
        )

        try:
            conn = self._get_connection()

            # Store the score in the database
            query = """
            MERGE (h:ResilienceHistory {entity_id: $entity_id, recorded_at: datetime()})
            SET h.score = $score,
                h.factors = $factors
            RETURN h
            """
            await conn.execute_write(
                query,
                {
                    "entity_id": entity_id,
                    "score": score,
                    "factors": str(factors or {}),
                },
            )

            logger.debug("Recorded resilience score", entity_id=entity_id, score=score)

        except Exception as e:
            logger.warning(
                "Failed to persist resilience score",
                entity_id=entity_id,
                error=str(e),
            )

        return record

    async def get_history(
        self, entity_id: str, days: int = 30
    ) -> list[HistoricalResilienceScore]:
        """
        Get historical scores for an entity.

        Args:
            entity_id: ID of the entity.
            days: Number of days of history to retrieve.

        Returns:
            List of historical scores, most recent first.
        """
        try:
            conn = self._get_connection()

            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            query = """
            MATCH (h:ResilienceHistory {entity_id: $entity_id})
            WHERE h.recorded_at >= $cutoff
            RETURN h.entity_id as entity_id,
                   h.score as score,
                   h.recorded_at as recorded_at,
                   h.factors as factors
            ORDER BY h.recorded_at DESC
            """
            results = await conn.execute_query(
                query,
                {"entity_id": entity_id, "cutoff": cutoff.isoformat()},
            )

            return [
                HistoricalResilienceScore(
                    entity_id=row["entity_id"],
                    score=row["score"],
                    recorded_at=row.get("recorded_at", datetime.now(timezone.utc)),
                    factors=eval(row.get("factors", "{}")),
                )
                for row in results
            ]

        except Exception as e:
            logger.warning(
                "Failed to retrieve resilience history",
                entity_id=entity_id,
                error=str(e),
            )
            return []

    async def calculate_trend(
        self, entity_id: str, days: int = 30
    ) -> tuple[str | None, float | None]:
        """
        Calculate trend direction and rate for an entity.

        Args:
            entity_id: ID of the entity.
            days: Number of days to analyze.

        Returns:
            Tuple of (trend_direction, trend_rate_per_week).
        """
        history = await self.get_history(entity_id, days)

        if len(history) < 2:
            return None, None

        # Calculate trend using first and last scores
        oldest = history[-1]
        newest = history[0]

        score_change = newest.score - oldest.score
        time_diff = (
            newest.recorded_at - oldest.recorded_at
        ).total_seconds() / (7 * 24 * 3600)  # Weeks

        if time_diff < 0.01:  # Less than ~1 hour
            return "stable", 0.0

        rate_per_week = score_change / time_diff if time_diff > 0 else 0.0

        # Determine trend direction
        if abs(rate_per_week) < 1.0:
            direction = "stable"
        elif rate_per_week > 0:
            direction = "improving"
        else:
            direction = "declining"

        return direction, round(rate_per_week, 2)


class ResilienceRecalculator:
    """
    Manages real-time resilience recalculation triggered by events.

    Implements the 5-minute SLA for recalculation after risk events.
    """

    # SLA for recalculation (in seconds)
    RECALCULATION_SLA_SECONDS = 300  # 5 minutes

    def __init__(self, connection=None):
        """
        Initialize the recalculator.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._scorer = ResilienceScorer(connection)
        self._tracker = ResilienceHistoryTracker(connection)
        self._pending_recalculations: dict[str, datetime] = {}

    async def trigger_recalculation(
        self, affected_entity_ids: list[str]
    ) -> dict[str, ResilienceScore]:
        """
        Trigger resilience recalculation for affected entities.

        Args:
            affected_entity_ids: List of entity IDs that need recalculation.

        Returns:
            Dictionary mapping entity IDs to new resilience scores.
        """
        start_time = datetime.now(timezone.utc)
        results: dict[str, ResilienceScore] = {}

        for entity_id in affected_entity_ids:
            self._pending_recalculations[entity_id] = start_time

            try:
                # Recalculate the score
                new_score = await self._scorer.calculate_component_resilience(entity_id)
                results[entity_id] = new_score

                # Record the new score
                await self._tracker.record_score(
                    entity_id,
                    new_score.score,
                    {"redundancy_factor": new_score.redundancy_factor},
                )

                # Remove from pending
                del self._pending_recalculations[entity_id]

            except Exception as e:
                logger.error(
                    "Recalculation failed",
                    entity_id=entity_id,
                    error=str(e),
                )

        # Check SLA compliance
        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()

        if duration_seconds > self.RECALCULATION_SLA_SECONDS:
            logger.warning(
                "Recalculation SLA violation",
                duration_seconds=duration_seconds,
                sla_seconds=self.RECALCULATION_SLA_SECONDS,
                entity_count=len(affected_entity_ids),
            )

        return results

    async def get_affected_entities_for_event(
        self, risk_event_location: str
    ) -> list[str]:
        """
        Find all entities affected by a risk event at a location.

        Args:
            risk_event_location: Location of the risk event.

        Returns:
            List of entity IDs that need recalculation.
        """
        try:
            conn = self._get_connection() if hasattr(self, '_connection') else get_connection()

            # Find suppliers in the affected location
            query = """
            MATCH (s:Supplier)-[:LOCATED_IN]->(l:Location {name: $location})
            OPTIONAL MATCH (s)-[:SUPPLIES]->(c:Component)
            OPTIONAL MATCH (c)-[:PART_OF]->(p:Product)
            RETURN collect(DISTINCT s.id) + collect(DISTINCT c.id) + collect(DISTINCT p.id) as affected
            """
            results = await conn.execute_query(query, {"location": risk_event_location})

            if results and results[0].get("affected"):
                return [eid for eid in results[0]["affected"] if eid]
            return []

        except Exception as e:
            logger.warning(
                "Failed to get affected entities",
                location=risk_event_location,
                error=str(e),
            )
            return []

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection
