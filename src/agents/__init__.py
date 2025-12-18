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
]
