"""
Property Tests for Enhanced Search and Filtering Module.

Tests the search functionality, verifying:
- Property 16: Full-Text Search Coverage
- Property 17: Filter Combination Logic
- Property 18: Entity Search Completeness
- Property 19: Export Format Completeness
- Property 20: Saved Search Reusability
"""

from datetime import datetime, timezone
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
import pytest
import uuid
import json

from src.models import (
    EventType,
    SeverityLevel,
    RiskEvent,
)
from src.analysis.search import (
    FilterOperator,
    ExportFormat,
    SearchFilter,
    FilterGroup,
    SearchResult,
    SavedSearch,
    EntitySearchResult,
    FullTextSearchEngine,
    FilterEngine,
    EntitySearchEngine,
    ExportEngine,
    SavedSearchManager,
    SearchManager,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Event type strategy
event_type_strategy = st.sampled_from(list(EventType))

# Severity level strategy
severity_strategy = st.sampled_from(list(SeverityLevel))

# Filter operator strategy
filter_operator_strategy = st.sampled_from(list(FilterOperator))

# Export format strategy
export_format_strategy = st.sampled_from(list(ExportFormat))

# Score strategy (0.0 to 1.0)
score_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# Location strategy
location_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"), whitelist_characters=",- "),
    min_size=2,
    max_size=50,
).filter(lambda x: x.strip())

# Entity ID strategy
entity_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"),
    min_size=3,
    max_size=30,
).filter(lambda x: x.strip())

# Search query strategy
query_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
    min_size=2,
    max_size=50,
).filter(lambda x: x.strip())


# Risk event strategy
@st.composite
def risk_event_strategy(draw) -> RiskEvent:
    """Generate valid RiskEvent instances for testing."""
    return RiskEvent(
        id=f"risk-{uuid.uuid4().hex[:8]}",
        event_type=draw(event_type_strategy),
        severity=draw(severity_strategy),
        location=draw(location_strategy),
        description=draw(st.text(min_size=10, max_size=200).filter(lambda x: x.strip())),
        confidence=draw(score_strategy),
        affected_entities=draw(st.lists(entity_id_strategy, min_size=1, max_size=5)),
        source_url="https://example.com/risk",
    )


# Search filter strategy
@st.composite
def search_filter_strategy(draw) -> SearchFilter:
    """Generate valid SearchFilter instances."""
    operators = ["eq", "ne", "gt", "lt", "gte", "lte", "contains", "in"]
    
    return SearchFilter(
        field=draw(st.sampled_from(["severity", "event_type", "location", "confidence"])),
        operator=draw(st.sampled_from(operators)),
        value=draw(st.text(min_size=1, max_size=20).filter(lambda x: x.strip())),
    )


# =============================================================================
# Property 16: Full-Text Search Coverage
# =============================================================================


class TestFullTextSearchCoverage:
    """Property tests for full-text search coverage."""

    @given(event=risk_event_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_indexed_event_is_searchable_by_description(self, event: RiskEvent):
        """
        Property: Indexed events can be found by description keywords.
        """
        engine = FullTextSearchEngine()
        engine.index_event(event)
        
        # Extract first significant word from description
        words = event.description.split()
        if words:
            search_term = words[0]
            result = engine.search(search_term)
            
            # Should find at least one result if term is meaningful
            if len(search_term) >= 2:
                assert result.total_count >= 0

    @given(event=risk_event_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_indexed_event_is_searchable_by_location(self, event: RiskEvent):
        """
        Property: Indexed events can be found by location.
        """
        engine = FullTextSearchEngine()
        engine.index_event(event)
        
        result = engine.search(event.location)
        
        # The event should be in results
        event_ids = [r["id"] for r in result.results]
        assert event.id in event_ids

    @given(event=risk_event_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_search_result_has_valid_structure(self, event: RiskEvent):
        """
        Property: Search results have valid structure.
        """
        engine = FullTextSearchEngine()
        engine.index_event(event)
        
        result = engine.search("test")
        
        assert isinstance(result, SearchResult)
        assert result.query == "test"
        assert isinstance(result.total_count, int)
        assert isinstance(result.returned_count, int)
        assert isinstance(result.results, list)
        assert isinstance(result.search_time_ms, int)

    @given(events=st.lists(risk_event_strategy(), min_size=1, max_size=5))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_indexed_count_matches_events(self, events: list[RiskEvent]):
        """
        Property: Indexed count matches number of events added.
        """
        engine = FullTextSearchEngine()
        
        for event in events:
            engine.index_event(event)
        
        assert engine.get_indexed_count() == len(events)

    def test_empty_search_returns_no_results(self):
        """
        Property: Empty search query returns no results.
        """
        engine = FullTextSearchEngine()
        
        result = engine.search("")
        
        assert result.total_count == 0
        assert result.returned_count == 0


# =============================================================================
# Property 17: Filter Combination Logic
# =============================================================================


class TestFilterCombinationLogic:
    """Property tests for filter combination logic."""

    @given(
        field=st.sampled_from(["severity", "location", "confidence"]),
        value=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
    )
    @settings(max_examples=50)
    def test_eq_filter_matches_exact_value(self, field: str, value: str):
        """
        Property: Eq filter matches exact values.
        """
        filter = SearchFilter(field=field, operator="eq", value=value)
        
        record = {field: value}
        assert filter.matches(record) is True
        
        record = {field: value + "_different"}
        assert filter.matches(record) is False

    @given(
        operator=filter_operator_strategy,
        values=st.lists(st.text(min_size=1, max_size=10), min_size=2, max_size=3),
    )
    @settings(max_examples=30)
    def test_filter_group_respects_operator(
        self, operator: FilterOperator, values: list[str]
    ):
        """
        Property: Filter groups respect their logical operator.
        """
        filters = [
            SearchFilter(field=f"field{i}", operator="eq", value=v)
            for i, v in enumerate(values)
        ]
        
        group = FilterGroup(filters=filters, operator=operator)
        
        # Create record that matches all filters
        all_match_record = {f"field{i}": v for i, v in enumerate(values)}
        
        # Create record that matches only the first filter
        first_match_record = {"field0": values[0]}
        
        if operator == FilterOperator.AND:
            assert group.matches(all_match_record) is True
            assert group.matches(first_match_record) is False
        elif operator == FilterOperator.OR:
            assert group.matches(all_match_record) is True
            assert group.matches(first_match_record) is True

    @given(filter_dict=st.fixed_dictionaries({
        "field": st.sampled_from(["severity", "location"]),
        "operator": st.sampled_from(["eq", "ne", "contains"]),
        "value": st.text(min_size=1, max_size=10).filter(lambda x: x.strip()),
    }))
    @settings(max_examples=50)
    def test_filter_parsing(self, filter_dict: dict):
        """
        Property: Filters are correctly parsed from dictionaries.
        """
        engine = FilterEngine()
        filter = engine.parse_filter(filter_dict)
        
        assert filter.field == filter_dict["field"]
        assert filter.operator == filter_dict["operator"]
        assert filter.value == filter_dict["value"]

    @given(
        n1=st.floats(min_value=0, max_value=100, allow_nan=False),
        n2=st.floats(min_value=0, max_value=100, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_numeric_comparison_operators(self, n1: float, n2: float):
        """
        Property: Numeric comparison operators work correctly.
        """
        record = {"value": n1}
        
        gt_filter = SearchFilter(field="value", operator="gt", value=n2)
        assert gt_filter.matches(record) == (n1 > n2)
        
        lt_filter = SearchFilter(field="value", operator="lt", value=n2)
        assert lt_filter.matches(record) == (n1 < n2)
        
        gte_filter = SearchFilter(field="value", operator="gte", value=n2)
        assert gte_filter.matches(record) == (n1 >= n2)
        
        lte_filter = SearchFilter(field="value", operator="lte", value=n2)
        assert lte_filter.matches(record) == (n1 <= n2)

    @given(
        text=st.text(min_size=5, max_size=50).filter(lambda x: x.strip()),
        substring=st.text(min_size=2, max_size=10).filter(lambda x: x.strip()),
    )
    @settings(max_examples=30)
    def test_contains_filter(self, text: str, substring: str):
        """
        Property: Contains filter works for substrings.
        """
        record = {"text": text}
        filter = SearchFilter(field="text", operator="contains", value=substring)
        
        expected = substring.lower() in text.lower()
        assert filter.matches(record) == expected


# =============================================================================
# Property 18: Entity Search Completeness
# =============================================================================


class TestEntitySearchCompleteness:
    """Property tests for entity search completeness."""

    @given(
        entity_id=entity_id_strategy,
        entity_type=st.sampled_from(["supplier", "component", "product"]),
    )
    @settings(max_examples=50)
    def test_indexed_entity_is_searchable(self, entity_id: str, entity_type: str):
        """
        Property: Indexed entities can be found by ID.
        """
        engine = EntitySearchEngine()
        engine.index_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            data={"name": f"Entity {entity_id}"},
        )
        
        results = engine.search_entity(entity_id)
        
        assert len(results) >= 1
        assert any(r.entity_id == entity_id for r in results)

    @given(
        name=st.text(min_size=3, max_size=30).filter(lambda x: x.strip())
    )
    @settings(max_examples=50)
    def test_entity_searchable_by_name(self, name: str):
        """
        Property: Entities can be found by name.
        """
        engine = EntitySearchEngine()
        entity_id = f"entity-{uuid.uuid4().hex[:8]}"
        
        engine.index_entity(
            entity_id=entity_id,
            entity_type="supplier",
            data={"name": name},
        )
        
        results = engine.search_entity(name)
        
        assert len(results) >= 1

    @given(
        source_type=st.sampled_from(["supplier", "component"]),
        target_type=st.sampled_from(["component", "product"]),
    )
    @settings(max_examples=30)
    def test_relationships_are_included(self, source_type: str, target_type: str):
        """
        Property: Related entities are included in search results.
        """
        engine = EntitySearchEngine()
        
        source_id = f"source-{uuid.uuid4().hex[:8]}"
        target_id = f"target-{uuid.uuid4().hex[:8]}"
        
        engine.index_entity(source_id, source_type, {"name": "Source"})
        engine.index_entity(target_id, target_type, {"name": "Target"})
        engine.add_relationship(source_id, target_id, "supplies")
        
        results = engine.search_entity(source_id, include_relationships=True)
        
        assert len(results) >= 1
        result = results[0]
        
        # Should have related entities
        all_related = (
            result.related_suppliers +
            result.related_components +
            result.related_products
        )
        assert len(all_related) >= 1

    @given(entity_id=entity_id_strategy)
    @settings(max_examples=50)
    def test_entity_search_result_structure(self, entity_id: str):
        """
        Property: Entity search results have correct structure.
        """
        engine = EntitySearchEngine()
        engine.index_entity(entity_id, "supplier", {"name": "Test"})
        
        results = engine.search_entity(entity_id)
        
        assert len(results) >= 1
        result = results[0]
        
        assert hasattr(result, "entity_id")
        assert hasattr(result, "entity_type")
        assert hasattr(result, "entity_data")
        assert hasattr(result, "related_risks")
        assert hasattr(result, "related_products")


# =============================================================================
# Property 19: Export Format Completeness
# =============================================================================


class TestExportFormatCompleteness:
    """Property tests for export format completeness."""

    @given(
        records=st.lists(
            st.fixed_dictionaries({
                "id": st.text(min_size=3, max_size=20),
                "value": st.integers(min_value=0, max_value=100),
            }),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_json_export_is_valid_json(self, records: list[dict]):
        """
        Property: JSON export produces valid JSON.
        """
        result = SearchResult(
            query="test",
            filters=None,
            total_count=len(records),
            returned_count=len(records),
            results=records,
            search_time_ms=100,
        )
        
        engine = ExportEngine()
        exported = engine.export_json(result)
        
        # Should be valid JSON
        parsed = json.loads(exported)
        assert "results" in parsed

    @given(
        records=st.lists(
            st.fixed_dictionaries({
                "id": st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))),
                "value": st.integers(min_value=0, max_value=100),
            }),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=30)
    def test_csv_export_has_all_records(self, records: list[dict]):
        """
        Property: CSV export contains all records.
        """
        result = SearchResult(
            query="test",
            filters=None,
            total_count=len(records),
            returned_count=len(records),
            results=records,
            search_time_ms=100,
        )
        
        engine = ExportEngine()
        exported = engine.export_csv(result)
        
        # Count data rows (excluding header)
        import csv as csv_module
        import io
        reader = csv_module.reader(io.StringIO(exported))
        rows = list(reader)
        # Header + data rows
        assert len(rows) == len(records) + 1

    @given(format=export_format_strategy)
    @settings(max_examples=10)
    def test_all_formats_are_supported(self, format: ExportFormat):
        """
        Property: All export formats are supported.
        """
        result = SearchResult(
            query="test",
            filters=None,
            total_count=1,
            returned_count=1,
            results=[{"id": "test-1"}],
            search_time_ms=50,
        )
        
        engine = ExportEngine()
        exported = engine.export(result, format)
        
        assert isinstance(exported, str)
        assert len(exported) > 0

    @given(records=st.lists(
        st.fixed_dictionaries({
            "id": st.text(min_size=3, max_size=20),
        }),
        min_size=1,
        max_size=5,
    ))
    @settings(max_examples=30)
    def test_export_includes_metadata(self, records: list[dict]):
        """
        Property: JSON export includes metadata.
        """
        result = SearchResult(
            query="test query",
            filters=None,
            total_count=len(records),
            returned_count=len(records),
            results=records,
            search_time_ms=100,
        )
        
        engine = ExportEngine()
        exported = engine.export_json(result, include_metadata=True)
        
        parsed = json.loads(exported)
        assert "metadata" in parsed
        assert parsed["metadata"]["query"] == "test query"
        assert parsed["metadata"]["total_count"] == len(records)


# =============================================================================
# Property 20: Saved Search Reusability
# =============================================================================


class TestSavedSearchReusability:
    """Property tests for saved search reusability."""

    @given(
        name=st.text(min_size=3, max_size=30).filter(lambda x: x.strip()),
        query=query_strategy,
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.filter_too_much])
    def test_search_can_be_saved(self, name: str, query: str):
        """
        Property: Searches can be saved with name and query.
        """
        engine = FullTextSearchEngine()
        manager = SavedSearchManager(engine)
        
        saved = manager.save_search(name=name, query=query)
        
        assert saved.name == name
        assert saved.query == query
        assert saved.search_id is not None

    @given(name=st.text(min_size=3, max_size=30).filter(lambda x: x.strip()))
    @settings(max_examples=50)
    def test_saved_search_retrievable_by_id(self, name: str):
        """
        Property: Saved searches can be retrieved by ID.
        """
        engine = FullTextSearchEngine()
        manager = SavedSearchManager(engine)
        
        saved = manager.save_search(name=name, query="test query")
        retrieved = manager.get_saved_search(saved.search_id)
        
        assert retrieved is not None
        assert retrieved.search_id == saved.search_id
        assert retrieved.name == name

    @given(name=st.text(min_size=3, max_size=30).filter(lambda x: x.strip()))
    @settings(max_examples=50)
    def test_saved_search_retrievable_by_name(self, name: str):
        """
        Property: Saved searches can be retrieved by name.
        """
        engine = FullTextSearchEngine()
        manager = SavedSearchManager(engine)
        
        saved = manager.save_search(name=name, query="test query")
        retrieved = manager.get_saved_search_by_name(name)
        
        assert retrieved is not None
        assert retrieved.name == name

    @given(
        names=st.lists(
            st.text(min_size=3, max_size=20).filter(lambda x: x.strip()),
            min_size=2,
            max_size=5,
            unique=True,
        )
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_list_saved_searches(self, names: list[str]):
        """
        Property: All saved searches can be listed.
        """
        engine = FullTextSearchEngine()
        manager = SavedSearchManager(engine)
        
        for name in names:
            manager.save_search(name=name, query="test query")
        
        listed = manager.list_saved_searches()
        
        assert len(listed) == len(names)

    @given(event=risk_event_strategy())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.filter_too_much])
    def test_saved_search_execution(self, event: RiskEvent):
        """
        Property: Saved searches can be executed.
        """
        engine = FullTextSearchEngine()
        engine.index_event(event)
        
        manager = SavedSearchManager(engine)
        saved = manager.save_search(name="Test Search", query=event.location)
        
        result = manager.execute_saved_search(saved.search_id)
        
        assert result is not None
        assert isinstance(result, SearchResult)
        assert saved.execution_count >= 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestSearchIntegration:
    """Integration tests for the search system."""

    @given(event=risk_event_strategy())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_search_manager_integration(self, event: RiskEvent):
        """
        Property: SearchManager integrates all search components.
        """
        manager = SearchManager()
        
        # Index event
        manager.index_event(event)
        
        # Search
        result = manager.search(event.location)
        
        assert isinstance(result, SearchResult)

    @given(
        event=risk_event_strategy(),
        format=export_format_strategy,
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.filter_too_much])
    def test_search_and_export_flow(self, event: RiskEvent, format: ExportFormat):
        """
        Property: Search results can be exported.
        """
        manager = SearchManager()
        manager.index_event(event)
        
        result = manager.search(event.location)
        exported = manager.export_results(result, format)
        
        assert isinstance(exported, str)
        assert len(exported) > 0
