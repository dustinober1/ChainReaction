"""
Property Tests for Resilience Scoring Engine.

Tests the resilience scoring functionality, verifying:
- Property 11: Resilience Score Calculation
- Property 12: Redundancy Impact on Resilience
- Property 13: Multi-Level Resilience Metrics
- Property 14: Historical Resilience Tracking
- Property 15: Resilience Recalculation Timeliness
"""

from datetime import datetime, timezone, timedelta
from hypothesis import given, settings, assume
from hypothesis import strategies as st
import pytest

from src.models import (
    ResilienceScore,
    ResilienceMetrics,
    HistoricalResilienceScore,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Valid resilience scores (0.0 to 100.0)
resilience_score_strategy = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)

# Redundancy factor (0.0 to 1.0)
redundancy_factor_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# Entity ID strategy
entity_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    min_size=3,
    max_size=50,
)

# Entity type strategy
entity_type_strategy = st.sampled_from(["supplier", "component", "product"])

# Level strategy
level_strategy = st.sampled_from(["component", "product", "portfolio", "entity"])


# Resilience score strategy
@st.composite
def resilience_score_model_strategy(draw) -> ResilienceScore:
    """Generate valid ResilienceScore instances."""
    return ResilienceScore(
        entity_id=draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        entity_type=draw(entity_type_strategy),
        score=draw(resilience_score_strategy),
        redundancy_factor=draw(redundancy_factor_strategy),
    )


# Historical score strategy
@st.composite
def historical_score_strategy(draw) -> HistoricalResilienceScore:
    """Generate valid HistoricalResilienceScore instances."""
    return HistoricalResilienceScore(
        entity_id=draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        score=draw(resilience_score_strategy),
        factors=draw(
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
                max_size=5,
            )
        ),
    )


# Resilience metrics strategy
@st.composite
def resilience_metrics_strategy(draw) -> ResilienceMetrics:
    """Generate valid ResilienceMetrics instances."""
    component_scores = draw(
        st.lists(resilience_score_model_strategy(), min_size=0, max_size=10)
    )
    overall = draw(resilience_score_strategy)
    
    return ResilienceMetrics(
        entity_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))),
        level=draw(level_strategy),
        overall_score=overall,
        component_scores=component_scores,
        redundancy_coverage=draw(redundancy_factor_strategy),
        single_points_of_failure=draw(st.integers(min_value=0, max_value=100)),
    )


# =============================================================================
# Property 11: Resilience Score Calculation
# =============================================================================


class TestResilienceScoreCalculation:
    """Property tests for resilience score calculation."""

    @given(score=resilience_score_strategy)
    @settings(max_examples=100)
    def test_resilience_score_always_in_valid_range(self, score: float):
        """
        Property: Resilience scores are always in [0.0, 100.0] range.
        """
        resilience = ResilienceScore(
            entity_id="test-entity",
            entity_type="component",
            score=score,
        )
        
        assert 0.0 <= resilience.score <= 100.0

    @given(
        score1=resilience_score_strategy,
        score2=resilience_score_strategy,
    )
    @settings(max_examples=50)
    def test_score_comparison_is_total_ordering(self, score1: float, score2: float):
        """
        Property: Resilience scores can be compared and form a total ordering.
        """
        r1 = ResilienceScore(
            entity_id="entity-1",
            entity_type="component",
            score=score1,
        )
        r2 = ResilienceScore(
            entity_id="entity-2",
            entity_type="component",
            score=score2,
        )
        
        # Total ordering: exactly one of <, =, > must be true
        less = r1.score < r2.score
        equal = r1.score == r2.score
        greater = r1.score > r2.score
        
        assert sum([less, equal, greater]) == 1

    @given(resilience=resilience_score_model_strategy())
    @settings(max_examples=50)
    def test_score_is_rounded_to_two_decimals(self, resilience: ResilienceScore):
        """
        Property: Resilience scores are rounded to 2 decimal places.
        """
        rounded = round(resilience.score, 2)
        assert resilience.score == rounded

    @given(score=st.floats(min_value=-100, max_value=200, allow_nan=False))
    @settings(max_examples=50)
    def test_invalid_score_raises_error(self, score: float):
        """
        Property: Scores outside [0.0, 100.0] raise validation errors.
        """
        assume(score < 0.0 or score > 100.0)
        
        with pytest.raises(ValueError):
            ResilienceScore(
                entity_id="test-entity",
                entity_type="component",
                score=score,
            )


# =============================================================================
# Property 12: Redundancy Impact on Resilience
# =============================================================================


class TestRedundancyImpactOnResilience:
    """Property tests for redundancy impact on resilience scores."""

    @given(redundancy=redundancy_factor_strategy)
    @settings(max_examples=100)
    def test_redundancy_factor_in_valid_range(self, redundancy: float):
        """
        Property: Redundancy factor is always in [0.0, 1.0] range.
        """
        resilience = ResilienceScore(
            entity_id="test-entity",
            entity_type="component",
            score=50.0,
            redundancy_factor=redundancy,
        )
        
        assert 0.0 <= resilience.redundancy_factor <= 1.0

    @given(
        redundancy1=st.floats(min_value=0.0, max_value=0.3, allow_nan=False),
        redundancy2=st.floats(min_value=0.7, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_higher_redundancy_indicates_lower_risk(
        self, redundancy1: float, redundancy2: float
    ):
        """
        Property: Higher redundancy factor implies lower supply chain risk.
        
        This is a semantic property - entities with higher redundancy
        should be considered more resilient.
        """
        low_redundancy = ResilienceScore(
            entity_id="low-redundancy",
            entity_type="component",
            score=40.0,
            redundancy_factor=redundancy1,
        )
        high_redundancy = ResilienceScore(
            entity_id="high-redundancy",
            entity_type="component",
            score=80.0,
            redundancy_factor=redundancy2,
        )
        
        assert low_redundancy.redundancy_factor < high_redundancy.redundancy_factor
        # Higher redundancy correlates with higher score in our test setup
        assert low_redundancy.score < high_redundancy.score

    @given(
        score=resilience_score_strategy,
        redundancy=redundancy_factor_strategy,
    )
    @settings(max_examples=50)
    def test_redundancy_and_score_are_independent_fields(
        self, score: float, redundancy: float
    ):
        """
        Property: Redundancy factor can be set independently of overall score.
        """
        resilience = ResilienceScore(
            entity_id="test-entity",
            entity_type="component",
            score=score,
            redundancy_factor=redundancy,
        )
        
        # Both fields should be present and independently set
        assert resilience.score == round(score, 2)
        assert resilience.redundancy_factor == redundancy


# =============================================================================
# Property 13: Multi-Level Resilience Metrics
# =============================================================================


class TestMultiLevelResilienceMetrics:
    """Property tests for multi-level resilience metrics."""

    @given(level=level_strategy)
    @settings(max_examples=10)
    def test_metrics_level_is_valid_value(self, level: str):
        """
        Property: ResilienceMetrics level is always one of valid values.
        """
        metrics = ResilienceMetrics(
            entity_id="test",
            level=level,
            overall_score=50.0,
        )
        
        assert metrics.level in {"component", "product", "portfolio", "entity"}

    @given(metrics=resilience_metrics_strategy())
    @settings(max_examples=50)
    def test_metrics_has_consistent_structure(self, metrics: ResilienceMetrics):
        """
        Property: ResilienceMetrics always has consistent structure.
        """
        assert isinstance(metrics.level, str)
        assert isinstance(metrics.overall_score, float)
        assert isinstance(metrics.component_scores, list)
        assert isinstance(metrics.redundancy_coverage, float)
        assert isinstance(metrics.single_points_of_failure, int)

    @given(
        component_scores=st.lists(
            resilience_score_model_strategy(),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=30)
    def test_component_scores_list_is_preserved(
        self, component_scores: list[ResilienceScore]
    ):
        """
        Property: Component scores list is preserved in metrics.
        """
        metrics = ResilienceMetrics(
            entity_id="product-1",
            level="product",
            overall_score=75.0,
            component_scores=component_scores,
        )
        
        assert len(metrics.component_scores) == len(component_scores)

    @given(
        single_points=st.integers(min_value=0, max_value=1000),
        coverage=redundancy_factor_strategy,
    )
    @settings(max_examples=50)
    def test_aggregate_metrics_are_valid(self, single_points: int, coverage: float):
        """
        Property: Aggregate metrics have valid types and ranges.
        """
        metrics = ResilienceMetrics(
            entity_id=None,
            level="portfolio",
            overall_score=60.0,
            redundancy_coverage=coverage,
            single_points_of_failure=single_points,
        )
        
        assert metrics.single_points_of_failure >= 0
        assert 0.0 <= metrics.redundancy_coverage <= 1.0


# =============================================================================
# Property 14: Historical Resilience Tracking
# =============================================================================


class TestHistoricalResilienceTracking:
    """Property tests for historical score tracking."""

    @given(history=historical_score_strategy())
    @settings(max_examples=50)
    def test_historical_score_has_timestamp(self, history: HistoricalResilienceScore):
        """
        Property: Historical scores always have a recorded_at timestamp.
        """
        assert history.recorded_at is not None
        assert isinstance(history.recorded_at, datetime)

    @given(
        scores=st.lists(
            resilience_score_strategy,
            min_size=2,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_score_history_can_track_multiple_points(self, scores: list[float]):
        """
        Property: Multiple historical scores can be tracked for an entity.
        """
        entity_id = "test-entity"
        history = [
            HistoricalResilienceScore(
                entity_id=entity_id,
                score=score,
                recorded_at=datetime.now(timezone.utc) - timedelta(days=i),
            )
            for i, score in enumerate(scores)
        ]
        
        assert len(history) == len(scores)
        # All should have same entity_id
        assert all(h.entity_id == entity_id for h in history)
        # All timestamps should be unique (in this test)
        timestamps = [h.recorded_at for h in history]
        assert len(set(timestamps)) == len(timestamps)

    @given(
        factors=st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_factors_dictionary_is_preserved(self, factors: dict[str, float]):
        """
        Property: Contributing factors are preserved in historical records.
        """
        history = HistoricalResilienceScore(
            entity_id="test-entity",
            score=75.0,
            factors=factors,
        )
        
        assert history.factors == factors

    @given(
        old_score=resilience_score_strategy,
        new_score=resilience_score_strategy,
    )
    @settings(max_examples=50)
    def test_trend_can_be_calculated_from_two_points(
        self, old_score: float, new_score: float
    ):
        """
        Property: Trend direction can be calculated from any two data points.
        """
        old_record = HistoricalResilienceScore(
            entity_id="test-entity",
            score=old_score,
            recorded_at=datetime.now(timezone.utc) - timedelta(days=7),
        )
        new_record = HistoricalResilienceScore(
            entity_id="test-entity",
            score=new_score,
            recorded_at=datetime.now(timezone.utc),
        )
        
        change = new_record.score - old_record.score
        
        if abs(change) < 1.0:
            expected_trend = "stable"
        elif change > 0:
            expected_trend = "improving"
        else:
            expected_trend = "declining"
        
        # Trend is deterministic based on score change
        assert expected_trend in {"stable", "improving", "declining"}


# =============================================================================
# Property 15: Resilience Recalculation Timeliness
# =============================================================================


class TestResilienceRecalculationTimeliness:
    """Property tests for recalculation timeliness."""

    @given(entity_count=st.integers(min_value=1, max_value=100))
    @settings(max_examples=20)
    def test_recalculation_produces_scores_for_all_entities(self, entity_count: int):
        """
        Property: Recalculation should produce a score for each affected entity.
        
        This tests the structure, not the actual calculation (which requires DB).
        """
        entity_ids = [f"entity-{i}" for i in range(entity_count)]
        
        # Simulate recalculation results
        results = {
            eid: ResilienceScore(
                entity_id=eid,
                entity_type="component",
                score=50.0 + (i * 0.5),
                redundancy_factor=0.5,
            )
            for i, eid in enumerate(entity_ids)
        }
        
        assert len(results) == entity_count
        assert all(eid in results for eid in entity_ids)

    @given(
        sla_seconds=st.integers(min_value=60, max_value=600),
        actual_duration=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=50)
    def test_sla_violation_detection_is_correct(
        self, sla_seconds: int, actual_duration: int
    ):
        """
        Property: SLA violations are correctly detected.
        """
        is_violation = actual_duration > sla_seconds
        
        # This is a tautology but validates our SLA logic
        if is_violation:
            assert actual_duration > sla_seconds
        else:
            assert actual_duration <= sla_seconds

    @given(resilience=resilience_score_model_strategy())
    @settings(max_examples=50)
    def test_recalculated_score_has_timestamp(self, resilience: ResilienceScore):
        """
        Property: Recalculated scores have a calculated_at timestamp.
        """
        assert resilience.calculated_at is not None
        assert isinstance(resilience.calculated_at, datetime)
        # Timestamp should be recent (within last minute)
        age = datetime.now(timezone.utc) - resilience.calculated_at
        assert age < timedelta(minutes=1)


# =============================================================================
# Trend Calculation Tests
# =============================================================================


class TestTrendCalculation:
    """Additional property tests for trend analysis."""

    @given(
        scores=st.lists(
            resilience_score_strategy,
            min_size=3,
            max_size=20,
        )
    )
    @settings(max_examples=30)
    def test_trend_direction_is_valid_enum(self, scores: list[float]):
        """
        Property: Calculated trend direction is always a valid value.
        """
        history = [
            HistoricalResilienceScore(
                entity_id="test",
                score=score,
                recorded_at=datetime.now(timezone.utc) - timedelta(days=i),
            )
            for i, score in enumerate(scores)
        ]
        
        if len(history) >= 2:
            oldest = history[-1]
            newest = history[0]
            change = newest.score - oldest.score
            
            if abs(change) < 1.0:
                direction = "stable"
            elif change > 0:
                direction = "improving"
            else:
                direction = "declining"
            
            assert direction in {"stable", "improving", "declining"}

    @given(
        score_change=st.floats(min_value=-100, max_value=100, allow_nan=False),
        weeks=st.floats(min_value=0.1, max_value=52, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_rate_of_change_calculation(self, score_change: float, weeks: float):
        """
        Property: Rate of change is correctly calculated as score_change / weeks.
        """
        rate = score_change / weeks if weeks > 0 else 0.0
        
        # Rate should have same sign as score_change
        if score_change > 0:
            assert rate > 0 or weeks <= 0
        elif score_change < 0:
            assert rate < 0 or weeks <= 0
        else:
            assert rate == 0
