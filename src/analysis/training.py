"""
Training Data Management for DSPy Module Compilation.

Provides utilities for managing training examples, versioning,
and triggering recompilation when data changes.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TrainingExample:
    """A single training example for DSPy compilation."""

    news_content: str
    expected_location: str
    expected_company: str
    expected_event_type: str
    expected_severity: str
    expected_confidence: str = "0.9"
    expected_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingDataset:
    """Collection of training examples with versioning."""

    name: str
    examples: list[TrainingExample]
    version: str = ""
    created_at: str = ""
    description: str = ""

    def __post_init__(self):
        if not self.version:
            self.version = self._compute_version()
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def _compute_version(self) -> str:
        """Compute a version hash based on examples."""
        content = json.dumps(
            [
                {
                    "news_content": e.news_content,
                    "expected_location": e.expected_location,
                    "expected_company": e.expected_company,
                    "expected_event_type": e.expected_event_type,
                    "expected_severity": e.expected_severity,
                }
                for e in self.examples
            ],
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:12]


class TrainingDataManager:
    """
    Manages training data for DSPy module compilation.

    Features:
    - Load/save training datasets
    - Version tracking
    - Detect changes requiring recompilation
    - Performance tracking across versions
    """

    def __init__(self, data_dir: str | Path = "data/training"):
        """
        Initialize the training data manager.

        Args:
            data_dir: Directory to store training data files.
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._current_version: str | None = None
        self._performance_history: list[dict[str, Any]] = []

    def create_default_examples(self) -> list[TrainingExample]:
        """Create default training examples for initial compilation."""
        return [
            TrainingExample(
                news_content="Workers at the Port of Vancouver have voted to strike starting Monday, causing significant disruptions to shipping operations across the Pacific coast.",
                expected_location="Vancouver",
                expected_company="Port of Vancouver",
                expected_event_type="Strike",
                expected_severity="High",
                expected_confidence="0.92",
                expected_summary="Port workers voting to strike will disrupt Pacific coast shipping operations.",
            ),
            TrainingExample(
                news_content="Typhoon Mangkhut has caused severe damage to manufacturing facilities in Taiwan's Hsinchu Science Park, affecting TSMC and other semiconductor companies.",
                expected_location="Taiwan",
                expected_company="TSMC",
                expected_event_type="Weather",
                expected_severity="Critical",
                expected_confidence="0.95",
                expected_summary="Typhoon damage to Taiwan semiconductor facilities affects major chipmakers.",
            ),
            TrainingExample(
                news_content="German auto parts supplier Continental AG has filed for bankruptcy protection amid declining electric vehicle component orders.",
                expected_location="Germany",
                expected_company="Continental AG",
                expected_event_type="Bankruptcy",
                expected_severity="High",
                expected_confidence="0.88",
                expected_summary="Major German auto supplier Continental AG files for bankruptcy protection.",
            ),
            TrainingExample(
                news_content="Fire breaks out at Samsung's Pyeongtaek semiconductor plant, production of memory chips temporarily halted.",
                expected_location="South Korea",
                expected_company="Samsung",
                expected_event_type="Fire",
                expected_severity="High",
                expected_confidence="0.91",
                expected_summary="Samsung semiconductor plant fire halts memory chip production.",
            ),
            TrainingExample(
                news_content="New US trade sanctions on Chinese technology companies affect exports of AI chips and advanced semiconductors from Nvidia and AMD.",
                expected_location="United States",
                expected_company="Nvidia, AMD",
                expected_event_type="Geopolitical",
                expected_severity="High",
                expected_confidence="0.89",
                expected_summary="US trade sanctions restrict AI chip exports to China affecting major chipmakers.",
            ),
            TrainingExample(
                news_content="A major ransomware attack has crippled logistics systems at Maersk shipping company, causing worldwide container tracking failures.",
                expected_location="Unknown",
                expected_company="Maersk",
                expected_event_type="CyberAttack",
                expected_severity="Critical",
                expected_confidence="0.94",
                expected_summary="Ransomware attack on Maersk disrupts global container shipping logistics.",
            ),
            TrainingExample(
                news_content="Flooding along the Mekong River has disrupted operations at multiple electronics factories in Vietnam, including suppliers to Apple and Samsung.",
                expected_location="Vietnam",
                expected_company="Apple, Samsung",
                expected_event_type="Weather",
                expected_severity="Medium",
                expected_confidence="0.85",
                expected_summary="Mekong River flooding disrupts Vietnam electronics manufacturing.",
            ),
            TrainingExample(
                news_content="The Suez Canal remains blocked after the container ship Ever Given ran aground, affecting global trade routes and causing delays for thousands of vessels.",
                expected_location="Egypt",
                expected_company="Evergreen Marine",
                expected_event_type="Transport",
                expected_severity="Critical",
                expected_confidence="0.97",
                expected_summary="Suez Canal blockage by Ever Given causes massive global shipping delays.",
            ),
        ]

    def save_dataset(self, dataset: TrainingDataset) -> Path:
        """
        Save a training dataset to disk.

        Args:
            dataset: The dataset to save.

        Returns:
            Path to the saved file.
        """
        filepath = self.data_dir / f"{dataset.name}_{dataset.version}.json"

        data = {
            "name": dataset.name,
            "version": dataset.version,
            "created_at": dataset.created_at,
            "description": dataset.description,
            "example_count": len(dataset.examples),
            "examples": [
                {
                    "news_content": e.news_content,
                    "expected_location": e.expected_location,
                    "expected_company": e.expected_company,
                    "expected_event_type": e.expected_event_type,
                    "expected_severity": e.expected_severity,
                    "expected_confidence": e.expected_confidence,
                    "expected_summary": e.expected_summary,
                    "metadata": e.metadata,
                }
                for e in dataset.examples
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(
            "Saved training dataset",
            name=dataset.name,
            version=dataset.version,
            examples=len(dataset.examples),
        )

        return filepath

    def load_dataset(self, filepath: str | Path) -> TrainingDataset:
        """
        Load a training dataset from disk.

        Args:
            filepath: Path to the dataset file.

        Returns:
            Loaded TrainingDataset.
        """
        with open(filepath) as f:
            data = json.load(f)

        examples = [
            TrainingExample(
                news_content=e["news_content"],
                expected_location=e["expected_location"],
                expected_company=e["expected_company"],
                expected_event_type=e["expected_event_type"],
                expected_severity=e["expected_severity"],
                expected_confidence=e.get("expected_confidence", "0.9"),
                expected_summary=e.get("expected_summary", ""),
                metadata=e.get("metadata", {}),
            )
            for e in data["examples"]
        ]

        return TrainingDataset(
            name=data["name"],
            examples=examples,
            version=data["version"],
            created_at=data["created_at"],
            description=data.get("description", ""),
        )

    def get_latest_version(self, dataset_name: str) -> str | None:
        """
        Get the latest version of a dataset.

        Args:
            dataset_name: Name of the dataset.

        Returns:
            Version string or None if no versions exist.
        """
        pattern = f"{dataset_name}_*.json"
        files = list(self.data_dir.glob(pattern))

        if not files:
            return None

        # Sort by modification time and return latest
        latest = max(files, key=lambda f: f.stat().st_mtime)
        # Extract version from filename
        version = latest.stem.split("_")[-1]
        return version

    def needs_recompilation(self, dataset: TrainingDataset) -> bool:
        """
        Check if a dataset change requires recompilation.

        Args:
            dataset: The current dataset.

        Returns:
            True if recompilation is needed.
        """
        latest_version = self.get_latest_version(dataset.name)

        if latest_version is None:
            # No previous version, needs compilation
            return True

        if dataset.version != latest_version:
            logger.info(
                "Dataset version changed, recompilation needed",
                old_version=latest_version,
                new_version=dataset.version,
            )
            return True

        return False

    def record_performance(
        self,
        dataset_version: str,
        accuracy: float,
        extraction_count: int,
        avg_confidence: float,
    ) -> None:
        """
        Record performance metrics for a dataset version.

        Args:
            dataset_version: Version of the dataset used.
            accuracy: Extraction accuracy (0-1).
            extraction_count: Number of extractions performed.
            avg_confidence: Average confidence score.
        """
        record = {
            "version": dataset_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "accuracy": accuracy,
            "extraction_count": extraction_count,
            "avg_confidence": avg_confidence,
        }

        self._performance_history.append(record)
        logger.info("Recorded performance metrics", **record)

    def get_performance_trend(self) -> list[dict[str, Any]]:
        """Get performance history for analysis."""
        return self._performance_history

    def convert_to_dspy_examples(
        self, dataset: TrainingDataset
    ) -> list[dict[str, str]]:
        """
        Convert training examples to DSPy-compatible format.

        Args:
            dataset: The training dataset.

        Returns:
            List of dictionaries suitable for DSPy compilation.
        """
        return [
            {
                "news_content": e.news_content,
                "location": e.expected_location,
                "company": e.expected_company,
                "event_type": e.expected_event_type,
                "severity": e.expected_severity,
                "confidence": e.expected_confidence,
                "summary": e.expected_summary,
            }
            for e in dataset.examples
        ]
