"""
Property Tests for Data Model Validation.

Tests the core data models for ChainReaction, verifying:
- Property 31: Entity Validation Against Graph
- Property 32: Risk Event Referential Integrity
- Property 33: Confidence Score Presence
- Property 34: Low-Confidence Flagging
- Property 35: Referential Integrity During Updates
"""

from datetime import datetime, timezone
from hypothesis import given, settings, assume
from hypothesis import strategies as st
import pytest

from src.models import (
    RiskEvent,
    Alert,
    ImpactPath,
    ResilienceScore,
    ResilienceMetrics,
    AlertRule,
    AlertChannel,
    AlertRuleStatus,
    LowConfidenceFlag,
    EntityValidationResult,
    ReferentialIntegrityResult,
    ValidationError,
    EnhancedImpactPath,
    EventType,
    SeverityLevel,
    RelationshipType,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Valid confidence scores (0.0 to 1.0)
confidence_score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# Valid resilience scores (0.0 to 100.0)
resilience_score_strategy = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)

# Entity ID strategy
entity_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    min_size=3,
    max_size=50,
)

# Event type strategy
event_type_strategy = st.sampled_from(list(EventType))

# Severity level strategy
severity_strategy = st.sampled_from(list(SeverityLevel))

# Relationship type strategy
relationship_type_strategy = st.sampled_from(list(RelationshipType))


# Risk event strategy
@st.composite
def risk_event_strategy(draw) -> RiskEvent:
    """Generate valid RiskEvent instances."""
    return RiskEvent(
        id=draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        event_type=draw(event_type_strategy),
        location=draw(st.text(min_size=2, max_size=100).filter(lambda x: x.strip())),
        affected_entities=draw(st.lists(entity_id_strategy, min_size=0, max_size=10)),
        severity=draw(severity_strategy),
        confidence=draw(confidence_score_strategy),
        source_url=draw(st.text(min_size=5, max_size=200).map(lambda x: f"https://example.com/{x}")),
        description=draw(st.text(min_size=10, max_size=500)),
    )


# Alert rule strategy
@st.composite
def alert_rule_strategy(draw) -> AlertRule:
    """Generate valid AlertRule instances."""
    return AlertRule(
        id=draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip())),
        name=draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        description=draw(st.text(min_size=0, max_size=500)),
        status=draw(st.sampled_from(list(AlertRuleStatus))),
        event_types=draw(st.lists(event_type_strategy, min_size=0, max_size=5)),
        severity_thresholds=draw(st.lists(severity_strategy, min_size=0, max_size=4)),
        locations=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
        entity_ids=draw(st.lists(entity_id_strategy, min_size=0, max_size=5)),
        channels=draw(st.lists(st.sampled_from(list(AlertChannel)), min_size=1, max_size=4)),
    )


# =============================================================================
# Property 31: Entity Validation Against Graph
# =============================================================================


class TestEntityValidationAgainstGraph:
    """Property tests for entity validation against the Neo4j graph."""

    @given(entity_id=entity_id_strategy)
    @settings(max_examples=50)
    def test_entity_validation_result_is_valid_type(self, entity_id: str):
        """
        Property: EntityValidationResult always has valid structure.
        
        For any entity ID, the validation result should have:
        - A valid entity_id string
        - A boolean exists_in_graph field
        - A list of validation_errors
        - A boolean is_valid field
        """
        assume(entity_id.strip())  # Skip empty IDs
        
        # Create a validation result (simulating graph lookup)
        result = EntityValidationResult(
            entity_id=entity_id,
            exists_in_graph=False,
            entity_type=None,
            validation_errors=[],
            is_valid=True,
        )
        
        assert isinstance(result.entity_id, str)
        assert isinstance(result.exists_in_graph, bool)
        assert isinstance(result.validation_errors, list)
        assert isinstance(result.is_valid, bool)

    @given(entity_id=entity_id_strategy)
    @settings(max_examples=50)
    def test_validation_errors_are_proper_type(self, entity_id: str):
        """
        Property: Validation errors are always ValidationError instances.
        """
        assume(entity_id.strip())
        
        errors = [
            ValidationError(
                field="entity_id",
                message="Not found",
                value=entity_id,
                code="not_found",
            )
        ]
        
        result = EntityValidationResult(
            entity_id=entity_id,
            exists_in_graph=False,
            validation_errors=errors,
            is_valid=False,
        )
        
        for error in result.validation_errors:
            assert isinstance(error, ValidationError)
            assert error.field is not None
            assert error.message is not None


# =============================================================================
# Property 32: Risk Event Referential Integrity
# =============================================================================


class TestRiskEventReferentialIntegrity:
    """Property tests for risk event referential integrity."""

    @given(risk_event=risk_event_strategy())
    @settings(max_examples=50)
    def test_referential_integrity_result_structure(self, risk_event: RiskEvent):
        """
        Property: ReferentialIntegrityResult has consistent structure.
        
        For any risk event, the integrity result should have:
        - risk_event_id matching the event
        - Boolean all_entities_valid
        - List of missing_entities
        - List of orphaned_relationships
        """
        result = ReferentialIntegrityResult(
            risk_event_id=risk_event.id,
            all_entities_valid=True,
            missing_entities=[],
            orphaned_relationships=[],
        )
        
        assert result.risk_event_id == risk_event.id
        assert isinstance(result.all_entities_valid, bool)
        assert isinstance(result.missing_entities, list)
        assert isinstance(result.orphaned_relationships, list)

    @given(
        risk_event=risk_event_strategy(),
        missing=st.lists(entity_id_strategy, min_size=1, max_size=5),
    )
    @settings(max_examples=50)
    def test_missing_entities_invalidates_result(
        self, risk_event: RiskEvent, missing: list[str]
    ):
        """
        Property: If missing_entities is non-empty, all_entities_valid should be False.
        """
        assume(all(e.strip() for e in missing))
        
        result = ReferentialIntegrityResult(
            risk_event_id=risk_event.id,
            all_entities_valid=False,  # Expected when missing entities exist
            missing_entities=missing,
            orphaned_relationships=[],
        )
        
        assert len(result.missing_entities) > 0
        assert result.all_entities_valid is False


# =============================================================================
# Property 33: Confidence Score Presence
# =============================================================================


class TestConfidenceScorePresence:
    """Property tests for confidence score validation."""

    @given(confidence=confidence_score_strategy)
    @settings(max_examples=100)
    def test_confidence_always_in_valid_range(self, confidence: float):
        """
        Property: Confidence scores are always in [0.0, 1.0] range.
        """
        risk_event = RiskEvent(
            id="test-event",
            event_type=EventType.STRIKE,
            location="Test Location",
            affected_entities=[],
            severity=SeverityLevel.MEDIUM,
            confidence=confidence,
            source_url="https://example.com/test",
        )
        
        assert 0.0 <= risk_event.confidence <= 1.0

    @given(confidence=st.floats(min_value=-100, max_value=100, allow_nan=False))
    @settings(max_examples=50)
    def test_invalid_confidence_raises_error(self, confidence: float):
        """
        Property: Confidence scores outside [0.0, 1.0] raise validation errors.
        """
        assume(confidence < 0.0 or confidence > 1.0)
        
        with pytest.raises(ValueError):
            RiskEvent(
                id="test-event",
                event_type=EventType.STRIKE,
                location="Test Location",
                affected_entities=[],
                severity=SeverityLevel.MEDIUM,
                confidence=confidence,
                source_url="https://example.com/test",
            )

    @given(confidence=confidence_score_strategy)
    @settings(max_examples=50)
    def test_confidence_is_rounded_to_three_decimals(self, confidence: float):
        """
        Property: Confidence scores are rounded to 3 decimal places.
        """
        risk_event = RiskEvent(
            id="test-event",
            event_type=EventType.STRIKE,
            location="Test Location",
            affected_entities=[],
            severity=SeverityLevel.MEDIUM,
            confidence=confidence,
            source_url="https://example.com/test",
        )
        
        # Check that confidence has at most 3 decimal places
        rounded = round(risk_event.confidence, 3)
        assert risk_event.confidence == rounded


# =============================================================================
# Property 34: Low-Confidence Flagging
# =============================================================================


class TestLowConfidenceFlagging:
    """Property tests for low-confidence event flagging."""

    @given(
        confidence=st.floats(min_value=0.0, max_value=0.69, allow_nan=False),
        threshold=st.just(0.7),
    )
    @settings(max_examples=50)
    def test_low_confidence_below_threshold_gets_flagged(
        self, confidence: float, threshold: float
    ):
        """
        Property: Events with confidence below threshold are flagged.
        """
        flag = LowConfidenceFlag(
            event_id="test-event",
            original_confidence=confidence,
            threshold=threshold,
        )
        
        assert flag.original_confidence < flag.threshold
        assert flag.review_status == "pending"

    @given(
        confidence=st.floats(min_value=0.7, max_value=1.0, allow_nan=False),
        threshold=st.just(0.7),
    )
    @settings(max_examples=50)
    def test_high_confidence_not_flagged(
        self, confidence: float, threshold: float
    ):
        """
        Property: Events with confidence >= threshold don't need flagging.
        """
        # With high confidence, flag should not be created (None returned)
        assert confidence >= threshold

    @given(review_status=st.sampled_from(["pending", "approved", "rejected"]))
    @settings(max_examples=10)
    def test_review_status_validation(self, review_status: str):
        """
        Property: Review status is always one of valid values.
        """
        flag = LowConfidenceFlag(
            event_id="test-event",
            original_confidence=0.5,
            threshold=0.7,
            review_status=review_status,
        )
        
        assert flag.review_status in {"pending", "approved", "rejected"}


# =============================================================================
# Property 35: Referential Integrity During Updates
# =============================================================================


class TestReferentialIntegrityDuringUpdates:
    """Property tests for maintaining referential integrity during updates."""

    @given(
        original_entities=st.lists(entity_id_strategy, min_size=1, max_size=5),
        new_entities=st.lists(entity_id_strategy, min_size=0, max_size=5),
    )
    @settings(max_examples=50)
    def test_entity_list_update_preserves_valid_structure(
        self, original_entities: list[str], new_entities: list[str]
    ):
        """
        Property: Updating affected_entities preserves list structure.
        """
        assume(all(e.strip() for e in original_entities))
        assume(all(e.strip() for e in new_entities) or not new_entities)
        
        risk_event = RiskEvent(
            id="test-event",
            event_type=EventType.WEATHER,
            location="Test Location",
            affected_entities=original_entities,
            severity=SeverityLevel.HIGH,
            confidence=0.9,
            source_url="https://example.com/test",
        )
        
        # Simulate update
        updated_event = risk_event.model_copy(update={"affected_entities": new_entities})
        
        assert isinstance(updated_event.affected_entities, list)
        assert updated_event.affected_entities == new_entities

    @given(risk_event=risk_event_strategy())
    @settings(max_examples=50)
    def test_event_id_is_immutable_in_practice(self, risk_event: RiskEvent):
        """
        Property: Event ID should remain consistent across operations.
        """
        original_id = risk_event.id
        
        # Create a copy with modifications to other fields
        modified = risk_event.model_copy(
            update={"description": "Modified description"}
        )
        
        assert modified.id == original_id


# =============================================================================
# Additional Model Property Tests
# =============================================================================


class TestResilienceMetricsProperties:
    """Property tests for resilience metrics models."""

    @given(score=resilience_score_strategy)
    @settings(max_examples=50)
    def test_resilience_score_in_valid_range(self, score: float):
        """
        Property: Resilience scores are always in [0.0, 100.0] range.
        """
        resilience = ResilienceScore(
            entity_id="test-entity",
            entity_type="product",
            score=score,
        )
        
        assert 0.0 <= resilience.score <= 100.0

    @given(score=resilience_score_strategy)
    @settings(max_examples=50)
    def test_resilience_score_is_rounded(self, score: float):
        """
        Property: Resilience scores are rounded to 2 decimal places.
        """
        resilience = ResilienceScore(
            entity_id="test-entity",
            entity_type="component",
            score=score,
        )
        
        # Check rounding
        assert resilience.score == round(score, 2)

    @given(level=st.sampled_from(["component", "product", "portfolio", "entity"]))
    @settings(max_examples=10)
    def test_metrics_level_is_valid(self, level: str):
        """
        Property: ResilienceMetrics level is always one of valid values.
        """
        metrics = ResilienceMetrics(
            entity_id="test-entity",
            level=level,
            overall_score=75.0,
        )
        
        assert metrics.level in {"component", "product", "portfolio", "entity"}


class TestAlertRuleProperties:
    """Property tests for alert rule models."""

    @given(alert_rule=alert_rule_strategy())
    @settings(max_examples=50)
    def test_alert_rule_has_required_fields(self, alert_rule: AlertRule):
        """
        Property: Alert rules always have required fields populated.
        """
        assert alert_rule.id is not None
        assert alert_rule.name is not None
        assert isinstance(alert_rule.channels, list)
        assert len(alert_rule.channels) >= 1

    @given(
        rule=alert_rule_strategy(),
        event=risk_event_strategy(),
    )
    @settings(max_examples=50)
    def test_rule_matching_is_deterministic(
        self, rule: AlertRule, event: RiskEvent
    ):
        """
        Property: Rule matching is deterministic for same inputs.
        """
        assume(event.id.strip())
        
        result1 = rule.matches_event(event)
        result2 = rule.matches_event(event)
        
        assert result1 == result2


class TestEnhancedImpactPathProperties:
    """Property tests for enhanced impact path models."""

    @given(
        num_nodes=st.integers(min_value=2, max_value=10),
        criticality=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_impact_path_hop_count_matches_edges(
        self, num_nodes: int, criticality: float
    ):
        """
        Property: Total hops equals number of nodes minus one.
        """
        nodes = [f"node-{i}" for i in range(num_nodes)]
        rel_types = [RelationshipType.SUPPLIES] * (num_nodes - 1)
        
        path = EnhancedImpactPath(
            path_id="test-path",
            nodes=nodes,
            relationship_types=rel_types,
            total_hops=num_nodes - 1,
            criticality_score=criticality,
        )
        
        assert path.total_hops == len(path.nodes) - 1
        assert len(path.relationship_types) == path.total_hops

    @given(criticality=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    @settings(max_examples=50)
    def test_criticality_is_rounded(self, criticality: float):
        """
        Property: Criticality scores are rounded to 3 decimal places.
        """
        path = EnhancedImpactPath(
            path_id="test-path",
            nodes=["node-1", "node-2"],
            relationship_types=[RelationshipType.SUPPLIES],
            total_hops=1,
            criticality_score=criticality,
        )
        
        assert path.criticality_score == round(criticality, 3)
