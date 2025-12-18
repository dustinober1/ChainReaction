"""
Property-Based Tests for Scout Agent and Search Coverage.

Feature: chain-reaction
Property 4: Comprehensive search coverage
Property 7: Multi-source search execution

Validates that the Scout Agent correctly executes searches across
all configured sources and generates comprehensive query coverage.

Validates: Requirements 2.1, 2.5
"""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from src.agents.queries import (
    QueryGenerator,
    SearchQuery,
    DynamicQueryGenerator,
)
from src.agents.scout import (
    MonitoringConfig,
    EventDeduplicator,
    RateLimiter,
    MonitoringEvent,
)
from src.agents.sources import NewsArticle

from datetime import datetime, timezone


# =============================================================================
# Test Strategies
# =============================================================================

@st.composite
def news_article_strategy(draw) -> NewsArticle:
    """Generate random news articles for testing."""
    return NewsArticle(
        source=draw(st.sampled_from(["tavily", "newsapi"])),
        url=draw(st.text(min_size=10, max_size=50).map(
            lambda s: f"https://news.example.com/{s}"
        )),
        title=draw(st.text(min_size=10, max_size=100)),
        content=draw(st.text(min_size=50, max_size=500)),
        published_at=draw(st.datetimes().map(lambda dt: dt.replace(tzinfo=timezone.utc))),
        relevance_score=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


@st.composite
def monitoring_config_strategy(draw) -> MonitoringConfig:
    """Generate random monitoring configurations."""
    return MonitoringConfig(
        interval_seconds=draw(st.integers(min_value=60, max_value=3600)),
        max_queries_per_run=draw(st.integers(min_value=1, max_value=50)),
        max_results_per_query=draw(st.integers(min_value=1, max_value=20)),
        days_back=draw(st.integers(min_value=1, max_value=30)),
        min_relevance_score=draw(st.floats(min_value=0.0, max_value=1.0)),
        dedup_window_hours=draw(st.integers(min_value=1, max_value=168)),
    )


# =============================================================================
# Property 4: Comprehensive search coverage
# =============================================================================


class TestComprehensiveSearchCoverage:
    """
    Property-based tests for comprehensive search coverage.

    Feature: chain-reaction, Property 4: Comprehensive search coverage
    """

    @given(st.lists(
        st.sampled_from(["taiwan", "china", "vietnam", "germany", "usa"]),
        min_size=1,
        max_size=5,
        unique=True,
    ))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_queries_cover_all_specified_regions(self, regions: list[str]):
        """
        Property: Generated queries cover all specified regions.

        Feature: chain-reaction, Property 4: Comprehensive search coverage
        Validates: Requirements 2.1
        """
        generator = QueryGenerator(include_regions=regions)
        queries = generator.generate_all_queries()

        # Extract unique regions from generated queries
        regional_queries = [q for q in queries if q.category.startswith("regional")]

        # Each region should have queries generated
        for region in regions:
            region_covered = any(
                region.lower() in q.description.lower() or
                region.lower() in q.query.lower()
                for q in regional_queries
            )
            assert region_covered, f"Region {region} not covered in queries"

    @given(st.lists(
        st.sampled_from(["strike", "weather", "fire", "cyber", "transport"]),
        min_size=1,
        max_size=5,
        unique=True,
    ))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_queries_cover_all_event_types(self, event_types: list[str]):
        """
        Property: Generated queries cover all specified event types.

        Feature: chain-reaction, Property 4: Comprehensive search coverage
        Validates: Requirements 2.1
        """
        generator = QueryGenerator(include_event_types=event_types)
        queries = generator.generate_all_queries()

        # Check for each event type
        for event_type in event_types:
            type_covered = any(
                event_type in q.category or event_type.lower() in q.query.lower()
                for q in queries
            )
            assert type_covered, f"Event type {event_type} not covered"

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_high_priority_queries_limited_correctly(self, max_count: int):
        """
        Property: High priority query limit is respected.

        Feature: chain-reaction, Property 4: Comprehensive search coverage
        Validates: Requirements 2.1
        """
        generator = QueryGenerator()
        queries = generator.get_high_priority_queries(max_count=max_count)

        assert len(queries) <= max_count

    def test_queries_include_all_categories(self):
        """
        Test: Query generation includes disruption, regional, industry, and company categories.

        Feature: chain-reaction, Property 4: Comprehensive search coverage
        Validates: Requirements 2.1
        """
        generator = QueryGenerator()
        queries = generator.generate_all_queries()

        categories = {q.category for q in queries}

        assert "disruption" in categories
        assert any("regional" in c for c in categories)
        assert "industry" in categories
        assert "company" in categories

    @given(st.lists(st.text(min_size=3, max_size=30), min_size=1, max_size=5))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_custom_companies_included_in_queries(self, companies: list[str]):
        """
        Property: Custom companies are included in generated queries.

        Feature: chain-reaction, Property 4: Comprehensive search coverage
        Validates: Requirements 2.1
        """
        # Filter empty companies
        companies = [c for c in companies if c.strip()]
        if not companies:
            return

        generator = QueryGenerator(custom_companies=companies)
        queries = generator.generate_all_queries()

        company_queries = [q for q in queries if q.category == "company"]

        for company in companies:
            company_covered = any(
                company in q.query or company in q.description
                for q in company_queries
            )
            assert company_covered, f"Company {company} not covered"


# =============================================================================
# Property 7: Multi-source search execution
# =============================================================================


class TestMultiSourceSearchExecution:
    """
    Property-based tests for multi-source search execution.

    Feature: chain-reaction, Property 7: Multi-source search execution
    """

    @given(st.lists(news_article_strategy(), min_size=2, max_size=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_deduplicator_detects_duplicates(self, articles: list[NewsArticle]):
        """
        Property: Deduplicator correctly identifies duplicate articles.

        Feature: chain-reaction, Property 7: Multi-source search execution
        Validates: Requirements 2.5
        """
        deduplicator = EventDeduplicator(window_hours=24)

        # First article should never be duplicate
        first = articles[0]
        assert not deduplicator.is_duplicate(first)
        deduplicator.mark_seen(first)

        # Same article again should be duplicate
        assert deduplicator.is_duplicate(first)

    @given(news_article_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_content_hash_is_deterministic(self, article: NewsArticle):
        """
        Property: Content hash is deterministic for same article.

        Feature: chain-reaction, Property 7: Multi-source search execution
        Validates: Requirements 2.5
        """
        hash1 = article.content_hash
        hash2 = article.content_hash

        assert hash1 == hash2
        assert len(hash1) == 16  # Expected hash length

    @given(st.lists(news_article_strategy(), min_size=5, max_size=20))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
    def test_deduplicator_stats_accurate(self, articles: list[NewsArticle]):
        """
        Property: Deduplicator stats reflect actual state.

        Feature: chain-reaction, Property 7: Multi-source search execution
        Validates: Requirements 2.5
        """
        deduplicator = EventDeduplicator()

        seen_count = 0
        for article in articles:
            if not deduplicator.is_duplicate(article):
                deduplicator.mark_seen(article)
                seen_count += 1

        stats = deduplicator.get_stats()
        assert stats["unique_articles_seen"] >= 1

    @given(
        st.integers(min_value=1, max_value=100),
        st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=50)
    def test_rate_limiter_respects_limits(
        self,
        rpm: int,
        rph: int,
    ):
        """
        Property: Rate limiter correctly tracks remaining quota.

        Feature: chain-reaction, Property 7: Multi-source search execution
        Validates: Requirements 2.5
        """
        limiter = RateLimiter(requests_per_minute=rpm, requests_per_hour=rph)
        remaining = limiter.get_remaining()

        assert remaining["minute_remaining"] == rpm
        assert remaining["hour_remaining"] == rph

    @given(monitoring_config_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_config_values_are_valid(self, config: MonitoringConfig):
        """
        Property: All monitoring config values are within valid ranges.

        Feature: chain-reaction, Property 7: Multi-source search execution
        Validates: Requirements 2.5
        """
        assert config.interval_seconds > 0
        assert config.max_queries_per_run > 0
        assert config.max_results_per_query > 0
        assert config.days_back > 0
        assert 0.0 <= config.min_relevance_score <= 1.0
        assert config.dedup_window_hours > 0


# =============================================================================
# Dynamic Query Tests
# =============================================================================


class TestDynamicQueryGeneration:
    """Tests for dynamic/follow-up query generation."""

    @given(
        st.text(min_size=3, max_size=30),  # location
        st.sampled_from(["strike", "weather", "fire", "bankruptcy"]),  # event_type
        st.lists(st.text(min_size=3, max_size=30), min_size=1, max_size=5),  # companies
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_followup_queries_generated(
        self,
        location: str,
        event_type: str,
        companies: list[str],
    ):
        """
        Property: Follow-up queries are generated for detected events.

        Feature: chain-reaction
        Validates: Requirements 2.1
        """
        # Filter empty values
        companies = [c for c in companies if c.strip()]
        if not location.strip() or not companies:
            return

        generator = DynamicQueryGenerator()
        followups = generator.generate_followup_queries(
            event_location=location,
            event_type=event_type,
            affected_companies=companies,
        )

        assert len(followups) > 0
        assert all(q.category == "followup" for q in followups)

    def test_recent_events_tracked(self):
        """
        Test: Dynamic generator tracks recent events.

        Feature: chain-reaction
        Validates: Requirements 2.1
        """
        generator = DynamicQueryGenerator()

        generator.add_recent_event("Factory fire in Taiwan")
        generator.add_recent_event("Port strike in LA")

        # Adding more should work
        for i in range(15):
            generator.add_recent_event(f"Event {i}")

        # Should only keep last 10
        assert len(generator._recent_events) == 10
