"""
Property Tests for Performance Optimization Module.

Tests the performance functionality, verifying:
- Property 26: Query Response Time Performance
- Property 27: Event Processing Throughput
- Property 28: Scout Agent Resource Limits
- Property 29: Data Retention Policy Enforcement
- Property 30: Horizontal Scalability
"""

from datetime import datetime, timedelta, timezone
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
import pytest
import time
import uuid

from src.analysis.performance import (
    CacheStrategy,
    RetentionPeriod,
    ResourceType,
    CacheEntry,
    CacheStats,
    BatchResult,
    ResourceUsage,
    ResourceLimits,
    RetentionPolicy,
    ThroughputMetrics,
    QueryCache,
    cached,
    BatchProcessor,
    ResourceMonitor,
    RetentionManager,
    ScalingManager,
    PerformanceManager,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Cache strategy
cache_strategy_strategy = st.sampled_from(list(CacheStrategy))

# Retention period strategy
retention_period_strategy = st.sampled_from(list(RetentionPeriod))

# Resource type strategy
resource_type_strategy = st.sampled_from(list(ResourceType))

# Cache key strategy - simpler alphanumeric only
cache_key_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_",
    min_size=3,
    max_size=50,
).filter(lambda x: x.strip())

# TTL strategy (1 second to 1 hour)
ttl_strategy = st.integers(min_value=1, max_value=3600)

# Batch size strategy
batch_size_strategy = st.integers(min_value=1, max_value=1000)

# Resource limit strategy
resource_limit_strategy = st.floats(min_value=1.0, max_value=1000.0, allow_nan=False)


# =============================================================================
# Property 26: Query Response Time Performance
# =============================================================================


class TestQueryResponseTimePerformance:
    """Property tests for query caching and performance."""

    @given(
        key=cache_key_strategy,
        value=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50)
    def test_cache_set_and_get(self, key: str, value: str):
        """
        Property: Cache set and get operations are consistent.
        """
        cache: QueryCache[str] = QueryCache()
        
        cache.set(key, value)
        result = cache.get(key)
        
        assert result == value

    @given(
        key=cache_key_strategy,
        value=st.integers(),
    )
    @settings(max_examples=50)
    def test_cache_hit_increments_stats(self, key: str, value: int):
        """
        Property: Cache hits are tracked in stats.
        """
        cache: QueryCache[int] = QueryCache()
        
        cache.set(key, value)
        
        # Trigger cache hit
        cache.get(key)
        
        stats = cache.get_stats()
        assert stats.hits >= 1

    @given(key=cache_key_strategy)
    @settings(max_examples=50)
    def test_cache_miss_increments_stats(self, key: str):
        """
        Property: Cache misses are tracked in stats.
        """
        cache: QueryCache[str] = QueryCache()
        
        # Trigger cache miss
        cache.get(key)
        
        stats = cache.get_stats()
        assert stats.misses >= 1

    @given(
        max_size=st.integers(min_value=2, max_value=10),
        num_entries=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=30)
    def test_cache_respects_max_size(self, max_size: int, num_entries: int):
        """
        Property: Cache never exceeds max size.
        """
        cache: QueryCache[int] = QueryCache(max_size=max_size)
        
        for i in range(num_entries):
            cache.set(f"key-{i}", i)
        
        stats = cache.get_stats()
        assert stats.size <= max_size

    @given(
        key=cache_key_strategy,
        value=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=30)
    def test_cache_invalidation(self, key: str, value: str):
        """
        Property: Cache invalidation removes entries.
        """
        cache: QueryCache[str] = QueryCache()
        
        cache.set(key, value)
        assert cache.get(key) == value
        
        cache.invalidate(key)
        assert cache.get(key) is None

    def test_cache_clear(self):
        """
        Property: Cache clear removes all entries.
        """
        cache: QueryCache[int] = QueryCache()
        
        for i in range(10):
            cache.set(f"key-{i}", i)
        
        cache.clear()
        
        stats = cache.get_stats()
        assert stats.size == 0


# =============================================================================
# Property 27: Event Processing Throughput
# =============================================================================


class TestEventProcessingThroughput:
    """Property tests for batch processing throughput."""

    @given(
        batch_size=st.integers(min_value=1, max_value=100),
        num_items=st.integers(min_value=1, max_value=200),
    )
    @settings(max_examples=30)
    def test_batch_processes_all_items(self, batch_size: int, num_items: int):
        """
        Property: Batch processor handles all items.
        """
        processor = BatchProcessor(batch_size=batch_size)
        items = list(range(num_items))
        
        def simple_processor(item):
            return item + 1
        
        result = processor.process_batch(items, simple_processor)
        
        assert result.processed + result.failed == len(items)

    @given(items=st.lists(st.integers(), min_size=1, max_size=50))
    @settings(max_examples=30)
    def test_batch_result_has_valid_structure(self, items: list[int]):
        """
        Property: Batch results have valid structure.
        """
        processor = BatchProcessor()
        
        result = processor.process_batch(items, lambda x: x)
        
        assert hasattr(result, "batch_id")
        assert hasattr(result, "processed")
        assert hasattr(result, "failed")
        assert hasattr(result, "duration_ms")
        assert hasattr(result, "items_per_second")

    @given(num_batches=st.integers(min_value=1, max_value=10))
    @settings(max_examples=20)
    def test_metrics_accumulate_correctly(self, num_batches: int):
        """
        Property: Throughput metrics accumulate across batches.
        """
        processor = BatchProcessor()
        
        items_per_batch = 10
        for _ in range(num_batches):
            processor.process_batch(
                list(range(items_per_batch)),
                lambda x: x,
            )
        
        metrics = processor.get_metrics()
        
        assert metrics.events_processed == num_batches * items_per_batch

    def test_throughput_rate_is_positive(self):
        """
        Property: Items per second is always positive for successful batches.
        """
        processor = BatchProcessor()
        
        result = processor.process_batch([1, 2, 3], lambda x: x)
        
        assert result.items_per_second > 0

    @given(target_rate=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False))
    @settings(max_examples=20)
    def test_target_rate_tracking(self, target_rate: float):
        """
        Property: Processor tracks target rate correctly.
        """
        processor = BatchProcessor(target_rate=target_rate)
        
        # Process enough to generate metrics
        processor.process_batch(list(range(100)), lambda x: x)
        
        # is_meeting_target should return boolean
        assert isinstance(processor.is_meeting_target(), bool)


# =============================================================================
# Property 28: Scout Agent Resource Limits
# =============================================================================


class TestScoutAgentResourceLimits:
    """Property tests for resource monitoring."""

    @given(resource_type=resource_type_strategy)
    @settings(max_examples=20)
    def test_usage_returns_valid_structure(self, resource_type: ResourceType):
        """
        Property: Resource usage has valid structure.
        """
        monitor = ResourceMonitor()
        
        usage = monitor.get_usage(resource_type)
        
        assert hasattr(usage, "resource_type")
        assert hasattr(usage, "current_value")
        assert hasattr(usage, "limit")
        assert hasattr(usage, "percentage")
        assert hasattr(usage, "timestamp")

    @given(
        cpu_limit=resource_limit_strategy,
        memory_limit=resource_limit_strategy,
    )
    @settings(max_examples=30)
    def test_limits_are_respected(self, cpu_limit: float, memory_limit: float):
        """
        Property: Resource limits are applied correctly.
        """
        limits = ResourceLimits(cpu_percent=cpu_limit, memory_mb=memory_limit)
        monitor = ResourceMonitor(limits=limits)
        
        cpu_usage = monitor.get_usage(ResourceType.CPU)
        memory_usage = monitor.get_usage(ResourceType.MEMORY)
        
        assert cpu_usage.limit == cpu_limit
        assert memory_usage.limit == memory_limit

    @given(
        resource_type=resource_type_strategy,
        value=st.floats(min_value=0.0, max_value=200.0, allow_nan=False),
    )
    @settings(max_examples=30)
    def test_set_usage_updates_correctly(self, resource_type: ResourceType, value: float):
        """
        Property: Setting usage updates the monitor state.
        """
        monitor = ResourceMonitor()
        
        monitor.set_usage(resource_type, value)
        usage = monitor.get_usage(resource_type)
        
        assert usage.current_value == value

    def test_violations_detected_when_over_limit(self):
        """
        Property: Violations are detected when usage exceeds limits.
        """
        limits = ResourceLimits(cpu_percent=50.0)
        monitor = ResourceMonitor(limits=limits)
        
        # Set usage over limit
        monitor.set_usage(ResourceType.CPU, 60.0)
        
        violations = monitor.check_limits()
        
        cpu_violations = [v for v in violations if v.resource_type == ResourceType.CPU]
        assert len(cpu_violations) >= 1

    @given(resource_type=resource_type_strategy)
    @settings(max_examples=20)
    def test_history_is_recorded(self, resource_type: ResourceType):
        """
        Property: Usage history is recorded.
        """
        monitor = ResourceMonitor()
        
        # Generate some history
        for _ in range(5):
            monitor.get_usage(resource_type)
        
        history = monitor.get_history(resource_type)
        
        assert len(history) >= 5


# =============================================================================
# Property 29: Data Retention Policy Enforcement
# =============================================================================


class TestDataRetentionPolicyEnforcement:
    """Property tests for data retention policies."""

    @given(
        data_type=st.text(min_size=3, max_size=20).filter(lambda x: x.strip()),
        retention_period=retention_period_strategy,
    )
    @settings(max_examples=50)
    def test_policy_can_be_added(self, data_type: str, retention_period: RetentionPeriod):
        """
        Property: Retention policies can be added.
        """
        manager = RetentionManager()
        
        policy = RetentionPolicy(
            data_type=data_type,
            retention_period=retention_period,
        )
        manager.add_policy(policy)
        
        retrieved = manager.get_policy(data_type)
        
        assert retrieved is not None
        assert retrieved.retention_period == retention_period

    @given(retention_period=retention_period_strategy)
    @settings(max_examples=20)
    def test_cutoff_date_respects_period(self, retention_period: RetentionPeriod):
        """
        Property: Cutoff date matches retention period.
        """
        manager = RetentionManager()
        
        policy = RetentionPolicy(
            data_type="test_data",
            retention_period=retention_period,
        )
        manager.add_policy(policy)
        
        cutoff = manager.get_retention_cutoff("test_data")
        
        if retention_period == RetentionPeriod.INDEFINITE:
            assert cutoff is None
        else:
            assert cutoff is not None
            assert cutoff < datetime.now(timezone.utc)

    def test_old_items_are_archived(self):
        """
        Property: Items older than retention period are archived.
        """
        manager = RetentionManager()
        
        policy = RetentionPolicy(
            data_type="events",
            retention_period=RetentionPeriod.DAYS_7,
            archive_enabled=True,
        )
        manager.add_policy(policy)
        
        # Create items: some recent, some old
        now = datetime.now(timezone.utc)
        items = [
            {"id": "1", "created_at": now.isoformat()},  # Recent
            {"id": "2", "created_at": (now - timedelta(days=30)).isoformat()},  # Old
        ]
        
        retained, archived, deleted = manager.apply_retention("events", items)
        
        assert len(retained) == 1
        assert len(archived) == 1
        assert len(deleted) == 0

    def test_indefinite_retention_keeps_all(self):
        """
        Property: Indefinite retention keeps all items.
        """
        manager = RetentionManager()
        
        policy = RetentionPolicy(
            data_type="critical",
            retention_period=RetentionPeriod.INDEFINITE,
        )
        manager.add_policy(policy)
        
        now = datetime.now(timezone.utc)
        items = [
            {"id": "1", "created_at": now.isoformat()},
            {"id": "2", "created_at": (now - timedelta(days=365)).isoformat()},
        ]
        
        retained, archived, deleted = manager.apply_retention("critical", items)
        
        assert len(retained) == 2
        assert len(archived) == 0
        assert len(deleted) == 0


# =============================================================================
# Property 30: Horizontal Scalability
# =============================================================================


class TestHorizontalScalability:
    """Property tests for horizontal scaling support."""

    def test_instance_has_unique_id(self):
        """
        Property: Each instance gets a unique ID.
        """
        manager1 = ScalingManager()
        manager2 = ScalingManager()
        
        assert manager1.instance_id != manager2.instance_id

    @given(key=cache_key_strategy, value=st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_shared_state_persists(self, key: str, value: str):
        """
        Property: Shared state can be set and retrieved.
        """
        manager = ScalingManager()
        
        manager.set_shared_state(key, value)
        retrieved = manager.get_shared_state(key)
        
        assert retrieved == value

    def test_instance_list_includes_self(self):
        """
        Property: Instance is registered in instance list.
        """
        manager = ScalingManager()
        
        instances = manager.get_instances()
        instance_ids = [i["id"] for i in instances]
        
        assert manager.instance_id in instance_ids

    def test_deregister_removes_instance(self):
        """
        Property: Deregistering removes instance from list.
        """
        manager = ScalingManager()
        instance_id = manager.instance_id
        
        manager.deregister()
        
        instances = manager.get_instances()
        instance_ids = [i["id"] for i in instances]
        
        assert instance_id not in instance_ids

    def test_heartbeat_updates_timestamp(self):
        """
        Property: Heartbeat updates instance timestamp.
        """
        manager = ScalingManager()
        
        manager.heartbeat()
        
        instances = manager.get_instances()
        self_instance = next(
            (i for i in instances if i["id"] == manager.instance_id),
            None,
        )
        
        assert self_instance is not None
        assert "last_heartbeat" in self_instance


# =============================================================================
# Integration Tests
# =============================================================================


class TestPerformanceIntegration:
    """Integration tests for performance management."""

    def test_performance_manager_initialization(self):
        """
        Property: PerformanceManager initializes all components.
        """
        manager = PerformanceManager()
        
        assert manager.cache is not None
        assert manager.batch_processor is not None
        assert manager.resource_monitor is not None
        assert manager.retention_manager is not None
        assert manager.scaling_manager is not None

    def test_health_status_structure(self):
        """
        Property: Health status has complete structure.
        """
        manager = PerformanceManager()
        
        status = manager.get_health_status()
        
        assert "instance_id" in status
        assert "cache" in status
        assert "throughput" in status
        assert "resources" in status
        assert "scaling" in status
        assert "healthy" in status

    @given(
        cache_size=st.integers(min_value=10, max_value=100),
        cache_ttl=st.integers(min_value=60, max_value=600),
        batch_size=st.integers(min_value=10, max_value=200),
    )
    @settings(max_examples=20)
    def test_manager_respects_configuration(
        self,
        cache_size: int,
        cache_ttl: int,
        batch_size: int,
    ):
        """
        Property: Manager respects configuration parameters.
        """
        manager = PerformanceManager(
            cache_size=cache_size,
            cache_ttl=cache_ttl,
            batch_size=batch_size,
        )
        
        # Fill cache to capacity
        for i in range(cache_size + 10):
            manager.cache.set(f"key-{i}", i)
        
        stats = manager.cache.get_stats()
        assert stats.size <= cache_size
