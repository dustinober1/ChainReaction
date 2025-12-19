"""
Mitigation Recommender System for Supply Chain Risk Management.

Provides intelligent mitigation option generation, ranking, simulation,
outcome tracking, and coordinated strategy planning.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
from collections import defaultdict
import uuid

import structlog

from src.models import (
    RiskEvent,
    SeverityLevel,
    EventType,
)
from src.graph.connection import get_connection

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class MitigationType(str, Enum):
    """Types of mitigation strategies."""

    ALTERNATIVE_SUPPLIER = "alternative_supplier"
    INVENTORY_BUFFER = "inventory_buffer"
    DUAL_SOURCING = "dual_sourcing"
    GEOGRAPHIC_DIVERSIFICATION = "geographic_diversification"
    PROCESS_OPTIMIZATION = "process_optimization"
    CONTRACTUAL_PROTECTION = "contractual_protection"
    EXPEDITED_SHIPPING = "expedited_shipping"
    COMPONENT_SUBSTITUTION = "component_substitution"


class MitigationStatus(str, Enum):
    """Status of a mitigation action."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FeasibilityLevel(str, Enum):
    """Feasibility level of a mitigation option."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class MitigationOption:
    """A single mitigation option for addressing a risk."""

    option_id: str
    risk_event_id: str
    mitigation_type: MitigationType
    title: str
    description: str
    
    # Ranking factors
    feasibility_score: float  # 0-1, higher is more feasible
    cost_impact: float  # Relative cost (0-1, lower is cheaper)
    timeline_days: int  # Days to implement
    effectiveness_score: float  # 0-1, higher is more effective
    
    # Details
    affected_components: list[str] = field(default_factory=list)
    alternative_supplier_ids: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: MitigationStatus = MitigationStatus.PROPOSED

    @property
    def combined_score(self) -> float:
        """Calculate combined ranking score."""
        # Weighted combination: effectiveness * feasibility / (cost * timeline_factor)
        timeline_factor = max(1, self.timeline_days / 30)  # Normalize to ~1 month
        return (self.effectiveness_score * self.feasibility_score) / (
            (self.cost_impact + 0.1) * timeline_factor
        )


@dataclass
class ImpactSimulation:
    """Results of simulating a mitigation's impact."""

    simulation_id: str
    option_id: str
    
    # Before metrics
    before_resilience_score: float
    before_single_points_of_failure: int
    before_supplier_redundancy: float
    
    # After metrics (projected)
    after_resilience_score: float
    after_single_points_of_failure: int
    after_supplier_redundancy: float
    
    # Delta
    resilience_improvement: float
    spof_reduction: int
    redundancy_improvement: float
    
    # Risk assessment
    implementation_risk: float  # 0-1
    confidence: float  # 0-1
    
    simulated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MitigationOutcome:
    """Recorded outcome of a mitigation action."""

    outcome_id: str
    option_id: str
    risk_event_id: str
    
    # Outcome details
    status: MitigationStatus
    actual_effectiveness: float  # 0-1, how effective it actually was
    actual_cost: float  # Actual cost relative to estimate
    actual_timeline_days: int
    
    # Comparison to prediction
    effectiveness_delta: float  # Actual - predicted
    cost_delta: float
    timeline_delta_days: int
    
    # Learning data
    lessons_learned: list[str] = field(default_factory=list)
    success_factors: list[str] = field(default_factory=list)
    failure_reasons: list[str] = field(default_factory=list)
    
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CoordinatedStrategy:
    """Coordinated mitigation strategy addressing multiple risks."""

    strategy_id: str
    affected_product_id: str
    risk_event_ids: list[str]
    
    # Component options
    mitigation_options: list[MitigationOption]
    
    # Combined metrics
    total_cost_impact: float
    total_timeline_days: int
    combined_effectiveness: float
    synergy_bonus: float  # Extra effectiveness from coordination
    
    # Strategy details
    execution_order: list[str]  # Option IDs in recommended order
    dependencies: dict[str, list[str]]  # Option ID -> dependent option IDs
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Mitigation Option Generator
# =============================================================================


class MitigationGenerator:
    """
    Generates mitigation options for supply chain risks.

    Identifies alternative suppliers, components, and strategies
    to address detected risk events.
    """

    # Default mitigation templates by event type
    MITIGATION_TEMPLATES = {
        EventType.STRIKE: [
            MitigationType.ALTERNATIVE_SUPPLIER,
            MitigationType.INVENTORY_BUFFER,
            MitigationType.EXPEDITED_SHIPPING,
        ],
        EventType.WEATHER: [
            MitigationType.GEOGRAPHIC_DIVERSIFICATION,
            MitigationType.INVENTORY_BUFFER,
            MitigationType.EXPEDITED_SHIPPING,
        ],
        EventType.BANKRUPTCY: [
            MitigationType.ALTERNATIVE_SUPPLIER,
            MitigationType.DUAL_SOURCING,
            MitigationType.CONTRACTUAL_PROTECTION,
        ],
        EventType.GEOPOLITICAL: [
            MitigationType.GEOGRAPHIC_DIVERSIFICATION,
            MitigationType.ALTERNATIVE_SUPPLIER,
            MitigationType.INVENTORY_BUFFER,
        ],
        EventType.FIRE: [
            MitigationType.ALTERNATIVE_SUPPLIER,
            MitigationType.EXPEDITED_SHIPPING,
            MitigationType.COMPONENT_SUBSTITUTION,
        ],
        EventType.PANDEMIC: [
            MitigationType.GEOGRAPHIC_DIVERSIFICATION,
            MitigationType.INVENTORY_BUFFER,
            MitigationType.PROCESS_OPTIMIZATION,
        ],
        EventType.CYBER_ATTACK: [
            MitigationType.ALTERNATIVE_SUPPLIER,
            MitigationType.DUAL_SOURCING,
            MitigationType.PROCESS_OPTIMIZATION,
        ],
        EventType.TRANSPORT: [
            MitigationType.EXPEDITED_SHIPPING,
            MitigationType.INVENTORY_BUFFER,
            MitigationType.GEOGRAPHIC_DIVERSIFICATION,
        ],
    }

    def __init__(self, connection=None):
        """
        Initialize the mitigation generator.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._generated_options: dict[str, list[MitigationOption]] = {}

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection

    async def generate_options(
        self, risk_event: RiskEvent, min_options: int = 1
    ) -> list[MitigationOption]:
        """
        Generate mitigation options for a risk event.

        Args:
            risk_event: The RiskEvent to mitigate.
            min_options: Minimum number of options to generate.

        Returns:
            List of MitigationOption objects.
        """
        options = []

        # Get applicable mitigation types
        mitigation_types = self.MITIGATION_TEMPLATES.get(
            risk_event.event_type,
            [MitigationType.ALTERNATIVE_SUPPLIER, MitigationType.INVENTORY_BUFFER],
        )

        # Find alternative suppliers for affected entities
        alternative_suppliers = await self._find_alternative_suppliers(
            risk_event.affected_entities
        )

        # Generate options for each mitigation type
        for mit_type in mitigation_types:
            option = await self._create_option(
                risk_event, mit_type, alternative_suppliers
            )
            if option:
                options.append(option)

        # Ensure minimum options
        while len(options) < min_options:
            fallback = self._create_fallback_option(risk_event, len(options))
            options.append(fallback)

        # Cache generated options
        self._generated_options[risk_event.id] = options

        logger.info(
            "Generated mitigation options",
            risk_event_id=risk_event.id,
            option_count=len(options),
        )

        return options

    async def _find_alternative_suppliers(
        self, entity_ids: list[str]
    ) -> dict[str, list[dict]]:
        """Find alternative suppliers for affected entities."""
        alternatives = {}

        try:
            conn = self._get_connection()

            for entity_id in entity_ids:
                query = """
                MATCH (c:Component {id: $entity_id})
                OPTIONAL MATCH (s:Supplier)-[:SUPPLIES]->(c)
                OPTIONAL MATCH (alt:Supplier)-[:BACKUP_FOR|ALTERNATIVE_TO]->(s)
                OPTIONAL MATCH (alt)-[:LOCATED_IN]->(l:Location)
                WHERE alt IS NOT NULL
                RETURN alt.id as supplier_id, 
                       alt.name as supplier_name,
                       l.name as location,
                       alt.risk_score as risk_score
                """
                results = await conn.execute_query(query, {"entity_id": entity_id})

                alternatives[entity_id] = [
                    {
                        "supplier_id": r.get("supplier_id"),
                        "supplier_name": r.get("supplier_name"),
                        "location": r.get("location"),
                        "risk_score": r.get("risk_score", 50),
                    }
                    for r in results
                    if r.get("supplier_id")
                ]

        except Exception as e:
            logger.warning("Failed to find alternatives", error=str(e))

        return alternatives

    async def _create_option(
        self,
        risk_event: RiskEvent,
        mit_type: MitigationType,
        alternatives: dict[str, list[dict]],
    ) -> MitigationOption | None:
        """Create a mitigation option of the specified type."""
        option_id = f"mit-{risk_event.id[:8]}-{mit_type.value[:8]}-{uuid.uuid4().hex[:6]}"

        # Calculate scores based on mitigation type
        type_params = self._get_type_parameters(mit_type)

        # Get alternative supplier IDs if applicable
        alt_supplier_ids = []
        if mit_type in [MitigationType.ALTERNATIVE_SUPPLIER, MitigationType.DUAL_SOURCING]:
            for entity_alts in alternatives.values():
                alt_supplier_ids.extend([a["supplier_id"] for a in entity_alts if a.get("supplier_id")])

        return MitigationOption(
            option_id=option_id,
            risk_event_id=risk_event.id,
            mitigation_type=mit_type,
            title=self._generate_title(mit_type, risk_event),
            description=self._generate_description(mit_type, risk_event),
            feasibility_score=type_params["feasibility"],
            cost_impact=type_params["cost"],
            timeline_days=type_params["timeline"],
            effectiveness_score=type_params["effectiveness"],
            affected_components=risk_event.affected_entities[:10],
            alternative_supplier_ids=alt_supplier_ids[:5],
            prerequisites=type_params.get("prerequisites", []),
            risks=type_params.get("risks", []),
        )

    def _get_type_parameters(self, mit_type: MitigationType) -> dict:
        """Get parameters for a mitigation type."""
        params = {
            MitigationType.ALTERNATIVE_SUPPLIER: {
                "feasibility": 0.7,
                "cost": 0.4,
                "timeline": 14,
                "effectiveness": 0.8,
                "prerequisites": ["Supplier qualification", "Quality verification"],
                "risks": ["Quality differences", "Capacity constraints"],
            },
            MitigationType.INVENTORY_BUFFER: {
                "feasibility": 0.9,
                "cost": 0.5,
                "timeline": 7,
                "effectiveness": 0.6,
                "prerequisites": ["Warehouse capacity", "Working capital"],
                "risks": ["Inventory holding costs", "Obsolescence"],
            },
            MitigationType.DUAL_SOURCING: {
                "feasibility": 0.6,
                "cost": 0.6,
                "timeline": 30,
                "effectiveness": 0.9,
                "prerequisites": ["Multiple qualified suppliers", "Split order capability"],
                "risks": ["Coordination complexity", "Higher overhead"],
            },
            MitigationType.GEOGRAPHIC_DIVERSIFICATION: {
                "feasibility": 0.5,
                "cost": 0.7,
                "timeline": 60,
                "effectiveness": 0.85,
                "prerequisites": ["Regional supplier availability", "Logistics setup"],
                "risks": ["Extended lead times", "Currency exposure"],
            },
            MitigationType.PROCESS_OPTIMIZATION: {
                "feasibility": 0.8,
                "cost": 0.3,
                "timeline": 21,
                "effectiveness": 0.5,
                "prerequisites": ["Process analysis", "Change management"],
                "risks": ["Implementation disruption", "Learning curve"],
            },
            MitigationType.CONTRACTUAL_PROTECTION: {
                "feasibility": 0.7,
                "cost": 0.2,
                "timeline": 45,
                "effectiveness": 0.4,
                "prerequisites": ["Legal review", "Supplier negotiation"],
                "risks": ["Enforcement challenges", "Relationship strain"],
            },
            MitigationType.EXPEDITED_SHIPPING: {
                "feasibility": 0.95,
                "cost": 0.8,
                "timeline": 3,
                "effectiveness": 0.7,
                "prerequisites": ["Carrier availability", "Budget approval"],
                "risks": ["High cost", "Limited capacity"],
            },
            MitigationType.COMPONENT_SUBSTITUTION: {
                "feasibility": 0.4,
                "cost": 0.5,
                "timeline": 45,
                "effectiveness": 0.75,
                "prerequisites": ["Engineering approval", "Testing/certification"],
                "risks": ["Performance differences", "Regulatory compliance"],
            },
        }
        return params.get(mit_type, {
            "feasibility": 0.5,
            "cost": 0.5,
            "timeline": 30,
            "effectiveness": 0.5,
            "prerequisites": [],
            "risks": [],
        })

    def _generate_title(self, mit_type: MitigationType, risk_event: RiskEvent) -> str:
        """Generate a title for the mitigation option."""
        titles = {
            MitigationType.ALTERNATIVE_SUPPLIER: f"Activate alternative supplier for {risk_event.location}",
            MitigationType.INVENTORY_BUFFER: f"Build inventory buffer for affected components",
            MitigationType.DUAL_SOURCING: f"Implement dual-sourcing strategy",
            MitigationType.GEOGRAPHIC_DIVERSIFICATION: f"Diversify supply base geographically",
            MitigationType.PROCESS_OPTIMIZATION: f"Optimize processes to reduce dependency",
            MitigationType.CONTRACTUAL_PROTECTION: f"Strengthen contractual protections",
            MitigationType.EXPEDITED_SHIPPING: f"Expedite shipments from alternative sources",
            MitigationType.COMPONENT_SUBSTITUTION: f"Substitute with alternative components",
        }
        return titles.get(mit_type, f"Mitigation for {risk_event.event_type.value}")

    def _generate_description(self, mit_type: MitigationType, risk_event: RiskEvent) -> str:
        """Generate a description for the mitigation option."""
        descriptions = {
            MitigationType.ALTERNATIVE_SUPPLIER: (
                f"Engage backup or alternative suppliers to maintain supply continuity "
                f"following the {risk_event.event_type.value} event in {risk_event.location}."
            ),
            MitigationType.INVENTORY_BUFFER: (
                f"Increase safety stock levels for components at risk from the "
                f"{risk_event.event_type.value} event to provide time buffer."
            ),
            MitigationType.DUAL_SOURCING: (
                f"Split orders between multiple qualified suppliers to reduce "
                f"single-source dependency for affected components."
            ),
            MitigationType.GEOGRAPHIC_DIVERSIFICATION: (
                f"Develop supplier relationships in different geographic regions "
                f"to reduce exposure to regional risks like {risk_event.event_type.value}."
            ),
            MitigationType.EXPEDITED_SHIPPING: (
                f"Use premium shipping methods to expedite delivery from "
                f"unaffected suppliers and minimize supply disruption."
            ),
        }
        return descriptions.get(
            mit_type,
            f"Implement {mit_type.value.replace('_', ' ')} to mitigate {risk_event.event_type.value} risk."
        )

    def _create_fallback_option(
        self, risk_event: RiskEvent, index: int
    ) -> MitigationOption:
        """Create a fallback mitigation option."""
        return MitigationOption(
            option_id=f"mit-fallback-{risk_event.id[:8]}-{index}",
            risk_event_id=risk_event.id,
            mitigation_type=MitigationType.INVENTORY_BUFFER,
            title="Emergency inventory build-up",
            description="Build emergency inventory reserves to maintain operations.",
            feasibility_score=0.85,
            cost_impact=0.6,
            timeline_days=7,
            effectiveness_score=0.5,
            affected_components=risk_event.affected_entities[:5],
        )


# =============================================================================
# Mitigation Ranker
# =============================================================================


class MitigationRanker:
    """
    Ranks mitigation options using multiple factors.

    Considers:
    - Feasibility score
    - Cost impact
    - Timeline
    - Effectiveness
    """

    # Default weights for ranking factors
    DEFAULT_WEIGHTS = {
        "feasibility": 0.25,
        "cost": 0.25,  # Inverse - lower is better
        "timeline": 0.20,  # Inverse - lower is better
        "effectiveness": 0.30,
    }

    def __init__(self, weights: dict[str, float] | None = None):
        """
        Initialize the ranker.

        Args:
            weights: Custom weights for ranking factors.
        """
        self.weights = weights or self.DEFAULT_WEIGHTS

    def rank_options(
        self, options: list[MitigationOption]
    ) -> list[tuple[MitigationOption, float]]:
        """
        Rank mitigation options by combined score.

        Args:
            options: List of mitigation options to rank.

        Returns:
            List of (option, score) tuples, sorted by score descending.
        """
        scored_options = []

        for option in options:
            score = self._calculate_ranking_score(option)
            scored_options.append((option, score))

        # Sort by score descending
        scored_options.sort(key=lambda x: x[1], reverse=True)

        logger.debug(
            "Ranked options",
            count=len(options),
            top_score=scored_options[0][1] if scored_options else 0,
        )

        return scored_options

    def _calculate_ranking_score(self, option: MitigationOption) -> float:
        """Calculate ranking score for an option."""
        # Normalize timeline (assume max 90 days)
        timeline_normalized = 1 - min(option.timeline_days / 90, 1.0)

        # Invert cost (lower is better)
        cost_normalized = 1 - option.cost_impact

        score = (
            self.weights["feasibility"] * option.feasibility_score
            + self.weights["cost"] * cost_normalized
            + self.weights["timeline"] * timeline_normalized
            + self.weights["effectiveness"] * option.effectiveness_score
        )

        return round(score, 4)

    def compare_options(
        self,
        option1: MitigationOption,
        option2: MitigationOption,
    ) -> dict[str, Any]:
        """
        Compare two mitigation options.

        Args:
            option1: First option.
            option2: Second option.

        Returns:
            Comparison result dictionary.
        """
        score1 = self._calculate_ranking_score(option1)
        score2 = self._calculate_ranking_score(option2)

        return {
            "option1_id": option1.option_id,
            "option2_id": option2.option_id,
            "option1_score": score1,
            "option2_score": score2,
            "winner": option1.option_id if score1 >= score2 else option2.option_id,
            "score_difference": abs(score1 - score2),
            "comparison": {
                "feasibility": option1.feasibility_score - option2.feasibility_score,
                "cost": option2.cost_impact - option1.cost_impact,  # Inverted
                "timeline": option2.timeline_days - option1.timeline_days,  # Inverted
                "effectiveness": option1.effectiveness_score - option2.effectiveness_score,
            },
        }


# =============================================================================
# Impact Simulator
# =============================================================================


class ImpactSimulator:
    """
    Simulates the impact of mitigation options on supply chain resilience.

    Calculates before/after metrics to help evaluate options.
    """

    def __init__(self, connection=None):
        """
        Initialize the impact simulator.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._simulations: dict[str, ImpactSimulation] = {}

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection

    async def simulate_impact(
        self, option: MitigationOption
    ) -> ImpactSimulation:
        """
        Simulate the impact of implementing a mitigation option.

        Args:
            option: The MitigationOption to simulate.

        Returns:
            ImpactSimulation results.
        """
        # Get current metrics
        before_metrics = await self._get_current_metrics(option.affected_components)

        # Calculate projected after metrics
        after_metrics = self._project_after_metrics(before_metrics, option)

        simulation = ImpactSimulation(
            simulation_id=f"sim-{option.option_id}-{uuid.uuid4().hex[:6]}",
            option_id=option.option_id,
            before_resilience_score=before_metrics["resilience_score"],
            before_single_points_of_failure=before_metrics["spof_count"],
            before_supplier_redundancy=before_metrics["redundancy"],
            after_resilience_score=after_metrics["resilience_score"],
            after_single_points_of_failure=after_metrics["spof_count"],
            after_supplier_redundancy=after_metrics["redundancy"],
            resilience_improvement=after_metrics["resilience_score"] - before_metrics["resilience_score"],
            spof_reduction=before_metrics["spof_count"] - after_metrics["spof_count"],
            redundancy_improvement=after_metrics["redundancy"] - before_metrics["redundancy"],
            implementation_risk=self._calculate_implementation_risk(option),
            confidence=option.feasibility_score * 0.8,
        )

        self._simulations[simulation.simulation_id] = simulation

        logger.info(
            "Simulated impact",
            option_id=option.option_id,
            resilience_improvement=simulation.resilience_improvement,
        )

        return simulation

    async def _get_current_metrics(
        self, component_ids: list[str]
    ) -> dict[str, float]:
        """Get current resilience metrics for components."""
        try:
            conn = self._get_connection()

            # Count suppliers per component
            supplier_counts = []
            spof_count = 0

            for comp_id in component_ids:
                query = """
                MATCH (c:Component {id: $comp_id})
                OPTIONAL MATCH (s:Supplier)-[:SUPPLIES]->(c)
                RETURN count(s) as supplier_count
                """
                results = await conn.execute_query(query, {"comp_id": comp_id})
                
                if results:
                    count = results[0].get("supplier_count", 0)
                    supplier_counts.append(count)
                    if count <= 1:
                        spof_count += 1

            if supplier_counts:
                avg_suppliers = sum(supplier_counts) / len(supplier_counts)
                redundancy = min(1.0, (avg_suppliers - 1) / 2)  # 0 at 1 supplier, 1 at 3+
                resilience = redundancy * 70 + 30  # Base score + redundancy bonus
            else:
                redundancy = 0.0
                resilience = 30.0

            return {
                "resilience_score": resilience,
                "spof_count": spof_count,
                "redundancy": redundancy,
            }

        except Exception as e:
            logger.warning("Failed to get current metrics", error=str(e))
            return {
                "resilience_score": 50.0,
                "spof_count": len(component_ids),
                "redundancy": 0.3,
            }

    def _project_after_metrics(
        self, before: dict[str, float], option: MitigationOption
    ) -> dict[str, float]:
        """Project metrics after implementing mitigation."""
        # Calculate improvements based on mitigation type
        type_improvements = {
            MitigationType.ALTERNATIVE_SUPPLIER: {
                "resilience_delta": 15,
                "spof_reduction_pct": 0.3,
                "redundancy_delta": 0.2,
            },
            MitigationType.DUAL_SOURCING: {
                "resilience_delta": 20,
                "spof_reduction_pct": 0.5,
                "redundancy_delta": 0.35,
            },
            MitigationType.INVENTORY_BUFFER: {
                "resilience_delta": 8,
                "spof_reduction_pct": 0.1,
                "redundancy_delta": 0.05,
            },
            MitigationType.GEOGRAPHIC_DIVERSIFICATION: {
                "resilience_delta": 18,
                "spof_reduction_pct": 0.4,
                "redundancy_delta": 0.3,
            },
            MitigationType.EXPEDITED_SHIPPING: {
                "resilience_delta": 5,
                "spof_reduction_pct": 0.0,
                "redundancy_delta": 0.0,
            },
        }

        improvements = type_improvements.get(option.mitigation_type, {
            "resilience_delta": 10,
            "spof_reduction_pct": 0.2,
            "redundancy_delta": 0.15,
        })

        # Apply effectiveness multiplier
        effectiveness = option.effectiveness_score

        new_resilience = min(100, before["resilience_score"] + 
                            improvements["resilience_delta"] * effectiveness)
        
        spof_reduction = int(before["spof_count"] * 
                            improvements["spof_reduction_pct"] * effectiveness)
        new_spof = max(0, before["spof_count"] - spof_reduction)
        
        new_redundancy = min(1.0, before["redundancy"] + 
                            improvements["redundancy_delta"] * effectiveness)

        return {
            "resilience_score": round(new_resilience, 2),
            "spof_count": new_spof,
            "redundancy": round(new_redundancy, 3),
        }

    def _calculate_implementation_risk(self, option: MitigationOption) -> float:
        """Calculate risk of implementation failure."""
        # Higher cost and longer timeline = higher risk
        # Lower feasibility = higher risk
        risk = (
            (1 - option.feasibility_score) * 0.4
            + option.cost_impact * 0.3
            + min(option.timeline_days / 90, 1.0) * 0.3
        )
        return round(min(1.0, risk), 3)

    def compare_simulations(
        self,
        simulations: list[ImpactSimulation],
    ) -> dict[str, Any]:
        """Compare multiple simulation results."""
        if not simulations:
            return {"error": "No simulations to compare"}

        best_resilience = max(simulations, key=lambda s: s.resilience_improvement)
        best_spof = max(simulations, key=lambda s: s.spof_reduction)
        lowest_risk = min(simulations, key=lambda s: s.implementation_risk)

        return {
            "simulation_count": len(simulations),
            "best_resilience_improvement": {
                "simulation_id": best_resilience.simulation_id,
                "improvement": best_resilience.resilience_improvement,
            },
            "best_spof_reduction": {
                "simulation_id": best_spof.simulation_id,
                "reduction": best_spof.spof_reduction,
            },
            "lowest_implementation_risk": {
                "simulation_id": lowest_risk.simulation_id,
                "risk": lowest_risk.implementation_risk,
            },
        }


# =============================================================================
# Outcome Tracker
# =============================================================================


class OutcomeTracker:
    """
    Tracks and learns from mitigation outcomes.

    Records actual results vs predictions to improve future recommendations.
    """

    def __init__(self):
        """Initialize the outcome tracker."""
        self._outcomes: list[MitigationOutcome] = []
        self._type_performance: dict[MitigationType, list[float]] = defaultdict(list)

    def record_outcome(
        self,
        option: MitigationOption,
        actual_effectiveness: float,
        actual_cost: float,
        actual_timeline_days: int,
        status: MitigationStatus,
        lessons_learned: list[str] | None = None,
    ) -> MitigationOutcome:
        """
        Record the outcome of a mitigation action.

        Args:
            option: The original mitigation option.
            actual_effectiveness: Actual effectiveness (0-1).
            actual_cost: Actual cost relative to estimate.
            actual_timeline_days: Actual implementation time.
            status: Final status of the mitigation.
            lessons_learned: Optional lessons learned.

        Returns:
            MitigationOutcome record.
        """
        outcome = MitigationOutcome(
            outcome_id=f"outcome-{option.option_id}-{uuid.uuid4().hex[:6]}",
            option_id=option.option_id,
            risk_event_id=option.risk_event_id,
            status=status,
            actual_effectiveness=actual_effectiveness,
            actual_cost=actual_cost,
            actual_timeline_days=actual_timeline_days,
            effectiveness_delta=actual_effectiveness - option.effectiveness_score,
            cost_delta=actual_cost - option.cost_impact,
            timeline_delta_days=actual_timeline_days - option.timeline_days,
            lessons_learned=lessons_learned or [],
            success_factors=self._identify_success_factors(option, status, actual_effectiveness),
            failure_reasons=self._identify_failure_reasons(option, status, actual_effectiveness),
        )

        self._outcomes.append(outcome)
        
        # Update type performance tracking
        if status in [MitigationStatus.COMPLETED]:
            self._type_performance[option.mitigation_type].append(actual_effectiveness)

        logger.info(
            "Recorded mitigation outcome",
            option_id=option.option_id,
            status=status.value,
            actual_effectiveness=actual_effectiveness,
        )

        return outcome

    def _identify_success_factors(
        self,
        option: MitigationOption,
        status: MitigationStatus,
        actual_effectiveness: float,
    ) -> list[str]:
        """Identify factors contributing to success."""
        factors = []

        if status == MitigationStatus.COMPLETED and actual_effectiveness >= 0.7:
            if option.feasibility_score >= 0.8:
                factors.append("High feasibility score")
            if option.timeline_days <= 14:
                factors.append("Quick implementation timeline")
            if len(option.alternative_supplier_ids) >= 2:
                factors.append("Multiple alternative suppliers available")

        return factors

    def _identify_failure_reasons(
        self,
        option: MitigationOption,
        status: MitigationStatus,
        actual_effectiveness: float,
    ) -> list[str]:
        """Identify reasons for failure or underperformance."""
        reasons = []

        if status == MitigationStatus.FAILED:
            if option.feasibility_score < 0.5:
                reasons.append("Low feasibility score")
            if option.cost_impact > 0.7:
                reasons.append("High cost impact")
            if option.timeline_days > 60:
                reasons.append("Extended timeline")

        elif actual_effectiveness < option.effectiveness_score * 0.7:
            reasons.append("Actual effectiveness below prediction")

        return reasons

    def get_type_performance(self) -> dict[str, dict[str, float]]:
        """Get performance statistics by mitigation type."""
        stats = {}

        for mit_type, effectiveness_values in self._type_performance.items():
            if effectiveness_values:
                stats[mit_type.value] = {
                    "avg_effectiveness": sum(effectiveness_values) / len(effectiveness_values),
                    "sample_count": len(effectiveness_values),
                    "max_effectiveness": max(effectiveness_values),
                    "min_effectiveness": min(effectiveness_values),
                }

        return stats

    def get_adjustment_factor(self, mit_type: MitigationType) -> float:
        """
        Get adjustment factor for future predictions based on historical performance.

        Args:
            mit_type: The mitigation type.

        Returns:
            Adjustment factor (1.0 = no adjustment).
        """
        if mit_type not in self._type_performance:
            return 1.0

        effectiveness_values = self._type_performance[mit_type]
        if len(effectiveness_values) < 3:
            return 1.0

        # Calculate average actual vs predicted ratio
        avg_actual = sum(effectiveness_values) / len(effectiveness_values)
        # Assume predicted average is 0.7 (typical)
        predicted_avg = 0.7

        return avg_actual / predicted_avg if predicted_avg > 0 else 1.0


# =============================================================================
# Coordinated Strategy Planner
# =============================================================================


class CoordinatedStrategyPlanner:
    """
    Plans coordinated mitigation strategies for multiple risks.

    Identifies synergies and optimizes combined approaches.
    """

    def __init__(self, connection=None):
        """
        Initialize the strategy planner.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._generator = MitigationGenerator(connection)
        self._ranker = MitigationRanker()

    async def create_coordinated_strategy(
        self,
        risk_events: list[RiskEvent],
        product_id: str,
    ) -> CoordinatedStrategy:
        """
        Create a coordinated strategy for multiple risks affecting a product.

        Args:
            risk_events: List of risk events to address.
            product_id: ID of the affected product.

        Returns:
            CoordinatedStrategy combining mitigation options.
        """
        all_options = []
        risk_ids = [e.id for e in risk_events]

        # Generate options for each risk
        for event in risk_events:
            options = await self._generator.generate_options(event, min_options=2)
            all_options.extend(options)

        # Identify synergies
        synergies = self._identify_synergies(all_options)

        # Select best options, considering synergies
        selected = self._select_coordinated_options(all_options, synergies)

        # Calculate combined metrics
        total_cost = sum(o.cost_impact for o in selected)
        total_timeline = max(o.timeline_days for o in selected) if selected else 0
        avg_effectiveness = (
            sum(o.effectiveness_score for o in selected) / len(selected)
            if selected else 0
        )

        # Calculate synergy bonus
        synergy_bonus = min(0.2, len(synergies) * 0.05)

        # Determine execution order
        execution_order = self._determine_execution_order(selected)

        strategy = CoordinatedStrategy(
            strategy_id=f"strategy-{product_id}-{uuid.uuid4().hex[:8]}",
            affected_product_id=product_id,
            risk_event_ids=risk_ids,
            mitigation_options=selected,
            total_cost_impact=min(1.0, total_cost),
            total_timeline_days=total_timeline,
            combined_effectiveness=min(1.0, avg_effectiveness + synergy_bonus),
            synergy_bonus=synergy_bonus,
            execution_order=[o.option_id for o in execution_order],
            dependencies=self._identify_dependencies(selected),
        )

        logger.info(
            "Created coordinated strategy",
            strategy_id=strategy.strategy_id,
            risk_count=len(risk_events),
            option_count=len(selected),
            synergy_bonus=synergy_bonus,
        )

        return strategy

    def _identify_synergies(
        self, options: list[MitigationOption]
    ) -> list[tuple[str, str, str]]:
        """
        Identify synergies between mitigation options.

        Returns list of (option1_id, option2_id, synergy_type) tuples.
        """
        synergies = []

        # Synergy: Same alternative suppliers
        supplier_options = [
            o for o in options if o.alternative_supplier_ids
        ]
        for i, opt1 in enumerate(supplier_options):
            for opt2 in supplier_options[i + 1:]:
                shared = set(opt1.alternative_supplier_ids) & set(opt2.alternative_supplier_ids)
                if shared:
                    synergies.append((opt1.option_id, opt2.option_id, "shared_supplier"))

        # Synergy: Complementary types
        complementary_pairs = [
            (MitigationType.ALTERNATIVE_SUPPLIER, MitigationType.INVENTORY_BUFFER),
            (MitigationType.DUAL_SOURCING, MitigationType.GEOGRAPHIC_DIVERSIFICATION),
        ]
        for opt1 in options:
            for opt2 in options:
                if opt1.option_id != opt2.option_id:
                    for pair in complementary_pairs:
                        if (opt1.mitigation_type, opt2.mitigation_type) == pair:
                            synergies.append((opt1.option_id, opt2.option_id, "complementary"))

        return synergies

    def _select_coordinated_options(
        self,
        options: list[MitigationOption],
        synergies: list[tuple[str, str, str]],
    ) -> list[MitigationOption]:
        """Select best options considering synergies."""
        # Rank all options
        ranked = self._ranker.rank_options(options)

        # Boost scores for options with synergies
        synergy_boost = defaultdict(float)
        for opt1_id, opt2_id, _ in synergies:
            synergy_boost[opt1_id] += 0.05
            synergy_boost[opt2_id] += 0.05

        # Re-rank with synergy boost
        boosted = [
            (opt, score + synergy_boost.get(opt.option_id, 0))
            for opt, score in ranked
        ]
        boosted.sort(key=lambda x: x[1], reverse=True)

        # Select top options, ensuring diversity
        selected = []
        seen_types = set()
        seen_risks = set()

        for opt, _ in boosted:
            # Include if new type or new risk
            if opt.mitigation_type not in seen_types or opt.risk_event_id not in seen_risks:
                selected.append(opt)
                seen_types.add(opt.mitigation_type)
                seen_risks.add(opt.risk_event_id)

            if len(selected) >= min(len(options), 5):
                break

        return selected

    def _determine_execution_order(
        self, options: list[MitigationOption]
    ) -> list[MitigationOption]:
        """Determine optimal execution order for options."""
        # Sort by: prerequisites count (ascending), timeline (ascending), effectiveness (descending)
        return sorted(
            options,
            key=lambda o: (
                len(o.prerequisites),
                o.timeline_days,
                -o.effectiveness_score,
            ),
        )

    def _identify_dependencies(
        self, options: list[MitigationOption]
    ) -> dict[str, list[str]]:
        """Identify dependencies between options."""
        dependencies = {}

        # Simple dependency: longer timeline options depend on shorter ones
        sorted_by_timeline = sorted(options, key=lambda o: o.timeline_days)

        for i, opt in enumerate(sorted_by_timeline):
            deps = []
            # Quick options are prerequisites for longer ones if same type
            for earlier in sorted_by_timeline[:i]:
                if (
                    earlier.mitigation_type == opt.mitigation_type
                    and earlier.timeline_days < opt.timeline_days
                ):
                    deps.append(earlier.option_id)
            if deps:
                dependencies[opt.option_id] = deps

        return dependencies
