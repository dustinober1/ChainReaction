"""
ChainReaction Analysis Module.

Contains DSPy-powered extraction modules and validation utilities.
"""

from src.analysis.signatures import RiskExtractor, EntityExtractor, ImpactAssessor
from src.analysis.modules import RiskAnalyst, EntityAnalyst, ImpactAnalyst
from src.analysis.validation import (
    ExtractionValidator,
    ConfidenceScorer,
    ExtractionErrorHandler,
    ValidationResult,
)
from src.analysis.training import (
    TrainingExample,
    TrainingDataset,
    TrainingDataManager,
)
from src.analysis.prioritization import (
    RiskPrioritizer,
    PriorityWeights,
    PrioritizedRisk,
    sort_by_severity,
    sort_by_timeline,
    sort_by_affected_count,
)
from src.analysis.reporting import (
    ReportGenerator,
    ImpactReport,
    TimelineEstimate,
    MitigationOption,
    ReportFormat,
)
from src.analysis.integrity import (
    EntityValidator,
    ReferentialIntegrityChecker,
    DataIntegrityManager,
    IntegrityCheckResult,
    format_validation_errors,
)
from src.analysis.resilience import (
    ResilienceScorer,
    ResilienceHistoryTracker,
    ResilienceRecalculator,
    RedundancyInfo,
)
from src.analysis.predictive import (
    PatternAnalyzer,
    EarlyWarningDetector,
    RiskForecaster,
    ProactiveAlertGenerator,
    ForecastAccuracyTracker,
    TrendDirection,
    WarningLevel,
    SeasonalPattern,
    RiskPattern,
    EarlyWarning,
    RiskForecast,
    ForecastAccuracy,
    PredictiveAlert,
)
from src.analysis.mitigation import (
    MitigationGenerator,
    MitigationRanker,
    ImpactSimulator,
    OutcomeTracker,
    CoordinatedStrategyPlanner,
    MitigationType,
    MitigationStatus,
    FeasibilityLevel,
    MitigationOption as MitigationOptionModel,
    ImpactSimulation,
    MitigationOutcome,
    CoordinatedStrategy,
)
from src.analysis.alerts import (
    AlertManager,
    AlertRuleManager,
    ChannelDeliverer,
    AcknowledgmentTracker,
    LatencyMonitor,
    DeliveryStatus,
    RuleChangeType,
    AlertInstance,
    RuleChange,
    DeliveryMetrics,
)

__all__ = [
    # Signatures
    "RiskExtractor",
    "EntityExtractor",
    "ImpactAssessor",
    # Modules
    "RiskAnalyst",
    "EntityAnalyst",
    "ImpactAnalyst",
    # Validation
    "ExtractionValidator",
    "ConfidenceScorer",
    "ExtractionErrorHandler",
    "ValidationResult",
    # Training
    "TrainingExample",
    "TrainingDataset",
    "TrainingDataManager",
    # Prioritization
    "RiskPrioritizer",
    "PriorityWeights",
    "PrioritizedRisk",
    "sort_by_severity",
    "sort_by_timeline",
    "sort_by_affected_count",
    # Reporting
    "ReportGenerator",
    "ImpactReport",
    "TimelineEstimate",
    "MitigationOption",
    "ReportFormat",
    # Integrity
    "EntityValidator",
    "ReferentialIntegrityChecker",
    "DataIntegrityManager",
    "IntegrityCheckResult",
    "format_validation_errors",
    # Resilience
    "ResilienceScorer",
    "ResilienceHistoryTracker",
    "ResilienceRecalculator",
    "RedundancyInfo",
    # Predictive Analytics
    "PatternAnalyzer",
    "EarlyWarningDetector",
    "RiskForecaster",
    "ProactiveAlertGenerator",
    "ForecastAccuracyTracker",
    "TrendDirection",
    "WarningLevel",
    "SeasonalPattern",
    "RiskPattern",
    "EarlyWarning",
    "RiskForecast",
    "ForecastAccuracy",
    "PredictiveAlert",
    # Mitigation
    "MitigationGenerator",
    "MitigationRanker",
    "ImpactSimulator",
    "OutcomeTracker",
    "CoordinatedStrategyPlanner",
    "MitigationType",
    "MitigationStatus",
    "FeasibilityLevel",
    "MitigationOptionModel",
    "ImpactSimulation",
    "MitigationOutcome",
    "CoordinatedStrategy",
    # Alerts
    "AlertManager",
    "AlertRuleManager",
    "ChannelDeliverer",
    "AcknowledgmentTracker",
    "LatencyMonitor",
    "DeliveryStatus",
    "RuleChangeType",
    "AlertInstance",
    "RuleChange",
    "DeliveryMetrics",
]
