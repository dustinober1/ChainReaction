"""
Search Query Generation for Supply Chain Monitoring.

Generates intelligent search queries to discover supply chain
disruption events across news sources.
"""

from dataclasses import dataclass
from typing import Iterator

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SearchQuery:
    """Represents a search query with metadata."""

    query: str
    category: str
    priority: int = 1  # 1 = highest priority
    description: str = ""


class QueryGenerator:
    """
    Generates search queries for supply chain disruption detection.

    Creates queries targeting:
    - Geographic regions with known supply chain activity
    - Specific event types (strikes, weather, geopolitical)
    - Industry-specific supply chain terms
    - Company-specific monitoring
    """

    # Base supply chain terms
    SUPPLY_CHAIN_TERMS = [
        "supply chain disruption",
        "manufacturing shutdown",
        "factory closure",
        "production halt",
        "supplier crisis",
        "component shortage",
        "logistics delay",
        "shipping disruption",
    ]

    # Geographic regions important for supply chains
    GEOGRAPHIC_REGIONS = {
        "taiwan": ["Taiwan", "Hsinchu", "TSMC", "semiconductor"],
        "china": ["China", "Shenzhen", "Guangdong", "manufacturing"],
        "vietnam": ["Vietnam", "Ho Chi Minh", "electronics manufacturing"],
        "south_korea": ["South Korea", "Seoul", "Samsung", "SK Hynix"],
        "japan": ["Japan", "Tokyo", "semiconductor", "automotive"],
        "germany": ["Germany", "Munich", "automotive", "industrial"],
        "usa": ["United States", "California", "Texas", "semiconductor"],
    }

    # Event type templates
    EVENT_TYPES = {
        "strike": [
            "workers strike",
            "labor dispute",
            "union walkout",
            "employee protest",
        ],
        "weather": [
            "typhoon damage",
            "earthquake disruption",
            "flood factory",
            "hurricane impact",
            "severe weather",
        ],
        "fire": [
            "factory fire",
            "manufacturing plant fire",
            "warehouse fire",
        ],
        "geopolitical": [
            "trade sanctions",
            "export restrictions",
            "tariff increase",
            "trade war",
        ],
        "cyber": [
            "ransomware attack",
            "cyber attack manufacturing",
            "data breach supply chain",
        ],
        "transport": [
            "port congestion",
            "shipping delay",
            "container shortage",
            "freight crisis",
        ],
        "bankruptcy": [
            "supplier bankruptcy",
            "manufacturer insolvency",
            "company liquidation",
        ],
    }

    # Industry sectors
    INDUSTRY_SECTORS = [
        "semiconductor",
        "electronics",
        "automotive",
        "pharmaceutical",
        "chemicals",
        "aerospace",
    ]

    def __init__(
        self,
        include_regions: list[str] | None = None,
        include_event_types: list[str] | None = None,
        custom_companies: list[str] | None = None,
    ):
        """
        Initialize the query generator.

        Args:
            include_regions: Specific regions to monitor (default: all).
            include_event_types: Specific event types to monitor (default: all).
            custom_companies: Additional company names to monitor.
        """
        self.regions = include_regions or list(self.GEOGRAPHIC_REGIONS.keys())
        self.event_types = include_event_types or list(self.EVENT_TYPES.keys())
        self.custom_companies = custom_companies or []

    def generate_all_queries(self) -> list[SearchQuery]:
        """
        Generate all search queries for comprehensive coverage.

        Returns:
            List of SearchQuery objects ordered by priority.
        """
        queries = []

        # Priority 1: High-priority disruption terms
        queries.extend(self._generate_disruption_queries())

        # Priority 2: Geographic + event type combinations
        queries.extend(self._generate_regional_queries())

        # Priority 3: Industry-specific queries
        queries.extend(self._generate_industry_queries())

        # Priority 4: Company-specific queries
        queries.extend(self._generate_company_queries())

        # Sort by priority
        queries.sort(key=lambda q: q.priority)

        logger.info("Generated search queries", count=len(queries))
        return queries

    def _generate_disruption_queries(self) -> list[SearchQuery]:
        """Generate high-priority disruption queries."""
        queries = []

        for term in self.SUPPLY_CHAIN_TERMS:
            queries.append(
                SearchQuery(
                    query=term,
                    category="disruption",
                    priority=1,
                    description=f"Core supply chain term: {term}",
                )
            )

        return queries

    def _generate_regional_queries(self) -> list[SearchQuery]:
        """Generate regional + event type queries."""
        queries = []

        for region in self.regions:
            if region not in self.GEOGRAPHIC_REGIONS:
                continue

            region_terms = self.GEOGRAPHIC_REGIONS[region]
            primary_location = region_terms[0]

            for event_type in self.event_types:
                if event_type not in self.EVENT_TYPES:
                    continue

                for event_term in self.EVENT_TYPES[event_type][:2]:  # Top 2 terms
                    query = f"{primary_location} {event_term}"
                    queries.append(
                        SearchQuery(
                            query=query,
                            category=f"regional_{event_type}",
                            priority=2,
                            description=f"{event_type} events in {region}",
                        )
                    )

        return queries

    def _generate_industry_queries(self) -> list[SearchQuery]:
        """Generate industry-specific queries."""
        queries = []

        for sector in self.INDUSTRY_SECTORS:
            for term in self.SUPPLY_CHAIN_TERMS[:3]:  # Top 3 disruption terms
                query = f"{sector} {term}"
                queries.append(
                    SearchQuery(
                        query=query,
                        category="industry",
                        priority=3,
                        description=f"{sector} sector disruptions",
                    )
                )

        return queries

    def _generate_company_queries(self) -> list[SearchQuery]:
        """Generate company-specific monitoring queries."""
        queries = []

        # Major supply chain players
        major_companies = [
            "TSMC", "Samsung Electronics", "Intel", "Foxconn",
            "Continental AG", "Bosch", "Nvidia", "AMD",
        ] + self.custom_companies

        for company in major_companies:
            query = f"{company} supply chain"
            queries.append(
                SearchQuery(
                    query=query,
                    category="company",
                    priority=4,
                    description=f"Monitoring: {company}",
                )
            )

        return queries

    def get_queries_by_category(self, category: str) -> list[SearchQuery]:
        """Get queries filtered by category."""
        all_queries = self.generate_all_queries()
        return [q for q in all_queries if q.category == category]

    def get_high_priority_queries(self, max_count: int = 20) -> list[SearchQuery]:
        """Get top priority queries for immediate execution."""
        all_queries = self.generate_all_queries()
        return all_queries[:max_count]

    def iterate_queries(
        self,
        max_per_run: int = 10,
    ) -> Iterator[list[SearchQuery]]:
        """
        Iterate through queries in batches.

        Args:
            max_per_run: Number of queries per batch.

        Yields:
            Batches of SearchQuery objects.
        """
        all_queries = self.generate_all_queries()

        for i in range(0, len(all_queries), max_per_run):
            yield all_queries[i : i + max_per_run]


class DynamicQueryGenerator:
    """
    Generates queries dynamically based on context.

    Can be enhanced with LLM-based query generation for
    adaptive monitoring.
    """

    def __init__(self, base_generator: QueryGenerator | None = None):
        """Initialize with optional base generator."""
        self.base_generator = base_generator or QueryGenerator()
        self._recent_events: list[str] = []

    def add_recent_event(self, event_description: str) -> None:
        """Add a recent event to influence query generation."""
        self._recent_events.append(event_description)
        # Keep only last 10 events
        self._recent_events = self._recent_events[-10:]

    def generate_followup_queries(
        self,
        event_location: str,
        event_type: str,
        affected_companies: list[str],
    ) -> list[SearchQuery]:
        """
        Generate follow-up queries based on a detected event.

        Args:
            event_location: Location of the detected event.
            event_type: Type of the event.
            affected_companies: List of affected company names.

        Returns:
            List of follow-up queries.
        """
        queries = []

        # Query for updates on the same location
        queries.append(
            SearchQuery(
                query=f"{event_location} {event_type} update",
                category="followup",
                priority=1,
                description=f"Follow-up on {event_location} event",
            )
        )

        # Query for affected companies
        for company in affected_companies[:3]:  # Limit to top 3
            queries.append(
                SearchQuery(
                    query=f"{company} supply chain impact",
                    category="followup",
                    priority=1,
                    description=f"Impact on {company}",
                )
            )

        # Related geographic queries
        queries.append(
            SearchQuery(
                query=f"{event_location} supply chain alternative suppliers",
                category="followup",
                priority=2,
                description="Alternative supplier search",
            )
        )

        return queries
