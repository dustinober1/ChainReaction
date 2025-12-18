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
]
