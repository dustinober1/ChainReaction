"""
LangGraph Workflow Orchestration for Supply Chain Risk Monitoring.

Implements the complete workflow coordination using LangGraph,
including conditional routing, error handling, and state persistence.
"""

from datetime import datetime, timezone
from typing import Any, Callable, Literal
import asyncio
import json
from pathlib import Path

from langgraph.graph import StateGraph, END
import structlog

from src.agents.state import AgentState, WorkflowConfig, create_initial_state
from src.agents.nodes import (
    monitor_node,
    extract_node,
    validate_node,
    analyze_node,
    alert_node,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Conditional Edge Functions
# =============================================================================


def should_extract(state: AgentState) -> Literal["extract", "end"]:
    """
    Determine if extraction should proceed.

    Args:
        state: Current workflow state.

    Returns:
        "extract" if there are events to process, "end" otherwise.
    """
    events = state.get("current_events", [])
    if events and len(events) > 0:
        return "extract"
    return "end"


def should_validate(state: AgentState) -> Literal["validate", "end"]:
    """
    Determine if validation should proceed.

    Args:
        state: Current workflow state.

    Returns:
        "validate" if there are risks to validate, "end" otherwise.
    """
    risks = state.get("extracted_risks", [])
    if risks and len(risks) > 0:
        return "validate"
    return "end"


def should_analyze(state: AgentState) -> Literal["analyze", "end"]:
    """
    Determine if analysis should proceed.

    Args:
        state: Current workflow state.

    Returns:
        "analyze" if there are validated risks, "end" otherwise.
    """
    risks = state.get("validated_risks", [])
    if risks and len(risks) > 0:
        return "analyze"
    return "end"


def should_alert(state: AgentState) -> Literal["alert", "end"]:
    """
    Determine if alerting should proceed.

    Args:
        state: Current workflow state.

    Returns:
        "alert" if there are impact assessments, "end" otherwise.
    """
    assessments = state.get("impact_assessments", [])
    if assessments and len(assessments) > 0:
        return "alert"
    return "end"


def check_for_errors(state: AgentState) -> Literal["continue", "handle_error"]:
    """
    Check if there are critical errors that need handling.

    Args:
        state: Current workflow state.

    Returns:
        "handle_error" if critical errors exist, "continue" otherwise.
    """
    errors = state.get("processing_errors", [])
    critical_errors = [e for e in errors if not e.recoverable]

    if critical_errors:
        return "handle_error"
    return "continue"


# =============================================================================
# Error Handling Node
# =============================================================================


async def error_handler_node(state: AgentState) -> dict[str, Any]:
    """
    Error Handler Node: Handles critical processing errors.

    Logs errors and determines if the workflow should retry or terminate.

    Args:
        state: Current workflow state.

    Returns:
        Updated state with error handling results.
    """
    errors = state.get("processing_errors", [])

    for error in errors:
        logger.error(
            "Processing error in workflow",
            stage=error.stage,
            error_type=error.error_type,
            message=error.message,
            recoverable=error.recoverable,
        )

    # Mark workflow as having errors
    return {
        "workflow_completed": True,
        "last_run_at": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Workflow Builder
# =============================================================================


def build_risk_monitoring_workflow() -> StateGraph:
    """
    Build the complete LangGraph workflow for risk monitoring.

    The workflow follows this pattern:
    1. Monitor → collect news from sources
    2. Extract → extract structured risk data
    3. Validate → filter low-confidence extractions
    4. Analyze → calculate supply chain impact
    5. Alert → generate alerts for high-severity events

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("monitor", monitor_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("alert", alert_node)
    workflow.add_node("error_handler", error_handler_node)

    # Set entry point
    workflow.set_entry_point("monitor")

    # Add conditional edges
    workflow.add_conditional_edges(
        "monitor",
        should_extract,
        {
            "extract": "extract",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "extract",
        should_validate,
        {
            "validate": "validate",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "validate",
        should_analyze,
        {
            "analyze": "analyze",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "analyze",
        should_alert,
        {
            "alert": "alert",
            "end": END,
        },
    )

    # Alert node always ends the workflow
    workflow.add_edge("alert", END)

    # Error handler always ends
    workflow.add_edge("error_handler", END)

    return workflow


# =============================================================================
# Workflow Executor
# =============================================================================


class WorkflowExecutor:
    """
    Manages execution of the risk monitoring workflow.

    Provides:
    - Single-run execution
    - Continuous monitoring loop
    - State persistence and recovery
    - Execution history tracking
    """

    def __init__(
        self,
        config: WorkflowConfig | None = None,
        state_file: str | Path | None = None,
    ):
        """
        Initialize the workflow executor.

        Args:
            config: Workflow configuration.
            state_file: Optional path for state persistence.
        """
        self.config = config or WorkflowConfig()
        self.state_file = Path(state_file) if state_file else None

        self._workflow = build_risk_monitoring_workflow()
        self._compiled = self._workflow.compile()
        self._execution_history: list[dict[str, Any]] = []
        self._is_running = False

    async def run_once(
        self,
        initial_state: AgentState | None = None,
    ) -> AgentState:
        """
        Run the workflow once.

        Args:
            initial_state: Optional initial state.

        Returns:
            Final workflow state.
        """
        start_time = datetime.now(timezone.utc)

        # Create initial state
        if initial_state is None:
            initial_state = create_initial_state()

        # Add config to state
        initial_state["workflow_config"] = self.config

        logger.info("Starting workflow execution")

        try:
            # Run the workflow
            final_state = await self._compiled.ainvoke(initial_state)

            # Record execution
            self._record_execution(
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                success=True,
                state=final_state,
            )

            # Persist state if configured
            if self.state_file:
                self._save_state(final_state)

            logger.info(
                "Workflow execution complete",
                duration=(datetime.now(timezone.utc) - start_time).total_seconds(),
                alerts=len(final_state.get("alerts_generated", [])),
            )

            return final_state

        except Exception as e:
            logger.error("Workflow execution failed", error=str(e))
            self._record_execution(
                start_time=start_time,
                end_time=datetime.now(timezone.utc),
                success=False,
                error=str(e),
            )
            raise

    async def run_continuous(
        self,
        interval_seconds: int = 300,
        max_runs: int | None = None,
    ) -> None:
        """
        Run the workflow continuously.

        Args:
            interval_seconds: Time between runs.
            max_runs: Maximum number of runs (None for infinite).
        """
        self._is_running = True
        run_count = 0

        logger.info(
            "Starting continuous workflow execution",
            interval=interval_seconds,
            max_runs=max_runs,
        )

        try:
            while self._is_running:
                await self.run_once()

                run_count += 1
                if max_runs and run_count >= max_runs:
                    break

                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info("Continuous execution cancelled")
        finally:
            self._is_running = False

    def stop(self) -> None:
        """Stop continuous execution."""
        self._is_running = False

    def _record_execution(
        self,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        state: AgentState | None = None,
        error: str | None = None,
    ) -> None:
        """Record execution in history."""
        record = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "success": success,
        }

        if state:
            record["events_processed"] = len(state.get("current_events", []))
            record["risks_extracted"] = len(state.get("extracted_risks", []))
            record["risks_validated"] = len(state.get("validated_risks", []))
            record["alerts_generated"] = len(state.get("alerts_generated", []))
            record["errors"] = len(state.get("processing_errors", []))

        if error:
            record["error"] = error

        self._execution_history.append(record)

        # Keep only last 100 records
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-100:]

    def _save_state(self, state: AgentState) -> None:
        """Save state to file."""
        if not self.state_file:
            return

        # Convert state to JSON-serializable format
        serializable = {
            "last_run_at": state.get("last_run_at"),
            "run_count": state.get("run_count", 0),
            "total_events_processed": len(state.get("current_events", [])),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(serializable, f, indent=2)

    def load_state(self) -> dict[str, Any] | None:
        """Load state from file."""
        if not self.state_file or not self.state_file.exists():
            return None

        with open(self.state_file) as f:
            return json.load(f)

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Get execution history."""
        return self._execution_history

    def get_stats(self) -> dict[str, Any]:
        """Get executor statistics."""
        total_runs = len(self._execution_history)
        successful_runs = sum(1 for r in self._execution_history if r["success"])

        total_alerts = sum(
            r.get("alerts_generated", 0) for r in self._execution_history
        )
        total_events = sum(
            r.get("events_processed", 0) for r in self._execution_history
        )

        return {
            "is_running": self._is_running,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
            "total_alerts_generated": total_alerts,
            "total_events_processed": total_events,
        }


# =============================================================================
# Convenience Functions
# =============================================================================


async def run_risk_monitoring() -> AgentState:
    """Run a single risk monitoring workflow execution."""
    executor = WorkflowExecutor()
    return await executor.run_once()


def get_workflow_graph() -> StateGraph:
    """Get the workflow graph for visualization."""
    return build_risk_monitoring_workflow()
