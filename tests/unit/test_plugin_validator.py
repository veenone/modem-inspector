"""Unit tests for PluginValidator.

Tests schema validation, semantic validation, and error message quality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from src.core.plugin_validator import PluginValidator
from src.core.plugin import (
    Plugin,
    PluginMetadata,
    PluginConnection,
    CommandDefinition,
    ParserDefinition,
    PluginValidation,
    ParserType,
    PluginCategory
)


class TestPluginValidatorSchemaValidation:
    """Test schema validation functionality."""

    @pytest.fixture
    def validator(self):
        """Create a PluginValidator instance."""
        return PluginValidator()

    def test_validate_schema_valid_plugin(self, validator):
        """Test schema validation with a valid plugin."""
        valid_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"

connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false

commands:
  basic:
    - cmd: "AT"
      description: "Test command"
      category: "basic"

validation:
  required_responses:
    - "AT"
"""
        is_valid, errors = validator.validate_schema(valid_yaml)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_schema_missing_required_field(self, validator):
        """Test schema validation with missing required field."""
        invalid_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"

connection:
  default_baud: 115200

commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""
        is_valid, errors = validator.validate_schema(invalid_yaml)
        assert is_valid is False
        assert len(errors) > 0
        assert any("version" in err.lower() for err in errors)

    def test_validate_schema_invalid_yaml_syntax(self, validator):
        """Test schema validation with invalid YAML syntax."""
        invalid_yaml = """
metadata:
  vendor: "quectel
  model: "ec200u"
"""
        is_valid, errors = validator.validate_schema(invalid_yaml)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_schema_invalid_at_command_format(self, validator):
        """Test schema validation with invalid AT command format."""
        invalid_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"

connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false

commands:
  basic:
    - cmd: "NOTVALID"
      description: "Test command that doesn't start with AT"
      category: "basic"
"""
        is_valid, errors = validator.validate_schema(invalid_yaml)
        assert is_valid is False
        assert len(errors) > 0
        # Should mention the cmd field or pattern mismatch
        assert any("cmd" in err.lower() or "pattern" in err.lower() for err in errors)

    def test_validate_schema_invalid_version_format(self, validator):
        """Test schema validation with invalid version format."""
        invalid_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0"

connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false

commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""
        is_valid, errors = validator.validate_schema(invalid_yaml)
        assert is_valid is False
        assert len(errors) > 0
        assert any("version" in err.lower() for err in errors)

    def test_validate_schema_invalid_category(self, validator):
        """Test schema validation with invalid category."""
        invalid_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "invalid_category"
  version: "1.0.0"

connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false

commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""
        is_valid, errors = validator.validate_schema(invalid_yaml)
        assert is_valid is False
        assert len(errors) > 0
        assert any("category" in err.lower() for err in errors)

    def test_validate_schema_invalid_baud_rate(self, validator):
        """Test schema validation with invalid baud rate."""
        invalid_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"

connection:
  default_baud: 1000
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false

commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""
        is_valid, errors = validator.validate_schema(invalid_yaml)
        assert is_valid is False
        assert len(errors) > 0


class TestPluginValidatorSemanticValidation:
    """Test semantic validation beyond schema."""

    @pytest.fixture
    def validator(self):
        """Create a PluginValidator instance."""
        return PluginValidator()

    @pytest.fixture
    def sample_plugin(self):
        """Create a sample plugin for testing."""
        return Plugin(
            metadata=PluginMetadata(
                vendor="quectel",
                model="ec200u",
                category="lte_cat1",
                version="1.0.0"
            ),
            connection=PluginConnection(),
            commands={
                "basic": [
                    CommandDefinition(cmd="AT", description="Test", category="basic")
                ]
            },
            parsers={}
        )

    def test_validate_plugin_no_warnings(self, validator, sample_plugin):
        """Test semantic validation with clean plugin."""
        warnings = validator.validate_plugin(sample_plugin)
        assert isinstance(warnings, list)
        assert len(warnings) == 0

    def test_validate_plugin_duplicate_commands(self, validator):
        """Test detection of duplicate commands."""
        plugin = Plugin(
            metadata=PluginMetadata(
                vendor="test",
                model="test",
                category="other",
                version="1.0.0"
            ),
            connection=PluginConnection(),
            commands={
                "basic": [
                    CommandDefinition(cmd="AT", description="Test 1", category="basic"),
                    CommandDefinition(cmd="AT", description="Test 2", category="basic")
                ]
            },
            parsers={}
        )

        warnings = validator.validate_plugin(plugin)
        assert len(warnings) > 0
        assert any("duplicate" in w.lower() for w in warnings)

    def test_validate_plugin_undefined_parser(self, validator):
        """Test detection of undefined parser references."""
        plugin = Plugin(
            metadata=PluginMetadata(
                vendor="test",
                model="test",
                category="other",
                version="1.0.0"
            ),
            connection=PluginConnection(),
            commands={
                "basic": [
                    CommandDefinition(
                        cmd="AT+CSQ",
                        description="Signal quality",
                        category="basic",
                        parser="nonexistent_parser"
                    )
                ]
            },
            parsers={}
        )

        warnings = validator.validate_plugin(plugin)
        assert len(warnings) > 0
        assert any("parser" in w.lower() and "nonexistent" in w.lower() for w in warnings)

    def test_validate_plugin_valid_parser_reference(self, validator):
        """Test that valid parser references don't generate warnings."""
        plugin = Plugin(
            metadata=PluginMetadata(
                vendor="test",
                model="test",
                category="other",
                version="1.0.0"
            ),
            connection=PluginConnection(),
            commands={
                "basic": [
                    CommandDefinition(
                        cmd="AT+CSQ",
                        description="Signal quality",
                        category="basic",
                        parser="signal_parser"
                    )
                ]
            },
            parsers={
                "signal_parser": ParserDefinition(
                    name="signal_parser",
                    type=ParserType.REGEX,
                    pattern=r"\+CSQ: (\d+),(\d+)"
                )
            }
        )

        warnings = validator.validate_plugin(plugin)
        # Should not have undefined parser warning
        assert not any("undefined" in w.lower() and "parser" in w.lower() for w in warnings)

    def test_validate_plugin_category_mismatch(self, validator):
        """Test detection of category mismatches."""
        plugin = Plugin(
            metadata=PluginMetadata(
                vendor="test",
                model="test",
                category="lte_cat1",
                version="1.0.0"
            ),
            connection=PluginConnection(),
            commands={
                "basic": [
                    CommandDefinition(
                        cmd="AT",
                        description="Test",
                        category="network"  # Mismatch with parent key
                    )
                ]
            },
            parsers={}
        )

        warnings = validator.validate_plugin(plugin)
        assert len(warnings) > 0
        assert any("category" in w.lower() for w in warnings)


class TestPluginValidatorTestPlugin:
    """Test hardware plugin testing functionality."""

    @pytest.fixture
    def validator(self):
        """Create a PluginValidator instance."""
        return PluginValidator()

    @pytest.fixture
    def sample_plugin(self):
        """Create a sample plugin for testing."""
        return Plugin(
            metadata=PluginMetadata(
                vendor="quectel",
                model="ec200u",
                category="lte_cat1",
                version="1.0.0"
            ),
            connection=PluginConnection(),
            commands={
                "basic": [
                    CommandDefinition(cmd="AT", description="Test", category="basic", critical=True),
                    CommandDefinition(cmd="AT+CGMI", description="Manufacturer", category="basic")
                ]
            },
            parsers={},
            validation=PluginValidation(
                required_responses=["AT"],
                expected_manufacturer="Quectel"
            )
        )

    def test_test_plugin_with_mocked_serial(self, validator, sample_plugin):
        """Test plugin testing with mocked serial handler."""
        mock_serial = Mock()
        mock_at_executor = Mock()

        # Mock successful AT command
        mock_response = Mock()
        mock_response.is_successful.return_value = True
        mock_response.raw = "OK"
        mock_at_executor.execute_command.return_value = mock_response

        result = validator.test_plugin(sample_plugin, mock_serial, mock_at_executor)

        assert result is not None
        assert hasattr(result, 'plugin_name')
        assert hasattr(result, 'total_commands')
        assert hasattr(result, 'passed')
        assert hasattr(result, 'failed')
        assert hasattr(result, 'errors')

    def test_test_plugin_critical_command_failure(self, validator, sample_plugin):
        """Test plugin testing with critical command failure."""
        mock_serial = Mock()
        mock_at_executor = Mock()

        # Mock failed critical command
        mock_response = Mock()
        mock_response.is_successful.return_value = False
        mock_response.error_message = "No response"
        mock_at_executor.execute_command.return_value = mock_response

        result = validator.test_plugin(sample_plugin, mock_serial, mock_at_executor)

        assert result is not None
        assert result.failed > 0
        assert result.total_commands > 0


class TestPluginValidatorErrorMessages:
    """Test error message quality and clarity."""

    @pytest.fixture
    def validator(self):
        """Create a PluginValidator instance."""
        return PluginValidator()

    def test_error_messages_include_field_names(self, validator):
        """Test that error messages include field names."""
        invalid_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"

connection:
  default_baud: 115200

commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""
        is_valid, errors = validator.validate_schema(invalid_yaml)
        assert is_valid is False
        # Error should mention the missing field
        assert any("version" in err.lower() or "metadata" in err.lower() for err in errors)

    def test_error_messages_are_actionable(self, validator):
        """Test that error messages provide actionable information."""
        invalid_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "invalid_cat"
  version: "1.0.0"

connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false

commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""
        is_valid, errors = validator.validate_schema(invalid_yaml)
        assert is_valid is False
        # Should have enough context to understand the issue
        assert len(errors) > 0
        assert all(isinstance(err, str) and len(err) > 10 for err in errors)
