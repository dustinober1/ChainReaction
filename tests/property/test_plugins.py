"""
Property Tests for Plugin Architecture and Extensibility Module.

Tests the plugin functionality, verifying:
- Property 44: Custom Source Plugin Integration
- Property 45: Custom Risk Type Configuration
- Property 46: Bidirectional Integration APIs
- Property 47: Custom DSPy Module Support
- Property 48: Extension Backward Compatibility
"""

from datetime import datetime, timezone
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
import pytest
from typing import Any

from src.analysis.plugins import (
    PluginType,
    PluginState,
    CompatibilityLevel,
    PluginVersion,
    PluginMetadata,
    PluginConfig,
    PluginStatus,
    CustomRiskType,
    IntegrationEvent,
    Plugin,
    SourcePlugin,
    AnalysisPlugin,
    IntegrationPlugin,
    RiskTypeRegistry,
    VersionManager,
    PluginManager,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Plugin type strategy
plugin_type_strategy = st.sampled_from(list(PluginType))

# Version component strategy
version_component_strategy = st.integers(min_value=0, max_value=99)

# Plugin ID strategy
plugin_id_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-",
    min_size=3,
    max_size=30,
).filter(lambda x: x and not x.startswith("-") and not x.endswith("-"))

# Keyword strategy
keyword_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz",
    min_size=3,
    max_size=20,
).filter(lambda x: x.strip())


# =============================================================================
# Test Plugin Implementations
# =============================================================================


class TestSourcePluginImpl(SourcePlugin):
    """Test implementation of SourcePlugin."""

    def __init__(self, plugin_id: str = "test-source"):
        super().__init__()
        self._plugin_id = plugin_id
        self._data = [{"id": "item-1", "content": "Test content"}]

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id=self._plugin_id,
            name="Test Source",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.SOURCE,
            description="Test source plugin",
        )

    def fetch_data(self) -> list[dict[str, Any]]:
        return self._data

    def get_source_info(self) -> dict[str, Any]:
        return {"type": "test", "url": "http://test.example.com"}


class TestAnalysisPluginImpl(AnalysisPlugin):
    """Test implementation of AnalysisPlugin."""

    def __init__(self, plugin_id: str = "test-analysis"):
        super().__init__()
        self._plugin_id = plugin_id

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id=self._plugin_id,
            name="Test Analysis",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.ANALYSIS,
            description="Test analysis plugin",
        )

    def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        return {"analyzed": True, "input_keys": list(data.keys())}


class TestIntegrationPluginImpl(IntegrationPlugin):
    """Test implementation of IntegrationPlugin."""

    def __init__(self, plugin_id: str = "test-integration"):
        super().__init__()
        self._plugin_id = plugin_id

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id=self._plugin_id,
            name="Test Integration",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.INTEGRATION,
            description="Test integration plugin",
        )


# =============================================================================
# Property 44: Custom Source Plugin Integration
# =============================================================================


class TestCustomSourcePluginIntegration:
    """Property tests for source plugin integration."""

    def test_source_plugin_can_be_registered(self):
        """
        Property: Source plugins can be registered with the manager.
        """
        manager = PluginManager()
        plugin = TestSourcePluginImpl()
        
        result = manager.register_plugin(plugin)
        
        assert result is True
        assert manager.get_plugin(plugin.metadata.id) is not None

    def test_source_plugin_lifecycle(self):
        """
        Property: Source plugins follow correct lifecycle.
        """
        plugin = TestSourcePluginImpl()
        
        # Initial state
        assert plugin.state == PluginState.UNLOADED
        
        # Load
        assert plugin.load() is True
        assert plugin.state == PluginState.LOADED
        
        # Initialize
        assert plugin.initialize() is True
        assert plugin.state == PluginState.INITIALIZED
        
        # Activate
        assert plugin.activate() is True
        assert plugin.state == PluginState.ACTIVE
        
        # Deactivate
        assert plugin.deactivate() is True
        assert plugin.state == PluginState.DISABLED

    def test_source_plugin_data_fetching(self):
        """
        Property: Source plugins return valid data.
        """
        plugin = TestSourcePluginImpl()
        plugin.load()
        plugin.initialize()
        plugin.activate()
        
        data = plugin.fetch_data()
        
        assert isinstance(data, list)
        assert len(data) > 0
        assert all("id" in item and "content" in item for item in data)

    def test_source_plugin_data_validation(self):
        """
        Property: Source plugins validate data correctly.
        """
        plugin = TestSourcePluginImpl()
        
        # Valid data
        valid_data = [{"id": "1", "content": "test"}]
        assert plugin.validate_data(valid_data) is True
        
        # Invalid data
        invalid_data = [{"id": "1"}]  # Missing content
        assert plugin.validate_data(invalid_data) is False
        
        # Empty data is valid
        assert plugin.validate_data([]) is True

    def test_collect_source_data(self):
        """
        Property: Plugin manager collects data from all active sources.
        """
        manager = PluginManager()
        
        plugin1 = TestSourcePluginImpl("source-1")
        plugin2 = TestSourcePluginImpl("source-2")
        
        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)
        
        manager.activate_plugin("source-1")
        manager.activate_plugin("source-2")
        
        data = manager.collect_source_data()
        
        # Should have data from both plugins
        assert len(data) >= 2


# =============================================================================
# Property 45: Custom Risk Type Configuration
# =============================================================================


class TestCustomRiskTypeConfiguration:
    """Property tests for custom risk type configuration."""

    def test_default_risk_types_registered(self):
        """
        Property: Default risk types are registered on initialization.
        """
        registry = RiskTypeRegistry()
        
        risk_types = registry.get_all()
        
        assert len(risk_types) > 0
        
        # Check default types exist
        default_ids = ["natural_disaster", "strike", "pandemic", "geopolitical"]
        for type_id in default_ids:
            assert registry.get(type_id) is not None

    @given(
        type_id=plugin_id_strategy,
        name=st.text(min_size=3, max_size=50).filter(lambda x: x.strip()),
    )
    @settings(max_examples=30)
    def test_custom_risk_type_registration(self, type_id: str, name: str):
        """
        Property: Custom risk types can be registered.
        """
        registry = RiskTypeRegistry()
        
        risk_type = CustomRiskType(
            type_id=type_id,
            name=name,
            description=f"Custom type: {name}",
            keywords=["test", "custom"],
        )
        
        result = registry.register(risk_type)
        
        assert result is True
        
        retrieved = registry.get(type_id)
        assert retrieved is not None
        assert retrieved.name == name

    @given(keyword=keyword_strategy)
    @settings(max_examples=30)
    def test_risk_type_keyword_matching(self, keyword: str):
        """
        Property: Risk types match by keywords.
        """
        registry = RiskTypeRegistry()
        
        # Register a custom type with the keyword
        risk_type = CustomRiskType(
            type_id="custom-test",
            name="Custom Test",
            description="Test type",
            keywords=[keyword],
        )
        registry.register(risk_type)
        
        # Match against text containing keyword
        matches = registry.match_text(f"Some text with {keyword} in it")
        
        assert "custom-test" in matches

    def test_risk_type_unregistration(self):
        """
        Property: Risk types can be unregistered.
        """
        registry = RiskTypeRegistry()
        
        # Register a custom type
        risk_type = CustomRiskType(
            type_id="to-remove",
            name="To Remove",
            description="Will be removed",
        )
        registry.register(risk_type)
        
        # Verify it exists
        assert registry.get("to-remove") is not None
        
        # Unregister
        result = registry.unregister("to-remove")
        assert result is True
        
        # Verify it's gone
        assert registry.get("to-remove") is None

    def test_custom_extraction_rules(self):
        """
        Property: Custom extraction rules are applied.
        """
        registry = RiskTypeRegistry()
        
        # Add custom rule
        registry.add_extraction_rule(
            "natural_disaster",
            lambda text: "custom_pattern" in text.lower(),
        )
        
        # Test matching
        matches = registry.match_text("This contains custom_pattern in text")
        
        assert "natural_disaster" in matches


# =============================================================================
# Property 46: Bidirectional Integration APIs
# =============================================================================


class TestBidirectionalIntegrationAPIs:
    """Property tests for bidirectional integration APIs."""

    def test_integration_plugin_event_handling(self):
        """
        Property: Integration plugins can handle inbound events.
        """
        plugin = TestIntegrationPluginImpl()
        
        handled_events = []
        
        def handler(event: IntegrationEvent):
            handled_events.append(event)
        
        plugin.register_event_handler("test_event", handler)
        
        event = IntegrationEvent(
            event_id="evt-1",
            event_type="test_event",
            source="system",
            target=plugin.metadata.id,
            payload={"data": "test"},
            timestamp=datetime.now(timezone.utc),
        )
        
        result = plugin.handle_inbound_event(event)
        
        assert result is True
        assert len(handled_events) == 1

    def test_integration_plugin_outbound_events(self):
        """
        Property: Integration plugins can send outbound events.
        """
        plugin = TestIntegrationPluginImpl()
        
        event = plugin.send_outbound_event(
            event_type="data_update",
            payload={"key": "value"},
            target="external_system",
        )
        
        assert event.event_type == "data_update"
        assert event.source == plugin.metadata.id
        assert event.target == "external_system"
        
        # Get pending events
        pending = plugin.get_pending_outbound_events()
        
        assert len(pending) == 1
        assert pending[0].event_id == event.event_id
        
        # Events should be cleared after retrieval
        assert len(plugin.get_pending_outbound_events()) == 0

    def test_event_bus_subscription(self):
        """
        Property: Event bus delivers events to subscribers.
        """
        manager = PluginManager()
        
        received_events = []
        
        def handler(event: IntegrationEvent):
            received_events.append(event)
        
        manager.subscribe_to_events(handler)
        
        event = IntegrationEvent(
            event_id="evt-1",
            event_type="test",
            source="test-plugin",
            target="system",
            payload={},
            timestamp=datetime.now(timezone.utc),
        )
        
        manager.publish_event(event)
        
        assert len(received_events) == 1

    def test_supported_event_types(self):
        """
        Property: Integration plugins report supported event types.
        """
        plugin = TestIntegrationPluginImpl()
        
        plugin.register_event_handler("type_a", lambda e: None)
        plugin.register_event_handler("type_b", lambda e: None)
        
        types = plugin.get_supported_event_types()
        
        assert "type_a" in types
        assert "type_b" in types


# =============================================================================
# Property 47: Custom DSPy Module Support
# =============================================================================


class TestCustomDSPyModuleSupport:
    """Property tests for custom analysis module support."""

    def test_analysis_plugin_registration(self):
        """
        Property: Analysis plugins can be registered.
        """
        manager = PluginManager()
        plugin = TestAnalysisPluginImpl()
        
        result = manager.register_plugin(plugin)
        
        assert result is True
        
        plugins = manager.get_plugins_by_type(PluginType.ANALYSIS)
        assert len(plugins) == 1

    def test_analysis_plugin_execution(self):
        """
        Property: Analysis plugins execute and return results.
        """
        plugin = TestAnalysisPluginImpl()
        plugin.load()
        plugin.initialize()
        plugin.activate()
        
        result = plugin.analyze({"key1": "value1", "key2": "value2"})
        
        assert result["analyzed"] is True
        assert "key1" in result["input_keys"]
        assert "key2" in result["input_keys"]

    def test_run_analysis_plugins(self):
        """
        Property: Plugin manager runs all active analysis plugins.
        """
        manager = PluginManager()
        
        plugin1 = TestAnalysisPluginImpl("analysis-1")
        plugin2 = TestAnalysisPluginImpl("analysis-2")
        
        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)
        
        manager.activate_plugin("analysis-1")
        manager.activate_plugin("analysis-2")
        
        results = manager.run_analysis_plugins({"test": "data"})
        
        assert len(results) == 2
        assert all("plugin_id" in r for r in results)
        assert all("result" in r for r in results)

    def test_analysis_plugin_schemas(self):
        """
        Property: Analysis plugins provide input/output schemas.
        """
        plugin = TestAnalysisPluginImpl()
        
        input_schema = plugin.get_input_schema()
        output_schema = plugin.get_output_schema()
        
        assert isinstance(input_schema, dict)
        assert isinstance(output_schema, dict)
        assert "type" in input_schema
        assert "type" in output_schema


# =============================================================================
# Property 48: Extension Backward Compatibility
# =============================================================================


class TestExtensionBackwardCompatibility:
    """Property tests for version management and compatibility."""

    @given(
        major=version_component_strategy,
        minor=version_component_strategy,
        patch=version_component_strategy,
    )
    @settings(max_examples=30)
    def test_version_parsing(self, major: int, minor: int, patch: int):
        """
        Property: Version strings are parsed correctly.
        """
        version_str = f"{major}.{minor}.{patch}"
        version = PluginVersion.parse(version_str)
        
        assert version.major == major
        assert version.minor == minor
        assert version.patch == patch

    def test_version_compatibility(self):
        """
        Property: Same major versions are compatible.
        """
        v1 = PluginVersion(1, 0, 0)
        v2 = PluginVersion(1, 5, 3)
        v3 = PluginVersion(2, 0, 0)
        
        assert v1.is_compatible_with(v2) is True
        assert v2.is_compatible_with(v1) is True
        assert v1.is_compatible_with(v3) is False

    def test_system_compatibility_check(self):
        """
        Property: Version manager checks system compatibility.
        """
        manager = VersionManager()
        
        # Compatible plugin
        metadata_compatible = PluginMetadata(
            id="test-1",
            name="Compatible",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.SOURCE,
            min_system_version=PluginVersion(1, 0, 0),
        )
        
        result = manager.check_system_compatibility(metadata_compatible)
        assert result == CompatibilityLevel.COMPATIBLE

    def test_plugin_dependency_check(self):
        """
        Property: Version manager checks plugin dependencies.
        """
        manager = VersionManager()
        
        # Register a dependency
        manager.register_plugin_version("dep-plugin", PluginVersion(1, 2, 0))
        
        # Check compatible version
        result = manager.check_plugin_compatibility(
            "dep-plugin",
            PluginVersion(1, 0, 0),
        )
        assert result == CompatibilityLevel.COMPATIBLE
        
        # Check incompatible version (missing)
        result = manager.check_plugin_compatibility(
            "missing-plugin",
            PluginVersion(1, 0, 0),
        )
        assert result == CompatibilityLevel.INCOMPATIBLE

    def test_full_compatibility_check(self):
        """
        Property: Full compatibility check validates all requirements.
        """
        manager = VersionManager()
        
        # Register dependencies
        manager.register_plugin_version("dep-a", PluginVersion(1, 0, 0))
        
        metadata = PluginMetadata(
            id="test-plugin",
            name="Test Plugin",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.SOURCE,
            min_system_version=PluginVersion(1, 0, 0),
            dependencies=["dep-a>=1.0.0"],
        )
        
        is_compatible = manager.is_fully_compatible(metadata)
        assert is_compatible is True


# =============================================================================
# Integration Tests
# =============================================================================


class TestPluginIntegration:
    """Integration tests for plugin management."""

    def test_plugin_manager_initialization(self):
        """
        Property: Plugin manager initializes correctly.
        """
        manager = PluginManager()
        
        assert manager.risk_type_registry is not None
        assert manager.version_manager is not None
        assert len(manager.get_all_plugins()) == 0

    def test_plugin_status_report(self):
        """
        Property: Status report contains all required information.
        """
        manager = PluginManager()
        
        # Register some plugins
        manager.register_plugin(TestSourcePluginImpl("src-1"))
        manager.register_plugin(TestAnalysisPluginImpl("ana-1"))
        
        report = manager.get_status_report()
        
        assert "total_plugins" in report
        assert report["total_plugins"] == 2
        assert "by_type" in report
        assert "by_state" in report
        assert "plugins" in report

    def test_plugin_type_filtering(self):
        """
        Property: Plugins can be filtered by type.
        """
        manager = PluginManager()
        
        manager.register_plugin(TestSourcePluginImpl("src-1"))
        manager.register_plugin(TestSourcePluginImpl("src-2"))
        manager.register_plugin(TestAnalysisPluginImpl("ana-1"))
        
        sources = manager.get_plugins_by_type(PluginType.SOURCE)
        analysis = manager.get_plugins_by_type(PluginType.ANALYSIS)
        
        assert len(sources) == 2
        assert len(analysis) == 1

    def test_plugin_unregistration(self):
        """
        Property: Plugins can be unregistered.
        """
        manager = PluginManager()
        
        plugin = TestSourcePluginImpl()
        manager.register_plugin(plugin)
        
        assert manager.get_plugin(plugin.metadata.id) is not None
        
        result = manager.unregister_plugin(plugin.metadata.id)
        
        assert result is True
        assert manager.get_plugin(plugin.metadata.id) is None

    def test_activation_deactivation(self):
        """
        Property: Plugins can be activated and deactivated.
        """
        manager = PluginManager()
        
        plugin = TestSourcePluginImpl()
        manager.register_plugin(plugin)
        
        # Plugin should be initialized after registration
        assert plugin.state == PluginState.INITIALIZED
        
        # Activate
        manager.activate_plugin(plugin.metadata.id)
        assert plugin.state == PluginState.ACTIVE
        
        # Deactivate
        manager.deactivate_plugin(plugin.metadata.id)
        assert plugin.state == PluginState.DISABLED
