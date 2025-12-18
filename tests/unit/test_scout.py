"""
Unit tests for the Scout Agent and related components.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from src.agents.queries import (
    QueryGenerator,
    SearchQuery,
    DynamicQueryGenerator,
)
from src.agents.scout import (
    MonitoringConfig,
    EventDeduplicator,
    RateLimiter,
    ScoutAgent,
    MonitoringEvent,
)
from src.agents.sources import NewsArticle


class TestQueryGenerator:
    """Tests for the QueryGenerator class."""

    def test_generates_disruption_queries(self):
        """Test that disruption queries are generated."""
        generator = QueryGenerator()
        queries = generator.generate_all_queries()

        disruption_queries = [q for q in queries if q.category == "disruption"]
        assert len(disruption_queries) > 0

        # Check for common terms
        query_texts = [q.query for q in disruption_queries]
        assert any("supply chain" in q for q in query_texts)

    def test_generates_regional_queries(self):
        """Test that regional queries are generated."""
        generator = QueryGenerator(include_regions=["taiwan", "china"])
        queries = generator.generate_all_queries()

        regional_queries = [q for q in queries if q.category.startswith("regional")]
        assert len(regional_queries) > 0

    def test_generates_industry_queries(self):
        """Test that industry queries are generated."""
        generator = QueryGenerator()
        queries = generator.generate_all_queries()

        industry_queries = [q for q in queries if q.category == "industry"]
        assert len(industry_queries) > 0

        # Check for industry sectors
        query_texts = [q.query for q in industry_queries]
        assert any("semiconductor" in q for q in query_texts)

    def test_generates_company_queries(self):
        """Test that company queries are generated."""
        generator = QueryGenerator()
        queries = generator.generate_all_queries()

        company_queries = [q for q in queries if q.category == "company"]
        assert len(company_queries) > 0

        # Check for major companies
        query_texts = [q.query for q in company_queries]
        assert any("TSMC" in q for q in query_texts)

    def test_custom_companies_included(self):
        """Test that custom companies are included."""
        custom = ["MyCompany Inc", "TestCorp"]
        generator = QueryGenerator(custom_companies=custom)
        queries = generator.generate_all_queries()

        company_queries = [q for q in queries if q.category == "company"]
        query_texts = [q.query for q in company_queries]

        assert any("MyCompany" in q for q in query_texts)
        assert any("TestCorp" in q for q in query_texts)

    def test_queries_sorted_by_priority(self):
        """Test that queries are sorted by priority."""
        generator = QueryGenerator()
        queries = generator.generate_all_queries()

        priorities = [q.priority for q in queries]
        assert priorities == sorted(priorities)

    def test_high_priority_limit(self):
        """Test that high priority queries are limited."""
        generator = QueryGenerator()

        queries_10 = generator.get_high_priority_queries(max_count=10)
        queries_5 = generator.get_high_priority_queries(max_count=5)

        assert len(queries_10) <= 10
        assert len(queries_5) <= 5
        assert len(queries_5) < len(queries_10)

    def test_query_iteration(self):
        """Test query batch iteration."""
        generator = QueryGenerator()

        batches = list(generator.iterate_queries(max_per_run=10))

        assert len(batches) > 0
        assert all(len(batch) <= 10 for batch in batches)


class TestDynamicQueryGenerator:
    """Tests for the DynamicQueryGenerator class."""

    def test_followup_queries_for_event(self):
        """Test follow-up query generation."""
        generator = DynamicQueryGenerator()

        followups = generator.generate_followup_queries(
            event_location="Taiwan",
            event_type="weather",
            affected_companies=["TSMC", "MediaTek"],
        )

        assert len(followups) > 0
        assert all(q.category == "followup" for q in followups)
        assert all(q.priority in [1, 2] for q in followups)

    def test_recent_event_tracking(self):
        """Test recent event memory."""
        generator = DynamicQueryGenerator()

        generator.add_recent_event("Event 1")
        generator.add_recent_event("Event 2")

        assert len(generator._recent_events) == 2

    def test_recent_event_limit(self):
        """Test that only last 10 events are kept."""
        generator = DynamicQueryGenerator()

        for i in range(15):
            generator.add_recent_event(f"Event {i}")

        assert len(generator._recent_events) == 10
        assert "Event 14" in generator._recent_events[-1]


class TestEventDeduplicator:
    """Tests for the EventDeduplicator class."""

    def test_first_article_not_duplicate(self):
        """Test that first occurrence is not a duplicate."""
        deduplicator = EventDeduplicator()

        article = NewsArticle(
            source="test",
            url="https://example.com/article1",
            title="Test Article",
            content="Content here",
            published_at=datetime.now(timezone.utc),
        )

        assert not deduplicator.is_duplicate(article)

    def test_same_article_is_duplicate(self):
        """Test that same article is detected as duplicate."""
        deduplicator = EventDeduplicator()

        article = NewsArticle(
            source="test",
            url="https://example.com/article1",
            title="Test Article",
            content="Content here",
            published_at=datetime.now(timezone.utc),
        )

        deduplicator.mark_seen(article)
        assert deduplicator.is_duplicate(article)

    def test_different_articles_not_duplicates(self):
        """Test that different articles are not duplicates."""
        deduplicator = EventDeduplicator()

        article1 = NewsArticle(
            source="test",
            url="https://example.com/article1",
            title="Test Article 1",
            content="Content 1",
            published_at=datetime.now(timezone.utc),
        )

        article2 = NewsArticle(
            source="test",
            url="https://example.com/article2",
            title="Test Article 2",
            content="Content 2",
            published_at=datetime.now(timezone.utc),
        )

        deduplicator.mark_seen(article1)
        assert not deduplicator.is_duplicate(article2)

    def test_stats_tracking(self):
        """Test deduplicator statistics."""
        deduplicator = EventDeduplicator()

        for i in range(5):
            article = NewsArticle(
                source="test",
                url=f"https://example.com/article{i}",
                title=f"Article {i}",
                content=f"Content {i}",
                published_at=datetime.now(timezone.utc),
            )
            deduplicator.mark_seen(article)

        stats = deduplicator.get_stats()
        assert stats["unique_articles_seen"] == 5


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    @pytest.mark.asyncio
    async def test_acquire_token(self):
        """Test token acquisition."""
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)

        # Should be able to acquire token
        result = await limiter.acquire()
        assert result is True

    @pytest.mark.asyncio
    async def test_remaining_quota(self):
        """Test remaining quota tracking."""
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)

        remaining_before = limiter.get_remaining()
        await limiter.acquire()
        remaining_after = limiter.get_remaining()

        assert remaining_after["minute_remaining"] == remaining_before["minute_remaining"] - 1
        assert remaining_after["hour_remaining"] == remaining_before["hour_remaining"] - 1

    @pytest.mark.asyncio
    async def test_rate_limit_exhaustion(self):
        """Test rate limit when exhausted."""
        limiter = RateLimiter(requests_per_minute=3, requests_per_hour=100)

        # Exhaust minute limit
        for _ in range(3):
            await limiter.acquire()

        # Should be rate limited
        result = await limiter.acquire()
        assert result is False


class TestMonitoringConfig:
    """Tests for MonitoringConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MonitoringConfig()

        assert config.interval_seconds == 300
        assert config.max_queries_per_run == 10
        assert config.days_back == 7
        assert config.min_relevance_score == 0.5

    def test_custom_config(self):
        """Test custom configuration."""
        config = MonitoringConfig(
            interval_seconds=600,
            max_queries_per_run=20,
            enabled_regions=["taiwan", "china"],
        )

        assert config.interval_seconds == 600
        assert config.max_queries_per_run == 20
        assert config.enabled_regions == ["taiwan", "china"]


class TestNewsArticle:
    """Tests for NewsArticle."""

    def test_content_hash_generation(self):
        """Test content hash is generated correctly."""
        article = NewsArticle(
            source="test",
            url="https://example.com/test",
            title="Test Title",
            content="Test content",
            published_at=datetime.now(timezone.utc),
        )

        hash1 = article.content_hash
        hash2 = article.content_hash

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_to_raw_event_conversion(self):
        """Test conversion to RawEvent model."""
        article = NewsArticle(
            source="tavily",
            url="https://example.com/news",
            title="Breaking News",
            content="Full article content here...",
            published_at=datetime.now(timezone.utc),
        )

        raw_event = article.to_raw_event()

        assert raw_event.source == "tavily"
        assert raw_event.url == "https://example.com/news"
        assert raw_event.title == "Breaking News"
        assert raw_event.content == "Full article content here..."
