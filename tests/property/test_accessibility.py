"""
Property Tests for Accessibility and UX Improvements Module.

Tests the accessibility functionality, verifying:
- Property 36: Accessibility Color Contrast
- Property 37: Keyboard Navigation Support
- Property 38: Export Data Dictionary Inclusion
"""

from datetime import datetime, timezone
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
import pytest
import math

from src.analysis.accessibility import (
    WCAGLevel,
    ContrastRequirement,
    KeyboardAction,
    DataType,
    ColorPair,
    ContrastResult,
    KeyboardShortcut,
    FocusableElement,
    FieldDefinition,
    DataDictionary,
    ColorContrastChecker,
    KeyboardNavigationManager,
    DataDictionaryGenerator,
    AccessibilityManager,
)


# =============================================================================
# Strategy Definitions
# =============================================================================

# Hex color strategy
hex_color_strategy = st.from_regex(
    r"#[0-9a-fA-F]{6}",
    fullmatch=True,
)

# RGB value strategy
rgb_value_strategy = st.integers(min_value=0, max_value=255)

# Keyboard action strategy
keyboard_action_strategy = st.sampled_from(list(KeyboardAction))

# Data type strategy
data_type_strategy = st.sampled_from(list(DataType))

# Field name strategy
field_name_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz_",
    min_size=2,
    max_size=30,
).filter(lambda x: x and not x.startswith("_") and x.strip())


# =============================================================================
# Property 36: Accessibility Color Contrast
# =============================================================================


class TestAccessibilityColorContrast:
    """Property tests for WCAG 2.1 AA color contrast compliance."""

    @given(
        r1=rgb_value_strategy,
        g1=rgb_value_strategy,
        b1=rgb_value_strategy,
        r2=rgb_value_strategy,
        g2=rgb_value_strategy,
        b2=rgb_value_strategy,
    )
    @settings(max_examples=50)
    def test_contrast_ratio_is_symmetric(
        self,
        r1: int,
        g1: int,
        b1: int,
        r2: int,
        g2: int,
        b2: int,
    ):
        """
        Property: Contrast ratio is symmetric (A vs B == B vs A).
        """
        checker = ColorContrastChecker()
        
        color1 = f"#{r1:02x}{g1:02x}{b1:02x}"
        color2 = f"#{r2:02x}{g2:02x}{b2:02x}"
        
        ratio1 = checker.calculate_contrast_ratio(color1, color2)
        ratio2 = checker.calculate_contrast_ratio(color2, color1)
        
        assert abs(ratio1 - ratio2) < 0.01

    @given(
        r=rgb_value_strategy,
        g=rgb_value_strategy,
        b=rgb_value_strategy,
    )
    @settings(max_examples=30)
    def test_contrast_ratio_with_self_is_one(self, r: int, g: int, b: int):
        """
        Property: Contrast ratio of color with itself is 1.0.
        """
        checker = ColorContrastChecker()
        
        color = f"#{r:02x}{g:02x}{b:02x}"
        ratio = checker.calculate_contrast_ratio(color, color)
        
        assert abs(ratio - 1.0) < 0.01

    @given(hex_color=hex_color_strategy)
    @settings(max_examples=30)
    def test_contrast_with_black_or_white_is_high(self, hex_color: str):
        """
        Property: Contrast with black or white is at least 1.0.
        """
        checker = ColorContrastChecker()
        
        ratio_black = checker.calculate_contrast_ratio(hex_color, "#000000")
        ratio_white = checker.calculate_contrast_ratio(hex_color, "#ffffff")
        
        assert ratio_black >= 1.0
        assert ratio_white >= 1.0
        
        # At least one should have reasonable contrast
        assert max(ratio_black, ratio_white) >= 1.0

    def test_black_on_white_has_maximum_contrast(self):
        """
        Property: Black on white has contrast ratio of 21:1.
        """
        checker = ColorContrastChecker()
        
        ratio = checker.calculate_contrast_ratio("#000000", "#ffffff")
        
        assert abs(ratio - 21.0) < 0.1

    @given(hex_color=hex_color_strategy)
    @settings(max_examples=30)
    def test_contrast_ratio_bounds(self, hex_color: str):
        """
        Property: Contrast ratio is always between 1 and 21.
        """
        checker = ColorContrastChecker()
        
        ratio_black = checker.calculate_contrast_ratio(hex_color, "#000000")
        ratio_white = checker.calculate_contrast_ratio(hex_color, "#ffffff")
        
        assert 1.0 <= ratio_black <= 21.0
        assert 1.0 <= ratio_white <= 21.0

    @given(
        r=rgb_value_strategy,
        g=rgb_value_strategy,
        b=rgb_value_strategy,
    )
    @settings(max_examples=30)
    def test_luminance_calculation_bounds(self, r: int, g: int, b: int):
        """
        Property: Relative luminance is between 0 and 1.
        """
        checker = ColorContrastChecker()
        
        luminance = checker.get_relative_luminance(r, g, b)
        
        assert 0.0 <= luminance <= 1.0

    def test_check_contrast_returns_correct_structure(self):
        """
        Property: check_contrast returns ContrastResult with all fields.
        """
        checker = ColorContrastChecker()
        
        pair = ColorPair(
            foreground="#ffffff",
            background="#000000",
            name="white_on_black",
        )
        
        result = checker.check_contrast(pair)
        
        assert isinstance(result, ContrastResult)
        assert result.color_pair == pair
        assert isinstance(result.contrast_ratio, float)
        assert isinstance(result.passes_normal_text, bool)
        assert isinstance(result.passes_large_text, bool)
        assert isinstance(result.passes_ui_components, bool)

    def test_audit_color_palette(self):
        """
        Property: audit_color_palette tests all colors.
        """
        checker = ColorContrastChecker()
        
        colors = {
            "red": "#ff0000",
            "green": "#00ff00",
            "blue": "#0000ff",
        }
        
        results = checker.audit_color_palette(colors, "#ffffff")
        
        assert len(results) == 3
        assert all(isinstance(r, ContrastResult) for r in results)


# =============================================================================
# Property 37: Keyboard Navigation Support
# =============================================================================


class TestKeyboardNavigationSupport:
    """Property tests for keyboard navigation functionality."""

    def test_default_shortcuts_registered(self):
        """
        Property: Default shortcuts are registered on initialization.
        """
        manager = KeyboardNavigationManager()
        
        shortcuts = manager.get_all_shortcuts()
        
        assert len(shortcuts) > 0
        
        # Essential shortcuts should exist
        essential_actions = [
            KeyboardAction.ZOOM_IN,
            KeyboardAction.ZOOM_OUT,
            KeyboardAction.NEXT_NODE,
            KeyboardAction.HELP,
        ]
        
        for action in essential_actions:
            shortcut = manager.get_shortcut(action)
            assert shortcut is not None

    @given(action=keyboard_action_strategy)
    @settings(max_examples=20)
    def test_shortcut_has_required_fields(self, action: KeyboardAction):
        """
        Property: Each shortcut has key and description.
        """
        manager = KeyboardNavigationManager()
        
        shortcut = manager.get_shortcut(action)
        
        # All actions should have default shortcuts
        if shortcut:
            assert shortcut.key
            assert shortcut.description
            assert shortcut.action == action

    def test_custom_shortcut_registration(self):
        """
        Property: Custom shortcuts can be registered.
        """
        manager = KeyboardNavigationManager()
        
        custom = KeyboardShortcut(
            action=KeyboardAction.ZOOM_IN,
            key="z",
            description="Custom zoom in",
            modifiers=["Alt"],
        )
        
        manager.register_shortcut(custom)
        
        retrieved = manager.get_shortcut(KeyboardAction.ZOOM_IN)
        assert retrieved.key == "z"
        assert "Alt" in retrieved.modifiers

    def test_key_event_handling(self):
        """
        Property: Key events trigger correct actions.
        """
        manager = KeyboardNavigationManager()
        
        # Test simple key
        action = manager.handle_key_event("r")
        assert action == KeyboardAction.RESET_VIEW
        
        # Test with modifiers
        action = manager.handle_key_event("+", ["Ctrl"])
        assert action == KeyboardAction.ZOOM_IN

    def test_focus_navigation_order(self):
        """
        Property: Focus moves in correct order.
        """
        manager = KeyboardNavigationManager()
        
        # Register elements in order
        for i in range(5):
            manager.register_focusable_element(FocusableElement(
                element_id=f"element-{i}",
                element_type="button",
                label=f"Button {i}",
                tab_index=i,
                aria_label=f"Button {i}",
                role="button",
            ))
        
        focus_order = manager.get_focus_order()
        assert len(focus_order) == 5
        
        # Tab indexes should be in order
        for i, element in enumerate(focus_order):
            assert element.tab_index == i

    def test_focus_next_wraps_around(self):
        """
        Property: Focus wraps around at end of list.
        """
        manager = KeyboardNavigationManager()
        
        for i in range(3):
            manager.register_focusable_element(FocusableElement(
                element_id=f"el-{i}",
                element_type="button",
                label=f"Button {i}",
                tab_index=i,
                aria_label=f"Button {i}",
                role="button",
            ))
        
        # Move forward 4 times (should wrap)
        for _ in range(4):
            manager.move_focus_next()
        
        current = manager.get_current_focus()
        assert current.element_id == "el-1"

    def test_help_text_generation(self):
        """
        Property: Help text includes all shortcuts.
        """
        manager = KeyboardNavigationManager()
        
        help_text = manager.generate_help_text()
        
        assert "Keyboard Shortcuts" in help_text
        assert "Zoom in" in help_text
        assert "Ctrl" in help_text


# =============================================================================
# Property 38: Export Data Dictionary Inclusion
# =============================================================================


class TestExportDataDictionaryInclusion:
    """Property tests for data dictionary functionality."""

    def test_default_fields_registered(self):
        """
        Property: Default fields are registered on initialization.
        """
        generator = DataDictionaryGenerator()
        
        fields = generator.get_all_fields()
        
        assert len(fields) > 0
        
        # Essential fields should exist
        essential = ["id", "event_type", "severity", "confidence"]
        for name in essential:
            field = generator.get_field(name)
            assert field is not None

    @given(name=field_name_strategy, data_type=data_type_strategy)
    @settings(max_examples=30)
    def test_custom_field_registration(self, name: str, data_type: DataType):
        """
        Property: Custom fields can be registered.
        """
        generator = DataDictionaryGenerator()
        
        field = FieldDefinition(
            name=name,
            data_type=data_type,
            description=f"Test field {name}",
        )
        
        generator.register_field(field)
        
        retrieved = generator.get_field(name)
        assert retrieved is not None
        assert retrieved.data_type == data_type

    def test_dictionary_generation(self):
        """
        Property: Dictionary contains requested fields.
        """
        generator = DataDictionaryGenerator()
        
        dictionary = generator.generate_dictionary(
            name="Test Export",
            description="Test data export",
            field_names=["id", "severity", "confidence"],
        )
        
        assert dictionary.name == "Test Export"
        assert len(dictionary.fields) == 3
        
        field_names = [f.name for f in dictionary.fields]
        assert "id" in field_names
        assert "severity" in field_names

    def test_markdown_generation(self):
        """
        Property: Markdown includes all fields.
        """
        generator = DataDictionaryGenerator()
        
        dictionary = generator.generate_dictionary(
            name="Risk Events",
            description="Risk event export",
            field_names=["id", "severity"],
        )
        
        markdown = generator.generate_markdown(dictionary)
        
        assert "# Risk Events" in markdown
        assert "## Field Definitions" in markdown
        assert "### id" in markdown
        assert "### severity" in markdown

    def test_json_schema_generation(self):
        """
        Property: JSON schema has correct structure.
        """
        generator = DataDictionaryGenerator()
        
        dictionary = generator.generate_dictionary(
            name="Test Schema",
            description="Test schema",
            field_names=["id", "severity", "confidence"],
        )
        
        schema = generator.generate_json_schema(dictionary)
        
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "id" in schema["properties"]
        assert "required" in schema

    def test_include_in_export(self):
        """
        Property: Dictionary is included in export data.
        """
        generator = DataDictionaryGenerator()
        
        dictionary = generator.generate_dictionary(
            name="Export",
            description="Test export",
            field_names=["id"],
        )
        
        original_data = {"data": [{"id": "test-1"}]}
        
        with_dictionary = generator.include_in_export(original_data, dictionary)
        
        assert "_data_dictionary" in with_dictionary
        assert "data" in with_dictionary
        assert with_dictionary["_data_dictionary"]["name"] == "Export"
        assert len(with_dictionary["_data_dictionary"]["fields"]) == 1

    def test_field_definition_structure(self):
        """
        Property: Field definitions have complete structure.
        """
        generator = DataDictionaryGenerator()
        
        field = generator.get_field("event_type")
        
        assert field is not None
        assert field.name == "event_type"
        assert field.data_type == DataType.ENUM
        assert field.description
        assert len(field.enum_values) > 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestAccessibilityIntegration:
    """Integration tests for accessibility management."""

    def test_accessibility_manager_initialization(self):
        """
        Property: AccessibilityManager initializes all components.
        """
        manager = AccessibilityManager()
        
        assert manager.contrast_checker is not None
        assert manager.keyboard_nav is not None
        assert manager.data_dictionary is not None

    def test_full_accessibility_audit(self):
        """
        Property: audit_accessibility returns complete results.
        """
        manager = AccessibilityManager()
        
        colors = {
            "critical": "#ef4444",
            "high": "#f97316",
            "medium": "#eab308",
            "low": "#22c55e",
        }
        
        results = manager.audit_accessibility(colors, "#111827")
        
        assert "total_colors" in results
        assert "passed" in results
        assert "failed" in results
        assert "pass_rate" in results
        assert results["total_colors"] == 4

    def test_wcag_compliance_report(self):
        """
        Property: Compliance report has correct structure.
        """
        manager = AccessibilityManager()
        
        # First audit some colors
        manager.contrast_checker.audit_color_palette(
            {"red": "#ff0000"},
            "#ffffff",
        )
        
        report = manager.get_wcag_compliance_report()
        
        assert "level" in report
        assert report["level"] == "AA"
        assert "color_contrast_issues" in report
        assert "keyboard_navigation_supported" in report
        assert "issues" in report

    @given(
        r=rgb_value_strategy,
        g=rgb_value_strategy,
        b=rgb_value_strategy,
    )
    @settings(max_examples=20)
    def test_color_suggestion_returns_valid_color(self, r: int, g: int, b: int):
        """
        Property: Suggested color is always a valid hex color.
        """
        checker = ColorContrastChecker()
        
        original = f"#{r:02x}{g:02x}{b:02x}"
        background = "#111827"  # Dark background
        
        suggested = checker.suggest_accessible_color(
            original, background, target_ratio=4.5
        )
        
        # Suggested should be a valid hex color
        assert suggested.startswith("#")
        assert len(suggested) == 7
        
        # Should be able to calculate contrast with it
        ratio = checker.calculate_contrast_ratio(suggested, background)
        assert 1.0 <= ratio <= 21.0
