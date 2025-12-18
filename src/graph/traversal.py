"""
Graph Traversal Utilities for Impact Analysis.

Provides algorithms for traversing the supply chain graph to determine
downstream impact of risk events and alternative sourcing options.
"""

from dataclasses import dataclass, field
from typing import Any
from collections import deque

import structlog

from src.graph.connection import Neo4jConnection, get_connection

logger = structlog.get_logger(__name__)


@dataclass
class GraphNode:
    """Represents a node in a traversal path."""

    id: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    depth: int = 0


@dataclass
class GraphEdge:
    """Represents an edge in a traversal path."""

    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraversalPath:
    """A complete path through the graph."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_depth: int

    @property
    def start_node(self) -> GraphNode | None:
        """Get the starting node of the path."""
        return self.nodes[0] if self.nodes else None

    @property
    def end_node(self) -> GraphNode | None:
        """Get the ending node of the path."""
        return self.nodes[-1] if self.nodes else None

    @property
    def relationship_types(self) -> list[str]:
        """Get all relationship types in the path."""
        return [e.relationship_type for e in self.edges]


@dataclass
class ImpactResult:
    """Result of an impact analysis."""

    affected_node_id: str
    affected_node_label: str
    distance_from_source: int
    impact_paths: list[TraversalPath]
    criticality_score: float = 0.0
    is_critical_path: bool = False


class GraphTraversal:
    """
    Utilities for traversing the supply chain graph.

    Supports:
    - Downstream impact analysis (what products are affected)
    - Upstream tracing (where do components come from)
    - Alternative path finding (backup suppliers)
    - Critical path identification
    """

    def __init__(self, connection: Neo4jConnection | None = None):
        """
        Initialize the traversal utilities.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection

    async def _get_connection(self) -> Neo4jConnection:
        """Get the database connection."""
        if self._connection is not None:
            return self._connection
        return await get_connection()

    async def find_downstream_impact(
        self,
        source_node_id: str,
        max_depth: int = 10,
    ) -> list[ImpactResult]:
        """
        Find all downstream nodes affected by an issue at source node.

        This traverses PART_OF relationships to find all products
        that depend on the affected component/supplier.

        Args:
            source_node_id: ID of the affected node.
            max_depth: Maximum traversal depth.

        Returns:
            List of ImpactResult objects for affected nodes.
        """
        conn = await self._get_connection()

        query = """
        MATCH path = (source {id: $source_id})-[:SUPPLIES|PART_OF*1..$max_depth]->(downstream)
        WHERE downstream:Product OR downstream:Component
        WITH downstream, 
             length(path) as distance,
             [node in nodes(path) | {id: node.id, labels: labels(node)}] as path_nodes,
             [rel in relationships(path) | type(rel)] as rel_types
        RETURN DISTINCT downstream.id as node_id,
               labels(downstream)[0] as node_label,
               distance,
               collect({nodes: path_nodes, rels: rel_types}) as paths
        ORDER BY distance
        """

        try:
            results = await conn.execute_query(
                query,
                {"source_id": source_node_id, "max_depth": max_depth},
            )

            impact_results = []
            for row in results:
                # Convert paths to TraversalPath objects
                paths = []
                for path_data in row.get("paths", []):
                    nodes = [
                        GraphNode(
                            id=n["id"],
                            label=n["labels"][0] if n["labels"] else "Unknown",
                            depth=i,
                        )
                        for i, n in enumerate(path_data.get("nodes", []))
                    ]

                    edges = []
                    rel_types = path_data.get("rels", [])
                    for i, rel_type in enumerate(rel_types):
                        if i < len(nodes) - 1:
                            edges.append(
                                GraphEdge(
                                    source_id=nodes[i].id,
                                    target_id=nodes[i + 1].id,
                                    relationship_type=rel_type,
                                )
                            )

                    if nodes:
                        paths.append(
                            TraversalPath(
                                nodes=nodes,
                                edges=edges,
                                total_depth=len(nodes) - 1,
                            )
                        )

                impact_results.append(
                    ImpactResult(
                        affected_node_id=row["node_id"],
                        affected_node_label=row["node_label"],
                        distance_from_source=row["distance"],
                        impact_paths=paths,
                    )
                )

            logger.info(
                "Downstream impact analysis complete",
                source_id=source_node_id,
                affected_count=len(impact_results),
            )

            return impact_results

        except Exception as e:
            logger.error("Impact analysis failed", error=str(e))
            raise

    async def find_upstream_sources(
        self,
        product_id: str,
        max_depth: int = 10,
    ) -> list[GraphNode]:
        """
        Find all upstream suppliers and components for a product.

        Traverses the graph backwards to find all sources.

        Args:
            product_id: ID of the product to trace.
            max_depth: Maximum traversal depth.

        Returns:
            List of GraphNode objects representing upstream sources.
        """
        conn = await self._get_connection()

        query = """
        MATCH path = (upstream)-[:SUPPLIES|PART_OF*1..$max_depth]->(product:Product {id: $product_id})
        WITH DISTINCT upstream, length(path) as distance
        RETURN upstream.id as id, 
               labels(upstream)[0] as label,
               upstream as properties,
               distance
        ORDER BY distance
        """

        results = await conn.execute_query(
            query,
            {"product_id": product_id, "max_depth": max_depth},
        )

        nodes = []
        for row in results:
            nodes.append(
                GraphNode(
                    id=row["id"],
                    label=row["label"],
                    properties=dict(row.get("properties", {})),
                    depth=row["distance"],
                )
            )

        return nodes

    async def find_alternative_paths(
        self,
        from_node_id: str,
        to_node_id: str,
        max_paths: int = 5,
    ) -> list[TraversalPath]:
        """
        Find alternative paths between two nodes.

        Useful for identifying backup supply routes.

        Args:
            from_node_id: Source node ID.
            to_node_id: Target node ID.
            max_paths: Maximum number of paths to return.

        Returns:
            List of TraversalPath objects.
        """
        conn = await self._get_connection()

        query = """
        MATCH path = shortestPath((a {id: $from_id})-[*..10]-(b {id: $to_id}))
        RETURN [node in nodes(path) | {id: node.id, labels: labels(node)}] as nodes,
               [rel in relationships(path) | type(rel)] as rels,
               length(path) as depth
        LIMIT $max_paths
        """

        results = await conn.execute_query(
            query,
            {
                "from_id": from_node_id,
                "to_id": to_node_id,
                "max_paths": max_paths,
            },
        )

        paths = []
        for row in results:
            nodes = [
                GraphNode(
                    id=n["id"],
                    label=n["labels"][0] if n["labels"] else "Unknown",
                    depth=i,
                )
                for i, n in enumerate(row.get("nodes", []))
            ]

            edges = []
            for i, rel_type in enumerate(row.get("rels", [])):
                if i < len(nodes) - 1:
                    edges.append(
                        GraphEdge(
                            source_id=nodes[i].id,
                            target_id=nodes[i + 1].id,
                            relationship_type=rel_type,
                        )
                    )

            paths.append(
                TraversalPath(nodes=nodes, edges=edges, total_depth=row["depth"])
            )

        return paths

    async def get_node_neighbors(
        self,
        node_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "outgoing",
    ) -> list[tuple[GraphNode, GraphEdge]]:
        """
        Get immediate neighbors of a node.

        Args:
            node_id: Node to get neighbors for.
            relationship_types: Optional filter for relationship types.
            direction: 'outgoing', 'incoming', or 'both'.

        Returns:
            List of (neighbor_node, connecting_edge) tuples.
        """
        conn = await self._get_connection()

        # Build relationship pattern
        rel_pattern = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_pattern = f":{rel_types}"

        # Build direction pattern
        if direction == "outgoing":
            pattern = f"(n {{id: $id}})-[r{rel_pattern}]->(neighbor)"
        elif direction == "incoming":
            pattern = f"(n {{id: $id}})<-[r{rel_pattern}]-(neighbor)"
        else:  # both
            pattern = f"(n {{id: $id}})-[r{rel_pattern}]-(neighbor)"

        query = f"""
        MATCH {pattern}
        RETURN neighbor.id as neighbor_id,
               labels(neighbor)[0] as neighbor_label,
               neighbor as neighbor_props,
               type(r) as rel_type,
               properties(r) as rel_props
        """

        results = await conn.execute_query(query, {"id": node_id})

        neighbors = []
        for row in results:
            neighbor = GraphNode(
                id=row["neighbor_id"],
                label=row["neighbor_label"],
                properties=dict(row.get("neighbor_props", {})),
            )
            edge = GraphEdge(
                source_id=node_id if direction == "outgoing" else row["neighbor_id"],
                target_id=row["neighbor_id"] if direction == "outgoing" else node_id,
                relationship_type=row["rel_type"],
                properties=dict(row.get("rel_props", {})),
            )
            neighbors.append((neighbor, edge))

        return neighbors


# =============================================================================
# In-Memory Graph for Testing
# =============================================================================


class InMemoryGraph:
    """
    In-memory graph representation for testing without Neo4j.

    Provides the same interface as GraphTraversal but operates
    on in-memory data structures.
    """

    def __init__(self):
        """Initialize an empty graph."""
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[tuple[str, GraphEdge]]] = {}

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = []
        self._adjacency[edge.source_id].append((edge.target_id, edge))

    def find_downstream(
        self,
        source_id: str,
        max_depth: int = 10,
    ) -> list[ImpactResult]:
        """
        Find all downstream nodes using BFS.

        Args:
            source_id: Starting node ID.
            max_depth: Maximum depth to traverse.

        Returns:
            List of ImpactResult objects.
        """
        if source_id not in self.nodes:
            return []

        results: dict[str, ImpactResult] = {}
        visited: set[str] = set()
        queue: deque[tuple[str, int, list[GraphNode], list[GraphEdge]]] = deque()

        # Start BFS
        queue.append((source_id, 0, [self.nodes[source_id]], []))
        visited.add(source_id)

        while queue:
            current_id, depth, path_nodes, path_edges = queue.popleft()

            if depth > max_depth:
                continue

            # Process current node (skip source)
            if current_id != source_id:
                node = self.nodes[current_id]
                if current_id not in results:
                    results[current_id] = ImpactResult(
                        affected_node_id=current_id,
                        affected_node_label=node.label,
                        distance_from_source=depth,
                        impact_paths=[],
                    )

                # Add this path
                results[current_id].impact_paths.append(
                    TraversalPath(
                        nodes=path_nodes.copy(),
                        edges=path_edges.copy(),
                        total_depth=depth,
                    )
                )

            # Explore neighbors
            for neighbor_id, edge in self._adjacency.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    if neighbor_id in self.nodes:
                        new_path_nodes = path_nodes + [self.nodes[neighbor_id]]
                        new_path_edges = path_edges + [edge]
                        queue.append(
                            (neighbor_id, depth + 1, new_path_nodes, new_path_edges)
                        )

        return list(results.values())

    def find_all_paths(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 10,
    ) -> list[TraversalPath]:
        """
        Find all paths between two nodes using DFS.

        Args:
            from_id: Source node ID.
            to_id: Target node ID.
            max_depth: Maximum path length.

        Returns:
            List of TraversalPath objects.
        """
        if from_id not in self.nodes or to_id not in self.nodes:
            return []

        paths: list[TraversalPath] = []
        visited: set[str] = set()

        def dfs(
            current_id: str,
            path_nodes: list[GraphNode],
            path_edges: list[GraphEdge],
        ) -> None:
            if len(path_nodes) > max_depth + 1:
                return

            if current_id == to_id:
                paths.append(
                    TraversalPath(
                        nodes=path_nodes.copy(),
                        edges=path_edges.copy(),
                        total_depth=len(path_nodes) - 1,
                    )
                )
                return

            visited.add(current_id)

            for neighbor_id, edge in self._adjacency.get(current_id, []):
                if neighbor_id not in visited and neighbor_id in self.nodes:
                    dfs(
                        neighbor_id,
                        path_nodes + [self.nodes[neighbor_id]],
                        path_edges + [edge],
                    )

            visited.remove(current_id)

        dfs(from_id, [self.nodes[from_id]], [])
        return paths

    def get_node_count(self) -> int:
        """Get the number of nodes in the graph."""
        return len(self.nodes)

    def get_edge_count(self) -> int:
        """Get the number of edges in the graph."""
        return len(self.edges)
