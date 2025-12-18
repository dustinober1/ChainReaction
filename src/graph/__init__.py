"""
ChainReaction Graph Module.

Contains Neo4j connection utilities, GraphRAG engine, and impact analysis.
"""

from src.graph.connection import (
    Neo4jConnection,
    get_connection,
    close_connection,
    setup_schema,
    validate_schema,
    clear_database,
)
from src.graph.repository import SupplyChainRepository
from src.graph.traversal import (
    GraphNode,
    GraphEdge,
    TraversalPath,
    ImpactResult,
    GraphTraversal,
    InMemoryGraph,
)
from src.graph.impact import (
    SupplierRedundancy,
    ImpactScore,
    RiskAssessmentResult,
    ImpactCalculator,
    RedundancyAnalyzer,
    RiskAssessor,
)

__all__ = [
    # Connection
    "Neo4jConnection",
    "get_connection",
    "close_connection",
    "setup_schema",
    "validate_schema",
    "clear_database",
    # Repository
    "SupplyChainRepository",
    # Traversal
    "GraphNode",
    "GraphEdge",
    "TraversalPath",
    "ImpactResult",
    "GraphTraversal",
    "InMemoryGraph",
    # Impact
    "SupplierRedundancy",
    "ImpactScore",
    "RiskAssessmentResult",
    "ImpactCalculator",
    "RedundancyAnalyzer",
    "RiskAssessor",
]
