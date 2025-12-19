"""
Enhanced Search and Filtering Module for Supply Chain Risk Management.

Provides full-text search, complex filter combinations, entity search
with relationship traversal, multi-format export, and saved searches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from collections import defaultdict
import uuid
import re
import json
import csv
import io
import structlog

from src.models import (
    RiskEvent,
    SeverityLevel,
    EventType,
    Supplier,
    Component,
    Product,
)
from src.graph.connection import get_connection

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class FilterOperator(str, Enum):
    """Logical operators for filter combinations."""

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class SortOrder(str, Enum):
    """Sort order for search results."""

    ASC = "asc"
    DESC = "desc"


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"


@dataclass
class SearchFilter:
    """A single filter condition."""

    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, contains, in
    value: Any

    def matches(self, record: dict) -> bool:
        """Check if a record matches this filter."""
        record_value = record.get(self.field)
        
        if record_value is None:
            return False
        
        if self.operator == "eq":
            return record_value == self.value
        elif self.operator == "ne":
            return record_value != self.value
        elif self.operator == "gt":
            return record_value > self.value
        elif self.operator == "lt":
            return record_value < self.value
        elif self.operator == "gte":
            return record_value >= self.value
        elif self.operator == "lte":
            return record_value <= self.value
        elif self.operator == "contains":
            if isinstance(record_value, str):
                return self.value.lower() in record_value.lower()
            elif isinstance(record_value, list):
                return self.value in record_value
            return False
        elif self.operator == "in":
            return record_value in self.value
        elif self.operator == "regex":
            if isinstance(record_value, str):
                return bool(re.search(self.value, record_value, re.IGNORECASE))
            return False
        
        return False


@dataclass
class FilterGroup:
    """A group of filters combined with a logical operator."""

    filters: list[SearchFilter | "FilterGroup"] = field(default_factory=list)
    operator: FilterOperator = FilterOperator.AND

    def matches(self, record: dict) -> bool:
        """Check if a record matches this filter group."""
        if not self.filters:
            return True

        if self.operator == FilterOperator.AND:
            return all(f.matches(record) for f in self.filters)
        elif self.operator == FilterOperator.OR:
            return any(f.matches(record) for f in self.filters)
        elif self.operator == FilterOperator.NOT:
            # NOT applies to the first filter only
            if self.filters:
                return not self.filters[0].matches(record)
            return True

        return True


@dataclass
class SearchResult:
    """Container for search results."""

    query: str
    filters: FilterGroup | None
    total_count: int
    returned_count: int
    results: list[dict]
    search_time_ms: int
    metadata: dict = field(default_factory=dict)


@dataclass
class SavedSearch:
    """A saved search query."""

    search_id: str
    name: str
    query: str
    filters: FilterGroup | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    last_executed: datetime | None = None
    execution_count: int = 0


@dataclass
class EntitySearchResult:
    """Result of an entity search with relationships."""

    entity_id: str
    entity_type: str
    entity_data: dict
    related_risks: list[dict] = field(default_factory=list)
    related_products: list[dict] = field(default_factory=list)
    related_suppliers: list[dict] = field(default_factory=list)
    related_components: list[dict] = field(default_factory=list)
    impact_paths: list[dict] = field(default_factory=list)


# =============================================================================
# Full-Text Search Engine
# =============================================================================


class FullTextSearchEngine:
    """
    Full-text search across risk events and entities.

    Indexes event descriptions, locations, and entities for keyword search.
    """

    def __init__(self):
        """Initialize the search engine."""
        self._index: dict[str, set[str]] = defaultdict(set)  # term -> event_ids
        self._events: dict[str, dict] = {}  # event_id -> event_data
        self._term_positions: dict[str, dict[str, list[int]]] = defaultdict(
            lambda: defaultdict(list)
        )  # term -> event_id -> positions

    def index_event(self, event: RiskEvent) -> None:
        """
        Index a risk event for full-text search.

        Args:
            event: RiskEvent to index.
        """
        event_dict = {
            "id": event.id,
            "description": event.description,
            "location": event.location,
            "event_type": event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
            "severity": event.severity.value if hasattr(event.severity, 'value') else str(event.severity),
            "confidence": event.confidence,
            "affected_entities": event.affected_entities,
            "source_url": event.source_url,
        }
        
        self._events[event.id] = event_dict

        # Index fields
        self._index_text(event.id, event.description, "description")
        self._index_text(event.id, event.location, "location")
        self._index_text(event.id, event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type), "event_type")
        self._index_text(event.id, event.source_url, "source_url")
        
        for entity in event.affected_entities:
            self._index_text(event.id, entity, "entity")

        logger.debug("Indexed event", event_id=event.id)

    def _index_text(self, event_id: str, text: str, field: str) -> None:
        """Index text content."""
        if not text:
            return
            
        terms = self._tokenize(text)
        for position, term in enumerate(terms):
            self._index[term].add(event_id)
            self._term_positions[term][event_id].append(position)

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into searchable terms."""
        # Convert to lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return [t for t in tokens if len(t) >= 2]

    def search(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0,
    ) -> SearchResult:
        """
        Search for events matching the query.

        Args:
            query: Search query string.
            limit: Maximum results to return.
            offset: Number of results to skip.

        Returns:
            SearchResult with matching events.
        """
        start_time = datetime.now(timezone.utc)

        query_terms = self._tokenize(query)
        if not query_terms:
            return SearchResult(
                query=query,
                filters=None,
                total_count=0,
                returned_count=0,
                results=[],
                search_time_ms=0,
            )

        # Find events matching all terms (AND logic)
        matching_ids: set[str] | None = None
        for term in query_terms:
            term_matches = self._index.get(term, set())
            # Also check partial matches
            for indexed_term, event_ids in self._index.items():
                if term in indexed_term:
                    term_matches = term_matches.union(event_ids)

            if matching_ids is None:
                matching_ids = term_matches.copy()
            else:
                matching_ids = matching_ids.intersection(term_matches)

        matching_ids = matching_ids or set()

        # Score and sort results
        scored_results = []
        for event_id in matching_ids:
            event = self._events.get(event_id)
            if event:
                score = self._calculate_relevance_score(event_id, query_terms)
                scored_results.append((score, event))

        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Apply pagination
        total_count = len(scored_results)
        paginated = scored_results[offset:offset + limit]
        results = [r[1] for r in paginated]

        end_time = datetime.now(timezone.utc)
        search_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return SearchResult(
            query=query,
            filters=None,
            total_count=total_count,
            returned_count=len(results),
            results=results,
            search_time_ms=search_time_ms,
        )

    def _calculate_relevance_score(self, event_id: str, query_terms: list[str]) -> float:
        """Calculate relevance score for an event."""
        score = 0.0
        
        for term in query_terms:
            # Count term occurrences
            positions = self._term_positions.get(term, {}).get(event_id, [])
            score += len(positions) * 1.0

            # Boost for exact matches
            for indexed_term in self._index:
                if term == indexed_term and event_id in self._index[indexed_term]:
                    score += 2.0

        return score

    def get_indexed_count(self) -> int:
        """Get number of indexed events."""
        return len(self._events)


# =============================================================================
# Filter Engine
# =============================================================================


class FilterEngine:
    """
    Complex filter combinations with AND/OR logic.

    Supports multiple filter types and logical combinations.
    """

    def __init__(self):
        """Initialize the filter engine."""
        pass

    def parse_filter(self, filter_dict: dict) -> SearchFilter:
        """
        Parse a filter dictionary into a SearchFilter.

        Args:
            filter_dict: Dictionary with field, operator, value.

        Returns:
            SearchFilter instance.
        """
        return SearchFilter(
            field=filter_dict.get("field", ""),
            operator=filter_dict.get("operator", "eq"),
            value=filter_dict.get("value"),
        )

    def parse_filter_group(self, group_dict: dict) -> FilterGroup:
        """
        Parse a filter group dictionary.

        Args:
            group_dict: Dictionary with filters and operator.

        Returns:
            FilterGroup instance.
        """
        operator = FilterOperator(group_dict.get("operator", "AND"))
        filters = []

        for f in group_dict.get("filters", []):
            if "filters" in f:
                # Nested group
                filters.append(self.parse_filter_group(f))
            else:
                # Simple filter
                filters.append(self.parse_filter(f))

        return FilterGroup(filters=filters, operator=operator)

    def apply_filters(
        self,
        records: list[dict],
        filter_group: FilterGroup,
    ) -> list[dict]:
        """
        Apply filter group to records.

        Args:
            records: List of records to filter.
            filter_group: Filter group to apply.

        Returns:
            Filtered records.
        """
        return [r for r in records if filter_group.matches(r)]

    def create_filter(
        self,
        field: str,
        operator: str,
        value: Any,
    ) -> SearchFilter:
        """Create a simple filter."""
        return SearchFilter(field=field, operator=operator, value=value)

    def combine_filters(
        self,
        filters: list[SearchFilter | FilterGroup],
        operator: FilterOperator = FilterOperator.AND,
    ) -> FilterGroup:
        """Combine multiple filters with a logical operator."""
        return FilterGroup(filters=filters, operator=operator)


# =============================================================================
# Entity Search
# =============================================================================


class EntitySearchEngine:
    """
    Entity search with relationship traversal.

    Searches for entities and returns related risks, products, and impact paths.
    """

    def __init__(self, connection=None):
        """
        Initialize the entity search engine.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self._entities: dict[str, dict] = {}
        self._relationships: dict[str, list[dict]] = defaultdict(list)

    def index_entity(
        self,
        entity_id: str,
        entity_type: str,
        data: dict,
    ) -> None:
        """
        Index an entity for search.

        Args:
            entity_id: Entity identifier.
            entity_type: Type of entity (supplier, component, product).
            data: Entity data.
        """
        self._entities[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            **data,
        }

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        data: dict | None = None,
    ) -> None:
        """
        Add a relationship between entities.

        Args:
            source_id: Source entity ID.
            target_id: Target entity ID.
            relationship_type: Type of relationship.
            data: Optional relationship data.
        """
        self._relationships[source_id].append({
            "target_id": target_id,
            "type": relationship_type,
            "data": data or {},
        })
        # Add reverse relationship for bidirectional search
        self._relationships[target_id].append({
            "target_id": source_id,
            "type": f"reverse_{relationship_type}",
            "data": data or {},
        })

    def search_entity(
        self,
        query: str,
        entity_type: str | None = None,
        include_relationships: bool = True,
        max_depth: int = 2,
    ) -> list[EntitySearchResult]:
        """
        Search for entities by name/ID.

        Args:
            query: Search query.
            entity_type: Optional type filter.
            include_relationships: Whether to include relationships.
            max_depth: Maximum relationship traversal depth.

        Returns:
            List of EntitySearchResult.
        """
        results = []
        query_lower = query.lower()

        for entity_id, entity_data in self._entities.items():
            # Check if entity matches query
            matches = False
            
            if query_lower in entity_id.lower():
                matches = True
            elif "name" in entity_data and query_lower in str(entity_data.get("name", "")).lower():
                matches = True
            
            if not matches:
                continue

            # Check type filter
            if entity_type and entity_data.get("type") != entity_type:
                continue

            result = EntitySearchResult(
                entity_id=entity_id,
                entity_type=entity_data.get("type", "unknown"),
                entity_data=entity_data,
            )

            if include_relationships:
                self._populate_relationships(result, max_depth)

            results.append(result)

        return results

    def _populate_relationships(
        self,
        result: EntitySearchResult,
        max_depth: int,
    ) -> None:
        """Populate relationship data for a search result."""
        visited: set[str] = {result.entity_id}
        to_visit: list[tuple[str, int]] = [(result.entity_id, 0)]

        while to_visit:
            current_id, depth = to_visit.pop(0)
            
            if depth >= max_depth:
                continue

            for rel in self._relationships.get(current_id, []):
                target_id = rel["target_id"]
                target_entity = self._entities.get(target_id, {})
                
                if target_id in visited:
                    continue
                    
                visited.add(target_id)

                rel_data = {
                    "id": target_id,
                    "relationship_type": rel["type"],
                    "relationship_data": rel["data"],
                    **target_entity,
                }

                target_type = target_entity.get("type", "unknown")
                
                if target_type == "supplier":
                    result.related_suppliers.append(rel_data)
                elif target_type == "component":
                    result.related_components.append(rel_data)
                elif target_type == "product":
                    result.related_products.append(rel_data)
                elif target_type == "risk":
                    result.related_risks.append(rel_data)

                to_visit.append((target_id, depth + 1))

    def get_entity(self, entity_id: str) -> dict | None:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def get_related_entities(
        self,
        entity_id: str,
        relationship_type: str | None = None,
    ) -> list[dict]:
        """Get entities related to a given entity."""
        related = []
        
        for rel in self._relationships.get(entity_id, []):
            if relationship_type and rel["type"] != relationship_type:
                continue
                
            target = self._entities.get(rel["target_id"])
            if target:
                related.append({
                    **target,
                    "relationship_type": rel["type"],
                    "relationship_data": rel["data"],
                })

        return related


# =============================================================================
# Export Engine
# =============================================================================


class ExportEngine:
    """
    Multi-format export for search results.

    Supports CSV and JSON export with full metadata.
    """

    def __init__(self):
        """Initialize the export engine."""
        pass

    def export(
        self,
        results: SearchResult | list[dict],
        format: ExportFormat,
        include_metadata: bool = True,
    ) -> str:
        """
        Export search results to specified format.

        Args:
            results: SearchResult or list of dicts.
            format: Export format (CSV or JSON).
            include_metadata: Whether to include metadata.

        Returns:
            Exported data as string.
        """
        if format == ExportFormat.CSV:
            return self.export_csv(results, include_metadata)
        elif format == ExportFormat.JSON:
            return self.export_json(results, include_metadata)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def export_csv(
        self,
        results: SearchResult | list[dict],
        include_metadata: bool = True,
    ) -> str:
        """Export results to CSV format."""
        if isinstance(results, SearchResult):
            records = results.results
            metadata = {
                "query": results.query,
                "total_count": results.total_count,
                "returned_count": results.returned_count,
                "search_time_ms": results.search_time_ms,
            }
        else:
            records = results
            metadata = {}

        if not records:
            return ""

        output = io.StringIO()
        
        # Get all unique fields
        all_fields: set[str] = set()
        for record in records:
            all_fields.update(record.keys())
        
        fields = sorted(all_fields)
        
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        
        for record in records:
            # Flatten complex fields
            flat_record = {}
            for key, value in record.items():
                if isinstance(value, (list, dict)):
                    flat_record[key] = json.dumps(value)
                else:
                    flat_record[key] = value
            writer.writerow(flat_record)

        return output.getvalue()

    def export_json(
        self,
        results: SearchResult | list[dict],
        include_metadata: bool = True,
    ) -> str:
        """Export results to JSON format."""
        if isinstance(results, SearchResult):
            data = {
                "results": results.results,
            }
            if include_metadata:
                data["metadata"] = {
                    "query": results.query,
                    "total_count": results.total_count,
                    "returned_count": results.returned_count,
                    "search_time_ms": results.search_time_ms,
                }
        else:
            data = {"results": results}

        # Custom JSON encoder for datetime objects
        def json_encoder(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'value'):  # Enum
                return obj.value
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(data, indent=2, default=json_encoder)


# =============================================================================
# Saved Search Manager
# =============================================================================


class SavedSearchManager:
    """
    Manages saved search queries.

    Allows saving, retrieving, and re-executing search queries.
    """

    def __init__(self, search_engine: FullTextSearchEngine):
        """
        Initialize the saved search manager.

        Args:
            search_engine: FullTextSearchEngine instance.
        """
        self._search_engine = search_engine
        self._saved_searches: dict[str, SavedSearch] = {}

    def save_search(
        self,
        name: str,
        query: str,
        filters: FilterGroup | None = None,
        created_by: str = "system",
    ) -> SavedSearch:
        """
        Save a search query.

        Args:
            name: Name for the saved search.
            query: Search query string.
            filters: Optional filter group.
            created_by: User saving the search.

        Returns:
            SavedSearch instance.
        """
        search_id = f"search-{uuid.uuid4().hex[:8]}"
        
        saved = SavedSearch(
            search_id=search_id,
            name=name,
            query=query,
            filters=filters,
            created_by=created_by,
        )
        
        self._saved_searches[search_id] = saved
        
        logger.info("Saved search", search_id=search_id, name=name)
        
        return saved

    def get_saved_search(self, search_id: str) -> SavedSearch | None:
        """Get a saved search by ID."""
        return self._saved_searches.get(search_id)

    def get_saved_search_by_name(self, name: str) -> SavedSearch | None:
        """Get a saved search by name."""
        for saved in self._saved_searches.values():
            if saved.name == name:
                return saved
        return None

    def list_saved_searches(self, created_by: str | None = None) -> list[SavedSearch]:
        """List all saved searches."""
        searches = list(self._saved_searches.values())
        
        if created_by:
            searches = [s for s in searches if s.created_by == created_by]
        
        return searches

    def execute_saved_search(
        self,
        search_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> SearchResult | None:
        """
        Execute a saved search.

        Args:
            search_id: ID of saved search.
            limit: Maximum results.
            offset: Result offset.

        Returns:
            SearchResult or None if search not found.
        """
        saved = self._saved_searches.get(search_id)
        if not saved:
            return None

        # Execute the search
        result = self._search_engine.search(
            query=saved.query,
            limit=limit,
            offset=offset,
        )

        # Apply filters if present
        if saved.filters:
            filter_engine = FilterEngine()
            result.results = filter_engine.apply_filters(
                result.results, saved.filters
            )
            result.returned_count = len(result.results)

        # Update execution stats
        saved.last_executed = datetime.now(timezone.utc)
        saved.execution_count += 1

        result.metadata["saved_search_id"] = search_id
        result.metadata["saved_search_name"] = saved.name

        return result

    def delete_saved_search(self, search_id: str) -> bool:
        """Delete a saved search."""
        if search_id in self._saved_searches:
            del self._saved_searches[search_id]
            return True
        return False

    def update_saved_search(
        self,
        search_id: str,
        name: str | None = None,
        query: str | None = None,
        filters: FilterGroup | None = None,
    ) -> SavedSearch | None:
        """Update a saved search."""
        saved = self._saved_searches.get(search_id)
        if not saved:
            return None

        if name:
            saved.name = name
        if query:
            saved.query = query
        if filters is not None:
            saved.filters = filters

        return saved


# =============================================================================
# Search Manager (Main Interface)
# =============================================================================


class SearchManager:
    """
    Main interface for enhanced search and filtering.

    Coordinates full-text search, filtering, entity search, and exports.
    """

    def __init__(self, connection=None):
        """
        Initialize the search manager.

        Args:
            connection: Optional Neo4j connection.
        """
        self._connection = connection
        self.full_text = FullTextSearchEngine()
        self.filter_engine = FilterEngine()
        self.entity_search = EntitySearchEngine(connection)
        self.export_engine = ExportEngine()
        self.saved_searches = SavedSearchManager(self.full_text)

    def search(
        self,
        query: str,
        filters: dict | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> SearchResult:
        """
        Perform a search with optional filters.

        Args:
            query: Search query string.
            filters: Optional filter dictionary.
            limit: Maximum results.
            offset: Result offset.

        Returns:
            SearchResult.
        """
        # Full-text search
        result = self.full_text.search(query, limit=limit + 100, offset=0)

        # Apply filters
        if filters:
            filter_group = self.filter_engine.parse_filter_group(filters)
            result.results = self.filter_engine.apply_filters(
                result.results, filter_group
            )
            result.filters = filter_group
            result.total_count = len(result.results)

        # Apply pagination after filtering
        result.results = result.results[offset:offset + limit]
        result.returned_count = len(result.results)

        return result

    def index_event(self, event: RiskEvent) -> None:
        """Index a risk event for search."""
        self.full_text.index_event(event)

    def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
    ) -> list[EntitySearchResult]:
        """Search for entities with relationships."""
        return self.entity_search.search_entity(
            query=query,
            entity_type=entity_type,
            include_relationships=True,
        )

    def export_results(
        self,
        results: SearchResult | list[dict],
        format: ExportFormat | str,
    ) -> str:
        """Export search results to specified format."""
        if isinstance(format, str):
            format = ExportFormat(format)
        return self.export_engine.export(results, format)
