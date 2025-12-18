"""
News Source Integration Clients.

Provides unified interfaces for fetching news from multiple sources
including Tavily Search API and NewsAPI.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any
import hashlib

import httpx
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.config import get_settings
from src.models import RawEvent

logger = structlog.get_logger(__name__)


@dataclass
class NewsArticle:
    """Represents a news article from any source."""

    source: str
    url: str
    title: str
    content: str
    published_at: datetime | None
    relevance_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        """Generate a hash for deduplication."""
        content = f"{self.title}{self.url}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_raw_event(self) -> RawEvent:
        """Convert to RawEvent model."""
        return RawEvent(
            source=self.source,
            url=self.url,
            title=self.title,
            content=self.content,
            published_at=self.published_at,
        )


class NewsClient(ABC):
    """Abstract base class for news source clients."""

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 10,
        days_back: int = 7,
    ) -> list[NewsArticle]:
        """
        Search for news articles matching a query.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.
            days_back: How many days back to search.

        Returns:
            List of NewsArticle objects.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the news source is accessible."""
        pass


class TavilyClient(NewsClient):
    """
    Client for Tavily Search API.

    Tavily provides AI-optimized search results focused on
    current events and news.
    """

    BASE_URL = "https://api.tavily.com"

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Tavily client.

        Args:
            api_key: Tavily API key. If None, loads from settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.tavily_api_key.get_secret_value()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def search(
        self,
        query: str,
        max_results: int = 10,
        days_back: int = 7,
    ) -> list[NewsArticle]:
        """
        Search for news using Tavily API.

        Args:
            query: Search query focused on supply chain topics.
            max_results: Maximum results to return.
            days_back: Days to look back (note: Tavily may have limited history).

        Returns:
            List of NewsArticle objects.
        """
        client = await self._get_client()

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": True,
            "max_results": max_results,
            "topic": "news",
        }

        try:
            response = await client.post(
                f"{self.BASE_URL}/search",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            articles = []
            for result in data.get("results", []):
                # Parse published date if available
                published_at = None
                if pub_date := result.get("published_date"):
                    try:
                        published_at = datetime.fromisoformat(
                            pub_date.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                article = NewsArticle(
                    source="tavily",
                    url=result.get("url", ""),
                    title=result.get("title", ""),
                    content=result.get("raw_content") or result.get("content", ""),
                    published_at=published_at,
                    relevance_score=result.get("score", 0.0),
                    metadata={
                        "domain": result.get("domain"),
                        "snippet": result.get("content", "")[:500],
                    },
                )
                articles.append(article)

            logger.info(
                "Tavily search complete",
                query=query[:50],
                results=len(articles),
            )
            return articles

        except httpx.HTTPStatusError as e:
            logger.error("Tavily API error", status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Tavily search failed", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check Tavily API connectivity."""
        try:
            # Simple search to verify API key
            results = await self.search("test", max_results=1)
            return True
        except Exception:
            return False


class NewsAPIClient(NewsClient):
    """
    Client for NewsAPI.org.

    Provides access to news articles from various publishers worldwide.
    """

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: str | None = None):
        """
        Initialize the NewsAPI client.

        Args:
            api_key: NewsAPI key. If None, loads from settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.newsapi_api_key.get_secret_value()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    )
    async def search(
        self,
        query: str,
        max_results: int = 10,
        days_back: int = 7,
    ) -> list[NewsArticle]:
        """
        Search for news using NewsAPI.

        Args:
            query: Search query string.
            max_results: Maximum results to return.
            days_back: Days to look back.

        Returns:
            List of NewsArticle objects.
        """
        client = await self._get_client()

        from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
            "%Y-%m-%d"
        )

        params = {
            "apiKey": self.api_key,
            "q": query,
            "from": from_date,
            "sortBy": "relevancy",
            "pageSize": max_results,
            "language": "en",
        }

        try:
            response = await client.get(
                f"{self.BASE_URL}/everything",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                raise ValueError(f"NewsAPI error: {data.get('message')}")

            articles = []
            for article in data.get("articles", []):
                # Parse published date
                published_at = None
                if pub_date := article.get("publishedAt"):
                    try:
                        published_at = datetime.fromisoformat(
                            pub_date.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

                news_article = NewsArticle(
                    source="newsapi",
                    url=article.get("url", ""),
                    title=article.get("title", ""),
                    content=article.get("content") or article.get("description", ""),
                    published_at=published_at,
                    relevance_score=0.8,  # NewsAPI doesn't provide relevance scores
                    metadata={
                        "author": article.get("author"),
                        "source_name": article.get("source", {}).get("name"),
                        "description": article.get("description", ""),
                    },
                )
                articles.append(news_article)

            logger.info(
                "NewsAPI search complete",
                query=query[:50],
                results=len(articles),
            )
            return articles

        except httpx.HTTPStatusError as e:
            logger.error("NewsAPI error", status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.error("NewsAPI search failed", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check NewsAPI connectivity."""
        try:
            results = await self.search("technology", max_results=1)
            return True
        except Exception:
            return False


class MultiSourceNewsClient:
    """
    Aggregates searches across multiple news sources.

    Handles deduplication and result merging from multiple APIs.
    """

    def __init__(
        self,
        tavily_api_key: str | None = None,
        newsapi_key: str | None = None,
    ):
        """
        Initialize the multi-source client.

        Args:
            tavily_api_key: Optional Tavily API key.
            newsapi_key: Optional NewsAPI key.
        """
        self.clients: list[NewsClient] = []

        # Initialize available clients
        try:
            self.clients.append(TavilyClient(api_key=tavily_api_key))
        except Exception as e:
            logger.warning("Tavily client not available", error=str(e))

        try:
            self.clients.append(NewsAPIClient(api_key=newsapi_key))
        except Exception as e:
            logger.warning("NewsAPI client not available", error=str(e))

        self._seen_hashes: set[str] = set()

    async def close(self) -> None:
        """Close all client connections."""
        for client in self.clients:
            if hasattr(client, "close"):
                await client.close()

    async def search_all(
        self,
        query: str,
        max_results_per_source: int = 10,
        days_back: int = 7,
    ) -> list[NewsArticle]:
        """
        Search all available news sources.

        Args:
            query: Search query string.
            max_results_per_source: Max results from each source.
            days_back: Days to look back.

        Returns:
            Deduplicated list of NewsArticle objects.
        """
        all_articles: list[NewsArticle] = []

        # Run searches in parallel
        tasks = [
            client.search(query, max_results_per_source, days_back)
            for client in self.clients
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "Source search failed",
                    source_index=i,
                    error=str(result),
                )
                continue

            for article in result:
                # Deduplicate by content hash
                if article.content_hash not in self._seen_hashes:
                    self._seen_hashes.add(article.content_hash)
                    all_articles.append(article)

        # Sort by relevance score
        all_articles.sort(key=lambda a: a.relevance_score, reverse=True)

        logger.info(
            "Multi-source search complete",
            query=query[:50],
            total_results=len(all_articles),
            sources=len(self.clients),
        )

        return all_articles

    async def check_sources(self) -> dict[str, bool]:
        """Check health of all news sources."""
        results = {}
        for client in self.clients:
            source_name = client.__class__.__name__
            try:
                results[source_name] = await client.health_check()
            except Exception:
                results[source_name] = False
        return results

    def clear_dedup_cache(self) -> None:
        """Clear the deduplication cache."""
        self._seen_hashes.clear()
