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
]
