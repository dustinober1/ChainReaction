"""
Agent State Management for LangGraph Orchestration.

Defines the state structure used to coordinate between Scout Agents,
Analysis modules, and the GraphRAG engine.
"""

from datetime import datetime
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field

from src.models import (
    Alert,
    ImpactAssessment,
    ProcessingError,
    RawEvent,
    RiskEvent,
)


def add_to_list(existing: list, new: list) -> list:
    """Reducer function to append new items to existing list."""
    return existing + new


def replace_value(existing, new):
    """Reducer function to replace a value."""
    return new


class AgentState(TypedDict):
    """
    State structure for LangGraph workflow coordination.

    This state is passed between workflow nodes and maintains
    the complete context of the risk monitoring pipeline.

    Attributes:
        current_events: Raw events discovered by the Scout Agent
        extracted_risks: Structured risk events from DSPy analysis
        validated_risks: Risks that passed validation checks
        impact_assessments: Completed impact assessments
        alerts_generated: Alerts created for significant risks
        processing_errors: Errors encountered during processing
        iteration_count: Number of monitoring iterations completed
        last_run_at: Timestamp of the last monitoring run
    """

    # Event pipeline state
    current_events: Annotated[list[RawEvent], add_to_list]
    extracted_risks: Annotated[list[RiskEvent], add_to_list]
    validated_risks: Annotated[list[RiskEvent], add_to_list]
    impact_assessments: Annotated[list[ImpactAssessment], add_to_list]
    alerts_generated: Annotated[list[Alert], add_to_list]

    # Error tracking
    processing_errors: Annotated[list[ProcessingError], add_to_list]

    # Workflow metadata
    iteration_count: Annotated[int, replace_value]
    last_run_at: Annotated[datetime | None, replace_value]
    is_running: Annotated[bool, replace_value]


class WorkflowConfig(BaseModel):
    """Configuration for the LangGraph workflow."""

    monitor_interval_seconds: int = Field(
        default=300, description="Interval between monitoring cycles"
    )
    max_events_per_cycle: int = Field(
        default=50, description="Maximum events to process per cycle"
    )
    confidence_threshold: float = Field(
        default=0.7, description="Minimum confidence for risk acceptance"
    )
    max_retries: int = Field(default=3, description="Maximum retries for failed operations")
    timeout_seconds: int = Field(default=60, description="Operation timeout in seconds")


def create_initial_state() -> AgentState:
    """Create a fresh initial state for the workflow."""
    return AgentState(
        current_events=[],
        extracted_risks=[],
        validated_risks=[],
        impact_assessments=[],
        alerts_generated=[],
        processing_errors=[],
        iteration_count=0,
        last_run_at=None,
        is_running=False,
    )
