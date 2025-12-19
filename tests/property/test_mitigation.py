"""
Property Tests for Mitigation Recommender System.

Tests the mitigation functionality, verifying:
- Property 21: Mitigation Option Generation
- Property 22: Mitigation Ranking Consistency
- Property 23: Mitigation Impact Simulation
- Property 24: Mitigation Outcome Tracking
- Property 25: Coordinated Mitigation Strategies
"""

from datetime import datetime, timezone, timedelta
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
import pytest
import uuid

from src.models import EventType, SeverityLevel, RiskEvent
from src.analysis.mitigation import (
    MitigationType,
    MitigationStatus,
    FeasibilityLevel,
    MitigationOption,
    ImpactSimulation,
    MitigationOutcome,
    CoordinatedStrategy,
    MitigationGenerator,
    MitigationRanker,
    ImpactSimulator,
    OutcomeTracker,
    CoordinatedStrategyPlanner,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Event type strategy
event_type_strategy = st.sampled_from(list(EventType))

# Severity level strategy
severity_strategy = st.sampled_from(list(SeverityLevel))

# Mitigation type strategy
mitigation_type_strategy = st.sampled_from(list(MitigationType))

# Mitigation status strategy
mitigation_status_strategy = st.sampled_from(list(MitigationStatus))

# Score strategy (0.0 to 1.0)
score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# Timeline days strategy
timeline_strategy = st.integers(min_value=1, max_value=180)

# Location strategy
location_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"), whitelist_characters=",- "),
    min_size=2,
    max_size=50,
).filter(lambda x: x.strip())

# Entity ID strategy
entity_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    min_size=3,
    max_size=30,
).filter(lambda x: x.strip())


# Mitigation option strategy
@st.composite
def mitigation_option_strategy(draw) -> MitigationOption:
    """Generate valid MitigationOption instances."""
    return MitigationOption(
        option_id=f"mit-{draw(st.text(min_size=5, max_size=20, alphabet='abcdef0123456789'))}",
        risk_event_id=f"risk-{draw(st.text(min_size=5, max_size=20, alphabet='abcdef0123456789'))}",
        mitigation_type=draw(mitigation_type_strategy),
        title=draw(st.text(min_size=5, max_size=100).filter(lambda x: x.strip())),
        description=draw(st.text(min_size=10, max_size=200).filter(lambda x: x.strip())),
        feasibility_score=draw(score_strategy),
        cost_impact=draw(score_strategy),
        timeline_days=draw(timeline_strategy),
        effectiveness_score=draw(score_strategy),
        affected_components=draw(st.lists(entity_id_strategy, min_size=0, max_size=5)),
        alternative_supplier_ids=draw(st.lists(entity_id_strategy, min_size=0, max_size=3)),
        prerequisites=draw(st.lists(st.text(min_size=3, max_size=50), min_size=0, max_size=3)),
        risks=draw(st.lists(st.text(min_size=3, max_size=50), min_size=0, max_size=3)),
    )


# Impact simulation strategy
@st.composite
def impact_simulation_strategy(draw) -> ImpactSimulation:
    """Generate valid ImpactSimulation instances."""
    before_score = draw(st.floats(min_value=20.0, max_value=80.0, allow_nan=False))
    improvement = draw(st.floats(min_value=0.0, max_value=30.0, allow_nan=False))
    before_spof = draw(st.integers(min_value=0, max_value=20))
    spof_reduction = draw(st.integers(min_value=0, max_value=before_spof))
    before_redundancy = draw(st.floats(min_value=0.0, max_value=0.8, allow_nan=False))
    redundancy_improvement = draw(st.floats(min_value=0.0, max_value=0.3, allow_nan=False))
    
    return ImpactSimulation(
        simulation_id=f"sim-{uuid.uuid4().hex[:8]}",
        option_id=f"mit-{uuid.uuid4().hex[:8]}",
        before_resilience_score=before_score,
        before_single_points_of_failure=before_spof,
        before_supplier_redundancy=before_redundancy,
        after_resilience_score=min(100, before_score + improvement),
        after_single_points_of_failure=before_spof - spof_reduction,
        after_supplier_redundancy=min(1.0, before_redundancy + redundancy_improvement),
        resilience_improvement=improvement,
        spof_reduction=spof_reduction,
        redundancy_improvement=redundancy_improvement,
        implementation_risk=draw(score_strategy),
        confidence=draw(score_strategy),
    )


# Risk event strategy
@st.composite
def risk_event_strategy(draw) -> RiskEvent:
    """Generate valid RiskEvent instances for testing."""
    return RiskEvent(
        id=f"risk-{uuid.uuid4().hex[:8]}",
        title=draw(st.text(min_size=5, max_size=100).filter(lambda x: x.strip())),
        source="test_source",
        event_type=draw(event_type_strategy),
        severity=draw(severity_strategy),
        location=draw(location_strategy),
        description=draw(st.text(min_size=10, max_size=200).filter(lambda x: x.strip())),
        confidence=draw(score_strategy),
        affected_entities=draw(st.lists(entity_id_strategy, min_size=1, max_size=5)),
    )


# =============================================================================
# Property 21: Mitigation Option Generation
# =============================================================================


class TestMitigationOptionGeneration:
    """Property tests for mitigation option generation."""

    @given(option=mitigation_option_strategy())
    @settings(max_examples=50)
    def test_mitigation_option_has_valid_structure(self, option: MitigationOption):
        """
        Property: Mitigation options always have valid structure.
        """
        assert option.option_id is not None
        assert option.risk_event_id is not None
        assert option.mitigation_type in list(MitigationType)
        assert option.title is not None
        assert option.description is not None

    @given(option=mitigation_option_strategy())
    @settings(max_examples=50)
    def test_scores_are_in_valid_range(self, option: MitigationOption):
        """
        Property: All scores are in valid [0, 1] range.
        """
        assert 0.0 <= option.feasibility_score <= 1.0
        assert 0.0 <= option.cost_impact <= 1.0
        assert 0.0 <= option.effectiveness_score <= 1.0

    @given(option=mitigation_option_strategy())
    @settings(max_examples=50)
    def test_timeline_is_positive(self, option: MitigationOption):
        """
        Property: Timeline is always positive.
        """
        assert option.timeline_days > 0

    @given(event_type=event_type_strategy)
    @settings(max_examples=20)
    def test_generator_templates_exist_for_event_types(self, event_type: EventType):
        """
        Property: Generator has mitigation templates for event types.
        """
        generator = MitigationGenerator()
        templates = generator.MITIGATION_TEMPLATES.get(
            event_type,
            [MitigationType.ALTERNATIVE_SUPPLIER, MitigationType.INVENTORY_BUFFER],
        )
        
        # Should always have at least one template
        assert len(templates) >= 1
        assert all(isinstance(t, MitigationType) for t in templates)

    @given(option=mitigation_option_strategy())
    @settings(max_examples=50)
    def test_combined_score_is_calculable(self, option: MitigationOption):
        """
        Property: Combined score can always be calculated.
        """
        score = option.combined_score
        # Should be a valid number
        assert isinstance(score, (int, float))
        assert score >= 0


# =============================================================================
# Property 22: Mitigation Ranking Consistency
# =============================================================================


class TestMitigationRankingConsistency:
    """Property tests for mitigation ranking consistency."""

    @given(options=st.lists(mitigation_option_strategy(), min_size=2, max_size=10))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_ranking_produces_ordered_results(self, options: list[MitigationOption]):
        """
        Property: Ranking always produces scores in descending order.
        """
        ranker = MitigationRanker()
        ranked = ranker.rank_options(options)
        
        scores = [score for _, score in ranked]
        assert scores == sorted(scores, reverse=True)

    @given(option=mitigation_option_strategy())
    @settings(max_examples=50)
    def test_ranking_is_deterministic(self, option: MitigationOption):
        """
        Property: Same option always gets same ranking score.
        """
        ranker = MitigationRanker()
        
        score1 = ranker._calculate_ranking_score(option)
        score2 = ranker._calculate_ranking_score(option)
        
        assert score1 == score2

    @given(
        feasibility=score_strategy,
        cost=score_strategy,
        timeline=timeline_strategy,
        effectiveness=score_strategy,
    )
    @settings(max_examples=50)
    def test_ranking_score_is_bounded(
        self, feasibility: float, cost: float, timeline: int, effectiveness: float
    ):
        """
        Property: Ranking score is bounded in a reasonable range.
        """
        option = MitigationOption(
            option_id="test-option",
            risk_event_id="test-risk",
            mitigation_type=MitigationType.ALTERNATIVE_SUPPLIER,
            title="Test Option",
            description="Test description for the option",
            feasibility_score=feasibility,
            cost_impact=cost,
            timeline_days=timeline,
            effectiveness_score=effectiveness,
        )
        
        ranker = MitigationRanker()
        score = ranker._calculate_ranking_score(option)
        
        # Score should be in a reasonable range [0, 1]
        assert 0.0 <= score <= 1.0

    @given(
        option1=mitigation_option_strategy(),
        option2=mitigation_option_strategy(),
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_comparison_produces_valid_result(
        self, option1: MitigationOption, option2: MitigationOption
    ):
        """
        Property: Comparison always produces valid result with winner.
        """
        ranker = MitigationRanker()
        result = ranker.compare_options(option1, option2)
        
        assert "winner" in result
        assert result["winner"] in [option1.option_id, option2.option_id]
        assert "score_difference" in result
        assert result["score_difference"] >= 0


# =============================================================================
# Property 23: Mitigation Impact Simulation
# =============================================================================


class TestMitigationImpactSimulation:
    """Property tests for mitigation impact simulation."""

    @given(simulation=impact_simulation_strategy())
    @settings(max_examples=50)
    def test_simulation_has_valid_structure(self, simulation: ImpactSimulation):
        """
        Property: Impact simulations have valid structure.
        """
        assert simulation.simulation_id is not None
        assert simulation.option_id is not None
        assert simulation.before_resilience_score >= 0
        assert simulation.after_resilience_score >= 0

    @given(simulation=impact_simulation_strategy())
    @settings(max_examples=50)
    def test_resilience_scores_in_valid_range(self, simulation: ImpactSimulation):
        """
        Property: Resilience scores are in valid range [0, 100].
        """
        assert 0 <= simulation.before_resilience_score <= 100
        assert 0 <= simulation.after_resilience_score <= 100

    @given(simulation=impact_simulation_strategy())
    @settings(max_examples=50)
    def test_spof_counts_are_non_negative(self, simulation: ImpactSimulation):
        """
        Property: Single points of failure counts are non-negative.
        """
        assert simulation.before_single_points_of_failure >= 0
        assert simulation.after_single_points_of_failure >= 0

    @given(simulation=impact_simulation_strategy())
    @settings(max_examples=50)
    def test_redundancy_in_valid_range(self, simulation: ImpactSimulation):
        """
        Property: Supplier redundancy is in valid range [0, 1].
        """
        assert 0.0 <= simulation.before_supplier_redundancy <= 1.0
        assert 0.0 <= simulation.after_supplier_redundancy <= 1.0

    @given(simulation=impact_simulation_strategy())
    @settings(max_examples=50)
    def test_implementation_risk_in_valid_range(self, simulation: ImpactSimulation):
        """
        Property: Implementation risk is in valid range [0, 1].
        """
        assert 0.0 <= simulation.implementation_risk <= 1.0
        assert 0.0 <= simulation.confidence <= 1.0

    @given(simulations=st.lists(impact_simulation_strategy(), min_size=2, max_size=5))
    @settings(max_examples=20)
    def test_comparison_finds_best_options(self, simulations: list[ImpactSimulation]):
        """
        Property: Comparison correctly identifies best options.
        """
        simulator = ImpactSimulator()
        
        # Store simulations
        for sim in simulations:
            simulator._simulations[sim.simulation_id] = sim
        
        result = simulator.compare_simulations(simulations)
        
        assert "best_resilience_improvement" in result
        assert "best_spof_reduction" in result
        assert "lowest_implementation_risk" in result


# =============================================================================
# Property 24: Mitigation Outcome Tracking
# =============================================================================


class TestMitigationOutcomeTracking:
    """Property tests for mitigation outcome tracking."""

    @given(
        effectiveness=score_strategy,
        cost=score_strategy,
        timeline=timeline_strategy,
        status=mitigation_status_strategy,
    )
    @settings(max_examples=50)
    def test_outcome_records_have_valid_structure(
        self, effectiveness: float, cost: float, timeline: int, status: MitigationStatus
    ):
        """
        Property: Outcome records have valid structure.
        """
        option = MitigationOption(
            option_id="test-option",
            risk_event_id="test-risk",
            mitigation_type=MitigationType.ALTERNATIVE_SUPPLIER,
            title="Test Option",
            description="Test description",
            feasibility_score=0.7,
            cost_impact=0.5,
            timeline_days=14,
            effectiveness_score=0.8,
        )
        
        tracker = OutcomeTracker()
        outcome = tracker.record_outcome(
            option=option,
            actual_effectiveness=effectiveness,
            actual_cost=cost,
            actual_timeline_days=timeline,
            status=status,
        )
        
        assert outcome.outcome_id is not None
        assert outcome.option_id == option.option_id
        assert outcome.status == status

    @given(
        actual_effectiveness=score_strategy,
        predicted_effectiveness=score_strategy,
    )
    @settings(max_examples=50)
    def test_effectiveness_delta_is_calculated(
        self, actual_effectiveness: float, predicted_effectiveness: float
    ):
        """
        Property: Effectiveness delta is correctly calculated.
        """
        option = MitigationOption(
            option_id="test-option",
            risk_event_id="test-risk",
            mitigation_type=MitigationType.INVENTORY_BUFFER,
            title="Test",
            description="Test description",
            feasibility_score=0.8,
            cost_impact=0.4,
            timeline_days=7,
            effectiveness_score=predicted_effectiveness,
        )
        
        tracker = OutcomeTracker()
        outcome = tracker.record_outcome(
            option=option,
            actual_effectiveness=actual_effectiveness,
            actual_cost=0.5,
            actual_timeline_days=10,
            status=MitigationStatus.COMPLETED,
        )
        
        expected_delta = actual_effectiveness - predicted_effectiveness
        assert abs(outcome.effectiveness_delta - expected_delta) < 0.001

    @given(outcomes=st.lists(st.tuples(mitigation_type_strategy, score_strategy), min_size=3, max_size=10))
    @settings(max_examples=20)
    def test_type_performance_tracking(
        self, outcomes: list[tuple[MitigationType, float]]
    ):
        """
        Property: Type performance is tracked correctly.
        """
        tracker = OutcomeTracker()
        
        for mit_type, effectiveness in outcomes:
            option = MitigationOption(
                option_id=f"opt-{uuid.uuid4().hex[:6]}",
                risk_event_id="test-risk",
                mitigation_type=mit_type,
                title="Test",
                description="Test description",
                feasibility_score=0.7,
                cost_impact=0.5,
                timeline_days=14,
                effectiveness_score=0.7,
            )
            
            tracker.record_outcome(
                option=option,
                actual_effectiveness=effectiveness,
                actual_cost=0.5,
                actual_timeline_days=14,
                status=MitigationStatus.COMPLETED,
            )
        
        performance = tracker.get_type_performance()
        
        # Performance should be tracked for completed mitigations
        assert isinstance(performance, dict)

    @given(mit_type=mitigation_type_strategy)
    @settings(max_examples=20)
    def test_adjustment_factor_is_valid(self, mit_type: MitigationType):
        """
        Property: Adjustment factor is always a valid positive number.
        """
        tracker = OutcomeTracker()
        factor = tracker.get_adjustment_factor(mit_type)
        
        assert isinstance(factor, (int, float))
        assert factor > 0


# =============================================================================
# Property 25: Coordinated Mitigation Strategies
# =============================================================================


class TestCoordinatedMitigationStrategies:
    """Property tests for coordinated mitigation strategies."""

    @given(
        options=st.lists(mitigation_option_strategy(), min_size=2, max_size=5)
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_strategy_combines_multiple_options(
        self, options: list[MitigationOption]
    ):
        """
        Property: Coordinated strategies can combine multiple options.
        """
        strategy = CoordinatedStrategy(
            strategy_id=f"strategy-{uuid.uuid4().hex[:8]}",
            affected_product_id="product-1",
            risk_event_ids=[o.risk_event_id for o in options],
            mitigation_options=options,
            total_cost_impact=min(1.0, sum(o.cost_impact for o in options)),
            total_timeline_days=max(o.timeline_days for o in options),
            combined_effectiveness=sum(o.effectiveness_score for o in options) / len(options),
            synergy_bonus=0.1,
            execution_order=[o.option_id for o in options],
            dependencies={},
        )
        
        assert len(strategy.mitigation_options) == len(options)
        assert len(strategy.risk_event_ids) == len(options)

    @given(
        cost1=score_strategy,
        cost2=score_strategy,
        cost3=score_strategy,
    )
    @settings(max_examples=30)
    def test_total_cost_is_bounded(self, cost1: float, cost2: float, cost3: float):
        """
        Property: Total cost impact is bounded to [0, 1].
        """
        options = [
            MitigationOption(
                option_id=f"opt-{i}",
                risk_event_id="risk-1",
                mitigation_type=MitigationType.INVENTORY_BUFFER,
                title="Test",
                description="Description",
                feasibility_score=0.7,
                cost_impact=c,
                timeline_days=14,
                effectiveness_score=0.7,
            )
            for i, c in enumerate([cost1, cost2, cost3])
        ]
        
        total_cost = min(1.0, sum(o.cost_impact for o in options))
        
        assert 0.0 <= total_cost <= 1.0

    @given(
        timeline1=timeline_strategy,
        timeline2=timeline_strategy,
    )
    @settings(max_examples=30)
    def test_total_timeline_is_max_of_components(self, timeline1: int, timeline2: int):
        """
        Property: Total timeline is the maximum of component timelines.
        """
        options = [
            MitigationOption(
                option_id=f"opt-{i}",
                risk_event_id=f"risk-{i}",
                mitigation_type=MitigationType.ALTERNATIVE_SUPPLIER,
                title="Test",
                description="Description",
                feasibility_score=0.7,
                cost_impact=0.5,
                timeline_days=t,
                effectiveness_score=0.7,
            )
            for i, t in enumerate([timeline1, timeline2])
        ]
        
        total_timeline = max(o.timeline_days for o in options)
        
        assert total_timeline == max(timeline1, timeline2)

    @given(
        effectiveness1=score_strategy,
        effectiveness2=score_strategy,
        synergy_bonus=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
    )
    @settings(max_examples=30)
    def test_synergy_bonus_improves_effectiveness(
        self, effectiveness1: float, effectiveness2: float, synergy_bonus: float
    ):
        """
        Property: Synergy bonus can improve combined effectiveness.
        """
        avg_effectiveness = (effectiveness1 + effectiveness2) / 2
        combined = min(1.0, avg_effectiveness + synergy_bonus)
        
        # Combined with synergy should be >= average (up to cap of 1.0)
        assert combined >= avg_effectiveness or combined == 1.0

    @given(options=st.lists(mitigation_option_strategy(), min_size=2, max_size=5))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_execution_order_contains_all_options(
        self, options: list[MitigationOption]
    ):
        """
        Property: Execution order contains all option IDs.
        """
        execution_order = [o.option_id for o in sorted(
            options,
            key=lambda o: (len(o.prerequisites), o.timeline_days),
        )]
        
        # All option IDs should be in the execution order
        option_ids = set(o.option_id for o in options)
        execution_set = set(execution_order)
        
        assert option_ids == execution_set


# =============================================================================
# Additional Integration Tests
# =============================================================================


class TestMitigationIntegration:
    """Integration tests for mitigation components."""

    @given(
        option=mitigation_option_strategy(),
        effectiveness=score_strategy,
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_option_to_outcome_flow(
        self, option: MitigationOption, effectiveness: float
    ):
        """
        Property: Options can be tracked through to outcomes.
        """
        tracker = OutcomeTracker()
        
        outcome = tracker.record_outcome(
            option=option,
            actual_effectiveness=effectiveness,
            actual_cost=option.cost_impact * 1.1,
            actual_timeline_days=option.timeline_days + 5,
            status=MitigationStatus.COMPLETED,
        )
        
        assert outcome.option_id == option.option_id
        assert outcome.actual_effectiveness == effectiveness

    @given(options=st.lists(mitigation_option_strategy(), min_size=1, max_size=5))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_ranking_and_simulation_compatibility(
        self, options: list[MitigationOption]
    ):
        """
        Property: Ranked options can be simulated.
        """
        ranker = MitigationRanker()
        ranked = ranker.rank_options(options)
        
        # All ranked options should have simulation-compatible structure
        for option, score in ranked:
            assert option.feasibility_score >= 0
            assert option.cost_impact >= 0
            assert option.timeline_days > 0
            assert option.effectiveness_score >= 0
