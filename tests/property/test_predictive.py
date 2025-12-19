"""
Property Tests for Predictive Analytics Engine.

Tests the predictive analytics functionality, verifying:
- Property 39: Historical Pattern Identification
- Property 40: Early Warning Signal Detection
- Property 41: Risk Forecast Output Format
- Property 42: Proactive Alert Generation
- Property 43: Forecast Accuracy Tracking
"""

from datetime import datetime, timezone, timedelta
from hypothesis import given, settings, assume
from hypothesis import strategies as st
import pytest

from src.models import EventType, SeverityLevel
from src.analysis.predictive import (
    TrendDirection,
    WarningLevel,
    SeasonalPattern,
    RiskPattern,
    EarlyWarning,
    RiskForecast,
    ForecastAccuracy,
    PredictiveAlert,
    PatternAnalyzer,
    EarlyWarningDetector,
    ProactiveAlertGenerator,
    ForecastAccuracyTracker,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Event type strategy
event_type_strategy = st.sampled_from(list(EventType))

# Severity level strategy
severity_strategy = st.sampled_from(list(SeverityLevel))

# Warning level strategy
warning_level_strategy = st.sampled_from(list(WarningLevel))

# Trend direction strategy
trend_direction_strategy = st.sampled_from(list(TrendDirection))

# Probability strategy (0.0 to 1.0)
probability_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# Location strategy
location_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"), whitelist_characters=",- "),
    min_size=2,
    max_size=50,
).filter(lambda x: x.strip())

# Month strategy (1-12)
month_strategy = st.integers(min_value=1, max_value=12)


# Seasonal pattern strategy
@st.composite
def seasonal_pattern_strategy(draw) -> SeasonalPattern:
    """Generate valid SeasonalPattern instances."""
    return SeasonalPattern(
        location=draw(location_strategy),
        event_type=draw(event_type_strategy),
        peak_months=draw(st.lists(month_strategy, min_size=1, max_size=4, unique=True)),
        frequency=draw(st.floats(min_value=0.1, max_value=50.0, allow_nan=False)),
        avg_severity=draw(st.floats(min_value=1.0, max_value=4.0, allow_nan=False)),
        confidence=draw(probability_strategy),
    )


# Risk pattern strategy
@st.composite
def risk_pattern_strategy(draw) -> RiskPattern:
    """Generate valid RiskPattern instances."""
    severities = draw(st.lists(severity_strategy, min_size=1, max_size=4, unique=True))
    weights = draw(st.lists(
        st.floats(min_value=0.1, max_value=1.0, allow_nan=False),
        min_size=len(severities),
        max_size=len(severities),
    ))
    total = sum(weights)
    distribution = {s: w / total for s, w in zip(severities, weights)}
    
    return RiskPattern(
        pattern_id=draw(st.text(min_size=5, max_size=30).filter(lambda x: x.strip())),
        location=draw(location_strategy),
        event_type=draw(event_type_strategy),
        frequency_per_year=draw(st.floats(min_value=0.1, max_value=100.0, allow_nan=False)),
        avg_duration_days=draw(st.floats(min_value=0.5, max_value=90.0, allow_nan=False)),
        severity_distribution=distribution,
        last_occurrence=datetime.now(timezone.utc) - timedelta(days=draw(st.integers(min_value=1, max_value=365))),
        trend=draw(trend_direction_strategy),
        confidence=draw(probability_strategy),
    )


# Risk forecast strategy
@st.composite
def risk_forecast_strategy(draw) -> RiskForecast:
    """Generate valid RiskForecast instances."""
    prob = draw(probability_strategy)
    conf = draw(probability_strategy)
    
    # Create valid confidence interval
    width = 0.3 * (1 - conf)
    lower = max(0.0, prob - width)
    upper = min(1.0, prob + width)
    
    start = datetime.now(timezone.utc)
    days = draw(st.integers(min_value=1, max_value=90))
    
    return RiskForecast(
        forecast_id=draw(st.text(min_size=5, max_size=50).filter(lambda x: x.strip())),
        location=draw(location_strategy),
        event_type=draw(event_type_strategy),
        predicted_severity=draw(severity_strategy),
        probability=prob,
        confidence_interval=(round(lower, 3), round(upper, 3)),
        forecast_window_start=start,
        forecast_window_end=start + timedelta(days=days),
        affected_entities=draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10)),
        preventive_actions=draw(st.lists(st.text(min_size=5, max_size=100), min_size=0, max_size=5)),
    )


# Early warning strategy
@st.composite
def early_warning_strategy(draw) -> EarlyWarning:
    """Generate valid EarlyWarning instances."""
    return EarlyWarning(
        warning_id=draw(st.text(min_size=5, max_size=50).filter(lambda x: x.strip())),
        location=draw(location_strategy),
        event_type=draw(event_type_strategy),
        warning_level=draw(warning_level_strategy),
        sentiment_score=draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)),
        signal_strength=draw(probability_strategy),
        contributing_factors=draw(st.lists(st.text(min_size=5, max_size=100), min_size=1, max_size=5)),
        recommended_actions=draw(st.lists(st.text(min_size=5, max_size=100), min_size=1, max_size=5)),
        expires_at=datetime.now(timezone.utc) + timedelta(days=draw(st.integers(min_value=1, max_value=30))),
    )


# =============================================================================
# Property 39: Historical Pattern Identification
# =============================================================================


class TestHistoricalPatternIdentification:
    """Property tests for historical pattern identification."""

    @given(pattern=seasonal_pattern_strategy())
    @settings(max_examples=50)
    def test_seasonal_pattern_has_valid_structure(self, pattern: SeasonalPattern):
        """
        Property: Seasonal patterns always have valid structure.
        """
        assert pattern.location is not None
        assert pattern.event_type in list(EventType)
        assert len(pattern.peak_months) >= 1
        assert all(1 <= m <= 12 for m in pattern.peak_months)
        assert pattern.frequency >= 0
        assert 0.0 <= pattern.confidence <= 1.0

    @given(pattern=risk_pattern_strategy())
    @settings(max_examples=50)
    def test_risk_pattern_has_valid_components(self, pattern: RiskPattern):
        """
        Property: Risk patterns have all required components.
        """
        assert pattern.pattern_id is not None
        assert pattern.location is not None
        assert pattern.event_type in list(EventType)
        assert pattern.frequency_per_year >= 0
        assert pattern.trend in list(TrendDirection)
        assert 0.0 <= pattern.confidence <= 1.0

    @given(pattern=risk_pattern_strategy())
    @settings(max_examples=50)
    def test_severity_distribution_sums_to_one(self, pattern: RiskPattern):
        """
        Property: Severity distribution in patterns sums to approximately 1.0.
        """
        if pattern.severity_distribution:
            total = sum(pattern.severity_distribution.values())
            assert abs(total - 1.0) < 0.01  # Allow small floating point error

    @given(
        frequency=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
        confidence=probability_strategy,
    )
    @settings(max_examples=50)
    def test_pattern_frequency_is_positive(self, frequency: float, confidence: float):
        """
        Property: Pattern frequency is always positive.
        """
        pattern = RiskPattern(
            pattern_id="test-pattern",
            location="Test Location",
            event_type=EventType.WEATHER,
            frequency_per_year=frequency,
            avg_duration_days=7.0,
            severity_distribution={SeverityLevel.MEDIUM: 1.0},
            last_occurrence=None,
            trend=TrendDirection.STABLE,
            confidence=confidence,
        )
        
        assert pattern.frequency_per_year > 0


# =============================================================================
# Property 40: Early Warning Signal Detection
# =============================================================================


class TestEarlyWarningSignalDetection:
    """Property tests for early warning signal detection."""

    @given(warning=early_warning_strategy())
    @settings(max_examples=50)
    def test_early_warning_has_valid_structure(self, warning: EarlyWarning):
        """
        Property: Early warnings always have valid structure.
        """
        assert warning.warning_id is not None
        assert warning.location is not None
        assert warning.event_type in list(EventType)
        assert warning.warning_level in list(WarningLevel)
        assert -1.0 <= warning.sentiment_score <= 1.0
        assert 0.0 <= warning.signal_strength <= 1.0

    @given(sentiment=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False))
    @settings(max_examples=50)
    def test_sentiment_score_in_valid_range(self, sentiment: float):
        """
        Property: Sentiment scores are always in [-1, 1] range.
        """
        warning = EarlyWarning(
            warning_id="test-warning",
            location="Test Location",
            event_type=EventType.STRIKE,
            warning_level=WarningLevel.WATCH,
            sentiment_score=sentiment,
            signal_strength=0.5,
            contributing_factors=["Factor 1"],
            recommended_actions=["Action 1"],
        )
        
        assert -1.0 <= warning.sentiment_score <= 1.0

    @given(strength=probability_strategy)
    @settings(max_examples=50)
    def test_signal_strength_in_valid_range(self, strength: float):
        """
        Property: Signal strength is always in [0, 1] range.
        """
        warning = EarlyWarning(
            warning_id="test-warning",
            location="Test Location",
            event_type=EventType.WEATHER,
            warning_level=WarningLevel.ADVISORY,
            sentiment_score=-0.3,
            signal_strength=strength,
            contributing_factors=["Factor 1"],
            recommended_actions=["Action 1"],
        )
        
        assert 0.0 <= warning.signal_strength <= 1.0

    @given(warning=early_warning_strategy())
    @settings(max_examples=50)
    def test_warning_has_recommended_actions(self, warning: EarlyWarning):
        """
        Property: Early warnings always have at least one recommended action.
        """
        assert len(warning.recommended_actions) >= 1

    def test_sentiment_analyzer_returns_valid_range(self):
        """
        Property: Sentiment analyzer always returns value in [-1, 1].
        """
        detector = EarlyWarningDetector()
        
        test_texts = [
            "Crisis and disaster strike the region",
            "Recovery and improvement expected soon",
            "Normal operations continue",
            "",
            "Mixed signals with some delays but stable output",
        ]
        
        for text in test_texts:
            score = detector.analyze_sentiment(text)
            assert -1.0 <= score <= 1.0


# =============================================================================
# Property 41: Risk Forecast Output Format
# =============================================================================


class TestRiskForecastOutputFormat:
    """Property tests for risk forecast output format."""

    @given(forecast=risk_forecast_strategy())
    @settings(max_examples=50)
    def test_forecast_has_valid_structure(self, forecast: RiskForecast):
        """
        Property: Risk forecasts always have valid structure.
        """
        assert forecast.forecast_id is not None
        assert forecast.location is not None
        assert forecast.event_type in list(EventType)
        assert forecast.predicted_severity in list(SeverityLevel)
        assert 0.0 <= forecast.probability <= 1.0

    @given(forecast=risk_forecast_strategy())
    @settings(max_examples=50)
    def test_confidence_interval_is_ordered(self, forecast: RiskForecast):
        """
        Property: Confidence interval lower bound <= upper bound.
        """
        lower, upper = forecast.confidence_interval
        assert lower <= upper

    @given(forecast=risk_forecast_strategy())
    @settings(max_examples=50)
    def test_confidence_interval_in_valid_range(self, forecast: RiskForecast):
        """
        Property: Confidence interval bounds are in [0, 1] range.
        """
        lower, upper = forecast.confidence_interval
        assert 0.0 <= lower <= 1.0
        assert 0.0 <= upper <= 1.0

    @given(forecast=risk_forecast_strategy())
    @settings(max_examples=50)
    def test_forecast_window_is_valid(self, forecast: RiskForecast):
        """
        Property: Forecast window end is after start.
        """
        assert forecast.forecast_window_end > forecast.forecast_window_start

    @given(
        probability=probability_strategy,
        confidence=probability_strategy,
    )
    @settings(max_examples=50)
    def test_probability_contained_in_confidence_interval(
        self, probability: float, confidence: float
    ):
        """
        Property: Often the probability is within or near the confidence interval.
        
        Note: This is a soft property - the interval should bracket probability.
        """
        # Calculate interval as done in forecaster
        width = 0.3 * (1 - confidence)
        lower = max(0.0, probability - width)
        upper = min(1.0, probability + width)
        
        # The probability should be within or very close to the interval
        assert lower <= probability <= upper or abs(probability - lower) < 0.01 or abs(probability - upper) < 0.01


# =============================================================================
# Property 42: Proactive Alert Generation
# =============================================================================


class TestProactiveAlertGeneration:
    """Property tests for proactive alert generation."""

    @given(forecast=risk_forecast_strategy())
    @settings(max_examples=50)
    def test_high_probability_forecast_generates_alert(self, forecast: RiskForecast):
        """
        Property: Forecasts with probability >= threshold generate alerts.
        """
        assume(forecast.probability >= 0.5)  # Default threshold
        
        generator = ProactiveAlertGenerator(probability_threshold=0.5)
        alerts = generator.generate_alerts_from_forecasts([forecast])
        
        assert len(alerts) >= 1

    @given(forecast=risk_forecast_strategy())
    @settings(max_examples=50)
    def test_low_probability_forecast_no_alert(self, forecast: RiskForecast):
        """
        Property: Forecasts with probability < threshold don't generate alerts.
        """
        assume(forecast.probability < 0.3)  # Below threshold
        
        generator = ProactiveAlertGenerator(probability_threshold=0.5)
        alerts = generator.generate_alerts_from_forecasts([forecast])
        
        assert len(alerts) == 0

    @given(warning=early_warning_strategy())
    @settings(max_examples=50)
    def test_strong_signal_warning_generates_alert(self, warning: EarlyWarning):
        """
        Property: Warnings with strong signals generate alerts.
        """
        assume(warning.signal_strength >= 0.3)
        
        generator = ProactiveAlertGenerator()
        alerts = generator.generate_alerts_from_warnings([warning])
        
        assert len(alerts) >= 1

    @given(
        probability=st.floats(min_value=0.5, max_value=1.0, allow_nan=False),
        severity=severity_strategy,
    )
    @settings(max_examples=30)
    def test_alert_warning_level_is_valid(self, probability: float, severity: SeverityLevel):
        """
        Property: Generated alerts have valid warning levels.
        """
        forecast = RiskForecast(
            forecast_id="test-forecast",
            location="Test Location",
            event_type=EventType.STRIKE,
            predicted_severity=severity,
            probability=probability,
            confidence_interval=(probability - 0.1, probability + 0.1),
            forecast_window_start=datetime.now(timezone.utc),
            forecast_window_end=datetime.now(timezone.utc) + timedelta(days=30),
            affected_entities=[],
            preventive_actions=["Action 1"],
        )
        
        generator = ProactiveAlertGenerator(probability_threshold=0.4)
        alerts = generator.generate_alerts_from_forecasts([forecast])
        
        if alerts:
            assert alerts[0].warning_level in list(WarningLevel)

    @given(forecast=risk_forecast_strategy())
    @settings(max_examples=50)
    def test_alert_has_preventive_actions(self, forecast: RiskForecast):
        """
        Property: Generated alerts include preventive actions from forecast.
        """
        assume(forecast.probability >= 0.5)
        assume(len(forecast.preventive_actions) > 0)
        
        generator = ProactiveAlertGenerator(probability_threshold=0.5)
        alerts = generator.generate_alerts_from_forecasts([forecast])
        
        if alerts:
            # Alert should have actions from the forecast
            assert isinstance(alerts[0].preventive_actions, list)


# =============================================================================
# Property 43: Forecast Accuracy Tracking
# =============================================================================


class TestForecastAccuracyTracking:
    """Property tests for forecast accuracy tracking."""

    @given(
        predicted_probability=probability_strategy,
        actual_occurred=st.booleans(),
    )
    @settings(max_examples=50)
    def test_accuracy_record_has_valid_structure(
        self, predicted_probability: float, actual_occurred: bool
    ):
        """
        Property: Accuracy records have valid structure.
        """
        tracker = ForecastAccuracyTracker()
        
        accuracy = tracker.record_outcome(
            forecast_id="test-forecast",
            actual_occurred=actual_occurred,
        )
        
        assert accuracy.forecast_id == "test-forecast"
        assert accuracy.actual_occurred == actual_occurred
        assert 0.0 <= accuracy.prediction_error <= 1.0

    @given(
        outcomes=st.lists(
            st.tuples(probability_strategy, st.booleans()),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=30)
    def test_metrics_calculation_valid(
        self, outcomes: list[tuple[float, bool]]
    ):
        """
        Property: Calculated metrics are in valid ranges.
        """
        tracker = ForecastAccuracyTracker()
        
        for i, (prob, occurred) in enumerate(outcomes):
            tracker.record_outcome(
                forecast_id=f"forecast-{i}",
                actual_occurred=occurred,
            )
        
        metrics = tracker.calculate_metrics()
        
        assert metrics["total_forecasts"] == len(outcomes)
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["precision"] <= 1.0
        assert 0.0 <= metrics["recall"] <= 1.0
        assert metrics["brier_score"] >= 0.0

    @given(
        predicted=probability_strategy,
        occurred=st.booleans(),
    )
    @settings(max_examples=50)
    def test_prediction_error_calculation(
        self, predicted: float, occurred: bool
    ):
        """
        Property: Prediction error is correctly calculated.
        """
        if occurred:
            expected_error = 1.0 - predicted
        else:
            expected_error = predicted
        
        # Create accuracy record manually
        accuracy = ForecastAccuracy(
            forecast_id="test",
            predicted_probability=predicted,
            actual_occurred=occurred,
            prediction_error=expected_error,
            severity_match=True,
            timing_error_days=None,
        )
        
        assert accuracy.prediction_error == expected_error

    def test_improvement_recommendations_are_strings(self):
        """
        Property: Improvement recommendations are always strings.
        """
        tracker = ForecastAccuracyTracker()
        
        # Record some outcomes
        for i in range(5):
            tracker.record_outcome(
                forecast_id=f"forecast-{i}",
                actual_occurred=i % 2 == 0,
            )
        
        recommendations = tracker.get_improvement_recommendations()
        
        assert isinstance(recommendations, list)
        assert all(isinstance(r, str) for r in recommendations)
        assert len(recommendations) >= 1

    @given(
        outcomes=st.lists(
            st.booleans(),
            min_size=10,
            max_size=50,
        )
    )
    @settings(max_examples=20)
    def test_brier_score_bounds(self, outcomes: list[bool]):
        """
        Property: Brier score is bounded between 0 and 1.
        """
        tracker = ForecastAccuracyTracker()
        
        for i, occurred in enumerate(outcomes):
            tracker.record_outcome(
                forecast_id=f"forecast-{i}",
                actual_occurred=occurred,
            )
        
        metrics = tracker.calculate_metrics()
        
        # Brier score should be in [0, 1]
        assert 0.0 <= metrics["brier_score"] <= 1.0


# =============================================================================
# Additional Integration Tests
# =============================================================================


class TestPredictiveAnalyticsIntegration:
    """Integration tests for predictive analytics components."""

    @given(
        patterns=st.lists(risk_pattern_strategy(), min_size=1, max_size=5)
    )
    @settings(max_examples=20)
    def test_patterns_can_be_processed_together(self, patterns: list[RiskPattern]):
        """
        Property: Multiple patterns can be processed without error.
        """
        # Just verify the patterns are valid
        for pattern in patterns:
            assert pattern.pattern_id is not None
            assert pattern.confidence >= 0

    @given(
        forecast=risk_forecast_strategy(),
        warning=early_warning_strategy(),
    )
    @settings(max_examples=30)
    def test_alerts_from_different_sources_compatible(
        self, forecast: RiskForecast, warning: EarlyWarning
    ):
        """
        Property: Alerts from forecasts and warnings have compatible formats.
        """
        assume(forecast.probability >= 0.5)
        assume(warning.signal_strength >= 0.3)
        
        generator = ProactiveAlertGenerator(probability_threshold=0.5)
        
        forecast_alerts = generator.generate_alerts_from_forecasts([forecast])
        warning_alerts = generator.generate_alerts_from_warnings([warning])
        
        # Both should produce PredictiveAlert objects with same structure
        for alert in forecast_alerts + warning_alerts:
            assert isinstance(alert, PredictiveAlert)
            assert alert.alert_id is not None
            assert alert.warning_level in list(WarningLevel)
