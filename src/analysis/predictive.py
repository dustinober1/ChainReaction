"""
Predictive Analytics Engine for Supply Chain Risk Forecasting.

Provides pattern analysis, early warning detection, risk forecasting,
and proactive alert generation with accuracy tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any
from collections import defaultdict
import math

import structlog

from src.models import (
    RiskEvent,
    EventType,
    SeverityLevel,
    Alert,
)
from src.graph.connection import get_connection

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class TrendDirection(str, Enum):
    """Direction of a detected trend."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    CYCLICAL = "cyclical"


class WarningLevel(str, Enum):
    """Level of early warning alert."""

    WATCH = "watch"
    ADVISORY = "advisory"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SeasonalPattern:
    """Represents a seasonal pattern in risk events."""

    location: str
    event_type: EventType
    peak_months: list[int]  # 1-12
    frequency: float  # Events per year
    avg_severity: float
    confidence: float  # 0-1


@dataclass
class RiskPattern:
    """A recurring risk pattern identified from historical data."""

    pattern_id: str
    location: str
    event_type: EventType
    frequency_per_year: float
    avg_duration_days: float
    severity_distribution: dict[SeverityLevel, float]
    last_occurrence: datetime | None
    trend: TrendDirection
    confidence: float


@dataclass
class EarlyWarning:
    """Early warning signal for potential risk."""

    warning_id: str
    location: str
    event_type: EventType
    warning_level: WarningLevel
    sentiment_score: float  # -1 to 1 (negative = concerning)
    signal_strength: float  # 0 to 1
    contributing_factors: list[str]
    recommended_actions: list[str]
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None


@dataclass
class RiskForecast:
    """Forecast of potential future risk event."""

    forecast_id: str
    location: str
    event_type: EventType
    predicted_severity: SeverityLevel
    probability: float  # 0-1
    confidence_interval: tuple[float, float]  # Lower, upper bounds
    forecast_window_start: datetime
    forecast_window_end: datetime
    affected_entities: list[str]
    preventive_actions: list[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ForecastAccuracy:
    """Accuracy metrics for historical forecasts."""

    forecast_id: str
    predicted_probability: float
    actual_occurred: bool
    prediction_error: float
    severity_match: bool
    timing_error_days: float | None
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PredictiveAlert:
    """Proactive alert generated from predictions."""

    alert_id: str
    forecast_id: str
    warning_level: WarningLevel
    title: str
    message: str
    affected_products: list[str]
    preventive_actions: list[str]
    probability_threshold: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Pattern Analyzer
# =============================================================================


class PatternAnalyzer:
    """
    Analyzes historical risk data to identify patterns and trends.

    Detects:
    - Seasonal patterns in risk events
    - Recurring risk factors by location and type
    - Frequency metrics and trends
    """

    def __init__(self, connection=None):
        """
        Initialize the pattern analyzer.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._pattern_cache: dict[str, RiskPattern] = {}

    def _get_connection(self):
        """Get the database connection."""
        if self._connection is None:
            return get_connection()
        return self._connection

    async def analyze_seasonal_patterns(
        self, location: str | None = None, lookback_years: int = 2
    ) -> list[SeasonalPattern]:
        """
        Analyze seasonal patterns in risk events.

        Args:
            location: Optional location filter.
            lookback_years: Years of history to analyze.

        Returns:
            List of identified seasonal patterns.
        """
        patterns = []

        try:
            conn = self._get_connection()
            cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_years * 365)

            # Query historical risk events
            query = """
            MATCH (e:RiskEvent)
            WHERE e.detected_at >= $cutoff
            """
            if location:
                query += " AND e.location = $location"
            query += """
            RETURN e.event_type as event_type,
                   e.location as location,
                   e.severity as severity,
                   e.detected_at as detected_at
            ORDER BY e.detected_at
            """

            params = {"cutoff": cutoff.isoformat()}
            if location:
                params["location"] = location

            results = await conn.execute_query(query, params)

            # Group events by location and type
            grouped = defaultdict(lambda: defaultdict(list))
            for row in results:
                loc = row.get("location", "Unknown")
                evt_type = row.get("event_type", "Other")
                grouped[loc][evt_type].append({
                    "detected_at": row.get("detected_at"),
                    "severity": row.get("severity"),
                })

            # Analyze each group for seasonal patterns
            for loc, type_events in grouped.items():
                for evt_type, events in type_events.items():
                    pattern = self._detect_seasonal_pattern(loc, evt_type, events)
                    if pattern:
                        patterns.append(pattern)

        except Exception as e:
            logger.warning("Seasonal pattern analysis failed", error=str(e))

        return patterns

    def _detect_seasonal_pattern(
        self, location: str, event_type: str, events: list[dict]
    ) -> SeasonalPattern | None:
        """
        Detect seasonal pattern from event list.

        Args:
            location: Location of events.
            event_type: Type of events.
            events: List of event data.

        Returns:
            SeasonalPattern if detected, None otherwise.
        """
        if len(events) < 3:
            return None

        try:
            # Extract months from events
            month_counts = defaultdict(int)
            severity_sum = 0.0
            
            for event in events:
                detected_at = event.get("detected_at")
                if detected_at:
                    if isinstance(detected_at, str):
                        detected_at = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
                    month_counts[detected_at.month] += 1
                
                severity = event.get("severity", "Medium")
                severity_map = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
                severity_sum += severity_map.get(severity, 2)

            total_events = len(events)
            avg_severity = severity_sum / total_events if total_events > 0 else 2.0

            # Find peak months (above average)
            avg_monthly = total_events / 12
            peak_months = [
                month for month, count in month_counts.items()
                if count > avg_monthly * 1.5
            ]

            if not peak_months:
                return None

            # Calculate frequency (events per year)
            years_span = max(1, len(events) / 12)
            frequency = total_events / years_span

            # Calculate confidence based on data volume
            confidence = min(1.0, len(events) / 10)

            return SeasonalPattern(
                location=location,
                event_type=EventType(event_type) if event_type in [e.value for e in EventType] else EventType.OTHER,
                peak_months=sorted(peak_months),
                frequency=frequency,
                avg_severity=avg_severity,
                confidence=confidence,
            )

        except Exception as e:
            logger.debug("Pattern detection failed", error=str(e))
            return None

    async def identify_recurring_patterns(
        self, min_occurrences: int = 3
    ) -> list[RiskPattern]:
        """
        Identify recurring risk patterns by location and type.

        Args:
            min_occurrences: Minimum events to consider a pattern.

        Returns:
            List of identified risk patterns.
        """
        patterns = []

        try:
            conn = self._get_connection()

            # Query for pattern groupings
            query = """
            MATCH (e:RiskEvent)
            WITH e.location as location, 
                 e.event_type as event_type,
                 collect(e) as events
            WHERE size(events) >= $min_occurrences
            RETURN location, event_type, 
                   size(events) as count,
                   [ev in events | ev.severity] as severities,
                   [ev in events | ev.detected_at] as dates
            """

            results = await conn.execute_query(query, {"min_occurrences": min_occurrences})

            for row in results:
                pattern = self._create_risk_pattern(
                    row["location"],
                    row["event_type"],
                    row["count"],
                    row.get("severities", []),
                    row.get("dates", []),
                )
                if pattern:
                    patterns.append(pattern)
                    self._pattern_cache[pattern.pattern_id] = pattern

        except Exception as e:
            logger.warning("Recurring pattern identification failed", error=str(e))

        return patterns

    def _create_risk_pattern(
        self,
        location: str,
        event_type: str,
        count: int,
        severities: list[str],
        dates: list,
    ) -> RiskPattern | None:
        """Create a RiskPattern from aggregated data."""
        try:
            # Calculate severity distribution
            severity_dist = defaultdict(int)
            for sev in severities:
                if sev:
                    severity_dist[sev] += 1
            
            total = sum(severity_dist.values()) or 1
            severity_distribution = {
                SeverityLevel(k): v / total
                for k, v in severity_dist.items()
                if k in [s.value for s in SeverityLevel]
            }

            # Parse dates and calculate metrics
            parsed_dates = []
            for d in dates:
                if d:
                    if isinstance(d, str):
                        parsed_dates.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
                    elif isinstance(d, datetime):
                        parsed_dates.append(d)

            last_occurrence = max(parsed_dates) if parsed_dates else None

            # Calculate frequency
            if len(parsed_dates) >= 2:
                date_range = (max(parsed_dates) - min(parsed_dates)).days
                years = max(date_range / 365, 0.1)
                frequency_per_year = count / years
            else:
                frequency_per_year = count

            # Determine trend
            if len(parsed_dates) >= 4:
                # Simple trend detection: compare first half vs second half
                mid = len(parsed_dates) // 2
                first_half = len([d for d in parsed_dates[:mid]])
                second_half = len([d for d in parsed_dates[mid:]])
                
                if second_half > first_half * 1.3:
                    trend = TrendDirection.INCREASING
                elif second_half < first_half * 0.7:
                    trend = TrendDirection.DECREASING
                else:
                    trend = TrendDirection.STABLE
            else:
                trend = TrendDirection.STABLE

            pattern_id = f"pattern-{location[:10]}-{event_type[:10]}-{count}"

            return RiskPattern(
                pattern_id=pattern_id,
                location=location,
                event_type=EventType(event_type) if event_type in [e.value for e in EventType] else EventType.OTHER,
                frequency_per_year=frequency_per_year,
                avg_duration_days=7.0,  # Default estimate
                severity_distribution=severity_distribution,
                last_occurrence=last_occurrence,
                trend=trend,
                confidence=min(1.0, count / 10),
            )

        except Exception as e:
            logger.debug("Risk pattern creation failed", error=str(e))
            return None

    def calculate_frequency_metrics(
        self, events: list[RiskEvent]
    ) -> dict[str, float]:
        """
        Calculate frequency metrics from a list of events.

        Args:
            events: List of RiskEvent objects.

        Returns:
            Dictionary of frequency metrics.
        """
        if not events:
            return {
                "total_events": 0,
                "events_per_month": 0.0,
                "events_per_week": 0.0,
                "avg_days_between": 0.0,
            }

        # Sort by date
        sorted_events = sorted(events, key=lambda e: e.detected_at)

        if len(sorted_events) < 2:
            return {
                "total_events": len(events),
                "events_per_month": 0.0,
                "events_per_week": 0.0,
                "avg_days_between": 0.0,
            }

        # Calculate time span
        time_span = (sorted_events[-1].detected_at - sorted_events[0].detected_at).days
        weeks = max(time_span / 7, 1)
        months = max(time_span / 30, 1)

        # Calculate gaps between events
        gaps = []
        for i in range(1, len(sorted_events)):
            gap = (sorted_events[i].detected_at - sorted_events[i-1].detected_at).days
            gaps.append(gap)

        avg_gap = sum(gaps) / len(gaps) if gaps else 0

        return {
            "total_events": len(events),
            "events_per_month": len(events) / months,
            "events_per_week": len(events) / weeks,
            "avg_days_between": avg_gap,
        }


# =============================================================================
# Early Warning Detector
# =============================================================================


class EarlyWarningDetector:
    """
    Detects early warning signals from sentiment analysis and patterns.

    Monitors for:
    - Escalating negative sentiment
    - Increasing event frequency
    - Pattern-based predictions
    """

    # Thresholds for warning levels
    THRESHOLDS = {
        WarningLevel.WATCH: 0.3,
        WarningLevel.ADVISORY: 0.5,
        WarningLevel.WARNING: 0.7,
        WarningLevel.CRITICAL: 0.9,
    }

    def __init__(self, connection=None):
        """
        Initialize the early warning detector.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._active_warnings: dict[str, EarlyWarning] = {}

    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of text content.

        Args:
            text: Text to analyze.

        Returns:
            Sentiment score from -1 (very negative) to 1 (very positive).
        """
        # Simple keyword-based sentiment for demonstration
        # In production, use a proper NLP model
        text_lower = text.lower()

        negative_keywords = [
            "crisis", "disaster", "failure", "collapse", "shortage",
            "strike", "protest", "closure", "bankruptcy", "disruption",
            "delay", "shutdown", "halt", "suspend", "warning",
        ]
        positive_keywords = [
            "recovery", "improvement", "resolution", "agreement",
            "stable", "growth", "expansion", "success", "reopening",
        ]

        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)
        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)

        total = neg_count + pos_count
        if total == 0:
            return 0.0

        # Score from -1 to 1
        return (pos_count - neg_count) / total

    def detect_escalating_signals(
        self,
        recent_events: list[RiskEvent],
        historical_baseline: float,
    ) -> list[EarlyWarning]:
        """
        Detect escalating risk signals compared to baseline.

        Args:
            recent_events: Recent risk events (e.g., last 7 days).
            historical_baseline: Historical average events per period.

        Returns:
            List of early warnings for escalating situations.
        """
        warnings = []

        # Group by location
        location_counts = defaultdict(lambda: {"count": 0, "events": []})
        for event in recent_events:
            location_counts[event.location]["count"] += 1
            location_counts[event.location]["events"].append(event)

        for location, data in location_counts.items():
            count = data["count"]
            events = data["events"]

            # Calculate escalation ratio
            if historical_baseline > 0:
                escalation_ratio = count / historical_baseline
            else:
                escalation_ratio = count

            # Determine warning level
            signal_strength = min(1.0, escalation_ratio / 3)

            if signal_strength < self.THRESHOLDS[WarningLevel.WATCH]:
                continue

            # Determine warning level
            warning_level = WarningLevel.WATCH
            for level, threshold in sorted(
                self.THRESHOLDS.items(), key=lambda x: x[1], reverse=True
            ):
                if signal_strength >= threshold:
                    warning_level = level
                    break

            # Get most common event type
            type_counts = defaultdict(int)
            for e in events:
                type_counts[e.event_type] += 1
            most_common_type = max(type_counts, key=type_counts.get)

            warning = EarlyWarning(
                warning_id=f"warning-{location}-{datetime.now().timestamp()}",
                location=location,
                event_type=most_common_type,
                warning_level=warning_level,
                sentiment_score=-0.5,  # Default negative for escalation
                signal_strength=signal_strength,
                contributing_factors=[
                    f"Event frequency {escalation_ratio:.1f}x above baseline",
                    f"{count} events detected recently",
                ],
                recommended_actions=self._get_recommended_actions(warning_level, most_common_type),
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )

            warnings.append(warning)
            self._active_warnings[warning.warning_id] = warning

        return warnings

    def _get_recommended_actions(
        self, level: WarningLevel, event_type: EventType
    ) -> list[str]:
        """Get recommended actions based on warning level and type."""
        base_actions = []

        if level in [WarningLevel.WARNING, WarningLevel.CRITICAL]:
            base_actions.extend([
                "Review and activate backup suppliers",
                "Increase inventory buffers for critical components",
                "Alert procurement team for expedited sourcing",
            ])

        if level == WarningLevel.CRITICAL:
            base_actions.extend([
                "Activate business continuity plan",
                "Notify executive leadership",
                "Begin customer impact assessment",
            ])

        # Type-specific actions
        type_actions = {
            EventType.STRIKE: ["Monitor labor negotiations", "Prepare alternative logistics"],
            EventType.WEATHER: ["Check weather forecasts", "Review transportation routes"],
            EventType.GEOPOLITICAL: ["Monitor news sources", "Review regulatory requirements"],
            EventType.CYBER_ATTACK: ["Enhance security monitoring", "Verify backup systems"],
        }

        base_actions.extend(type_actions.get(event_type, []))
        return base_actions[:5]  # Limit to 5 actions

    def get_active_warnings(self) -> list[EarlyWarning]:
        """Get all currently active warnings."""
        now = datetime.now(timezone.utc)
        # Filter out expired warnings
        active = [
            w for w in self._active_warnings.values()
            if w.expires_at is None or w.expires_at > now
        ]
        return active


# =============================================================================
# Risk Forecaster
# =============================================================================


class RiskForecaster:
    """
    Generates risk forecasts using historical patterns and current signals.

    Creates probability-based predictions with confidence intervals.
    """

    def __init__(self, connection=None):
        """
        Initialize the risk forecaster.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._pattern_analyzer = PatternAnalyzer(connection)
        self._forecasts: dict[str, RiskForecast] = {}

    async def generate_forecasts(
        self,
        patterns: list[RiskPattern],
        forecast_days: int = 30,
    ) -> list[RiskForecast]:
        """
        Generate risk forecasts based on identified patterns.

        Args:
            patterns: List of risk patterns to base forecasts on.
            forecast_days: Number of days to forecast.

        Returns:
            List of risk forecasts.
        """
        forecasts = []
        now = datetime.now(timezone.utc)

        for pattern in patterns:
            # Calculate probability based on pattern frequency and trend
            base_probability = self._calculate_base_probability(pattern, forecast_days)

            # Adjust for trend
            trend_multiplier = {
                TrendDirection.INCREASING: 1.3,
                TrendDirection.DECREASING: 0.7,
                TrendDirection.STABLE: 1.0,
                TrendDirection.CYCLICAL: 1.1,
            }.get(pattern.trend, 1.0)

            probability = min(1.0, base_probability * trend_multiplier)

            # Skip low probability forecasts
            if probability < 0.15:
                continue

            # Calculate confidence interval
            confidence_interval = self._calculate_confidence_interval(
                probability, pattern.confidence
            )

            # Determine predicted severity
            predicted_severity = self._predict_severity(pattern.severity_distribution)

            # Get affected entities
            affected = await self._get_affected_entities(pattern.location)

            forecast = RiskForecast(
                forecast_id=f"forecast-{pattern.pattern_id}-{now.timestamp()}",
                location=pattern.location,
                event_type=pattern.event_type,
                predicted_severity=predicted_severity,
                probability=probability,
                confidence_interval=confidence_interval,
                forecast_window_start=now,
                forecast_window_end=now + timedelta(days=forecast_days),
                affected_entities=affected,
                preventive_actions=self._generate_preventive_actions(
                    pattern.event_type, predicted_severity
                ),
            )

            forecasts.append(forecast)
            self._forecasts[forecast.forecast_id] = forecast

        return forecasts

    def _calculate_base_probability(
        self, pattern: RiskPattern, forecast_days: int
    ) -> float:
        """Calculate base probability from pattern frequency."""
        # Expected events in forecast window
        expected_events = (pattern.frequency_per_year / 365) * forecast_days

        # Probability of at least one event (Poisson approximation)
        if expected_events > 0:
            probability = 1 - math.exp(-expected_events)
        else:
            probability = 0.0

        # Adjust for recency of last occurrence
        if pattern.last_occurrence:
            days_since = (datetime.now(timezone.utc) - pattern.last_occurrence).days
            expected_gap = 365 / max(pattern.frequency_per_year, 0.1)
            
            if days_since > expected_gap * 1.5:
                probability *= 1.2  # Overdue, increase probability
            elif days_since < expected_gap * 0.5:
                probability *= 0.8  # Recent, decrease probability

        return min(1.0, probability * pattern.confidence)

    def _calculate_confidence_interval(
        self, probability: float, pattern_confidence: float
    ) -> tuple[float, float]:
        """Calculate confidence interval for probability estimate."""
        # Width of interval inversely proportional to pattern confidence
        width = 0.3 * (1 - pattern_confidence)
        
        lower = max(0.0, probability - width)
        upper = min(1.0, probability + width)
        
        return (round(lower, 3), round(upper, 3))

    def _predict_severity(
        self, severity_distribution: dict[SeverityLevel, float]
    ) -> SeverityLevel:
        """Predict most likely severity from distribution."""
        if not severity_distribution:
            return SeverityLevel.MEDIUM

        # Return the most likely severity
        return max(severity_distribution, key=severity_distribution.get)

    async def _get_affected_entities(self, location: str) -> list[str]:
        """Get entities potentially affected by event at location."""
        try:
            conn = self._connection or get_connection()
            query = """
            MATCH (s:Supplier)-[:LOCATED_IN]->(l:Location {name: $location})
            OPTIONAL MATCH (s)-[:SUPPLIES]->(c:Component)
            OPTIONAL MATCH (c)-[:PART_OF]->(p:Product)
            RETURN collect(DISTINCT s.id) + collect(DISTINCT c.id) + collect(DISTINCT p.id) as affected
            LIMIT 100
            """
            results = await conn.execute_query(query, {"location": location})
            if results:
                return [e for e in results[0].get("affected", []) if e][:20]
        except Exception:
            pass
        return []

    def _generate_preventive_actions(
        self, event_type: EventType, severity: SeverityLevel
    ) -> list[str]:
        """Generate preventive actions based on event type and severity."""
        actions = []

        # Severity-based actions
        if severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            actions.extend([
                "Pre-position additional inventory",
                "Verify and test backup supplier relationships",
                "Prepare customer communication templates",
            ])

        # Type-specific actions
        type_actions = {
            EventType.STRIKE: [
                "Review labor contract expiration dates",
                "Identify alternative logistics providers",
            ],
            EventType.WEATHER: [
                "Monitor long-range weather forecasts",
                "Review flood/storm insurance coverage",
            ],
            EventType.GEOPOLITICAL: [
                "Monitor political developments",
                "Review trade compliance requirements",
            ],
            EventType.FIRE: [
                "Verify fire safety certifications",
                "Review business interruption insurance",
            ],
            EventType.PANDEMIC: [
                "Review health and safety protocols",
                "Assess remote work capabilities",
            ],
        }

        actions.extend(type_actions.get(event_type, []))
        return actions[:5]


# =============================================================================
# Proactive Alert Generator
# =============================================================================


class ProactiveAlertGenerator:
    """
    Generates proactive alerts from predictions and forecasts.

    Triggers alerts when predictions exceed thresholds and includes
    recommended preventive actions.
    """

    # Default threshold for generating alerts
    DEFAULT_PROBABILITY_THRESHOLD = 0.5

    def __init__(self, probability_threshold: float | None = None):
        """
        Initialize the alert generator.

        Args:
            probability_threshold: Minimum probability to trigger alerts.
        """
        self.probability_threshold = (
            probability_threshold or self.DEFAULT_PROBABILITY_THRESHOLD
        )
        self._generated_alerts: list[PredictiveAlert] = []

    def generate_alerts_from_forecasts(
        self, forecasts: list[RiskForecast]
    ) -> list[PredictiveAlert]:
        """
        Generate proactive alerts from risk forecasts.

        Args:
            forecasts: List of risk forecasts.

        Returns:
            List of generated predictive alerts.
        """
        alerts = []

        for forecast in forecasts:
            if forecast.probability < self.probability_threshold:
                continue

            # Determine warning level based on probability and severity
            warning_level = self._determine_warning_level(
                forecast.probability, forecast.predicted_severity
            )

            alert = PredictiveAlert(
                alert_id=f"palert-{forecast.forecast_id}",
                forecast_id=forecast.forecast_id,
                warning_level=warning_level,
                title=f"Predicted {forecast.event_type.value} Risk: {forecast.location}",
                message=self._generate_alert_message(forecast),
                affected_products=forecast.affected_entities[:10],
                preventive_actions=forecast.preventive_actions,
                probability_threshold=self.probability_threshold,
            )

            alerts.append(alert)
            self._generated_alerts.append(alert)

        return alerts

    def generate_alerts_from_warnings(
        self, warnings: list[EarlyWarning]
    ) -> list[PredictiveAlert]:
        """
        Generate proactive alerts from early warnings.

        Args:
            warnings: List of early warnings.

        Returns:
            List of generated predictive alerts.
        """
        alerts = []

        for warning in warnings:
            if warning.signal_strength < 0.3:
                continue

            alert = PredictiveAlert(
                alert_id=f"walert-{warning.warning_id}",
                forecast_id="",
                warning_level=warning.warning_level,
                title=f"Early Warning: {warning.event_type.value} signals in {warning.location}",
                message=self._generate_warning_message(warning),
                affected_products=[],
                preventive_actions=warning.recommended_actions,
                probability_threshold=warning.signal_strength,
            )

            alerts.append(alert)
            self._generated_alerts.append(alert)

        return alerts

    def _determine_warning_level(
        self, probability: float, severity: SeverityLevel
    ) -> WarningLevel:
        """Determine warning level from probability and severity."""
        severity_weights = {
            SeverityLevel.LOW: 0.5,
            SeverityLevel.MEDIUM: 1.0,
            SeverityLevel.HIGH: 1.5,
            SeverityLevel.CRITICAL: 2.0,
        }

        weighted_score = probability * severity_weights.get(severity, 1.0)

        if weighted_score >= 1.4:
            return WarningLevel.CRITICAL
        elif weighted_score >= 1.0:
            return WarningLevel.WARNING
        elif weighted_score >= 0.6:
            return WarningLevel.ADVISORY
        else:
            return WarningLevel.WATCH

    def _generate_alert_message(self, forecast: RiskForecast) -> str:
        """Generate alert message from forecast."""
        return (
            f"Predictive analysis indicates a {forecast.probability:.0%} probability "
            f"of a {forecast.predicted_severity.value} severity {forecast.event_type.value} event "
            f"in {forecast.location} within the next "
            f"{(forecast.forecast_window_end - forecast.forecast_window_start).days} days. "
            f"Confidence interval: {forecast.confidence_interval[0]:.0%} - {forecast.confidence_interval[1]:.0%}."
        )

    def _generate_warning_message(self, warning: EarlyWarning) -> str:
        """Generate alert message from warning."""
        return (
            f"Early warning signals detected for {warning.event_type.value} risk in {warning.location}. "
            f"Signal strength: {warning.signal_strength:.0%}. "
            f"Contributing factors: {', '.join(warning.contributing_factors[:3])}."
        )

    def get_all_alerts(self) -> list[PredictiveAlert]:
        """Get all generated alerts."""
        return self._generated_alerts


# =============================================================================
# Accuracy Tracker
# =============================================================================


class ForecastAccuracyTracker:
    """
    Tracks and evaluates forecast accuracy for model improvement.

    Compares predictions to actual outcomes and calculates accuracy metrics.
    """

    def __init__(self):
        """Initialize the accuracy tracker."""
        self._accuracy_records: list[ForecastAccuracy] = []
        self._forecast_outcomes: dict[str, bool] = {}

    def record_outcome(
        self,
        forecast_id: str,
        actual_occurred: bool,
        actual_severity: SeverityLevel | None = None,
        actual_date: datetime | None = None,
    ) -> ForecastAccuracy:
        """
        Record the actual outcome for a forecast.

        Args:
            forecast_id: ID of the forecast.
            actual_occurred: Whether the event actually occurred.
            actual_severity: Actual severity if event occurred.
            actual_date: Actual date of event if occurred.

        Returns:
            ForecastAccuracy record.
        """
        # This would normally look up the original forecast
        # For now, create a basic accuracy record
        predicted_probability = 0.7  # Would come from stored forecast
        
        # Calculate prediction error
        if actual_occurred:
            prediction_error = 1.0 - predicted_probability
        else:
            prediction_error = predicted_probability

        # Calculate timing error if applicable
        timing_error = None
        if actual_date:
            # Would compare to forecast window
            timing_error = 0.0  # Placeholder

        accuracy = ForecastAccuracy(
            forecast_id=forecast_id,
            predicted_probability=predicted_probability,
            actual_occurred=actual_occurred,
            prediction_error=prediction_error,
            severity_match=True,  # Placeholder
            timing_error_days=timing_error,
        )

        self._accuracy_records.append(accuracy)
        self._forecast_outcomes[forecast_id] = actual_occurred

        return accuracy

    def calculate_metrics(self) -> dict[str, float]:
        """
        Calculate overall accuracy metrics.

        Returns:
            Dictionary of accuracy metrics.
        """
        if not self._accuracy_records:
            return {
                "total_forecasts": 0,
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "mean_prediction_error": 0.0,
                "brier_score": 0.0,
            }

        total = len(self._accuracy_records)
        
        # Count correct predictions
        true_positives = sum(
            1 for r in self._accuracy_records
            if r.predicted_probability >= 0.5 and r.actual_occurred
        )
        false_positives = sum(
            1 for r in self._accuracy_records
            if r.predicted_probability >= 0.5 and not r.actual_occurred
        )
        true_negatives = sum(
            1 for r in self._accuracy_records
            if r.predicted_probability < 0.5 and not r.actual_occurred
        )
        false_negatives = sum(
            1 for r in self._accuracy_records
            if r.predicted_probability < 0.5 and r.actual_occurred
        )

        # Calculate metrics
        accuracy = (true_positives + true_negatives) / total if total > 0 else 0.0
        
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )

        # Mean prediction error
        mean_error = sum(r.prediction_error for r in self._accuracy_records) / total

        # Brier score (lower is better)
        brier = sum(
            (r.predicted_probability - (1.0 if r.actual_occurred else 0.0)) ** 2
            for r in self._accuracy_records
        ) / total

        return {
            "total_forecasts": total,
            "accuracy": round(accuracy, 3),
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "mean_prediction_error": round(mean_error, 3),
            "brier_score": round(brier, 3),
        }

    def get_improvement_recommendations(self) -> list[str]:
        """
        Get recommendations for improving forecast accuracy.

        Returns:
            List of improvement recommendations.
        """
        metrics = self.calculate_metrics()
        recommendations = []

        if metrics["total_forecasts"] < 10:
            recommendations.append(
                "Collect more forecast outcomes to improve accuracy assessment"
            )

        if metrics["precision"] < 0.5:
            recommendations.append(
                "High false positive rate - consider raising probability threshold"
            )

        if metrics["recall"] < 0.5:
            recommendations.append(
                "Missing many actual events - consider lowering probability threshold"
            )

        if metrics["brier_score"] > 0.3:
            recommendations.append(
                "Overall calibration needs improvement - review pattern weights"
            )

        if metrics["mean_prediction_error"] > 0.4:
            recommendations.append(
                "Prediction errors are high - consider additional data sources"
            )

        return recommendations if recommendations else ["Forecast accuracy is acceptable"]
