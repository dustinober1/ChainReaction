"""
Scout Agent for Autonomous Supply Chain Monitoring.

Implements LangGraph-based agent for continuous news monitoring,
event detection, and risk extraction from multiple sources.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Awaitable
import hashlib

import structlog

from src.agents.sources import MultiSourceNewsClient, NewsArticle
from src.agents.queries import QueryGenerator, SearchQuery
from src.models import RawEvent, RiskEvent, EventType, SeverityLevel

logger = structlog.get_logger(__name__)


@dataclass
class MonitoringConfig:
    """Configuration for the monitoring loop."""

    interval_seconds: int = 300  # 5 minutes
    max_queries_per_run: int = 10
    max_results_per_query: int = 5
    days_back: int = 7
    min_relevance_score: float = 0.5
    dedup_window_hours: int = 24
    enabled_regions: list[str] = field(default_factory=list)
    enabled_event_types: list[str] = field(default_factory=list)


@dataclass
class MonitoringEvent:
    """An event detected during monitoring."""

    article: NewsArticle
    detected_at: datetime
    query_used: str
    relevance_score: float


class EventDeduplicator:
    """
    Handles event deduplication across monitoring runs.

    Uses content hashing and time windows to prevent
    duplicate processing of the same news.
    """

    def __init__(self, window_hours: int = 24):
        """
        Initialize the deduplicator.

        Args:
            window_hours: Time window for deduplication.
        """
        self.window_hours = window_hours
        self._seen_hashes: dict[str, datetime] = {}

    def is_duplicate(self, article: NewsArticle) -> bool:
        """
        Check if an article is a duplicate.

        Args:
            article: The article to check.

        Returns:
            True if the article is a duplicate.
        """
        content_hash = self._compute_hash(article)
        now = datetime.now(timezone.utc)

        if content_hash in self._seen_hashes:
            seen_at = self._seen_hashes[content_hash]
            if now - seen_at < timedelta(hours=self.window_hours):
                return True

        return False

    def mark_seen(self, article: NewsArticle) -> None:
        """Mark an article as seen."""
        content_hash = self._compute_hash(article)
        self._seen_hashes[content_hash] = datetime.now(timezone.utc)

    def _compute_hash(self, article: NewsArticle) -> str:
        """Compute content hash for an article."""
        content = f"{article.title}|{article.url}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def cleanup_expired(self) -> int:
        """Remove expired entries from the cache."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=self.window_hours)

        expired = [
            h for h, t in self._seen_hashes.items() if t < cutoff
        ]

        for h in expired:
            del self._seen_hashes[h]

        return len(expired)

    def get_stats(self) -> dict[str, Any]:
        """Get deduplication statistics."""
        return {
            "unique_articles_seen": len(self._seen_hashes),
            "window_hours": self.window_hours,
        }


class RateLimiter:
    """
    Rate limiter for API calls.

    Implements token bucket algorithm for smooth rate limiting.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        """
        Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute.
            requests_per_hour: Maximum requests per hour.
        """
        self.rpm_limit = requests_per_minute
        self.rph_limit = requests_per_hour

        self._minute_tokens = requests_per_minute
        self._hour_tokens = requests_per_hour
        self._last_minute_refill = datetime.now(timezone.utc)
        self._last_hour_refill = datetime.now(timezone.utc)

    async def acquire(self) -> bool:
        """
        Acquire a rate limit token.

        Returns:
            True if token acquired, False if rate limited.
        """
        self._refill_tokens()

        if self._minute_tokens > 0 and self._hour_tokens > 0:
            self._minute_tokens -= 1
            self._hour_tokens -= 1
            return True

        return False

    async def wait_for_token(self) -> None:
        """Wait until a token is available."""
        while not await self.acquire():
            await asyncio.sleep(1.0)

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = datetime.now(timezone.utc)

        # Refill minute tokens
        minute_elapsed = (now - self._last_minute_refill).total_seconds()
        if minute_elapsed >= 60:
            self._minute_tokens = self.rpm_limit
            self._last_minute_refill = now

        # Refill hour tokens
        hour_elapsed = (now - self._last_hour_refill).total_seconds()
        if hour_elapsed >= 3600:
            self._hour_tokens = self.rph_limit
            self._last_hour_refill = now

    def get_remaining(self) -> dict[str, int]:
        """Get remaining rate limit quota."""
        self._refill_tokens()
        return {
            "minute_remaining": self._minute_tokens,
            "hour_remaining": self._hour_tokens,
        }


class ScoutAgent:
    """
    Autonomous agent for supply chain news monitoring.

    Features:
    - Multi-source news search
    - Intelligent query generation
    - Event deduplication
    - Rate limiting
    - Callback-based event processing
    """

    def __init__(
        self,
        config: MonitoringConfig | None = None,
        news_client: MultiSourceNewsClient | None = None,
        query_generator: QueryGenerator | None = None,
    ):
        """
        Initialize the Scout Agent.

        Args:
            config: Monitoring configuration.
            news_client: News client for searching.
            query_generator: Query generator for searches.
        """
        self.config = config or MonitoringConfig()
        self.news_client = news_client or MultiSourceNewsClient()
        self.query_generator = query_generator or QueryGenerator(
            include_regions=self.config.enabled_regions or None,
            include_event_types=self.config.enabled_event_types or None,
        )

        self.deduplicator = EventDeduplicator(
            window_hours=self.config.dedup_window_hours
        )
        self.rate_limiter = RateLimiter()

        # Callbacks for event processing
        self._event_callbacks: list[Callable[[MonitoringEvent], Awaitable[None]]] = []

        # State tracking
        self._is_running = False
        self._last_run: datetime | None = None
        self._total_events_detected = 0
        self._run_history: list[dict[str, Any]] = []

    async def close(self) -> None:
        """Cleanup resources."""
        await self.news_client.close()

    def register_callback(
        self,
        callback: Callable[[MonitoringEvent], Awaitable[None]],
    ) -> None:
        """
        Register a callback for detected events.

        Args:
            callback: Async function to call when events are detected.
        """
        self._event_callbacks.append(callback)

    async def run_once(self) -> list[MonitoringEvent]:
        """
        Run a single monitoring cycle.

        Returns:
            List of detected events.
        """
        logger.info("Starting monitoring run")
        run_start = datetime.now(timezone.utc)

        events_detected: list[MonitoringEvent] = []

        # Get queries for this run
        queries = self.query_generator.get_high_priority_queries(
            max_count=self.config.max_queries_per_run
        )

        for query in queries:
            # Check rate limit
            await self.rate_limiter.wait_for_token()

            try:
                # Search for articles
                articles = await self.news_client.search_all(
                    query=query.query,
                    max_results_per_source=self.config.max_results_per_query,
                    days_back=self.config.days_back,
                )

                # Process each article
                for article in articles:
                    # Filter by relevance
                    if article.relevance_score < self.config.min_relevance_score:
                        continue

                    # Check for duplicates
                    if self.deduplicator.is_duplicate(article):
                        continue

                    # Create monitoring event
                    event = MonitoringEvent(
                        article=article,
                        detected_at=datetime.now(timezone.utc),
                        query_used=query.query,
                        relevance_score=article.relevance_score,
                    )

                    events_detected.append(event)
                    self.deduplicator.mark_seen(article)

                    # Notify callbacks
                    for callback in self._event_callbacks:
                        try:
                            await callback(event)
                        except Exception as e:
                            logger.error("Callback error", error=str(e))

            except Exception as e:
                logger.warning(
                    "Query search failed",
                    query=query.query,
                    error=str(e),
                )
                continue

        # Update stats
        self._last_run = run_start
        self._total_events_detected += len(events_detected)
        self._run_history.append({
            "timestamp": run_start.isoformat(),
            "queries_executed": len(queries),
            "events_detected": len(events_detected),
        })

        # Cleanup old dedup entries
        self.deduplicator.cleanup_expired()

        logger.info(
            "Monitoring run complete",
            duration_seconds=(datetime.now(timezone.utc) - run_start).total_seconds(),
            events_detected=len(events_detected),
        )

        return events_detected

    async def run_continuous(self, max_runs: int | None = None) -> None:
        """
        Run continuous monitoring loop.

        Args:
            max_runs: Maximum number of runs (None for infinite).
        """
        self._is_running = True
        run_count = 0

        logger.info(
            "Starting continuous monitoring",
            interval=self.config.interval_seconds,
        )

        try:
            while self._is_running:
                await self.run_once()

                run_count += 1
                if max_runs and run_count >= max_runs:
                    break

                # Wait for next interval
                await asyncio.sleep(self.config.interval_seconds)

        except asyncio.CancelledError:
            logger.info("Monitoring cancelled")
        finally:
            self._is_running = False

    def stop(self) -> None:
        """Stop the continuous monitoring loop."""
        self._is_running = False
        logger.info("Monitoring stop requested")

    def get_stats(self) -> dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "is_running": self._is_running,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "total_events_detected": self._total_events_detected,
            "total_runs": len(self._run_history),
            "dedup_stats": self.deduplicator.get_stats(),
            "rate_limit_remaining": self.rate_limiter.get_remaining(),
            "recent_runs": self._run_history[-5:],
        }

    async def test_sources(self) -> dict[str, bool]:
        """Test connectivity to all news sources."""
        return await self.news_client.check_sources()


# =============================================================================
# Event Processing Helpers
# =============================================================================


async def log_event_callback(event: MonitoringEvent) -> None:
    """Simple callback that logs detected events."""
    logger.info(
        "Event detected",
        title=event.article.title[:50],
        source=event.article.source,
        relevance=event.relevance_score,
    )


async def create_raw_event_callback(
    events_list: list[RawEvent],
) -> Callable[[MonitoringEvent], Awaitable[None]]:
    """Create a callback that appends raw events to a list."""

    async def callback(event: MonitoringEvent) -> None:
        raw_event = event.article.to_raw_event()
        events_list.append(raw_event)

    return callback
