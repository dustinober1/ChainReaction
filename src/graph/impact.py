"""
Risk Assessment and Impact Calculation Engine.

Provides algorithms for calculating the impact of risk events on
the supply chain, including severity scoring and redundancy analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import math

import structlog

from src.graph.traversal import (
    GraphTraversal,
    InMemoryGraph,
    ImpactResult,
    TraversalPath,
    GraphNode,
)
from src.graph.connection import Neo4jConnection, get_connection
from src.models import RiskEvent, SeverityLevel, ImpactAssessment, ImpactPath

logger = structlog.get_logger(__name__)


@dataclass
class SupplierRedundancy:
    """Redundancy analysis for a component."""

    component_id: str
    component_name: str
    supplier_count: int
    primary_supplier_id: str | None
    backup_suppliers: list[str]
    redundancy_score: float  # 0-1, higher = more redundant
    is_single_source: bool
    is_critical: bool


@dataclass
class ImpactScore:
    """Calculated impact score for a risk event."""

    risk_event_id: str
    overall_score: float  # 0-10 scale
    severity_component: float
    proximity_component: float
    criticality_component: float
    redundancy_component: float
    affected_products_count: int
    affected_revenue: float


@dataclass
class RiskAssessmentResult:
    """Complete result of a risk assessment."""

    risk_event: RiskEvent
    impact_score: ImpactScore
    affected_products: list[str]
    affected_suppliers: list[str]
    impact_paths: list[ImpactResult]
    redundancy_analysis: list[SupplierRedundancy]
    mitigation_options: list[str]
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ImpactCalculator:
    """
    Calculates the impact of risk events on the supply chain.

    Uses graph traversal to determine affected products and
    calculates severity based on multiple factors.
    """

    # Weight factors for impact calculation
    SEVERITY_WEIGHTS = {
        SeverityLevel.LOW: 0.25,
        SeverityLevel.MEDIUM: 0.50,
        SeverityLevel.HIGH: 0.75,
        SeverityLevel.CRITICAL: 1.0,
    }

    # Distance decay factor (impact decreases with distance)
    DISTANCE_DECAY = 0.8

    def __init__(
        self,
        connection: Neo4jConnection | None = None,
        graph: InMemoryGraph | None = None,
    ):
        """
        Initialize the impact calculator.

        Args:
            connection: Optional Neo4j connection for production use.
            graph: Optional in-memory graph for testing.
        """
        self._connection = connection
        self._in_memory_graph = graph
        self._traversal = GraphTraversal(connection) if connection else None

    async def calculate_impact(
        self,
        risk_event: RiskEvent,
        affected_node_ids: list[str] | None = None,
    ) -> ImpactScore:
        """
        Calculate the overall impact score for a risk event.

        Args:
            risk_event: The risk event to assess.
            affected_node_ids: Optional list of directly affected nodes.

        Returns:
            ImpactScore with breakdown of impact factors.
        """
        # Get severity component
        severity_component = self.SEVERITY_WEIGHTS.get(
            risk_event.severity, 0.5
        ) * 10

        # Get affected products
        affected_products = []
        proximity_scores = []

        if affected_node_ids and self._in_memory_graph:
            # Use in-memory graph for testing
            for node_id in affected_node_ids:
                impacts = self._in_memory_graph.find_downstream(node_id)
                for impact in impacts:
                    if impact.affected_node_label == "Product":
                        affected_products.append(impact.affected_node_id)
                        # Calculate proximity score (closer = higher impact)
                        proximity = self.DISTANCE_DECAY ** impact.distance_from_source
                        proximity_scores.append(proximity)

        elif affected_node_ids and self._traversal:
            # Use Neo4j traversal
            for node_id in affected_node_ids:
                impacts = await self._traversal.find_downstream_impact(node_id)
                for impact in impacts:
                    if impact.affected_node_label == "Product":
                        affected_products.append(impact.affected_node_id)
                        proximity = self.DISTANCE_DECAY ** impact.distance_from_source
                        proximity_scores.append(proximity)

        # Calculate proximity component
        proximity_component = 0.0
        if proximity_scores:
            proximity_component = sum(proximity_scores) / len(proximity_scores) * 10

        # Criticality component (based on number of affected products)
        criticality_component = min(len(set(affected_products)) * 0.5, 10.0)

        # Redundancy component (placeholder - would need supplier data)
        redundancy_component = 5.0  # Default medium (no redundancy data)

        # Calculate overall score
        overall_score = (
            severity_component * 0.3
            + proximity_component * 0.25
            + criticality_component * 0.25
            + redundancy_component * 0.2
        )

        overall_score = min(max(overall_score, 0.0), 10.0)

        return ImpactScore(
            risk_event_id=risk_event.id,
            overall_score=round(overall_score, 2),
            severity_component=round(severity_component, 2),
            proximity_component=round(proximity_component, 2),
            criticality_component=round(criticality_component, 2),
            redundancy_component=round(redundancy_component, 2),
            affected_products_count=len(set(affected_products)),
            affected_revenue=0.0,  # Would need product data
        )

    def calculate_impact_from_paths(
        self,
        risk_event: RiskEvent,
        impact_results: list[ImpactResult],
    ) -> ImpactScore:
        """
        Calculate impact score from pre-computed traversal results.

        Args:
            risk_event: The risk event.
            impact_results: Pre-computed impact traversal results.

        Returns:
            ImpactScore with breakdown.
        """
        severity_component = self.SEVERITY_WEIGHTS.get(
            risk_event.severity, 0.5
        ) * 10

        affected_products = []
        proximity_scores = []

        for impact in impact_results:
            if impact.affected_node_label == "Product":
                affected_products.append(impact.affected_node_id)
                proximity = self.DISTANCE_DECAY ** impact.distance_from_source
                proximity_scores.append(proximity)

        proximity_component = 0.0
        if proximity_scores:
            proximity_component = sum(proximity_scores) / len(proximity_scores) * 10

        criticality_component = min(len(set(affected_products)) * 0.5, 10.0)
        redundancy_component = 5.0

        overall_score = (
            severity_component * 0.3
            + proximity_component * 0.25
            + criticality_component * 0.25
            + redundancy_component * 0.2
        )

        return ImpactScore(
            risk_event_id=risk_event.id,
            overall_score=round(min(max(overall_score, 0.0), 10.0), 2),
            severity_component=round(severity_component, 2),
            proximity_component=round(proximity_component, 2),
            criticality_component=round(criticality_component, 2),
            redundancy_component=round(redundancy_component, 2),
            affected_products_count=len(set(affected_products)),
            affected_revenue=0.0,
        )


class RedundancyAnalyzer:
    """
    Analyzes supplier redundancy across the supply chain.

    Identifies single-source components and calculates
    redundancy scores for risk assessment.
    """

    def __init__(
        self,
        connection: Neo4jConnection | None = None,
        graph: InMemoryGraph | None = None,
    ):
        """
        Initialize the redundancy analyzer.

        Args:
            connection: Optional Neo4j connection.
            graph: Optional in-memory graph for testing.
        """
        self._connection = connection
        self._in_memory_graph = graph

    async def analyze_product_redundancy(
        self,
        product_id: str,
    ) -> list[SupplierRedundancy]:
        """
        Analyze supplier redundancy for all components of a product.

        Args:
            product_id: ID of the product to analyze.

        Returns:
            List of SupplierRedundancy results for each component.
        """
        if self._connection is None:
            # Testing mode - return mock data
            return []

        conn = self._connection

        query = """
        MATCH (c:Component)-[:PART_OF*1..]->(p:Product {id: $product_id})
        OPTIONAL MATCH (s:Supplier)-[:SUPPLIES]->(c)
        WITH c, collect(DISTINCT s.id) as supplier_ids, c.critical as is_critical
        RETURN c.id as component_id,
               c.name as component_name,
               supplier_ids,
               is_critical
        ORDER BY size(supplier_ids)
        """

        results = await conn.execute_query(query, {"product_id": product_id})

        redundancy_results = []
        for row in results:
            supplier_ids = row.get("supplier_ids", [])
            supplier_count = len([s for s in supplier_ids if s])

            redundancy_score = self._calculate_redundancy_score(supplier_count)

            redundancy_results.append(
                SupplierRedundancy(
                    component_id=row["component_id"],
                    component_name=row.get("component_name", "Unknown"),
                    supplier_count=supplier_count,
                    primary_supplier_id=supplier_ids[0] if supplier_ids else None,
                    backup_suppliers=supplier_ids[1:] if len(supplier_ids) > 1 else [],
                    redundancy_score=redundancy_score,
                    is_single_source=supplier_count <= 1,
                    is_critical=row.get("is_critical", False),
                )
            )

        return redundancy_results

    def analyze_redundancy_in_memory(
        self,
        product_id: str,
        component_supplier_map: dict[str, list[str]],
        critical_components: set[str] | None = None,
    ) -> list[SupplierRedundancy]:
        """
        Analyze redundancy using in-memory data.

        Args:
            product_id: ID of the product.
            component_supplier_map: Mapping of component IDs to supplier IDs.
            critical_components: Set of critical component IDs.

        Returns:
            List of SupplierRedundancy results.
        """
        critical_components = critical_components or set()
        results = []

        for component_id, suppliers in component_supplier_map.items():
            supplier_count = len(suppliers)
            redundancy_score = self._calculate_redundancy_score(supplier_count)

            results.append(
                SupplierRedundancy(
                    component_id=component_id,
                    component_name=f"Component-{component_id}",
                    supplier_count=supplier_count,
                    primary_supplier_id=suppliers[0] if suppliers else None,
                    backup_suppliers=suppliers[1:] if len(suppliers) > 1 else [],
                    redundancy_score=redundancy_score,
                    is_single_source=supplier_count <= 1,
                    is_critical=component_id in critical_components,
                )
            )

        return results

    def _calculate_redundancy_score(self, supplier_count: int) -> float:
        """
        Calculate redundancy score based on supplier count.

        Args:
            supplier_count: Number of available suppliers.

        Returns:
            Redundancy score between 0 and 1.
        """
        if supplier_count == 0:
            return 0.0
        elif supplier_count == 1:
            return 0.2  # Single source risk
        elif supplier_count == 2:
            return 0.5  # Some redundancy
        elif supplier_count == 3:
            return 0.8  # Good redundancy
        else:
            return 1.0  # Excellent redundancy


class RiskAssessor:
    """
    High-level risk assessment combining impact and redundancy analysis.

    Provides complete assessment of risk events including
    mitigation recommendations.
    """

    def __init__(
        self,
        connection: Neo4jConnection | None = None,
        graph: InMemoryGraph | None = None,
    ):
        """
        Initialize the risk assessor.

        Args:
            connection: Optional Neo4j connection.
            graph: Optional in-memory graph for testing.
        """
        self.impact_calculator = ImpactCalculator(connection, graph)
        self.redundancy_analyzer = RedundancyAnalyzer(connection, graph)
        self._connection = connection
        self._in_memory_graph = graph
        self._traversal = GraphTraversal(connection) if connection else None

    async def assess_risk(
        self,
        risk_event: RiskEvent,
        affected_suppliers: list[str] | None = None,
    ) -> RiskAssessmentResult:
        """
        Perform complete risk assessment for an event.

        Args:
            risk_event: The risk event to assess.
            affected_suppliers: Optional list of affected supplier IDs.

        Returns:
            Complete RiskAssessmentResult.
        """
        affected_suppliers = affected_suppliers or []

        # Find affected nodes from event
        impact_paths: list[ImpactResult] = []
        affected_products: list[str] = []

        if self._traversal:
            for supplier_id in affected_suppliers:
                impacts = await self._traversal.find_downstream_impact(supplier_id)
                impact_paths.extend(impacts)
                for impact in impacts:
                    if impact.affected_node_label == "Product":
                        affected_products.append(impact.affected_node_id)

        elif self._in_memory_graph:
            for supplier_id in affected_suppliers:
                impacts = self._in_memory_graph.find_downstream(supplier_id)
                impact_paths.extend(impacts)
                for impact in impacts:
                    if impact.affected_node_label == "Product":
                        affected_products.append(impact.affected_node_id)

        # Calculate impact score
        impact_score = self.impact_calculator.calculate_impact_from_paths(
            risk_event, impact_paths
        )

        # Analyze redundancy for affected products
        redundancy_analysis: list[SupplierRedundancy] = []
        if self._connection:
            for product_id in set(affected_products):
                redundancy = await self.redundancy_analyzer.analyze_product_redundancy(
                    product_id
                )
                redundancy_analysis.extend(redundancy)

        # Generate mitigation options
        mitigation_options = self._generate_mitigation_options(
            impact_score, redundancy_analysis
        )

        return RiskAssessmentResult(
            risk_event=risk_event,
            impact_score=impact_score,
            affected_products=list(set(affected_products)),
            affected_suppliers=affected_suppliers,
            impact_paths=impact_paths,
            redundancy_analysis=redundancy_analysis,
            mitigation_options=mitigation_options,
        )

    def _generate_mitigation_options(
        self,
        impact_score: ImpactScore,
        redundancy_analysis: list[SupplierRedundancy],
    ) -> list[str]:
        """
        Generate mitigation recommendations based on assessment.

        Args:
            impact_score: Calculated impact score.
            redundancy_analysis: Redundancy analysis results.

        Returns:
            List of mitigation recommendation strings.
        """
        options = []

        # Severity-based recommendations
        if impact_score.overall_score >= 7.0:
            options.append("URGENT: Activate crisis management protocols")
            options.append("Notify executive leadership immediately")
        elif impact_score.overall_score >= 5.0:
            options.append("Escalate to supply chain management team")

        # Redundancy-based recommendations
        single_source = [r for r in redundancy_analysis if r.is_single_source]
        if single_source:
            options.append(
                f"Identify alternative suppliers for {len(single_source)} single-source components"
            )

        critical_at_risk = [
            r for r in redundancy_analysis if r.is_critical and r.is_single_source
        ]
        if critical_at_risk:
            options.append(
                f"CRITICAL: {len(critical_at_risk)} critical components have no backup"
            )

        # Product-specific recommendations
        if impact_score.affected_products_count > 0:
            options.append(
                f"Review production schedules for {impact_score.affected_products_count} affected products"
            )

        # General recommendations
        options.append("Increase safety stock for affected components")
        options.append("Monitor situation for further developments")

        return options

    def to_impact_assessment_model(
        self,
        result: RiskAssessmentResult,
    ) -> ImpactAssessment:
        """
        Convert assessment result to ImpactAssessment model.

        Args:
            result: The RiskAssessmentResult.

        Returns:
            ImpactAssessment model instance.
        """
        impact_paths = []
        for impact in result.impact_paths[:5]:  # Limit to 5 paths
            if impact.impact_paths:
                for traversal_path in impact.impact_paths[:2]:  # 2 paths per impact
                    impact_paths.append(
                        ImpactPath(
                            nodes=[n.id for n in traversal_path.nodes],
                            relationship_types=traversal_path.relationship_types,
                            total_hops=traversal_path.total_depth,
                            criticality_score=0.5,
                        )
                    )

        # Calculate redundancy level
        if result.redundancy_analysis:
            avg_redundancy = sum(
                r.redundancy_score for r in result.redundancy_analysis
            ) / len(result.redundancy_analysis)
        else:
            avg_redundancy = 0.5

        return ImpactAssessment(
            risk_event_id=result.risk_event.id,
            affected_products=result.affected_products,
            impact_paths=impact_paths,
            severity_score=result.impact_score.overall_score,
            mitigation_options=result.mitigation_options,
            redundancy_level=avg_redundancy,
        )
