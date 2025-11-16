"""Unit tests for Plugin data models.

Tests Plugin dataclasses for immutability, helper methods, field defaults,
and enum values.
"""

import pytest
from dataclasses import FrozenInstanceError
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


class TestPluginMetadata:
    """Test PluginMetadata dataclass."""

    def test_metadata_immutable(self):
        """Test that PluginMetadata is frozen (immutable)."""
        metadata = PluginMetadata(
            vendor="quectel",
            model="ec200u",
            category=PluginCategory.LTE_CAT1,
            version="1.0.0"
        )

        with pytest.raises(FrozenInstanceError):
            metadata.vendor = "simcom"

    def test_metadata_required_fields(self):
        """Test that all required fields must be provided."""
        metadata = PluginMetadata(
            vendor="quectel",
            model="ec200u",
            category=PluginCategory.LTE_CAT1,
            version="1.0.0"
        )

        assert metadata.vendor == "quectel"
        assert metadata.model == "ec200u"
        assert metadata.category == PluginCategory.LTE_CAT1
        assert metadata.version == "1.0.0"

    def test_metadata_optional_fields(self):
        """Test optional fields have None defaults."""
        metadata = PluginMetadata(
            vendor="quectel",
            model="ec200u",
            category=PluginCategory.LTE_CAT1,
            version="1.0.0"
        )

        assert metadata.author is None
        assert metadata.compatible_with is None
        assert metadata.variants is None

    def test_metadata_with_optional_fields(self):
        """Test metadata with optional fields provided."""
        metadata = PluginMetadata(
            vendor="quectel",
            model="ec200u",
            category=PluginCategory.LTE_CAT1,
            version="1.0.0",
            author="Test Author",
            compatible_with="inspector_v2.0+",
            variants=["EC200U-EU", "EC200U-CN"]
        )

        assert metadata.author == "Test Author"
        assert metadata.compatible_with == "inspector_v2.0+"
        assert metadata.variants == ["EC200U-EU", "EC200U-CN"]


class TestPluginConnection:
    """Test PluginConnection dataclass."""

    def test_connection_immutable(self):
        """Test that PluginConnection is frozen."""
        connection = PluginConnection(
            default_baud=115200,
            data_bits=8,
            parity="N",
            stop_bits=1,
            flow_control=False
        )

        with pytest.raises(FrozenInstanceError):
            connection.default_baud = 9600

    def test_connection_default_values(self):
        """Test connection default values."""
        connection = PluginConnection(
            default_baud=115200,
            data_bits=8,
            parity="N",
            stop_bits=1,
            flow_control=False
        )

        assert connection.default_baud == 115200
        assert connection.data_bits == 8
        assert connection.parity == "N"
        assert connection.stop_bits == 1
        assert connection.flow_control is False

    def test_connection_optional_init_sequence(self):
        """Test optional init_sequence field."""
        connection = PluginConnection(
            default_baud=115200,
            data_bits=8,
            parity="N",
            stop_bits=1,
            flow_control=False
        )

        assert connection.init_sequence is None


class TestCommandDefinition:
    """Test CommandDefinition dataclass."""

    def test_command_immutable(self):
        """Test that CommandDefinition is frozen."""
        cmd = CommandDefinition(
            cmd="AT",
            description="Test command",
            category="basic"
        )

        with pytest.raises(FrozenInstanceError):
            cmd.cmd = "AT+CGMI"

    def test_command_required_fields(self):
        """Test required command fields."""
        cmd = CommandDefinition(
            cmd="AT",
            description="Test command",
            category="basic"
        )

        assert cmd.cmd == "AT"
        assert cmd.description == "Test command"
        assert cmd.category == "basic"

    def test_command_optional_fields_defaults(self):
        """Test optional fields have correct defaults."""
        cmd = CommandDefinition(
            cmd="AT",
            description="Test command",
            category="basic"
        )

        assert cmd.timeout is None
        assert cmd.parser is None
        assert cmd.critical is False
        assert cmd.quick is False
        assert cmd.expected_format is None

    def test_command_with_all_fields(self):
        """Test command with all optional fields."""
        cmd = CommandDefinition(
            cmd="AT+CGMI",
            description="Get manufacturer",
            category="basic",
            timeout=10,
            parser="manufacturer_parser",
            critical=True,
            quick=True,
            expected_format="string"
        )

        assert cmd.timeout == 10
        assert cmd.parser == "manufacturer_parser"
        assert cmd.critical is True
        assert cmd.quick is True
        assert cmd.expected_format == "string"


class TestParserDefinition:
    """Test ParserDefinition dataclass."""

    def test_parser_immutable(self):
        """Test that ParserDefinition is frozen."""
        parser = ParserDefinition(
            name="test_parser",
            type=ParserType.REGEX,
            pattern=r"\+CGMI: (.+)"
        )

        with pytest.raises(FrozenInstanceError):
            parser.name = "new_name"

    def test_regex_parser(self):
        """Test regex parser definition."""
        parser = ParserDefinition(
            name="signal_parser",
            type=ParserType.REGEX,
            pattern=r"\+CSQ: (\d+),(\d+)",
            groups=["rssi", "ber"]
        )

        assert parser.name == "signal_parser"
        assert parser.type == ParserType.REGEX
        assert parser.pattern == r"\+CSQ: (\d+),(\d+)"
        assert parser.groups == ["rssi", "ber"]

    def test_json_parser(self):
        """Test JSON parser definition."""
        parser = ParserDefinition(
            name="json_parser",
            type=ParserType.JSON,
            json_path="data.value"
        )

        assert parser.name == "json_parser"
        assert parser.type == ParserType.JSON
        assert parser.json_path == "data.value"

    def test_custom_parser(self):
        """Test custom parser definition."""
        parser = ParserDefinition(
            name="custom_parser",
            type=ParserType.CUSTOM,
            module="parsers.custom.my_parser",
            function="parse_response"
        )

        assert parser.name == "custom_parser"
        assert parser.type == ParserType.CUSTOM
        assert parser.module == "parsers.custom.my_parser"
        assert parser.function == "parse_response"


class TestPluginValidation:
    """Test PluginValidation dataclass."""

    def test_validation_immutable(self):
        """Test that PluginValidation is frozen."""
        validation = PluginValidation(
            required_responses=["AT", "AT+CGMI"]
        )

        with pytest.raises(FrozenInstanceError):
            validation.required_responses = ["AT"]

    def test_validation_optional_fields_defaults(self):
        """Test all fields are optional with None defaults."""
        validation = PluginValidation()

        assert validation.required_responses is None
        assert validation.expected_manufacturer is None
        assert validation.expected_model_pattern is None
        assert validation.expected_values is None

    def test_validation_with_all_fields(self):
        """Test validation with all fields."""
        validation = PluginValidation(
            required_responses=["AT", "AT+CGMI"],
            expected_manufacturer="Quectel",
            expected_model_pattern="EC200.*",
            expected_values={"network": ["LTE", "5G"]}
        )

        assert validation.required_responses == ["AT", "AT+CGMI"]
        assert validation.expected_manufacturer == "Quectel"
        assert validation.expected_model_pattern == "EC200.*"
        assert validation.expected_values == {"network": ["LTE", "5G"]}


class TestPlugin:
    """Test Plugin dataclass and helper methods."""

    @pytest.fixture
    def sample_plugin(self):
        """Create a sample plugin for testing."""
        metadata = PluginMetadata(
            vendor="quectel",
            model="ec200u",
            category=PluginCategory.LTE_CAT1,
            version="1.0.0"
        )

        connection = PluginConnection(
            default_baud=115200,
            data_bits=8,
            parity="N",
            stop_bits=1,
            flow_control=False
        )

        commands = {
            "basic": [
                CommandDefinition(cmd="AT", description="Test", category="basic"),
                CommandDefinition(cmd="AT+CGMI", description="Manufacturer", category="basic")
            ],
            "network": [
                CommandDefinition(cmd="AT+CSQ", description="Signal quality", category="network"),
                CommandDefinition(cmd="AT+COPS?", description="Operator", category="network")
            ]
        }

        parsers = {
            "signal_parser": ParserDefinition(
                name="signal_parser",
                type=ParserType.REGEX,
                pattern=r"\+CSQ: (\d+),(\d+)",
                groups=["rssi", "ber"]
            )
        }

        validation = PluginValidation(
            required_responses=["AT"]
        )

        return Plugin(
            metadata=metadata,
            connection=connection,
            commands=commands,
            parsers=parsers,
            validation=validation
        )

    def test_plugin_immutable(self, sample_plugin):
        """Test that Plugin is frozen."""
        with pytest.raises(FrozenInstanceError):
            sample_plugin.metadata = None

    def test_get_all_commands(self, sample_plugin):
        """Test get_all_commands() returns all commands."""
        all_commands = sample_plugin.get_all_commands()

        assert len(all_commands) == 4
        command_strings = [cmd.cmd for cmd in all_commands]
        assert "AT" in command_strings
        assert "AT+CGMI" in command_strings
        assert "AT+CSQ" in command_strings
        assert "AT+COPS?" in command_strings

    def test_get_all_commands_empty(self):
        """Test get_all_commands() with no commands."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", PluginCategory.OTHER, "1.0.0"),
            connection=PluginConnection(115200, 8, "N", 1, False),
            commands={},
            parsers={}
        )

        assert plugin.get_all_commands() == []

    def test_get_commands_by_category(self, sample_plugin):
        """Test get_commands_by_category()."""
        basic_commands = sample_plugin.get_commands_by_category("basic")
        network_commands = sample_plugin.get_commands_by_category("network")

        assert len(basic_commands) == 2
        assert len(network_commands) == 2

        basic_cmd_strings = [cmd.cmd for cmd in basic_commands]
        assert "AT" in basic_cmd_strings
        assert "AT+CGMI" in basic_cmd_strings

    def test_get_commands_by_category_nonexistent(self, sample_plugin):
        """Test get_commands_by_category() with nonexistent category."""
        commands = sample_plugin.get_commands_by_category("power")
        assert commands == []

    def test_get_parser(self, sample_plugin):
        """Test get_parser() retrieves parser by name."""
        parser = sample_plugin.get_parser("signal_parser")

        assert parser is not None
        assert parser.name == "signal_parser"
        assert parser.type == ParserType.REGEX

    def test_get_parser_nonexistent(self, sample_plugin):
        """Test get_parser() with nonexistent parser."""
        parser = sample_plugin.get_parser("nonexistent_parser")
        assert parser is None

    def test_get_parser_no_parsers(self):
        """Test get_parser() when plugin has no parsers."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", PluginCategory.OTHER, "1.0.0"),
            connection=PluginConnection(115200, 8, "N", 1, False),
            commands={},
            parsers={}
        )

        assert plugin.get_parser("any_parser") is None

    def test_get_init_commands(self):
        """Test get_init_commands() returns init sequence."""
        connection = PluginConnection(
            default_baud=115200,
            data_bits=8,
            parity="N",
            stop_bits=1,
            flow_control=False,
            init_sequence=[
                {"cmd": "ATE0", "expected": "OK"},
                {"cmd": "AT+CMEE=2", "expected": "OK"}
            ]
        )

        plugin = Plugin(
            metadata=PluginMetadata("test", "test", PluginCategory.OTHER, "1.0.0"),
            connection=connection,
            commands={},
            parsers={}
        )

        init_commands = plugin.get_init_commands()
        assert len(init_commands) == 2
        assert init_commands[0] == "ATE0"
        assert init_commands[1] == "AT+CMEE=2"

    def test_get_init_commands_none(self, sample_plugin):
        """Test get_init_commands() when no init sequence."""
        init_commands = sample_plugin.get_init_commands()
        assert init_commands == []


class TestParserType:
    """Test ParserType enum."""

    def test_parser_type_values(self):
        """Test ParserType enum has expected values."""
        assert ParserType.REGEX.value == "regex"
        assert ParserType.JSON.value == "json"
        assert ParserType.CUSTOM.value == "custom"
        assert ParserType.NONE.value == "none"

    def test_parser_type_from_string(self):
        """Test creating ParserType from string."""
        assert ParserType("regex") == ParserType.REGEX
        assert ParserType("json") == ParserType.JSON
        assert ParserType("custom") == ParserType.CUSTOM

    def test_parser_type_invalid(self):
        """Test invalid parser type raises error."""
        with pytest.raises(ValueError):
            ParserType("invalid")


class TestPluginCategory:
    """Test PluginCategory enum."""

    def test_category_values(self):
        """Test PluginCategory enum has expected values."""
        assert PluginCategory.FIVEG_HIGHPERF.value == "5g_highperf"
        assert PluginCategory.LTE_CAT1.value == "lte_cat1"
        assert PluginCategory.AUTOMOTIVE.value == "automotive"
        assert PluginCategory.IOT.value == "iot"
        assert PluginCategory.NBIOT.value == "nbiot"
        assert PluginCategory.OTHER.value == "other"

    def test_category_from_string(self):
        """Test creating PluginCategory from string."""
        assert PluginCategory("lte_cat1") == PluginCategory.LTE_CAT1
        assert PluginCategory("5g_highperf") == PluginCategory.FIVEG_HIGHPERF

    def test_category_invalid(self):
        """Test invalid category raises error."""
        with pytest.raises(ValueError):
            PluginCategory("invalid_category")
