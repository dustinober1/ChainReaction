"""
Performance Optimization Module for Supply Chain Risk Management.

Provides query caching, batch processing, resource monitoring,
data retention policies, and horizontal scaling support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, TypeVar, Generic
from collections import defaultdict
from functools import wraps
import threading
import time
import asyncio
import uuid
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# =============================================================================
# Enums and Data Classes
# =============================================================================


class CacheStrategy(str, Enum):
    """Caching strategies."""

    LRU = "lru"  # Least Recently Used
    TTL = "ttl"  # Time To Live
    LFU = "lfu"  # Least Frequently Used


class RetentionPeriod(str, Enum):
    """Data retention periods."""

    DAYS_7 = "7_days"
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    DAYS_365 = "365_days"
    INDEFINITE = "indefinite"


class ResourceType(str, Enum):
    """Types of monitored resources."""

    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    DISK = "disk"


@dataclass
class CacheEntry(Generic[T]):
    """A cached entry with metadata."""

    key: str
    value: T
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: int | None = None

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl_seconds


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@dataclass
class BatchResult:
    """Result of batch processing."""

    batch_id: str
    processed: int
    failed: int
    duration_ms: int
    items_per_second: float
    errors: list[str] = field(default_factory=list)


@dataclass
class ResourceUsage:
    """Current resource usage snapshot."""

    resource_type: ResourceType
    current_value: float
    limit: float
    percentage: float
    timestamp: datetime


@dataclass
class ResourceLimits:
    """Resource limits configuration."""

    cpu_percent: float = 80.0
    memory_mb: float = 512.0
    network_mbps: float = 100.0
    disk_iops: float = 1000.0


@dataclass
class RetentionPolicy:
    """Data retention policy."""

    data_type: str
    retention_period: RetentionPeriod
    archive_enabled: bool = True
    archive_destination: str = "cold_storage"
    cleanup_batch_size: int = 1000


@dataclass
class ThroughputMetrics:
    """Throughput monitoring metrics."""

    events_processed: int = 0
    events_per_minute: float = 0.0
    peak_rate: float = 0.0
    avg_processing_time_ms: float = 0.0
    last_updated: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# Query Cache
# =============================================================================


class QueryCache(Generic[T]):
    """
    Thread-safe query caching with multiple eviction strategies.

    Supports LRU, TTL, and LFU caching strategies with automatic invalidation.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,  # 5 minutes
        strategy: CacheStrategy = CacheStrategy.LRU,
    ):
        """
        Initialize the query cache.

        Args:
            max_size: Maximum number of entries.
            default_ttl: Default TTL in seconds.
            strategy: Eviction strategy.
        """
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._strategy = strategy
        self._cache: dict[str, CacheEntry[T]] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()
        self._invalidation_callbacks: list[Callable[[str], None]] = []

    def get(self, key: str) -> T | None:
        """
        Get a value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None
            
            # Update access metadata
            entry.last_accessed = datetime.now(timezone.utc)
            entry.access_count += 1
            self._stats.hits += 1
            
            return entry.value

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Optional TTL override.
        """
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict()
            
            now = datetime.now(timezone.utc)
            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                last_accessed=now,
                ttl_seconds=ttl if ttl is not None else self._default_ttl,
            )
            self._stats.size = len(self._cache)

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.

        Args:
            key: Key to invalidate.

        Returns:
            True if entry was removed.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                
                for callback in self._invalidation_callbacks:
                    try:
                        callback(key)
                    except Exception as e:
                        logger.error("Invalidation callback failed", error=str(e))
                
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate entries matching a pattern.

        Args:
            pattern: Prefix pattern to match.

        Returns:
            Number of entries invalidated.
        """
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(pattern)]
            
            for key in keys_to_remove:
                del self._cache[key]
            
            self._stats.size = len(self._cache)
            self._stats.evictions += len(keys_to_remove)
            
            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats.size = 0

    def _evict(self) -> None:
        """Evict entries based on strategy."""
        if not self._cache:
            return

        if self._strategy == CacheStrategy.LRU:
            # Remove least recently used
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].last_accessed,
            )
            del self._cache[oldest_key]
        
        elif self._strategy == CacheStrategy.LFU:
            # Remove least frequently used
            lfu_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].access_count,
            )
            del self._cache[lfu_key]
        
        elif self._strategy == CacheStrategy.TTL:
            # Remove expired entries first, then oldest
            now = datetime.now(timezone.utc)
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            
            if expired:
                for key in expired[:1]:  # Remove one
                    del self._cache[key]
            else:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].created_at,
                )
                del self._cache[oldest_key]
        
        self._stats.evictions += 1

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=len(self._cache),
            )

    def on_invalidate(self, callback: Callable[[str], None]) -> None:
        """Register an invalidation callback."""
        self._invalidation_callbacks.append(callback)


# =============================================================================
# Cache Decorator
# =============================================================================


def cached(
    cache: QueryCache,
    key_prefix: str = "",
    ttl: int | None = None,
):
    """
    Decorator for caching function results.

    Args:
        cache: QueryCache instance to use.
        key_prefix: Prefix for cache keys.
        ttl: Optional TTL override.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# =============================================================================
# Batch Processor
# =============================================================================


class BatchProcessor:
    """
    Batch processing for high-throughput event handling.

    Processes events in configurable batches with throughput monitoring.
    """

    def __init__(
        self,
        batch_size: int = 100,
        max_wait_seconds: float = 1.0,
        target_rate: float = 100.0,  # events per minute
    ):
        """
        Initialize the batch processor.

        Args:
            batch_size: Maximum batch size.
            max_wait_seconds: Maximum seconds to wait for batch.
            target_rate: Target throughput rate.
        """
        self._batch_size = batch_size
        self._max_wait = max_wait_seconds
        self._target_rate = target_rate
        self._metrics = ThroughputMetrics()
        self._processing_times: list[float] = []
        self._lock = threading.Lock()

    def process_batch(
        self,
        items: list[Any],
        processor: Callable[[Any], Any],
    ) -> BatchResult:
        """
        Process a batch of items.

        Args:
            items: Items to process.
            processor: Processing function.

        Returns:
            BatchResult with processing statistics.
        """
        batch_id = f"batch-{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        processed = 0
        failed = 0
        errors: list[str] = []
        
        for item in items:
            try:
                processor(item)
                processed += 1
            except Exception as e:
                failed += 1
                errors.append(str(e))
        
        duration_ms = int((time.time() - start_time) * 1000)
        items_per_second = len(items) / max(duration_ms / 1000, 0.001)
        
        # Update metrics
        with self._lock:
            self._metrics.events_processed += processed
            self._processing_times.append(duration_ms)
            if len(self._processing_times) > 100:
                self._processing_times = self._processing_times[-100:]
            
            self._metrics.avg_processing_time_ms = (
                sum(self._processing_times) / len(self._processing_times)
            )
            
            if items_per_second > self._metrics.peak_rate:
                self._metrics.peak_rate = items_per_second
            
            # Calculate events per minute
            self._metrics.events_per_minute = items_per_second * 60
            self._metrics.last_updated = datetime.now(timezone.utc)
        
        logger.info(
            "Batch processed",
            batch_id=batch_id,
            processed=processed,
            failed=failed,
            duration_ms=duration_ms,
        )
        
        return BatchResult(
            batch_id=batch_id,
            processed=processed,
            failed=failed,
            duration_ms=duration_ms,
            items_per_second=items_per_second,
            errors=errors,
        )

    async def process_batch_async(
        self,
        items: list[Any],
        processor: Callable[[Any], Any],
    ) -> BatchResult:
        """Process a batch asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.process_batch,
            items,
            processor,
        )

    def get_metrics(self) -> ThroughputMetrics:
        """Get current throughput metrics."""
        with self._lock:
            return ThroughputMetrics(
                events_processed=self._metrics.events_processed,
                events_per_minute=self._metrics.events_per_minute,
                peak_rate=self._metrics.peak_rate,
                avg_processing_time_ms=self._metrics.avg_processing_time_ms,
                last_updated=self._metrics.last_updated,
            )

    def is_meeting_target(self) -> bool:
        """Check if meeting target throughput."""
        return self._metrics.events_per_minute >= self._target_rate


# =============================================================================
# Resource Monitor
# =============================================================================


class ResourceMonitor:
    """
    Monitors system resource usage and enforces limits.

    Tracks CPU, memory, network, and disk usage with alerting.
    """

    def __init__(self, limits: ResourceLimits | None = None):
        """
        Initialize the resource monitor.

        Args:
            limits: Resource limits configuration.
        """
        self._limits = limits or ResourceLimits()
        self._usage_history: dict[ResourceType, list[ResourceUsage]] = defaultdict(list)
        self._violation_callbacks: list[Callable[[ResourceUsage], None]] = []
        self._lock = threading.Lock()
        
        # Simulated current usage (in real implementation, use psutil)
        self._current_usage: dict[ResourceType, float] = {
            ResourceType.CPU: 25.0,
            ResourceType.MEMORY: 256.0,
            ResourceType.NETWORK: 10.0,
            ResourceType.DISK: 100.0,
        }

    def get_usage(self, resource_type: ResourceType) -> ResourceUsage:
        """
        Get current resource usage.

        Args:
            resource_type: Type of resource to check.

        Returns:
            ResourceUsage snapshot.
        """
        current = self._current_usage.get(resource_type, 0.0)
        limit = self._get_limit(resource_type)
        percentage = (current / limit * 100) if limit > 0 else 0.0
        
        usage = ResourceUsage(
            resource_type=resource_type,
            current_value=current,
            limit=limit,
            percentage=percentage,
            timestamp=datetime.now(timezone.utc),
        )
        
        with self._lock:
            self._usage_history[resource_type].append(usage)
            # Keep last 100 samples
            if len(self._usage_history[resource_type]) > 100:
                self._usage_history[resource_type] = (
                    self._usage_history[resource_type][-100:]
                )
        
        return usage

    def _get_limit(self, resource_type: ResourceType) -> float:
        """Get limit for resource type."""
        if resource_type == ResourceType.CPU:
            return self._limits.cpu_percent
        elif resource_type == ResourceType.MEMORY:
            return self._limits.memory_mb
        elif resource_type == ResourceType.NETWORK:
            return self._limits.network_mbps
        elif resource_type == ResourceType.DISK:
            return self._limits.disk_iops
        return 100.0

    def check_limits(self) -> list[ResourceUsage]:
        """
        Check all resource limits.

        Returns:
            List of violations.
        """
        violations = []
        
        for resource_type in ResourceType:
            usage = self.get_usage(resource_type)
            
            if usage.percentage >= 100:
                violations.append(usage)
                
                for callback in self._violation_callbacks:
                    try:
                        callback(usage)
                    except Exception as e:
                        logger.error(
                            "Violation callback failed",
                            error=str(e),
                        )
        
        return violations

    def set_usage(self, resource_type: ResourceType, value: float) -> None:
        """Set simulated resource usage (for testing)."""
        with self._lock:
            self._current_usage[resource_type] = value

    def is_within_limits(self) -> bool:
        """Check if all resources are within limits."""
        for resource_type in ResourceType:
            usage = self.get_usage(resource_type)
            if usage.percentage >= 100:
                return False
        return True

    def on_violation(self, callback: Callable[[ResourceUsage], None]) -> None:
        """Register a violation callback."""
        self._violation_callbacks.append(callback)

    def get_history(
        self,
        resource_type: ResourceType,
        limit: int = 100,
    ) -> list[ResourceUsage]:
        """Get usage history for a resource type."""
        with self._lock:
            return self._usage_history[resource_type][-limit:]


# =============================================================================
# Data Retention Manager
# =============================================================================


class RetentionManager:
    """
    Manages data retention policies and archival.

    Defines retention periods, archives old data, and runs cleanup jobs.
    """

    def __init__(self):
        """Initialize the retention manager."""
        self._policies: dict[str, RetentionPolicy] = {}
        self._archived_counts: dict[str, int] = defaultdict(int)
        self._deleted_counts: dict[str, int] = defaultdict(int)

    def add_policy(self, policy: RetentionPolicy) -> None:
        """
        Add a retention policy.

        Args:
            policy: RetentionPolicy to add.
        """
        self._policies[policy.data_type] = policy
        logger.info(
            "Added retention policy",
            data_type=policy.data_type,
            period=policy.retention_period.value,
        )

    def get_policy(self, data_type: str) -> RetentionPolicy | None:
        """Get retention policy for a data type."""
        return self._policies.get(data_type)

    def get_retention_cutoff(self, data_type: str) -> datetime | None:
        """
        Get the cutoff datetime for a data type.

        Args:
            data_type: Type of data.

        Returns:
            Cutoff datetime or None if indefinite.
        """
        policy = self._policies.get(data_type)
        if not policy:
            return None
        
        if policy.retention_period == RetentionPeriod.INDEFINITE:
            return None
        
        now = datetime.now(timezone.utc)
        
        period_days = {
            RetentionPeriod.DAYS_7: 7,
            RetentionPeriod.DAYS_30: 30,
            RetentionPeriod.DAYS_90: 90,
            RetentionPeriod.DAYS_365: 365,
        }
        
        days = period_days.get(policy.retention_period, 30)
        return now - timedelta(days=days)

    def apply_retention(
        self,
        data_type: str,
        items: list[dict],
        date_field: str = "created_at",
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """
        Apply retention policy to items.

        Args:
            data_type: Type of data.
            items: Items to process.
            date_field: Field containing item date.

        Returns:
            Tuple of (retained, archived, deleted) items.
        """
        policy = self._policies.get(data_type)
        if not policy:
            return items, [], []
        
        cutoff = self.get_retention_cutoff(data_type)
        if cutoff is None:
            return items, [], []
        
        retained = []
        to_archive = []
        to_delete = []
        
        for item in items:
            item_date = item.get(date_field)
            if isinstance(item_date, str):
                item_date = datetime.fromisoformat(item_date.replace("Z", "+00:00"))
            
            if item_date and item_date < cutoff:
                if policy.archive_enabled:
                    to_archive.append(item)
                    self._archived_counts[data_type] += 1
                else:
                    to_delete.append(item)
                    self._deleted_counts[data_type] += 1
            else:
                retained.append(item)
        
        logger.info(
            "Applied retention policy",
            data_type=data_type,
            retained=len(retained),
            archived=len(to_archive),
            deleted=len(to_delete),
        )
        
        return retained, to_archive, to_delete

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Get retention statistics."""
        return {
            "archived": dict(self._archived_counts),
            "deleted": dict(self._deleted_counts),
        }


# =============================================================================
# Horizontal Scaling Support
# =============================================================================


class ScalingManager:
    """
    Manages horizontal scaling configuration and shared state.

    Supports multiple API instances with distributed state.
    """

    def __init__(self, instance_id: str | None = None):
        """
        Initialize the scaling manager.

        Args:
            instance_id: Unique instance identifier.
        """
        self._instance_id = instance_id or f"instance-{uuid.uuid4().hex[:8]}"
        self._registered_instances: dict[str, dict] = {}
        self._shared_state: dict[str, Any] = {}
        self._lock = threading.Lock()
        
        # Register self
        self._register_instance()

    def _register_instance(self) -> None:
        """Register this instance."""
        self._registered_instances[self._instance_id] = {
            "id": self._instance_id,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "health": "healthy",
        }

    @property
    def instance_id(self) -> str:
        """Get instance ID."""
        return self._instance_id

    def get_instances(self) -> list[dict]:
        """Get all registered instances."""
        with self._lock:
            return list(self._registered_instances.values())

    def set_shared_state(self, key: str, value: Any) -> None:
        """
        Set shared state.

        Args:
            key: State key.
            value: State value.
        """
        with self._lock:
            self._shared_state[key] = {
                "value": value,
                "updated_by": self._instance_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

    def get_shared_state(self, key: str) -> Any | None:
        """
        Get shared state.

        Args:
            key: State key.

        Returns:
            State value or None.
        """
        with self._lock:
            state = self._shared_state.get(key)
            return state["value"] if state else None

    def heartbeat(self) -> None:
        """Send heartbeat to indicate instance is alive."""
        with self._lock:
            if self._instance_id in self._registered_instances:
                self._registered_instances[self._instance_id]["last_heartbeat"] = (
                    datetime.now(timezone.utc).isoformat()
                )

    def deregister(self) -> None:
        """Deregister this instance."""
        with self._lock:
            if self._instance_id in self._registered_instances:
                del self._registered_instances[self._instance_id]


# =============================================================================
# Performance Manager (Main Interface)
# =============================================================================


class PerformanceManager:
    """
    Main interface for performance optimization.

    Coordinates caching, batch processing, resource monitoring, and scaling.
    """

    def __init__(
        self,
        cache_size: int = 1000,
        cache_ttl: int = 300,
        batch_size: int = 100,
        resource_limits: ResourceLimits | None = None,
        instance_id: str | None = None,
    ):
        """
        Initialize the performance manager.

        Args:
            cache_size: Maximum cache entries.
            cache_ttl: Default cache TTL.
            batch_size: Default batch size.
            resource_limits: Resource limits.
            instance_id: Instance identifier.
        """
        self.cache = QueryCache(
            max_size=cache_size,
            default_ttl=cache_ttl,
        )
        self.batch_processor = BatchProcessor(batch_size=batch_size)
        self.resource_monitor = ResourceMonitor(resource_limits)
        self.retention_manager = RetentionManager()
        self.scaling_manager = ScalingManager(instance_id)

    def get_health_status(self) -> dict:
        """Get overall performance health status."""
        cache_stats = self.cache.get_stats()
        throughput = self.batch_processor.get_metrics()
        within_limits = self.resource_monitor.is_within_limits()
        
        return {
            "instance_id": self.scaling_manager.instance_id,
            "cache": {
                "hit_rate": cache_stats.hit_rate,
                "size": cache_stats.size,
                "evictions": cache_stats.evictions,
            },
            "throughput": {
                "events_per_minute": throughput.events_per_minute,
                "peak_rate": throughput.peak_rate,
                "meeting_target": self.batch_processor.is_meeting_target(),
            },
            "resources": {
                "within_limits": within_limits,
            },
            "scaling": {
                "active_instances": len(self.scaling_manager.get_instances()),
            },
            "healthy": cache_stats.hit_rate >= 0 and within_limits,
        }
