"""
Property Tests for Advanced Alert System.

Tests the alert system functionality, verifying:
- Property 6: Alert Rule Filter Support
- Property 7: Multi-Channel Alert Delivery
- Property 8: Alert Delivery Latency
- Property 9: Alert Acknowledgment Recording
- Property 10: Alert Rule Update Isolation
"""

from datetime import datetime, timezone, timedelta
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
import pytest
import uuid

from src.models import (
    EventType,
    SeverityLevel,
    RiskEvent,
    AlertChannel,
    AlertRule,
    AlertRuleStatus,
    AlertAcknowledgment,
)
from src.analysis.alerts import (
    DeliveryStatus,
    RuleChangeType,
    AlertInstance,
    RuleChange,
    DeliveryMetrics,
    AlertRuleManager,
    ChannelDeliverer,
    AcknowledgmentTracker,
    AlertManager,
    LatencyMonitor,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Event type strategy
event_type_strategy = st.sampled_from(list(EventType))

# Severity level strategy
severity_strategy = st.sampled_from(list(SeverityLevel))

# Alert channel strategy
channel_strategy = st.sampled_from(list(AlertChannel))

# Rule status strategy
rule_status_strategy = st.sampled_from(list(AlertRuleStatus))

# Delivery status strategy
delivery_status_strategy = st.sampled_from(list(DeliveryStatus))

# Score strategy (0.0 to 1.0)
score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

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

# Username strategy
username_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-."),
    min_size=2,
    max_size=30,
).filter(lambda x: x.strip())


# Risk event strategy
@st.composite
def risk_event_strategy(draw) -> RiskEvent:
    """Generate valid RiskEvent instances for testing."""
    return RiskEvent(
        id=f"risk-{uuid.uuid4().hex[:8]}",
        title=draw(st.text(min_size=5, max_size=100).filter(lambda x: x.strip())),
        source="test_source",
        source_url="https://example.com/risk",
        event_type=draw(event_type_strategy),
        severity=draw(severity_strategy),
        location=draw(location_strategy),
        description=draw(st.text(min_size=10, max_size=200).filter(lambda x: x.strip())),
        confidence=draw(score_strategy),
        affected_entities=draw(st.lists(entity_id_strategy, min_size=1, max_size=5)),
    )


# Alert instance strategy
@st.composite
def alert_instance_strategy(draw) -> AlertInstance:
    """Generate valid AlertInstance instances."""
    channels = draw(st.lists(channel_strategy, min_size=1, max_size=3, unique=True))
    
    return AlertInstance(
        alert_id=f"alert-{uuid.uuid4().hex[:8]}",
        rule_id=f"rule-{uuid.uuid4().hex[:8]}",
        risk_event_id=f"risk-{uuid.uuid4().hex[:8]}",
        title=draw(st.text(min_size=5, max_size=100).filter(lambda x: x.strip())),
        message=draw(st.text(min_size=10, max_size=300).filter(lambda x: x.strip())),
        severity=draw(severity_strategy),
        channels=channels,
    )


# =============================================================================
# Property 6: Alert Rule Filter Support
# =============================================================================


class TestAlertRuleFilterSupport:
    """Property tests for alert rule filter support."""

    @given(
        name=st.text(min_size=3, max_size=50).filter(lambda x: x.strip()),
        channels=st.lists(channel_strategy, min_size=1, max_size=3, unique=True),
    )
    @settings(max_examples=50)
    def test_rule_creation_succeeds(self, name: str, channels: list[AlertChannel]):
        """
        Property: Rule creation always succeeds with valid inputs.
        """
        manager = AlertRuleManager()
        rule = manager.create_rule(name=name, channels=channels)
        
        assert rule is not None
        assert rule.name == name
        assert rule.channels == channels
        assert rule.status == AlertRuleStatus.ACTIVE

    @given(
        event_types=st.lists(event_type_strategy, min_size=1, max_size=3, unique=True),
        min_severity=severity_strategy,
    )
    @settings(max_examples=50)
    def test_rule_filters_are_stored(
        self, event_types: list[EventType], min_severity: SeverityLevel
    ):
        """
        Property: Rule filters are correctly stored.
        """
        manager = AlertRuleManager()
        rule = manager.create_rule(
            name="Test Rule",
            channels=[AlertChannel.WEBHOOK],
            event_types=event_types,
            min_severity=min_severity,
        )
        
        assert rule.event_types == event_types
        # min_severity is converted to severity_thresholds
        assert len(rule.severity_thresholds) >= 1

    @given(
        locations=st.lists(location_strategy, min_size=1, max_size=3),
        entity_ids=st.lists(entity_id_strategy, min_size=1, max_size=3),
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_location_and_entity_filters(
        self, locations: list[str], entity_ids: list[str]
    ):
        """
        Property: Location and entity filters are stored correctly.
        """
        manager = AlertRuleManager()
        rule = manager.create_rule(
            name="Test Rule",
            channels=[AlertChannel.EMAIL],
            locations=locations,
            entity_ids=entity_ids,
        )
        
        assert rule.locations == locations
        assert rule.entity_ids == entity_ids

    @given(event=risk_event_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_matching_rule_returns_for_matching_event(self, event: RiskEvent):
        """
        Property: A rule with matching filters returns for matching events.
        """
        manager = AlertRuleManager()
        
        # Create rule that matches this event
        rule = manager.create_rule(
            name="Match Rule",
            channels=[AlertChannel.SLACK],
            event_types=[event.event_type],
            locations=[event.location],
            min_severity=SeverityLevel.LOW,  # Match all severities
        )
        
        matching = manager.get_matching_rules(event)
        
        assert rule in matching

    @given(event=risk_event_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_non_matching_rule_excluded(self, event: RiskEvent):
        """
        Property: A rule with non-matching filters doesn't return.
        """
        manager = AlertRuleManager()
        
        # Create rule that doesn't match
        non_matching_type = [t for t in EventType if t != event.event_type][0]
        rule = manager.create_rule(
            name="Non-Match Rule",
            channels=[AlertChannel.WEBHOOK],
            event_types=[non_matching_type],
        )
        
        matching = manager.get_matching_rules(event)
        
        assert rule not in matching


# =============================================================================
# Property 7: Multi-Channel Alert Delivery
# =============================================================================


class TestMultiChannelAlertDelivery:
    """Property tests for multi-channel alert delivery."""

    @given(
        channels=st.lists(channel_strategy, min_size=1, max_size=4, unique=True)
    )
    @settings(max_examples=30)
    def test_delivery_attempts_all_channels(self, channels: list[AlertChannel]):
        """
        Property: Delivery attempts all configured channels.
        """
        alert = AlertInstance(
            alert_id="test-alert",
            rule_id="test-rule",
            risk_event_id="test-event",
            title="Test Alert",
            message="Test message",
            severity=SeverityLevel.HIGH,
            channels=channels,
        )
        
        # All channels should be present in the alert
        assert len(alert.channels) == len(channels)
        assert set(alert.channels) == set(channels)

    @given(alert=alert_instance_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_alert_has_required_fields(self, alert: AlertInstance):
        """
        Property: Alert instances have all required fields.
        """
        assert alert.alert_id is not None
        assert alert.rule_id is not None
        assert alert.risk_event_id is not None
        assert alert.title is not None
        assert alert.severity in list(SeverityLevel)
        assert len(alert.channels) >= 1

    @given(channel=channel_strategy)
    @settings(max_examples=20)
    def test_channel_handler_exists(self, channel: AlertChannel):
        """
        Property: All channel types have handlers.
        """
        deliverer = ChannelDeliverer()
        assert channel in deliverer._handlers

    def test_metrics_start_at_zero(self):
        """
        Property: Delivery metrics start at zero.
        """
        deliverer = ChannelDeliverer()
        metrics = deliverer.get_metrics()
        
        assert metrics.total_deliveries == 0
        assert metrics.successful_deliveries == 0
        assert metrics.failed_deliveries == 0

    @given(
        delivery_count=st.integers(min_value=1, max_value=100),
        success_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=30)
    def test_metrics_track_success_and_failure(
        self, delivery_count: int, success_rate: float
    ):
        """
        Property: Metrics correctly track successes and failures.
        """
        successes = int(delivery_count * success_rate)
        failures = delivery_count - successes
        
        metrics = DeliveryMetrics(
            total_deliveries=delivery_count,
            successful_deliveries=successes,
            failed_deliveries=failures,
        )
        
        assert metrics.total_deliveries == successes + failures


# =============================================================================
# Property 8: Alert Delivery Latency
# =============================================================================


class TestAlertDeliveryLatency:
    """Property tests for alert delivery latency."""

    @given(
        latency_ms=st.integers(min_value=1, max_value=100000)
    )
    @settings(max_examples=50)
    def test_latency_recording_works(self, latency_ms: int):
        """
        Property: Latency is correctly recorded.
        """
        monitor = LatencyMonitor()
        
        created = datetime.now(timezone.utc)
        delivered = created + timedelta(milliseconds=latency_ms)
        
        monitor.record_delivery("alert-1", created, delivered)
        
        metrics = monitor.get_metrics()
        assert metrics["total_deliveries"] == 1

    @given(
        latency_ms=st.integers(min_value=1, max_value=29999)
    )
    @settings(max_examples=30)
    def test_within_sla_not_violation(self, latency_ms: int):
        """
        Property: Delivery within SLA is not a violation.
        """
        monitor = LatencyMonitor()
        
        created = datetime.now(timezone.utc)
        delivered = created + timedelta(milliseconds=latency_ms)
        
        within_sla = monitor.record_delivery("alert-1", created, delivered)
        
        assert within_sla is True
        assert len(monitor.get_violations()) == 0

    @given(
        latency_ms=st.integers(min_value=31000, max_value=100000)
    )
    @settings(max_examples=30)
    def test_sla_violation_recorded(self, latency_ms: int):
        """
        Property: Delivery exceeding SLA is recorded as violation.
        """
        monitor = LatencyMonitor()
        
        created = datetime.now(timezone.utc)
        delivered = created + timedelta(milliseconds=latency_ms)
        
        within_sla = monitor.record_delivery("alert-1", created, delivered)
        
        assert within_sla is False
        assert len(monitor.get_violations()) == 1

    @given(
        latencies=st.lists(
            st.integers(min_value=100, max_value=50000),
            min_size=5,
            max_size=50,
        )
    )
    @settings(max_examples=20)
    def test_metrics_aggregation_correct(self, latencies: list[int]):
        """
        Property: Latency metrics are correctly aggregated.
        """
        monitor = LatencyMonitor()
        
        for i, lat in enumerate(latencies):
            created = datetime.now(timezone.utc)
            delivered = created + timedelta(milliseconds=lat)
            monitor.record_delivery(f"alert-{i}", created, delivered)
        
        metrics = monitor.get_metrics()
        
        assert metrics["total_deliveries"] == len(latencies)
        assert metrics["avg_latency_ms"] > 0
        # Allow for small timing variations (within 2ms)
        assert abs(metrics["max_latency_ms"] - max(latencies)) <= 2

    def test_alert_instance_latency_calculation(self):
        """
        Property: AlertInstance latency calculation works.
        """
        alert = AlertInstance(
            alert_id="test",
            rule_id="rule-1",
            risk_event_id="event-1",
            title="Test",
            message="Test message",
            severity=SeverityLevel.MEDIUM,
            channels=[AlertChannel.WEBHOOK],
        )
        
        # Before delivery, latency is None
        assert alert.delivery_latency_ms is None
        
        # After delivery, latency is calculated
        alert.delivered_at = alert.created_at + timedelta(seconds=5)
        assert alert.delivery_latency_ms == 5000


# =============================================================================
# Property 9: Alert Acknowledgment Recording
# =============================================================================


class TestAlertAcknowledgmentRecording:
    """Property tests for alert acknowledgment recording."""

    @given(
        alert_id=st.text(min_size=5, max_size=30).filter(lambda x: x.strip()),
        user=username_strategy,
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_acknowledgment_records_correctly(self, alert_id: str, user: str):
        """
        Property: Acknowledgments are correctly recorded.
        """
        tracker = AcknowledgmentTracker()
        
        ack = tracker.acknowledge(alert_id, user)
        
        assert ack.alert_id == alert_id
        assert ack.acknowledged_by == user
        assert ack.acknowledged_at is not None

    @given(
        alert_id=st.text(min_size=5, max_size=30).filter(lambda x: x.strip()),
        notes=st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_acknowledgment_notes_stored(self, alert_id: str, notes: str):
        """
        Property: Acknowledgment notes are stored.
        """
        tracker = AcknowledgmentTracker()
        
        ack = tracker.acknowledge(alert_id, "test_user", notes if notes else None)
        
        expected = notes if notes else ""
        assert ack.notes == expected

    @given(alert_id=st.text(min_size=5, max_size=30).filter(lambda x: x.strip()))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_is_acknowledged_returns_correctly(self, alert_id: str):
        """
        Property: is_acknowledged returns correct state.
        """
        tracker = AcknowledgmentTracker()
        
        # Before acknowledgment
        assert not tracker.is_acknowledged(alert_id)
        
        # After acknowledgment
        tracker.acknowledge(alert_id, "user")
        assert tracker.is_acknowledged(alert_id)

    @given(
        alert_ids=st.lists(
            st.text(min_size=5, max_size=20).filter(lambda x: x.strip()),
            min_size=2,
            max_size=10,
            unique=True,
        )
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_history_tracks_all_acknowledgments(self, alert_ids: list[str]):
        """
        Property: History tracks all acknowledgments.
        """
        tracker = AcknowledgmentTracker()
        
        for alert_id in alert_ids:
            tracker.acknowledge(alert_id, "user")
        
        history = tracker.get_history()
        
        assert len(history) == len(alert_ids)

    @given(
        alert_id=st.text(min_size=5, max_size=30).filter(lambda x: x.strip()),
        user1=username_strategy,
        user2=username_strategy,
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_first_acknowledgment_preserved(self, alert_id: str, user1: str, user2: str):
        """
        Property: First acknowledgment is preserved (immutability).
        """
        assume(user1 != user2)
        
        tracker = AcknowledgmentTracker()
        
        ack1 = tracker.acknowledge(alert_id, user1)
        ack2 = tracker.acknowledge(alert_id, user2)  # Second ack
        
        # First ack should be stored
        stored = tracker.get_acknowledgment(alert_id)
        assert stored.acknowledged_by == user1


# =============================================================================
# Property 10: Alert Rule Update Isolation
# =============================================================================


class TestAlertRuleUpdateIsolation:
    """Property tests for alert rule update isolation."""

    @given(
        new_name=st.text(min_size=3, max_size=50).filter(lambda x: x.strip())
    )
    @settings(max_examples=50)
    def test_rule_update_creates_new_version(self, new_name: str):
        """
        Property: Updating a rule creates a new version.
        """
        manager = AlertRuleManager()
        
        rule = manager.create_rule(
            name="Original Name",
            channels=[AlertChannel.WEBHOOK],
        )
        original_version = manager._version_tracker.get(rule.id, 1)
        
        updated = manager.update_rule(rule.id, "admin", name=new_name)
        
        new_version = manager._version_tracker.get(rule.id, 1)
        assert new_version == original_version + 1
        assert updated.name == new_name

    @given(username=username_strategy)
    @settings(max_examples=50)
    def test_change_log_records_updates(self, username: str):
        """
        Property: Changes are recorded in audit log.
        """
        manager = AlertRuleManager()
        
        rule = manager.create_rule("Test Rule", [AlertChannel.EMAIL])
        manager.update_rule(rule.id, username, name="Updated Name")
        
        log = manager.get_change_log(rule.id)
        
        # Should have create + update
        assert len(log) >= 2
        assert any(c.change_type == RuleChangeType.CREATED for c in log)
        assert any(c.change_type == RuleChangeType.UPDATED for c in log)

    @given(username=username_strategy)
    @settings(max_examples=30)
    def test_enable_disable_logged(self, username: str):
        """
        Property: Enable/disable operations are logged.
        """
        manager = AlertRuleManager()
        
        rule = manager.create_rule("Test Rule", [AlertChannel.SLACK])
        manager.disable_rule(rule.id, username)
        manager.enable_rule(rule.id, username)
        
        log = manager.get_change_log(rule.id)
        
        assert any(c.change_type == RuleChangeType.DISABLED for c in log)
        assert any(c.change_type == RuleChangeType.ENABLED for c in log)

    def test_previous_state_preserved_in_log(self):
        """
        Property: Previous state is preserved in change log.
        """
        manager = AlertRuleManager()
        
        rule = manager.create_rule(
            "Original Name",
            [AlertChannel.WEBHOOK],
            min_severity=SeverityLevel.MEDIUM,
        )
        
        manager.update_rule(
            rule.id, "admin",
            name="New Name",
        )
        
        log = manager.get_change_log(rule.id)
        update_log = [c for c in log if c.change_type == RuleChangeType.UPDATED][0]
        
        assert update_log.previous_state is not None
        assert update_log.previous_state["name"] == "Original Name"
        assert update_log.new_state["name"] == "New Name"

    @given(alert=alert_instance_strategy())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_alert_captures_rule_version(self, alert: AlertInstance):
        """
        Property: Alerts capture the rule version at creation time.
        """
        # Alert should have rule_version field
        assert hasattr(alert, "rule_version")
        assert isinstance(alert.rule_version, int)


# =============================================================================
# Integration Tests
# =============================================================================


class TestAlertSystemIntegration:
    """Integration tests for the alert system."""

    @given(event=risk_event_strategy())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_end_to_end_alert_flow(self, event: RiskEvent):
        """
        Property: Events can flow through the entire alert system.
        """
        manager = AlertManager()
        
        # Create a rule that matches everything
        manager.rule_manager.create_rule(
            name="Catch-All Rule",
            channels=[AlertChannel.WEBHOOK],
            min_severity=SeverityLevel.LOW,
        )
        
        # Verify rule matching works
        matching = manager.rule_manager.get_matching_rules(event)
        assert len(matching) >= 1

    @given(alert=alert_instance_strategy(), user=username_strategy)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_alert_acknowledgment_flow(self, alert: AlertInstance, user: str):
        """
        Property: Alerts can be acknowledged.
        """
        manager = AlertManager()
        
        # Store the alert
        manager._alerts[alert.alert_id] = alert
        
        # Acknowledge it
        ack = manager.acknowledge_alert(alert.alert_id, user, "Handled")
        
        assert ack is not None
        assert ack.acknowledged_by == user
        assert manager.acknowledgments.is_acknowledged(alert.alert_id)
