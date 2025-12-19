"""
Plugin Architecture and Extensibility Module for Supply Chain Risk Management.

Provides a comprehensive plugin system with:
- Plugin base classes and lifecycle management
- Custom source plugins for Scout Agent
- Custom risk type configuration
- Bidirectional integration APIs
- Custom DSPy module support
- Version management and compatibility checking
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TypeVar, Generic
from pathlib import Path
import importlib.util
import inspect
import re
import uuid
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# =============================================================================
# Enums and Data Classes
# =============================================================================


class PluginType(str, Enum):
    """Types of plugins supported by the system."""

    SOURCE = "source"           # Data source plugins
    RISK_TYPE = "risk_type"     # Custom risk type definitions
    ANALYSIS = "analysis"       # Custom analysis modules
    INTEGRATION = "integration"  # Integration/webhook plugins
    VISUALIZATION = "visualization"  # Dashboard plugins


class PluginState(str, Enum):
    """Plugin lifecycle states."""

    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


class CompatibilityLevel(str, Enum):
    """Compatibility levels for version checking."""

    COMPATIBLE = "compatible"
    MINOR_ISSUES = "minor_issues"
    MAJOR_ISSUES = "major_issues"
    INCOMPATIBLE = "incompatible"


@dataclass
class PluginVersion:
    """Version information for a plugin."""

    major: int
    minor: int
    patch: int
    prerelease: str = ""

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        return version

    @classmethod
    def parse(cls, version_str: str) -> "PluginVersion":
        """Parse a version string."""
        match = re.match(
            r"(\d+)\.(\d+)\.(\d+)(?:-(.+))?",
            version_str.strip(),
        )
        if not match:
            return cls(0, 0, 0)
        
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4) or "",
        )

    def is_compatible_with(self, other: "PluginVersion") -> bool:
        """Check if compatible with another version (same major)."""
        return self.major == other.major


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""

    id: str
    name: str
    version: PluginVersion
    plugin_type: PluginType
    description: str = ""
    author: str = ""
    min_system_version: PluginVersion = field(
        default_factory=lambda: PluginVersion(1, 0, 0)
    )
    max_system_version: PluginVersion | None = None
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class PluginConfig:
    """Configuration for a plugin instance."""

    enabled: bool = True
    settings: dict[str, Any] = field(default_factory=dict)
    priority: int = 100  # Lower = higher priority


@dataclass
class PluginStatus:
    """Current status of a plugin."""

    plugin_id: str
    state: PluginState
    error_message: str = ""
    loaded_at: datetime | None = None
    last_activity: datetime | None = None
    invocation_count: int = 0


@dataclass
class CustomRiskType:
    """Definition of a custom risk type."""

    type_id: str
    name: str
    description: str
    severity_default: str = "Medium"
    keywords: list[str] = field(default_factory=list)
    extraction_patterns: list[str] = field(default_factory=list)
    color: str = "#6b7280"  # Gray default
    icon: str = "warning"


@dataclass
class IntegrationEvent:
    """Event for bidirectional integration."""

    event_id: str
    event_type: str
    source: str  # "system" or plugin_id
    target: str  # "system" or plugin_id
    payload: dict[str, Any]
    timestamp: datetime


# =============================================================================
# Plugin Base Class
# =============================================================================


class Plugin(ABC):
    """
    Abstract base class for all plugins.

    Plugins must implement lifecycle methods and provide metadata.
    """

    def __init__(self, config: PluginConfig | None = None):
        """
        Initialize the plugin.

        Args:
            config: Optional plugin configuration.
        """
        self._config = config or PluginConfig()
        self._state = PluginState.UNLOADED
        self._status: PluginStatus | None = None  # Lazy initialization

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass

    @property
    def config(self) -> PluginConfig:
        """Get plugin configuration."""
        return self._config

    @property
    def state(self) -> PluginState:
        """Get current plugin state."""
        return self._state

    @property
    def status(self) -> PluginStatus:
        """Get current plugin status."""
        if self._status is None:
            self._status = PluginStatus(
                plugin_id=self.metadata.id,
                state=self._state,
            )
        return self._status

    def load(self) -> bool:
        """
        Load the plugin.

        Returns:
            True if loaded successfully.
        """
        try:
            # Ensure status is initialized
            _ = self.status
            self._state = PluginState.LOADED
            self._status.state = PluginState.LOADED
            self._status.loaded_at = datetime.now(timezone.utc)
            logger.info("Plugin loaded", plugin_id=self.metadata.id)
            return True
        except Exception as e:
            self._state = PluginState.ERROR
            if self._status:
                self._status.state = PluginState.ERROR
                self._status.error_message = str(e)
            return False

    def initialize(self) -> bool:
        """
        Initialize the plugin after loading.

        Returns:
            True if initialized successfully.
        """
        if self._state != PluginState.LOADED:
            return False
        
        try:
            self._on_initialize()
            self._state = PluginState.INITIALIZED
            self._status.state = PluginState.INITIALIZED
            return True
        except Exception as e:
            self._state = PluginState.ERROR
            self._status.error_message = str(e)
            return False

    def activate(self) -> bool:
        """
        Activate the plugin for use.

        Returns:
            True if activated successfully.
        """
        if self._state != PluginState.INITIALIZED:
            return False
        
        try:
            self._on_activate()
            self._state = PluginState.ACTIVE
            self._status.state = PluginState.ACTIVE
            return True
        except Exception as e:
            self._state = PluginState.ERROR
            self._status.error_message = str(e)
            return False

    def deactivate(self) -> bool:
        """
        Deactivate the plugin.

        Returns:
            True if deactivated successfully.
        """
        if self._state != PluginState.ACTIVE:
            return False
        
        try:
            self._on_deactivate()
            self._state = PluginState.DISABLED
            self._status.state = PluginState.DISABLED
            return True
        except Exception as e:
            self._state = PluginState.ERROR
            self._status.error_message = str(e)
            return False

    def unload(self) -> bool:
        """
        Unload the plugin.

        Returns:
            True if unloaded successfully.
        """
        try:
            self._on_unload()
            self._state = PluginState.UNLOADED
            self._status.state = PluginState.UNLOADED
            return True
        except Exception as e:
            self._state = PluginState.ERROR
            self._status.error_message = str(e)
            return False

    def _on_initialize(self) -> None:
        """Hook for plugin initialization. Override in subclass."""
        pass

    def _on_activate(self) -> None:
        """Hook for plugin activation. Override in subclass."""
        pass

    def _on_deactivate(self) -> None:
        """Hook for plugin deactivation. Override in subclass."""
        pass

    def _on_unload(self) -> None:
        """Hook for plugin unload. Override in subclass."""
        pass


# =============================================================================
# Source Plugin Interface
# =============================================================================


class SourcePlugin(Plugin):
    """
    Plugin for custom data sources.

    Allows integration of custom news sources, APIs, or data feeds.
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Default metadata - override in subclass."""
        return PluginMetadata(
            id=f"source-{uuid.uuid4().hex[:8]}",
            name="Source Plugin",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.SOURCE,
            description="Custom data source plugin",
        )

    @abstractmethod
    def fetch_data(self) -> list[dict[str, Any]]:
        """
        Fetch data from the source.

        Returns:
            List of data items in standardized format.
        """
        pass

    @abstractmethod
    def get_source_info(self) -> dict[str, Any]:
        """
        Get information about the source.

        Returns:
            Source information dictionary.
        """
        pass

    def validate_data(self, data: list[dict[str, Any]]) -> bool:
        """
        Validate fetched data.

        Args:
            data: Data to validate.

        Returns:
            True if data is valid.
        """
        if not data:
            return True
        
        required_fields = ["id", "content"]
        for item in data:
            if not all(field in item for field in required_fields):
                return False
        
        return True


# =============================================================================
# Analysis Plugin Interface
# =============================================================================


class AnalysisPlugin(Plugin):
    """
    Plugin for custom analysis modules.

    Allows integration of custom DSPy modules or analysis pipelines.
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Default metadata - override in subclass."""
        return PluginMetadata(
            id=f"analysis-{uuid.uuid4().hex[:8]}",
            name="Analysis Plugin",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.ANALYSIS,
            description="Custom analysis plugin",
        )

    @abstractmethod
    def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Perform analysis on input data.

        Args:
            data: Input data to analyze.

        Returns:
            Analysis results.
        """
        pass

    def get_input_schema(self) -> dict:
        """Get JSON schema for input data."""
        return {"type": "object"}

    def get_output_schema(self) -> dict:
        """Get JSON schema for output data."""
        return {"type": "object"}


# =============================================================================
# Integration Plugin Interface
# =============================================================================


class IntegrationPlugin(Plugin):
    """
    Plugin for bidirectional integrations.

    Supports receiving and sending events to external systems.
    """

    def __init__(self, config: PluginConfig | None = None):
        """Initialize the integration plugin."""
        super().__init__(config)
        self._event_handlers: dict[str, list[Callable]] = {}
        self._outbound_events: list[IntegrationEvent] = []

    @property
    def metadata(self) -> PluginMetadata:
        """Default metadata - override in subclass."""
        return PluginMetadata(
            id=f"integration-{uuid.uuid4().hex[:8]}",
            name="Integration Plugin",
            version=PluginVersion(1, 0, 0),
            plugin_type=PluginType.INTEGRATION,
            description="Custom integration plugin",
        )

    def register_event_handler(
        self,
        event_type: str,
        handler: Callable[[IntegrationEvent], None],
    ) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: Type of event to handle.
            handler: Handler function.
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def handle_inbound_event(self, event: IntegrationEvent) -> bool:
        """
        Handle an inbound event.

        Args:
            event: Event to handle.

        Returns:
            True if event was handled.
        """
        handlers = self._event_handlers.get(event.event_type, [])
        if not handlers:
            return False
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Event handler failed", error=str(e))
        
        return True

    def send_outbound_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        target: str = "system",
    ) -> IntegrationEvent:
        """
        Create and queue an outbound event.

        Args:
            event_type: Type of event.
            payload: Event payload.
            target: Target system or plugin.

        Returns:
            Created event.
        """
        event = IntegrationEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            source=self.metadata.id,
            target=target,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
        )
        self._outbound_events.append(event)
        return event

    def get_pending_outbound_events(self) -> list[IntegrationEvent]:
        """Get all pending outbound events."""
        events = self._outbound_events.copy()
        self._outbound_events.clear()
        return events

    def get_supported_event_types(self) -> list[str]:
        """Get list of supported event types."""
        return list(self._event_handlers.keys())


# =============================================================================
# Risk Type Registry
# =============================================================================


class RiskTypeRegistry:
    """
    Registry for custom risk types.

    Allows defining and managing custom risk type configurations.
    """

    def __init__(self):
        """Initialize the risk type registry."""
        self._risk_types: dict[str, CustomRiskType] = {}
        self._extraction_rules: dict[str, list[Callable[[str], bool]]] = {}
        
        # Register default risk types
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default risk types."""
        defaults = [
            CustomRiskType(
                type_id="natural_disaster",
                name="Natural Disaster",
                description="Earthquakes, floods, hurricanes, etc.",
                severity_default="High",
                keywords=["earthquake", "flood", "hurricane", "tsunami", "wildfire"],
                color="#ef4444",
                icon="cloud-lightning",
            ),
            CustomRiskType(
                type_id="strike",
                name="Strike",
                description="Labor strikes and work stoppages",
                severity_default="Medium",
                keywords=["strike", "walkout", "labor dispute", "union"],
                color="#f97316",
                icon="users",
            ),
            CustomRiskType(
                type_id="pandemic",
                name="Pandemic",
                description="Disease outbreaks affecting supply chains",
                severity_default="Critical",
                keywords=["pandemic", "outbreak", "epidemic", "virus"],
                color="#dc2626",
                icon="shield-alert",
            ),
            CustomRiskType(
                type_id="geopolitical",
                name="Geopolitical",
                description="Political events, sanctions, trade wars",
                severity_default="High",
                keywords=["sanctions", "tariff", "trade war", "embargo"],
                color="#8b5cf6",
                icon="globe",
            ),
        ]
        
        for risk_type in defaults:
            self._risk_types[risk_type.type_id] = risk_type

    def register(self, risk_type: CustomRiskType) -> bool:
        """
        Register a custom risk type.

        Args:
            risk_type: Risk type to register.

        Returns:
            True if registered successfully.
        """
        if not risk_type.type_id:
            return False
        
        self._risk_types[risk_type.type_id] = risk_type
        logger.info("Registered risk type", type_id=risk_type.type_id)
        return True

    def unregister(self, type_id: str) -> bool:
        """
        Unregister a risk type.

        Args:
            type_id: ID of risk type to remove.

        Returns:
            True if removed.
        """
        if type_id in self._risk_types:
            del self._risk_types[type_id]
            return True
        return False

    def get(self, type_id: str) -> CustomRiskType | None:
        """Get a risk type by ID."""
        return self._risk_types.get(type_id)

    def get_all(self) -> list[CustomRiskType]:
        """Get all registered risk types."""
        return list(self._risk_types.values())

    def add_extraction_rule(
        self,
        type_id: str,
        rule: Callable[[str], bool],
    ) -> None:
        """
        Add a custom extraction rule for a risk type.

        Args:
            type_id: Risk type ID.
            rule: Function that returns True if text matches risk type.
        """
        if type_id not in self._extraction_rules:
            self._extraction_rules[type_id] = []
        self._extraction_rules[type_id].append(rule)

    def match_text(self, text: str) -> list[str]:
        """
        Match text against all risk types.

        Args:
            text: Text to match.

        Returns:
            List of matching risk type IDs.
        """
        matches = []
        text_lower = text.lower()
        
        for type_id, risk_type in self._risk_types.items():
            # Check keywords
            if any(kw in text_lower for kw in risk_type.keywords):
                matches.append(type_id)
                continue
            
            # Check extraction patterns
            for pattern in risk_type.extraction_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    matches.append(type_id)
                    break
            
            # Check custom rules
            rules = self._extraction_rules.get(type_id, [])
            if any(rule(text) for rule in rules):
                matches.append(type_id)
        
        return list(set(matches))


# =============================================================================
# Version Manager
# =============================================================================


class VersionManager:
    """
    Manages plugin versions and compatibility.

    Ensures plugins are compatible with the system and each other.
    """

    SYSTEM_VERSION = PluginVersion(1, 0, 0)

    def __init__(self):
        """Initialize the version manager."""
        self._plugin_versions: dict[str, PluginVersion] = {}

    def register_plugin_version(
        self,
        plugin_id: str,
        version: PluginVersion,
    ) -> None:
        """Register a plugin's version."""
        self._plugin_versions[plugin_id] = version

    def check_system_compatibility(
        self,
        plugin_metadata: PluginMetadata,
    ) -> CompatibilityLevel:
        """
        Check if a plugin is compatible with the system.

        Args:
            plugin_metadata: Plugin metadata.

        Returns:
            Compatibility level.
        """
        min_version = plugin_metadata.min_system_version
        max_version = plugin_metadata.max_system_version
        
        # Check minimum version
        if self.SYSTEM_VERSION.major < min_version.major:
            return CompatibilityLevel.INCOMPATIBLE
        
        if (self.SYSTEM_VERSION.major == min_version.major and
            self.SYSTEM_VERSION.minor < min_version.minor):
            return CompatibilityLevel.MAJOR_ISSUES
        
        # Check maximum version
        if max_version:
            if self.SYSTEM_VERSION.major > max_version.major:
                return CompatibilityLevel.INCOMPATIBLE
            
            if (self.SYSTEM_VERSION.major == max_version.major and
                self.SYSTEM_VERSION.minor > max_version.minor):
                return CompatibilityLevel.MINOR_ISSUES
        
        return CompatibilityLevel.COMPATIBLE

    def check_plugin_compatibility(
        self,
        plugin_id: str,
        required_version: PluginVersion,
    ) -> CompatibilityLevel:
        """
        Check if a plugin version meets requirements.

        Args:
            plugin_id: Plugin to check.
            required_version: Required minimum version.

        Returns:
            Compatibility level.
        """
        actual = self._plugin_versions.get(plugin_id)
        if not actual:
            return CompatibilityLevel.INCOMPATIBLE
        
        if actual.major != required_version.major:
            return CompatibilityLevel.INCOMPATIBLE
        
        if actual.minor < required_version.minor:
            return CompatibilityLevel.MAJOR_ISSUES
        
        if actual.patch < required_version.patch:
            return CompatibilityLevel.MINOR_ISSUES
        
        return CompatibilityLevel.COMPATIBLE

    def check_all_dependencies(
        self,
        plugin_metadata: PluginMetadata,
    ) -> dict[str, CompatibilityLevel]:
        """
        Check all dependencies for a plugin.

        Args:
            plugin_metadata: Plugin metadata.

        Returns:
            Dictionary of dependency to compatibility level.
        """
        results = {}
        
        for dependency in plugin_metadata.dependencies:
            # Parse dependency format: "plugin_id>=1.0.0"
            match = re.match(r"([a-z0-9_-]+)>=(\d+\.\d+\.\d+)", dependency)
            if match:
                dep_id = match.group(1)
                required = PluginVersion.parse(match.group(2))
                results[dep_id] = self.check_plugin_compatibility(dep_id, required)
            else:
                results[dependency] = CompatibilityLevel.INCOMPATIBLE
        
        return results

    def is_fully_compatible(
        self,
        plugin_metadata: PluginMetadata,
    ) -> bool:
        """Check if a plugin is fully compatible."""
        system_compat = self.check_system_compatibility(plugin_metadata)
        if system_compat != CompatibilityLevel.COMPATIBLE:
            return False
        
        dep_compat = self.check_all_dependencies(plugin_metadata)
        return all(
            level == CompatibilityLevel.COMPATIBLE
            for level in dep_compat.values()
        )


# =============================================================================
# Plugin Manager
# =============================================================================


class PluginManager:
    """
    Central manager for all plugins.

    Handles plugin lifecycle, registration, and integration.
    """

    def __init__(self, plugin_dir: Path | None = None):
        """
        Initialize the plugin manager.

        Args:
            plugin_dir: Optional directory for plugin files.
        """
        self._plugins: dict[str, Plugin] = {}
        self._plugin_dir = plugin_dir
        self.risk_type_registry = RiskTypeRegistry()
        self.version_manager = VersionManager()
        self._event_bus: list[Callable[[IntegrationEvent], None]] = []

    def register_plugin(self, plugin: Plugin) -> bool:
        """
        Register a plugin with the manager.

        Args:
            plugin: Plugin to register.

        Returns:
            True if registered successfully.
        """
        metadata = plugin.metadata
        
        # Check compatibility
        compat = self.version_manager.check_system_compatibility(metadata)
        if compat == CompatibilityLevel.INCOMPATIBLE:
            logger.error(
                "Plugin incompatible with system",
                plugin_id=metadata.id,
            )
            return False
        
        # Register version
        self.version_manager.register_plugin_version(
            metadata.id,
            metadata.version,
        )
        
        # Load and initialize
        if not plugin.load():
            return False
        
        if not plugin.initialize():
            return False
        
        self._plugins[metadata.id] = plugin
        logger.info("Plugin registered", plugin_id=metadata.id)
        return True

    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin.

        Args:
            plugin_id: ID of plugin to unregister.

        Returns:
            True if unregistered successfully.
        """
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        
        plugin.deactivate()
        plugin.unload()
        
        del self._plugins[plugin_id]
        logger.info("Plugin unregistered", plugin_id=plugin_id)
        return True

    def get_plugin(self, plugin_id: str) -> Plugin | None:
        """Get a plugin by ID."""
        return self._plugins.get(plugin_id)

    def get_all_plugins(self) -> list[Plugin]:
        """Get all registered plugins."""
        return list(self._plugins.values())

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[Plugin]:
        """Get all plugins of a specific type."""
        return [
            p for p in self._plugins.values()
            if p.metadata.plugin_type == plugin_type
        ]

    def activate_plugin(self, plugin_id: str) -> bool:
        """Activate a plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        return plugin.activate()

    def deactivate_plugin(self, plugin_id: str) -> bool:
        """Deactivate a plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        return plugin.deactivate()

    def subscribe_to_events(
        self,
        handler: Callable[[IntegrationEvent], None],
    ) -> None:
        """Subscribe to integration events."""
        self._event_bus.append(handler)

    def publish_event(self, event: IntegrationEvent) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish.
        """
        for handler in self._event_bus:
            try:
                handler(event)
            except Exception as e:
                logger.error("Event handler failed", error=str(e))

    def collect_source_data(self) -> list[dict[str, Any]]:
        """
        Collect data from all active source plugins.

        Returns:
            Combined data from all sources.
        """
        all_data = []
        
        for plugin in self.get_plugins_by_type(PluginType.SOURCE):
            if plugin.state != PluginState.ACTIVE:
                continue
            
            if isinstance(plugin, SourcePlugin):
                try:
                    data = plugin.fetch_data()
                    if plugin.validate_data(data):
                        all_data.extend(data)
                except Exception as e:
                    logger.error(
                        "Source plugin error",
                        plugin_id=plugin.metadata.id,
                        error=str(e),
                    )
        
        return all_data

    def run_analysis_plugins(
        self,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Run all active analysis plugins on data.

        Args:
            data: Input data to analyze.

        Returns:
            List of analysis results.
        """
        results = []
        
        for plugin in self.get_plugins_by_type(PluginType.ANALYSIS):
            if plugin.state != PluginState.ACTIVE:
                continue
            
            if isinstance(plugin, AnalysisPlugin):
                try:
                    result = plugin.analyze(data)
                    results.append({
                        "plugin_id": plugin.metadata.id,
                        "result": result,
                    })
                except Exception as e:
                    logger.error(
                        "Analysis plugin error",
                        plugin_id=plugin.metadata.id,
                        error=str(e),
                    )
        
        return results

    def process_integration_events(self) -> list[IntegrationEvent]:
        """
        Collect and process events from integration plugins.

        Returns:
            List of collected events.
        """
        events = []
        
        for plugin in self.get_plugins_by_type(PluginType.INTEGRATION):
            if plugin.state != PluginState.ACTIVE:
                continue
            
            if isinstance(plugin, IntegrationPlugin):
                plugin_events = plugin.get_pending_outbound_events()
                events.extend(plugin_events)
        
        # Publish events
        for event in events:
            self.publish_event(event)
        
        return events

    def get_status_report(self) -> dict[str, Any]:
        """Get status report for all plugins."""
        return {
            "total_plugins": len(self._plugins),
            "by_type": {
                pt.value: len(self.get_plugins_by_type(pt))
                for pt in PluginType
            },
            "by_state": {
                state.value: sum(
                    1 for p in self._plugins.values()
                    if p.state == state
                )
                for state in PluginState
            },
            "plugins": [
                {
                    "id": p.metadata.id,
                    "name": p.metadata.name,
                    "version": str(p.metadata.version),
                    "type": p.metadata.plugin_type.value,
                    "state": p.state.value,
                }
                for p in self._plugins.values()
            ],
        }
