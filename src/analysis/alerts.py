"""
Advanced Alert System for Supply Chain Risk Management.

Provides alert rule management, multi-channel notification delivery,
latency monitoring, acknowledgment tracking, and rule update isolation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable
from collections import defaultdict
import uuid
import asyncio
import structlog

from src.models import (
    RiskEvent,
    SeverityLevel,
    EventType,
    AlertChannel,
    AlertRule,
    AlertRuleStatus,
    AlertAcknowledgment,
    AlertDeliveryRecord,
)
from src.graph.connection import get_connection

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class DeliveryStatus(str, Enum):
    """Status of alert delivery attempt."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    ACKNOWLEDGED = "acknowledged"


class RuleChangeType(str, Enum):
    """Type of rule change for audit trail."""

    CREATED = "created"
    UPDATED = "updated"
    ENABLED = "enabled"
    DISABLED = "disabled"
    DELETED = "deleted"


@dataclass
class AlertInstance:
    """A specific alert generated from a rule match."""

    alert_id: str
    rule_id: str
    risk_event_id: str
    
    # Alert content
    title: str
    message: str
    severity: SeverityLevel
    
    # Delivery tracking
    channels: list[AlertChannel]
    delivery_status: dict[str, DeliveryStatus] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    acknowledgment_notes: str | None = None
    
    # Audit
    rule_version: int = 1

    @property
    def delivery_latency_ms(self) -> int | None:
        """Calculate delivery latency in milliseconds."""
        if self.delivered_at:
            delta = self.delivered_at - self.created_at
            return int(delta.total_seconds() * 1000)
        return None


@dataclass
class RuleChange:
    """Audit trail entry for rule changes."""

    change_id: str
    rule_id: str
    change_type: RuleChangeType
    changed_by: str
    changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    previous_state: dict | None = None
    new_state: dict | None = None


@dataclass
class DeliveryMetrics:
    """Metrics for alert delivery performance."""

    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: int = 0
    sla_violations: int = 0
    
    # SLA is 30 seconds = 30000ms
    SLA_THRESHOLD_MS = 30000


# =============================================================================
# Alert Rule Manager
# =============================================================================


class AlertRuleManager:
    """
    Manages alert rule creation, storage, and retrieval.

    Supports filtering by event type, location, entities, and severity.
    """

    def __init__(self, connection=None):
        """
        Initialize the alert rule manager.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._rules: dict[str, AlertRule] = {}
        self._rule_versions: dict[str, list[dict]] = defaultdict(list)
        self._change_log: list[RuleChange] = []
        self._version_tracker: dict[str, int] = {}  # Track versions separately

    def create_rule(
        self,
        name: str,
        channels: list[AlertChannel],
        event_types: list[EventType] | None = None,
        locations: list[str] | None = None,
        entity_ids: list[str] | None = None,
        min_severity: SeverityLevel = SeverityLevel.LOW,
        created_by: str = "system",
    ) -> AlertRule:
        """
        Create a new alert rule.

        Args:
            name: Name of the rule.
            channels: Channels to send alerts to.
            event_types: Optional event type filter.
            locations: Optional location filter.
            entity_ids: Optional entity ID filter.
            min_severity: Minimum severity to trigger.
            created_by: User creating the rule.

        Returns:
            Created AlertRule.
        """
        rule_id = f"rule-{uuid.uuid4().hex[:8]}"

        # Build severity thresholds list from min_severity
        severity_order = [SeverityLevel.LOW, SeverityLevel.MEDIUM, 
                         SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        min_idx = severity_order.index(min_severity)
        severity_thresholds = severity_order[min_idx:]

        rule = AlertRule(
            id=rule_id,
            name=name,
            channels=channels,
            event_types=event_types or [],
            severity_thresholds=severity_thresholds,
            locations=locations or [],
            entity_ids=entity_ids or [],
            status=AlertRuleStatus.ACTIVE,
            created_by=created_by,
        )

        self._rules[rule_id] = rule
        self._version_tracker[rule_id] = 1
        self._save_version(rule)
        self._log_change(rule_id, RuleChangeType.CREATED, created_by, None, rule)

        logger.info("Created alert rule", rule_id=rule_id, name=name)

        return rule

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        status: AlertRuleStatus | None = None,
        channel: AlertChannel | None = None,
    ) -> list[AlertRule]:
        """
        List all rules, optionally filtered.

        Args:
            status: Optional status filter.
            channel: Optional channel filter.

        Returns:
            List of matching rules.
        """
        rules = list(self._rules.values())

        if status:
            rules = [r for r in rules if r.status == status]

        if channel:
            rules = [r for r in rules if channel in r.channels]

        return rules

    def update_rule(
        self, rule_id: str, updated_by: str, **updates
    ) -> AlertRule | None:
        """
        Update a rule's configuration.

        Updates only apply to future alerts (isolation).

        Args:
            rule_id: ID of rule to update.
            updated_by: User making the update.
            **updates: Fields to update.

        Returns:
            Updated AlertRule or None if not found.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return None

        # Save previous state
        previous_state = self._rule_to_dict(rule)

        # Apply updates
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        rule.updated_at = datetime.now(timezone.utc)
        self._version_tracker[rule_id] = self._version_tracker.get(rule_id, 0) + 1

        self._save_version(rule)
        self._log_change(
            rule_id, RuleChangeType.UPDATED, updated_by, previous_state, rule
        )

        logger.info("Updated alert rule", rule_id=rule_id, updates=list(updates.keys()))

        return rule

    def enable_rule(self, rule_id: str, by: str = "system") -> bool:
        """Enable a rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False

        previous = self._rule_to_dict(rule)
        rule.status = AlertRuleStatus.ACTIVE
        rule.updated_at = datetime.now(timezone.utc)

        self._log_change(rule_id, RuleChangeType.ENABLED, by, previous, rule)
        return True

    def disable_rule(self, rule_id: str, by: str = "system") -> bool:
        """Disable a rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False

        previous = self._rule_to_dict(rule)
        rule.status = AlertRuleStatus.DISABLED
        rule.updated_at = datetime.now(timezone.utc)

        self._log_change(rule_id, RuleChangeType.DISABLED, by, previous, rule)
        return True

    def delete_rule(self, rule_id: str, by: str = "system") -> bool:
        """Delete a rule (mark as deleted)."""
        rule = self._rules.get(rule_id)
        if not rule:
            return False

        previous = self._rule_to_dict(rule)
        rule.status = AlertRuleStatus.DISABLED
        rule.updated_at = datetime.now(timezone.utc)

        self._log_change(rule_id, RuleChangeType.DELETED, by, previous, rule)
        return True

    def get_matching_rules(self, event: RiskEvent) -> list[AlertRule]:
        """
        Get all active rules that match a risk event.

        Args:
            event: RiskEvent to match against.

        Returns:
            List of matching rules.
        """
        matching = []

        for rule in self._rules.values():
            if rule.status != AlertRuleStatus.ACTIVE:
                continue

            if self._event_matches_rule(event, rule):
                matching.append(rule)

        return matching

    def _event_matches_rule(self, event: RiskEvent, rule: AlertRule) -> bool:
        """Check if an event matches a rule's filters."""
        # Check severity using severity_thresholds
        if rule.severity_thresholds:
            if event.severity not in rule.severity_thresholds:
                return False

        # Check event type filter
        if rule.event_types:
            if event.event_type not in rule.event_types:
                return False

        # Check location filter
        if rule.locations:
            if event.location not in rule.locations:
                return False

        # Check entity filter
        if rule.entity_ids:
            if not any(e in rule.entity_ids for e in event.affected_entities):
                return False

        return True

    def _save_version(self, rule: AlertRule) -> None:
        """Save a version of the rule for history."""
        self._rule_versions[rule.id].append(self._rule_to_dict(rule))

    def _rule_to_dict(self, rule: AlertRule) -> dict:
        """Convert rule to dictionary for storage."""
        return {
            "id": rule.id,
            "name": rule.name,
            "version": self._version_tracker.get(rule.id, 1),
            "status": rule.status.value,
            "channels": [c.value for c in rule.channels],
            "severity_thresholds": [s.value for s in rule.severity_thresholds],
            "event_types": [e.value for e in rule.event_types],
            "locations": rule.locations,
            "entity_ids": rule.entity_ids,
            "created_at": rule.created_at.isoformat(),
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        }

    def _log_change(
        self,
        rule_id: str,
        change_type: RuleChangeType,
        by: str,
        previous: dict | None,
        rule: AlertRule | None,
    ) -> None:
        """Log a rule change for audit."""
        change = RuleChange(
            change_id=f"change-{uuid.uuid4().hex[:8]}",
            rule_id=rule_id,
            change_type=change_type,
            changed_by=by,
            previous_state=previous,
            new_state=self._rule_to_dict(rule) if rule else None,
        )
        self._change_log.append(change)

    def get_change_log(self, rule_id: str | None = None) -> list[RuleChange]:
        """Get audit trail of rule changes."""
        if rule_id:
            return [c for c in self._change_log if c.rule_id == rule_id]
        return self._change_log



# =============================================================================
# Multi-Channel Delivery
# =============================================================================


class ChannelDeliverer:
    """
    Delivers alerts through multiple channels.

    Supports webhook, email, Slack, and extensible custom channels.
    """

    # SLA threshold in seconds
    SLA_THRESHOLD_SECONDS = 30

    def __init__(self):
        """Initialize the channel deliverer."""
        self._handlers: dict[AlertChannel, Callable] = {
            AlertChannel.WEBHOOK: self._deliver_webhook,
            AlertChannel.EMAIL: self._deliver_email,
            AlertChannel.SLACK: self._deliver_slack,
            AlertChannel.SMS: self._deliver_sms,
        }
        self._delivery_records: list[AlertDeliveryRecord] = []
        self._metrics = DeliveryMetrics()

    async def deliver_alert(
        self,
        alert: AlertInstance,
        config: dict[AlertChannel, dict] | None = None,
    ) -> dict[str, DeliveryStatus]:
        """
        Deliver an alert through all configured channels.

        Args:
            alert: AlertInstance to deliver.
            config: Channel-specific configuration.

        Returns:
            Dictionary of channel -> delivery status.
        """
        config = config or {}
        results = {}
        delivery_start = datetime.now(timezone.utc)

        for channel in alert.channels:
            handler = self._handlers.get(channel)
            if not handler:
                logger.warning("No handler for channel", channel=channel.value)
                results[channel.value] = DeliveryStatus.FAILED
                continue

            try:
                channel_config = config.get(channel, {})
                success = await handler(alert, channel_config)
                
                status = DeliveryStatus.DELIVERED if success else DeliveryStatus.FAILED
                results[channel.value] = status

                # Record delivery
                record = AlertDeliveryRecord(
                    alert_id=alert.alert_id,
                    channel=channel,
                    recipient=channel_config.get("recipient", "default"),
                    delivered=success,
                    error_message=None if success else "Delivery failed",
                )
                self._delivery_records.append(record)

            except Exception as e:
                logger.error(
                    "Channel delivery failed",
                    channel=channel.value,
                    error=str(e),
                )
                results[channel.value] = DeliveryStatus.FAILED

        # Update alert timing
        delivery_end = datetime.now(timezone.utc)
        if any(s == DeliveryStatus.DELIVERED for s in results.values()):
            alert.delivered_at = delivery_end

        # Update metrics
        self._update_metrics(alert, results, delivery_start, delivery_end)

        return results

    async def _deliver_webhook(self, alert: AlertInstance, config: dict) -> bool:
        """Deliver alert via webhook."""
        url = config.get("url")
        if not url:
            logger.debug("Webhook URL not configured, simulating delivery")
            # Simulate successful delivery for demo
            await asyncio.sleep(0.01)
            return True

        # In production, make HTTP POST request
        logger.info(
            "Webhook delivery",
            alert_id=alert.alert_id,
            url=url,
        )
        return True

    async def _deliver_email(self, alert: AlertInstance, config: dict) -> bool:
        """Deliver alert via email."""
        recipients = config.get("recipients", [])
        logger.info(
            "Email delivery",
            alert_id=alert.alert_id,
            recipient_count=len(recipients),
        )
        # Simulate delivery
        await asyncio.sleep(0.01)
        return True

    async def _deliver_slack(self, alert: AlertInstance, config: dict) -> bool:
        """Deliver alert via Slack."""
        channel = config.get("channel", "#alerts")
        logger.info(
            "Slack delivery",
            alert_id=alert.alert_id,
            channel=channel,
        )
        # Simulate delivery
        await asyncio.sleep(0.01)
        return True

    async def _deliver_sms(self, alert: AlertInstance, config: dict) -> bool:
        """Deliver alert via SMS."""
        phone_numbers = config.get("phone_numbers", [])
        logger.info(
            "SMS delivery",
            alert_id=alert.alert_id,
            recipient_count=len(phone_numbers),
        )
        await asyncio.sleep(0.01)
        return True

    async def _deliver_push(self, alert: AlertInstance, config: dict) -> bool:
        """Deliver alert via push notification."""
        user_ids = config.get("user_ids", [])
        logger.info(
            "Push delivery",
            alert_id=alert.alert_id,
            user_count=len(user_ids),
        )
        await asyncio.sleep(0.01)
        return True

    def _update_metrics(
        self,
        alert: AlertInstance,
        results: dict[str, DeliveryStatus],
        start: datetime,
        end: datetime,
    ) -> None:
        """Update delivery metrics."""
        latency_ms = int((end - start).total_seconds() * 1000)

        for status in results.values():
            self._metrics.total_deliveries += 1
            if status == DeliveryStatus.DELIVERED:
                self._metrics.successful_deliveries += 1
            else:
                self._metrics.failed_deliveries += 1

        # Update latency stats
        if latency_ms > self._metrics.max_latency_ms:
            self._metrics.max_latency_ms = latency_ms

        # Update average
        total = self._metrics.total_deliveries
        if total > 0:
            prev_total = (self._metrics.avg_latency_ms * (total - 1))
            self._metrics.avg_latency_ms = (prev_total + latency_ms) / total

        # Check SLA
        if latency_ms > self.SLA_THRESHOLD_SECONDS * 1000:
            self._metrics.sla_violations += 1
            logger.warning(
                "SLA violation",
                alert_id=alert.alert_id,
                latency_ms=latency_ms,
                threshold_ms=self.SLA_THRESHOLD_SECONDS * 1000,
            )

    def get_metrics(self) -> DeliveryMetrics:
        """Get current delivery metrics."""
        return self._metrics

    def register_handler(
        self,
        channel: AlertChannel,
        handler: Callable,
    ) -> None:
        """Register a custom channel handler."""
        self._handlers[channel] = handler


# =============================================================================
# Acknowledgment Tracker
# =============================================================================


class AcknowledgmentTracker:
    """
    Tracks alert acknowledgments.

    Records acknowledgment data immutably and provides history queries.
    """

    def __init__(self):
        """Initialize the acknowledgment tracker."""
        self._acknowledgments: dict[str, AlertAcknowledgment] = {}
        self._history: list[AlertAcknowledgment] = []

    def acknowledge(
        self,
        alert_id: str,
        acknowledged_by: str,
        notes: str | None = None,
    ) -> AlertAcknowledgment:
        """
        Record an acknowledgment for an alert.

        Args:
            alert_id: ID of the alert.
            acknowledged_by: User acknowledging.
            notes: Optional acknowledgment notes.

        Returns:
            AlertAcknowledgment record.
        """
        ack = AlertAcknowledgment(
            alert_id=alert_id,
            acknowledged_by=acknowledged_by,
            notes=notes or "",
        )

        # Store immutably - don't overwrite existing
        if alert_id not in self._acknowledgments:
            self._acknowledgments[alert_id] = ack

        # Always add to history
        self._history.append(ack)

        logger.info(
            "Alert acknowledged",
            alert_id=alert_id,
            by=acknowledged_by,
        )

        return ack

    def get_acknowledgment(self, alert_id: str) -> AlertAcknowledgment | None:
        """Get acknowledgment for an alert."""
        return self._acknowledgments.get(alert_id)

    def is_acknowledged(self, alert_id: str) -> bool:
        """Check if an alert has been acknowledged."""
        return alert_id in self._acknowledgments

    def get_history(
        self,
        alert_id: str | None = None,
        user: str | None = None,
        since: datetime | None = None,
    ) -> list[AlertAcknowledgment]:
        """
        Get acknowledgment history with optional filters.

        Args:
            alert_id: Filter by alert ID.
            user: Filter by acknowledging user.
            since: Filter by time.

        Returns:
            List of acknowledgment records.
        """
        history = self._history

        if alert_id:
            history = [a for a in history if a.alert_id == alert_id]

        if user:
            history = [a for a in history if a.acknowledged_by == user]

        if since:
            history = [a for a in history if a.acknowledged_at >= since]

        return history

    def get_unacknowledged_count(self) -> int:
        """Get count of alerts without acknowledgment."""
        # This would need integration with AlertManager in production
        return 0


# =============================================================================
# Alert Manager (Main Interface)
# =============================================================================


class AlertManager:
    """
    Main interface for the advanced alert system.

    Coordinates rule management, alert generation, delivery, and tracking.
    """

    def __init__(self, connection=None):
        """
        Initialize the alert manager.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self.rule_manager = AlertRuleManager(connection)
        self.deliverer = ChannelDeliverer()
        self.acknowledgments = AcknowledgmentTracker()
        
        self._alerts: dict[str, AlertInstance] = {}
        self._event_to_alerts: dict[str, list[str]] = defaultdict(list)

    async def process_risk_event(
        self,
        event: RiskEvent,
        channel_config: dict[AlertChannel, dict] | None = None,
    ) -> list[AlertInstance]:
        """
        Process a risk event and generate/deliver alerts.

        Args:
            event: RiskEvent to process.
            channel_config: Optional channel-specific configuration.

        Returns:
            List of generated alerts.
        """
        alerts = []
        matching_rules = self.rule_manager.get_matching_rules(event)

        for rule in matching_rules:
            alert = self._create_alert(event, rule)
            self._alerts[alert.alert_id] = alert
            self._event_to_alerts[event.id].append(alert.alert_id)

            # Deliver alert
            delivery_results = await self.deliverer.deliver_alert(
                alert, channel_config
            )
            alert.delivery_status = delivery_results

            alerts.append(alert)

        logger.info(
            "Processed risk event",
            event_id=event.id,
            matching_rules=len(matching_rules),
            alerts_generated=len(alerts),
        )

        return alerts

    def _create_alert(self, event: RiskEvent, rule: AlertRule) -> AlertInstance:
        """Create an alert instance from event and rule."""
        return AlertInstance(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            rule_id=rule.id,
            risk_event_id=event.id,
            title=f"[{event.severity.value}] {event.event_type.value}: {event.title}",
            message=f"Risk detected in {event.location}: {event.description[:200]}",
            severity=event.severity,
            channels=rule.channels,
            rule_version=self.rule_manager._version_tracker.get(rule.id, 1),
        )

    def get_alert(self, alert_id: str) -> AlertInstance | None:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def get_alerts_for_event(self, event_id: str) -> list[AlertInstance]:
        """Get all alerts generated for a risk event."""
        alert_ids = self._event_to_alerts.get(event_id, [])
        return [self._alerts[aid] for aid in alert_ids if aid in self._alerts]

    def acknowledge_alert(
        self,
        alert_id: str,
        by: str,
        notes: str | None = None,
    ) -> AlertAcknowledgment | None:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return None

        ack = self.acknowledgments.acknowledge(alert_id, by, notes)
        
        alert.acknowledged_at = ack.acknowledged_at
        alert.acknowledged_by = by
        alert.acknowledgment_notes = notes

        return ack

    def get_delivery_metrics(self) -> DeliveryMetrics:
        """Get delivery performance metrics."""
        return self.deliverer.get_metrics()

    def get_pending_alerts(self) -> list[AlertInstance]:
        """Get alerts that haven't been acknowledged."""
        return [
            a for a in self._alerts.values()
            if not self.acknowledgments.is_acknowledged(a.alert_id)
        ]

    def get_sla_violations(self) -> list[AlertInstance]:
        """Get alerts that violated delivery SLA."""
        sla_ms = DeliveryMetrics.SLA_THRESHOLD_MS
        violations = []
        
        for alert in self._alerts.values():
            latency = alert.delivery_latency_ms
            if latency and latency > sla_ms:
                violations.append(alert)
        
        return violations


# =============================================================================
# Alert Latency Monitor
# =============================================================================


class LatencyMonitor:
    """
    Monitors alert delivery latency and SLA compliance.

    Tracks metrics and alerts on violations.
    """

    SLA_THRESHOLD_MS = 30000  # 30 seconds

    def __init__(self):
        """Initialize the latency monitor."""
        self._latencies: list[tuple[str, int, datetime]] = []
        self._violations: list[tuple[str, int, datetime]] = []

    def record_delivery(
        self, alert_id: str, created_at: datetime, delivered_at: datetime
    ) -> bool:
        """
        Record a delivery and check SLA compliance.

        Args:
            alert_id: ID of the alert.
            created_at: When the alert was created.
            delivered_at: When the alert was delivered.

        Returns:
            True if within SLA, False if violation.
        """
        latency_ms = int((delivered_at - created_at).total_seconds() * 1000)
        self._latencies.append((alert_id, latency_ms, delivered_at))

        if latency_ms > self.SLA_THRESHOLD_MS:
            self._violations.append((alert_id, latency_ms, delivered_at))
            logger.warning(
                "SLA violation",
                alert_id=alert_id,
                latency_ms=latency_ms,
            )
            return False

        return True

    def get_metrics(self) -> dict[str, Any]:
        """Get latency metrics."""
        if not self._latencies:
            return {
                "total_deliveries": 0,
                "avg_latency_ms": 0,
                "max_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "sla_violations": 0,
                "sla_compliance_rate": 1.0,
            }

        latencies = [l[1] for l in self._latencies]
        sorted_latencies = sorted(latencies)
        
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        return {
            "total_deliveries": len(latencies),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "max_latency_ms": max(latencies),
            "p95_latency_ms": sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)],
            "p99_latency_ms": sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)],
            "sla_violations": len(self._violations),
            "sla_compliance_rate": 1 - (len(self._violations) / len(latencies)),
        }

    def get_violations(
        self, since: datetime | None = None
    ) -> list[tuple[str, int, datetime]]:
        """Get SLA violations."""
        if since:
            return [v for v in self._violations if v[2] >= since]
        return self._violations
