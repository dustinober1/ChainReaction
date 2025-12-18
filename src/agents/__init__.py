"""
ChainReaction Agents Module.

Contains LangGraph agents for autonomous supply chain monitoring
and risk processing.
"""

from src.agents.state import (
    AgentState,
    WorkflowConfig,
    create_initial_state,
)
from src.agents.queries import (
    SearchQuery,
    QueryGenerator,
    DynamicQueryGenerator,
)
from src.agents.sources import (
    NewsArticle,
    NewsClient,
    TavilyClient,
    NewsAPIClient,
    MultiSourceNewsClient,
)
from src.agents.scout import (
    MonitoringConfig,
    MonitoringEvent,
    EventDeduplicator,
    RateLimiter,
    ScoutAgent,
)
from src.agents.nodes import (
    monitor_node,
    extract_node,
    validate_node,
    analyze_node,
    alert_node,
)
from src.agents.workflow import (
    build_risk_monitoring_workflow,
    WorkflowExecutor,
    run_risk_monitoring,
)

__all__ = [
    # State
    "AgentState",
    "WorkflowConfig",
    "create_initial_state",
    # Queries
    "SearchQuery",
    "QueryGenerator",
    "DynamicQueryGenerator",
    # Sources
    "NewsArticle",
    "NewsClient",
    "TavilyClient",
    "NewsAPIClient",
    "MultiSourceNewsClient",
    # Scout
    "MonitoringConfig",
    "MonitoringEvent",
    "EventDeduplicator",
    "RateLimiter",
    "ScoutAgent",
    # Nodes
    "monitor_node",
    "extract_node",
    "validate_node",
    "analyze_node",
    "alert_node",
    # Workflow
    "build_risk_monitoring_workflow",
    "WorkflowExecutor",
    "run_risk_monitoring",
]
