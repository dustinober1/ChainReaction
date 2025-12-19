"""
Accessibility and UX Improvements Module for Supply Chain Risk Management.

Provides WCAG 2.1 AA color contrast compliance, keyboard navigation support,
and data dictionary generation for exports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
import math
import re
import structlog

logger = structlog.get_logger(__name__)


# =============================================================================
# Enums and Data Classes
# =============================================================================


class WCAGLevel(str, Enum):
    """WCAG compliance levels."""

    A = "A"
    AA = "AA"
    AAA = "AAA"


class ContrastRequirement(str, Enum):
    """WCAG contrast requirements."""

    NORMAL_TEXT = "normal_text"      # 4.5:1 minimum
    LARGE_TEXT = "large_text"        # 3:1 minimum
    UI_COMPONENTS = "ui_components"  # 3:1 minimum
    NON_TEXT = "non_text"            # 3:1 minimum


class KeyboardAction(str, Enum):
    """Keyboard navigation actions."""

    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_UP = "pan_up"
    PAN_DOWN = "pan_down"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    FILTER_CRITICAL = "filter_critical"
    FILTER_HIGH = "filter_high"
    FILTER_MEDIUM = "filter_medium"
    FILTER_LOW = "filter_low"
    RESET_VIEW = "reset_view"
    TOGGLE_LEGEND = "toggle_legend"
    NEXT_NODE = "next_node"
    PREV_NODE = "prev_node"
    SELECT_NODE = "select_node"
    SEARCH = "search"
    HELP = "help"


class DataType(str, Enum):
    """Data types for data dictionary."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"


@dataclass
class ColorPair:
    """A foreground/background color pair for contrast checking."""

    foreground: str
    background: str
    name: str = ""


@dataclass
class ContrastResult:
    """Result of a contrast ratio check."""

    color_pair: ColorPair
    contrast_ratio: float
    passes_normal_text: bool  # 4.5:1
    passes_large_text: bool   # 3:1
    passes_ui_components: bool  # 3:1
    recommendation: str = ""


@dataclass
class KeyboardShortcut:
    """A keyboard shortcut definition."""

    action: KeyboardAction
    key: str  # e.g., "Ctrl+Plus", "ArrowUp", "F"
    description: str
    modifiers: list[str] = field(default_factory=list)  # ["Ctrl", "Shift", "Alt"]
    enabled: bool = True


@dataclass
class FocusableElement:
    """Definition of a focusable UI element."""

    element_id: str
    element_type: str  # "button", "input", "link", "node"
    label: str
    tab_index: int
    aria_label: str
    role: str


@dataclass
class FieldDefinition:
    """Definition of a field for the data dictionary."""

    name: str
    data_type: DataType
    description: str
    nullable: bool = False
    format_pattern: str = ""
    example: str = ""
    enum_values: list[str] = field(default_factory=list)
    related_fields: list[str] = field(default_factory=list)


@dataclass
class DataDictionary:
    """Complete data dictionary for an export format."""

    name: str
    version: str
    description: str
    fields: list[FieldDefinition] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Color Contrast Utilities (WCAG 2.1 AA Compliance)
# =============================================================================


class ColorContrastChecker:
    """
    WCAG 2.1 AA color contrast compliance checker.

    Validates color combinations meet accessibility requirements.
    """

    # WCAG minimum contrast ratios
    NORMAL_TEXT_RATIO = 4.5
    LARGE_TEXT_RATIO = 3.0
    UI_COMPONENT_RATIO = 3.0

    def __init__(self):
        """Initialize the color contrast checker."""
        self._audit_results: list[ContrastResult] = []

    def parse_color(self, color: str) -> tuple[int, int, int]:
        """
        Parse a color string to RGB values.

        Args:
            color: Color in hex (#RRGGBB), rgb(), or hsl() format.

        Returns:
            Tuple of (R, G, B) values (0-255).
        """
        color = color.strip().lower()

        # Handle hex format
        if color.startswith("#"):
            hex_color = color[1:]
            if len(hex_color) == 3:
                hex_color = "".join(c * 2 for c in hex_color)
            if len(hex_color) == 6:
                return (
                    int(hex_color[0:2], 16),
                    int(hex_color[2:4], 16),
                    int(hex_color[4:6], 16),
                )

        # Handle rgb() format
        rgb_match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color)
        if rgb_match:
            return (
                int(rgb_match.group(1)),
                int(rgb_match.group(2)),
                int(rgb_match.group(3)),
            )

        # Handle rgba() format
        rgba_match = re.match(
            r"rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)", color
        )
        if rgba_match:
            return (
                int(rgba_match.group(1)),
                int(rgba_match.group(2)),
                int(rgba_match.group(3)),
            )

        # Default to black
        return (0, 0, 0)

    def get_relative_luminance(self, r: int, g: int, b: int) -> float:
        """
        Calculate the relative luminance of a color.

        Uses WCAG 2.1 formula.

        Args:
            r, g, b: RGB values (0-255).

        Returns:
            Relative luminance (0.0 to 1.0).
        """
        def linearize(channel: int) -> float:
            srgb = channel / 255.0
            if srgb <= 0.03928:
                return srgb / 12.92
            return ((srgb + 0.055) / 1.055) ** 2.4

        r_linear = linearize(r)
        g_linear = linearize(g)
        b_linear = linearize(b)

        return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear

    def calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """
        Calculate the contrast ratio between two colors.

        Args:
            color1: First color.
            color2: Second color.

        Returns:
            Contrast ratio (1.0 to 21.0).
        """
        r1, g1, b1 = self.parse_color(color1)
        r2, g2, b2 = self.parse_color(color2)

        l1 = self.get_relative_luminance(r1, g1, b1)
        l2 = self.get_relative_luminance(r2, g2, b2)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    def check_contrast(
        self,
        color_pair: ColorPair,
        requirement: ContrastRequirement = ContrastRequirement.NORMAL_TEXT,
    ) -> ContrastResult:
        """
        Check if a color pair meets contrast requirements.

        Args:
            color_pair: Foreground/background color pair.
            requirement: Type of contrast requirement.

        Returns:
            ContrastResult with pass/fail status.
        """
        ratio = self.calculate_contrast_ratio(
            color_pair.foreground,
            color_pair.background,
        )

        passes_normal = ratio >= self.NORMAL_TEXT_RATIO
        passes_large = ratio >= self.LARGE_TEXT_RATIO
        passes_ui = ratio >= self.UI_COMPONENT_RATIO

        # Generate recommendation
        recommendation = ""
        if requirement == ContrastRequirement.NORMAL_TEXT and not passes_normal:
            needed = self.NORMAL_TEXT_RATIO - ratio
            recommendation = f"Increase contrast by {needed:.2f} to meet WCAG AA for normal text"
        elif requirement == ContrastRequirement.LARGE_TEXT and not passes_large:
            needed = self.LARGE_TEXT_RATIO - ratio
            recommendation = f"Increase contrast by {needed:.2f} to meet WCAG AA for large text"

        result = ContrastResult(
            color_pair=color_pair,
            contrast_ratio=round(ratio, 2),
            passes_normal_text=passes_normal,
            passes_large_text=passes_large,
            passes_ui_components=passes_ui,
            recommendation=recommendation,
        )

        self._audit_results.append(result)
        return result

    def audit_color_palette(
        self,
        colors: dict[str, str],
        background: str,
    ) -> list[ContrastResult]:
        """
        Audit a color palette against a background.

        Args:
            colors: Dictionary of color name to hex value.
            background: Background color to test against.

        Returns:
            List of ContrastResult for each color.
        """
        results = []
        for name, color in colors.items():
            pair = ColorPair(
                foreground=color,
                background=background,
                name=name,
            )
            result = self.check_contrast(pair)
            results.append(result)
        return results

    def suggest_accessible_color(
        self,
        original: str,
        background: str,
        target_ratio: float = 4.5,
    ) -> str:
        """
        Suggest an accessible alternative color.

        Args:
            original: Original color that fails contrast.
            background: Background color.
            target_ratio: Target contrast ratio.

        Returns:
            Suggested accessible color.
        """
        r, g, b = self.parse_color(original)
        bg_r, bg_g, bg_b = self.parse_color(background)

        bg_luminance = self.get_relative_luminance(bg_r, bg_g, bg_b)

        # Determine if we need to go lighter or darker
        original_luminance = self.get_relative_luminance(r, g, b)

        if bg_luminance > 0.5:
            # Dark background, need lighter foreground
            factor = 0.95
        else:
            # Light background, need darker foreground
            factor = 1.05

        # Iteratively adjust color
        new_r, new_g, new_b = r, g, b
        for _ in range(100):
            current_ratio = self.calculate_contrast_ratio(
                f"rgb({new_r}, {new_g}, {new_b})",
                background,
            )
            if current_ratio >= target_ratio:
                break

            if factor < 1:
                new_r = int(min(255, new_r / factor))
                new_g = int(min(255, new_g / factor))
                new_b = int(min(255, new_b / factor))
            else:
                new_r = int(max(0, new_r / factor))
                new_g = int(max(0, new_g / factor))
                new_b = int(max(0, new_b / factor))

        return f"#{new_r:02x}{new_g:02x}{new_b:02x}"

    def get_audit_results(self) -> list[ContrastResult]:
        """Get all audit results."""
        return self._audit_results.copy()

    def get_failed_results(self) -> list[ContrastResult]:
        """Get only failed contrast checks."""
        return [r for r in self._audit_results if not r.passes_normal_text]


# =============================================================================
# Keyboard Navigation Support
# =============================================================================


class KeyboardNavigationManager:
    """
    Manages keyboard navigation and shortcuts.

    Provides accessible keyboard controls for the dashboard.
    """

    def __init__(self):
        """Initialize the keyboard navigation manager."""
        self._shortcuts: dict[KeyboardAction, KeyboardShortcut] = {}
        self._focusable_elements: list[FocusableElement] = []
        self._current_focus_index: int = 0
        self._action_handlers: dict[KeyboardAction, Callable] = {}
        
        # Register default shortcuts
        self._register_default_shortcuts()

    def _register_default_shortcuts(self) -> None:
        """Register default keyboard shortcuts."""
        default_shortcuts = [
            KeyboardShortcut(
                action=KeyboardAction.ZOOM_IN,
                key="+",
                description="Zoom in on the graph",
                modifiers=["Ctrl"],
            ),
            KeyboardShortcut(
                action=KeyboardAction.ZOOM_OUT,
                key="-",
                description="Zoom out on the graph",
                modifiers=["Ctrl"],
            ),
            KeyboardShortcut(
                action=KeyboardAction.PAN_UP,
                key="ArrowUp",
                description="Pan the view up",
            ),
            KeyboardShortcut(
                action=KeyboardAction.PAN_DOWN,
                key="ArrowDown",
                description="Pan the view down",
            ),
            KeyboardShortcut(
                action=KeyboardAction.PAN_LEFT,
                key="ArrowLeft",
                description="Pan the view left",
            ),
            KeyboardShortcut(
                action=KeyboardAction.PAN_RIGHT,
                key="ArrowRight",
                description="Pan the view right",
            ),
            KeyboardShortcut(
                action=KeyboardAction.FILTER_CRITICAL,
                key="1",
                description="Toggle critical severity filter",
            ),
            KeyboardShortcut(
                action=KeyboardAction.FILTER_HIGH,
                key="2",
                description="Toggle high severity filter",
            ),
            KeyboardShortcut(
                action=KeyboardAction.FILTER_MEDIUM,
                key="3",
                description="Toggle medium severity filter",
            ),
            KeyboardShortcut(
                action=KeyboardAction.FILTER_LOW,
                key="4",
                description="Toggle low severity filter",
            ),
            KeyboardShortcut(
                action=KeyboardAction.RESET_VIEW,
                key="r",
                description="Reset view to default",
            ),
            KeyboardShortcut(
                action=KeyboardAction.TOGGLE_LEGEND,
                key="l",
                description="Toggle legend visibility",
            ),
            KeyboardShortcut(
                action=KeyboardAction.NEXT_NODE,
                key="Tab",
                description="Focus next node",
            ),
            KeyboardShortcut(
                action=KeyboardAction.PREV_NODE,
                key="Tab",
                description="Focus previous node",
                modifiers=["Shift"],
            ),
            KeyboardShortcut(
                action=KeyboardAction.SELECT_NODE,
                key="Enter",
                description="Select focused node",
            ),
            KeyboardShortcut(
                action=KeyboardAction.SEARCH,
                key="f",
                description="Open search",
                modifiers=["Ctrl"],
            ),
            KeyboardShortcut(
                action=KeyboardAction.HELP,
                key="?",
                description="Show keyboard shortcuts help",
            ),
        ]

        for shortcut in default_shortcuts:
            self._shortcuts[shortcut.action] = shortcut

    def register_shortcut(self, shortcut: KeyboardShortcut) -> None:
        """
        Register a keyboard shortcut.

        Args:
            shortcut: Shortcut to register.
        """
        self._shortcuts[shortcut.action] = shortcut
        logger.info(
            "Registered keyboard shortcut",
            action=shortcut.action.value,
            key=shortcut.key,
        )

    def get_shortcut(self, action: KeyboardAction) -> KeyboardShortcut | None:
        """Get shortcut for an action."""
        return self._shortcuts.get(action)

    def get_all_shortcuts(self) -> list[KeyboardShortcut]:
        """Get all registered shortcuts."""
        return list(self._shortcuts.values())

    def register_action_handler(
        self,
        action: KeyboardAction,
        handler: Callable,
    ) -> None:
        """Register a handler for an action."""
        self._action_handlers[action] = handler

    def handle_key_event(
        self,
        key: str,
        modifiers: list[str] | None = None,
    ) -> KeyboardAction | None:
        """
        Handle a keyboard event.

        Args:
            key: Key pressed.
            modifiers: Active modifier keys.

        Returns:
            The action triggered, or None.
        """
        modifiers = modifiers or []
        modifiers_set = set(m.lower() for m in modifiers)

        for action, shortcut in self._shortcuts.items():
            if not shortcut.enabled:
                continue

            shortcut_modifiers = set(m.lower() for m in shortcut.modifiers)
            
            if shortcut.key.lower() == key.lower() and shortcut_modifiers == modifiers_set:
                # Execute handler if registered
                if action in self._action_handlers:
                    self._action_handlers[action]()
                return action

        return None

    def register_focusable_element(self, element: FocusableElement) -> None:
        """Register a focusable element."""
        self._focusable_elements.append(element)
        # Sort by tab index
        self._focusable_elements.sort(key=lambda e: e.tab_index)

    def get_focus_order(self) -> list[FocusableElement]:
        """Get elements in focus order."""
        return self._focusable_elements.copy()

    def move_focus_next(self) -> FocusableElement | None:
        """Move focus to next element."""
        if not self._focusable_elements:
            return None
        
        self._current_focus_index = (
            self._current_focus_index + 1
        ) % len(self._focusable_elements)
        
        return self._focusable_elements[self._current_focus_index]

    def move_focus_prev(self) -> FocusableElement | None:
        """Move focus to previous element."""
        if not self._focusable_elements:
            return None
        
        self._current_focus_index = (
            self._current_focus_index - 1
        ) % len(self._focusable_elements)
        
        return self._focusable_elements[self._current_focus_index]

    def get_current_focus(self) -> FocusableElement | None:
        """Get currently focused element."""
        if not self._focusable_elements:
            return None
        return self._focusable_elements[self._current_focus_index]

    def generate_help_text(self) -> str:
        """Generate help text for keyboard shortcuts."""
        lines = ["Keyboard Shortcuts", "=" * 40]
        
        for shortcut in sorted(self._shortcuts.values(), key=lambda s: s.action.value):
            if not shortcut.enabled:
                continue
            
            key_combo = shortcut.key
            if shortcut.modifiers:
                key_combo = "+".join(shortcut.modifiers) + "+" + key_combo
            
            lines.append(f"  {key_combo:<20} {shortcut.description}")
        
        return "\n".join(lines)


# =============================================================================
# Data Dictionary Generator
# =============================================================================


class DataDictionaryGenerator:
    """
    Generates data dictionaries for exports.

    Provides documentation for all exported data fields.
    """

    def __init__(self):
        """Initialize the data dictionary generator."""
        self._field_definitions: dict[str, FieldDefinition] = {}
        self._register_default_fields()

    def _register_default_fields(self) -> None:
        """Register default field definitions."""
        default_fields = [
            # Risk Event Fields
            FieldDefinition(
                name="id",
                data_type=DataType.STRING,
                description="Unique identifier for the risk event",
                nullable=False,
                format_pattern="risk-[a-z0-9]{8}",
                example="risk-abc12345",
            ),
            FieldDefinition(
                name="event_type",
                data_type=DataType.ENUM,
                description="Type of disruption event",
                nullable=False,
                enum_values=[
                    "Natural Disaster",
                    "Strike",
                    "Pandemic",
                    "Geopolitical",
                    "Regulatory",
                    "Supplier Failure",
                ],
                example="Natural Disaster",
            ),
            FieldDefinition(
                name="severity",
                data_type=DataType.ENUM,
                description="Impact severity level",
                nullable=False,
                enum_values=["Critical", "High", "Medium", "Low"],
                example="High",
            ),
            FieldDefinition(
                name="location",
                data_type=DataType.STRING,
                description="Geographic location of the event",
                nullable=False,
                example="Taiwan",
            ),
            FieldDefinition(
                name="confidence",
                data_type=DataType.FLOAT,
                description="Extraction confidence score (0.0 to 1.0)",
                nullable=False,
                format_pattern="0.0-1.0",
                example="0.85",
            ),
            FieldDefinition(
                name="description",
                data_type=DataType.STRING,
                description="Brief description of the risk event",
                nullable=True,
                example="Semiconductor shortage affecting chip production",
            ),
            FieldDefinition(
                name="detected_at",
                data_type=DataType.DATETIME,
                description="Timestamp when event was detected",
                nullable=False,
                format_pattern="ISO 8601",
                example="2024-01-15T10:30:00Z",
            ),
            FieldDefinition(
                name="affected_entities",
                data_type=DataType.ARRAY,
                description="List of entity IDs affected by this event",
                nullable=False,
                example='["supplier-1", "component-a"]',
                related_fields=["id"],
            ),
            # Supplier Fields
            FieldDefinition(
                name="supplier_id",
                data_type=DataType.STRING,
                description="Unique identifier for the supplier",
                nullable=False,
                format_pattern="supplier-[a-z0-9]+",
                example="supplier-tsmc-001",
            ),
            FieldDefinition(
                name="supplier_name",
                data_type=DataType.STRING,
                description="Human-readable supplier name",
                nullable=False,
                example="TSMC",
            ),
            FieldDefinition(
                name="tier",
                data_type=DataType.INTEGER,
                description="Supplier tier level (1=direct, 2+=indirect)",
                nullable=False,
                format_pattern="1-5",
                example="1",
            ),
            FieldDefinition(
                name="risk_score",
                data_type=DataType.FLOAT,
                description="Calculated risk score for entity (0.0 to 1.0)",
                nullable=True,
                format_pattern="0.0-1.0",
                example="0.65",
            ),
            # Resilience Fields
            FieldDefinition(
                name="resilience_score",
                data_type=DataType.FLOAT,
                description="Overall resilience score (0.0 to 1.0)",
                nullable=False,
                format_pattern="0.0-1.0",
                example="0.78",
            ),
            FieldDefinition(
                name="supplier_diversity",
                data_type=DataType.FLOAT,
                description="Supplier diversification score (0.0 to 1.0)",
                nullable=True,
                format_pattern="0.0-1.0",
                example="0.82",
            ),
            FieldDefinition(
                name="geographic_distribution",
                data_type=DataType.FLOAT,
                description="Geographic distribution score (0.0 to 1.0)",
                nullable=True,
                format_pattern="0.0-1.0",
                example="0.65",
            ),
        ]

        for field in default_fields:
            self._field_definitions[field.name] = field

    def register_field(self, field: FieldDefinition) -> None:
        """
        Register a field definition.

        Args:
            field: Field definition to register.
        """
        self._field_definitions[field.name] = field
        logger.info("Registered field definition", field_name=field.name)

    def get_field(self, name: str) -> FieldDefinition | None:
        """Get a field definition by name."""
        return self._field_definitions.get(name)

    def get_all_fields(self) -> list[FieldDefinition]:
        """Get all registered field definitions."""
        return list(self._field_definitions.values())

    def generate_dictionary(
        self,
        name: str,
        description: str,
        field_names: list[str],
        version: str = "1.0.0",
    ) -> DataDictionary:
        """
        Generate a data dictionary for specified fields.

        Args:
            name: Dictionary name.
            description: Dictionary description.
            field_names: List of field names to include.
            version: Version string.

        Returns:
            Generated DataDictionary.
        """
        fields = []
        for field_name in field_names:
            field = self._field_definitions.get(field_name)
            if field:
                fields.append(field)
            else:
                logger.warning(
                    "Field not found in definitions",
                    field_name=field_name,
                )

        return DataDictionary(
            name=name,
            version=version,
            description=description,
            fields=fields,
        )

    def generate_markdown(self, dictionary: DataDictionary) -> str:
        """
        Generate markdown documentation for a data dictionary.

        Args:
            dictionary: Data dictionary to document.

        Returns:
            Markdown formatted documentation.
        """
        lines = [
            f"# {dictionary.name}",
            "",
            dictionary.description,
            "",
            f"**Version:** {dictionary.version}",
            f"**Generated:** {dictionary.generated_at.isoformat()}",
            "",
            "## Field Definitions",
            "",
        ]

        for field in dictionary.fields:
            lines.extend([
                f"### {field.name}",
                "",
                f"**Type:** `{field.data_type.value}`",
                f"**Nullable:** {'Yes' if field.nullable else 'No'}",
                "",
                field.description,
                "",
            ])

            if field.format_pattern:
                lines.append(f"**Format:** `{field.format_pattern}`")
            
            if field.example:
                lines.append(f"**Example:** `{field.example}`")
            
            if field.enum_values:
                lines.append(f"**Allowed Values:** {', '.join(field.enum_values)}")
            
            if field.related_fields:
                lines.append(f"**Related Fields:** {', '.join(field.related_fields)}")
            
            lines.append("")

        return "\n".join(lines)

    def generate_json_schema(self, dictionary: DataDictionary) -> dict:
        """
        Generate JSON Schema for a data dictionary.

        Args:
            dictionary: Data dictionary.

        Returns:
            JSON Schema as dictionary.
        """
        properties = {}
        required = []

        type_mapping = {
            DataType.STRING: "string",
            DataType.INTEGER: "integer",
            DataType.FLOAT: "number",
            DataType.BOOLEAN: "boolean",
            DataType.DATE: "string",
            DataType.DATETIME: "string",
            DataType.ARRAY: "array",
            DataType.OBJECT: "object",
            DataType.ENUM: "string",
        }

        for field in dictionary.fields:
            prop: dict[str, Any] = {
                "type": type_mapping[field.data_type],
                "description": field.description,
            }

            if field.format_pattern:
                if field.data_type == DataType.DATETIME:
                    prop["format"] = "date-time"
                elif field.data_type == DataType.DATE:
                    prop["format"] = "date"

            if field.enum_values:
                prop["enum"] = field.enum_values

            if field.data_type == DataType.ARRAY:
                prop["items"] = {"type": "string"}

            properties[field.name] = prop

            if not field.nullable:
                required.append(field.name)

        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": dictionary.name,
            "description": dictionary.description,
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def include_in_export(
        self,
        export_data: dict,
        dictionary: DataDictionary,
    ) -> dict:
        """
        Include data dictionary in an export.

        Args:
            export_data: Original export data.
            dictionary: Data dictionary to include.

        Returns:
            Export with embedded dictionary.
        """
        return {
            "_data_dictionary": {
                "name": dictionary.name,
                "version": dictionary.version,
                "description": dictionary.description,
                "generated_at": dictionary.generated_at.isoformat(),
                "fields": [
                    {
                        "name": f.name,
                        "type": f.data_type.value,
                        "description": f.description,
                        "nullable": f.nullable,
                        "format": f.format_pattern,
                        "example": f.example,
                    }
                    for f in dictionary.fields
                ],
            },
            **export_data,
        }


# =============================================================================
# Accessibility Manager (Main Interface)
# =============================================================================


class AccessibilityManager:
    """
    Main interface for accessibility features.

    Coordinates color contrast, keyboard navigation, and data dictionary.
    """

    def __init__(self):
        """Initialize the accessibility manager."""
        self.contrast_checker = ColorContrastChecker()
        self.keyboard_nav = KeyboardNavigationManager()
        self.data_dictionary = DataDictionaryGenerator()

    def audit_accessibility(
        self,
        colors: dict[str, str],
        background: str,
    ) -> dict:
        """
        Perform a full accessibility audit.

        Args:
            colors: Color palette to audit.
            background: Background color.

        Returns:
            Audit results summary.
        """
        contrast_results = self.contrast_checker.audit_color_palette(colors, background)
        
        passed = sum(1 for r in contrast_results if r.passes_normal_text)
        failed = len(contrast_results) - passed

        return {
            "total_colors": len(contrast_results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(contrast_results) if contrast_results else 0,
            "results": contrast_results,
            "keyboard_shortcuts": len(self.keyboard_nav.get_all_shortcuts()),
            "focusable_elements": len(self.keyboard_nav.get_focus_order()),
        }

    def get_wcag_compliance_report(self) -> dict:
        """Generate WCAG compliance report."""
        failed = self.contrast_checker.get_failed_results()
        
        return {
            "level": WCAGLevel.AA.value,
            "color_contrast_issues": len(failed),
            "keyboard_navigation_supported": True,
            "issues": [
                {
                    "type": "color_contrast",
                    "color": r.color_pair.name,
                    "ratio": r.contrast_ratio,
                    "required": 4.5,
                    "recommendation": r.recommendation,
                }
                for r in failed
            ],
        }
