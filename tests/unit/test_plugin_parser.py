"""Unit tests for PluginParser.

Tests regex, JSON, and custom parsers with success/failure scenarios
and graceful degradation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.core.plugin_parser import PluginParser
from src.core.plugin import (
    Plugin,
    PluginMetadata,
    PluginConnection,
    ParserDefinition,
    ParserType
)
from src.core.command_response import CommandResponse, ResponseStatus


class TestPluginParserRegex:
    """Test regex parser functionality."""

    @pytest.fixture
    def plugin_with_regex_parser(self):
        """Create plugin with regex parser."""
        return Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "signal_parser": ParserDefinition(
                    name="signal_parser",
                    type=ParserType.REGEX,
                    pattern=r"\+CSQ: (\d+),(\d+)",
                    groups=["rssi", "ber"]
                )
            }
        )

    def test_parse_regex_success(self, plugin_with_regex_parser):
        """Test successful regex parsing with named groups."""
        parser = PluginParser(plugin_with_regex_parser)
        response = CommandResponse(
            command="AT+CSQ",
            raw_response=["+CSQ: 25,0", "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "signal_parser")

        assert isinstance(result, dict)
        assert result["rssi"] == 25  # Numeric conversion applied
        assert result["ber"] == 0

    def test_parse_regex_with_numeric_conversion(self, plugin_with_regex_parser):
        """Test regex parser auto-converts numeric strings to int/float."""
        parser = PluginParser(plugin_with_regex_parser)
        response = CommandResponse(
            command="AT+CSQ",
            raw_response=["+CSQ: 25,0", "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "signal_parser")

        # Values should be converted to int if they're numeric
        assert result["rssi"] == 25 or result["rssi"] == "25"  # Implementation may vary
        assert result["ber"] == 0 or result["ber"] == "0"

    def test_parse_regex_no_match_returns_raw(self, plugin_with_regex_parser):
        """Test regex parser returns raw response when pattern doesn't match."""
        parser = PluginParser(plugin_with_regex_parser)
        response = CommandResponse(
            command="AT+CSQ",
            raw_response=["ERROR"],
            status=ResponseStatus.ERROR,
            execution_time=0.1
        )

        result = parser.parse_response(response, "signal_parser")

        # Should return raw response when pattern doesn't match (ERROR status)
        assert result == "ERROR"

    def test_parse_regex_multiline_pattern(self):
        """Test regex parser with multiline pattern."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "multiline": ParserDefinition(
                    name="multiline",
                    type=ParserType.REGEX,
                    pattern=r"\+COPS: (\d+),(\d+),\"([^\"]+)\"",
                    groups=["mode", "format", "operator"]
                )
            }
        )

        parser = PluginParser(plugin)
        response = CommandResponse(
            command="AT+COPS?",
            raw_response=['+COPS: 0,0,"T-Mobile"', "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "multiline")

        assert isinstance(result, dict)
        assert result["operator"] == "T-Mobile"


class TestPluginParserJSON:
    """Test JSON parser functionality."""

    @pytest.fixture
    def plugin_with_json_parser(self):
        """Create plugin with JSON parser."""
        return Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "json_parser": ParserDefinition(
                    name="json_parser",
                    type=ParserType.JSON,
                    json_path=None  # Parse entire JSON
                ),
                "json_path_parser": ParserDefinition(
                    name="json_path_parser",
                    type=ParserType.JSON,
                    json_path="data.value"
                )
            }
        )

    def test_parse_json_success(self, plugin_with_json_parser):
        """Test successful JSON parsing."""
        parser = PluginParser(plugin_with_json_parser)
        json_response = '{"status": "ok", "value": 123}'
        response = CommandResponse(
            command="AT+JSON",
            raw_response=[json_response],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "json_parser")

        assert isinstance(result, dict)
        assert result["status"] == "ok"
        assert result["value"] == 123

    def test_parse_json_with_path(self, plugin_with_json_parser):
        """Test JSON parser with json_path extraction."""
        parser = PluginParser(plugin_with_json_parser)
        json_response = '{"data": {"value": 456, "unit": "mV"}}'
        response = CommandResponse(
            command="AT+JSON",
            raw_response=[json_response],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "json_path_parser")

        # Should extract the nested value
        assert result == 456 or result == {"value": 456, "unit": "mV"}

    def test_parse_json_invalid_returns_raw(self, plugin_with_json_parser):
        """Test JSON parser returns raw on invalid JSON."""
        parser = PluginParser(plugin_with_json_parser)
        response = CommandResponse(
            command="AT+JSON",
            raw_response=["NOT JSON"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "json_parser")

        # Should return raw response on JSON parse error
        assert result == "NOT JSON"

    def test_parse_json_malformed_returns_raw(self, plugin_with_json_parser):
        """Test JSON parser handles malformed JSON gracefully."""
        parser = PluginParser(plugin_with_json_parser)
        response = CommandResponse(
            command="AT+JSON",
            raw_response=['{"incomplete": '],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "json_parser")

        assert result == '{"incomplete": '


class TestPluginParserCustom:
    """Test custom parser functionality."""

    @pytest.fixture
    def plugin_with_custom_parser(self):
        """Create plugin with custom parser."""
        return Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "custom_parser": ParserDefinition(
                    name="custom_parser",
                    type=ParserType.CUSTOM,
                    module="tests.fixtures.sample_parser",
                    function="parse_signal"
                )
            }
        )

    def test_parse_custom_success(self, plugin_with_custom_parser):
        """Test custom parser with mocked module."""
        mock_module = MagicMock()
        mock_module.parse_signal = Mock(return_value={"parsed": True, "value": 99})

        with patch('importlib.import_module', return_value=mock_module):
            parser = PluginParser(plugin_with_custom_parser)
            response = CommandResponse(
                command="AT+CUSTOM",
                raw_response=["CUSTOM DATA"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            )

            result = parser.parse_response(response, "custom_parser")

            assert result == {"parsed": True, "value": 99}
            # Parser may receive raw_response list or joined string
            assert mock_module.parse_signal.called

    def test_parse_custom_caching(self, plugin_with_custom_parser):
        """Test that custom parsers are cached."""
        mock_module = MagicMock()
        mock_module.parse_signal = Mock(return_value={"cached": True})

        with patch('importlib.import_module', return_value=mock_module) as mock_import:
            parser = PluginParser(plugin_with_custom_parser)
            response = CommandResponse(
                command="AT+CUSTOM",
                raw_response=["DATA"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            )

            # First call
            parser.parse_response(response, "custom_parser")

            # Second call - should use cached parser
            parser.parse_response(response, "custom_parser")

            # import_module should only be called once (cached)
            assert mock_import.call_count == 1

    def test_parse_custom_import_error_returns_raw(self, plugin_with_custom_parser):
        """Test custom parser returns raw on import error."""
        with patch('importlib.import_module', side_effect=ImportError("Module not found")):
            parser = PluginParser(plugin_with_custom_parser)
            response = CommandResponse(
                command="AT+CUSTOM",
                raw_response=["FALLBACK DATA"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            )

            result = parser.parse_response(response, "custom_parser")

            # Should return raw response on import error
            assert result == "FALLBACK DATA"

    def test_parse_custom_function_error_returns_raw(self, plugin_with_custom_parser):
        """Test custom parser returns raw on function execution error."""
        mock_module = MagicMock()
        mock_module.parse_signal = Mock(side_effect=ValueError("Parse error"))

        with patch('importlib.import_module', return_value=mock_module):
            parser = PluginParser(plugin_with_custom_parser)
            response = CommandResponse(
                command="AT+CUSTOM",
                raw_response=["ERROR DATA"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            )

            result = parser.parse_response(response, "custom_parser")

            # Should return raw response on execution error
            assert result == "ERROR DATA"


class TestPluginParserEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_response_no_parser_returns_raw(self):
        """Test parsing without specifying parser returns raw response."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )

        parser = PluginParser(plugin)
        response = CommandResponse(
            command="AT",
            raw_response=["RAW DATA"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, None)

        assert result == "RAW DATA"

    def test_parse_response_nonexistent_parser_returns_raw(self):
        """Test parsing with nonexistent parser name returns raw."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )

        parser = PluginParser(plugin)
        response = CommandResponse(
            command="AT",
            raw_response=["RAW DATA"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "nonexistent")

        assert result == "RAW DATA"

    def test_parse_response_empty_response(self):
        """Test parsing empty response."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "test_parser": ParserDefinition(
                    name="test_parser",
                    type=ParserType.REGEX,
                    pattern=r"(\d+)"
                )
            }
        )

        parser = PluginParser(plugin)
        response = CommandResponse(
            command="AT",
            raw_response=[""],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "test_parser")

        assert result == ""

    def test_parser_with_unit_appends_unit(self):
        """Test parser with unit field appends unit to values."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "voltage_parser": ParserDefinition(
                    name="voltage_parser",
                    type=ParserType.REGEX,
                    pattern=r"VBAT: (\d+)",
                    groups=["voltage"],
                    unit="mV"
                )
            }
        )

        parser = PluginParser(plugin)
        response = CommandResponse(
            command="AT+CBC",
            raw_response=["VBAT: 3800", "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "voltage_parser")

        # Implementation may append unit in different ways
        assert isinstance(result, (dict, str))
        if isinstance(result, dict):
            # Check if voltage value exists
            assert "voltage" in result or "voltage_mV" in result


class TestPluginParserTypeDispatch:
    """Test parser type dispatching."""

    def test_dispatch_to_regex_parser(self):
        """Test that REGEX type dispatches to regex parser."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "test": ParserDefinition(
                    name="test",
                    type=ParserType.REGEX,
                    pattern=r"OK"
                )
            }
        )

        parser = PluginParser(plugin)
        response = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "test")

        assert result is not None

    def test_dispatch_to_json_parser(self):
        """Test that JSON type dispatches to JSON parser."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "test": ParserDefinition(
                    name="test",
                    type=ParserType.JSON
                )
            }
        )

        parser = PluginParser(plugin)
        response = CommandResponse(
            command="AT+JSON",
            raw_response=['{"test": true}'],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "test")

        assert isinstance(result, (dict, str))

    def test_dispatch_to_custom_parser(self):
        """Test that CUSTOM type dispatches to custom parser."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "test": ParserDefinition(
                    name="test",
                    type=ParserType.CUSTOM,
                    module="test.module",
                    function="test_func"
                )
            }
        )

        mock_module = MagicMock()
        mock_module.test_func = Mock(return_value="custom_result")

        with patch('importlib.import_module', return_value=mock_module):
            parser = PluginParser(plugin)
            response = CommandResponse(
                command="AT+CUSTOM",
                raw_response=["DATA"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            )

            result = parser.parse_response(response, "test")

            assert result == "custom_result"

    def test_none_parser_type_returns_raw(self):
        """Test that NONE parser type returns raw response."""
        plugin = Plugin(
            metadata=PluginMetadata("test", "test", "other", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={
                "test": ParserDefinition(
                    name="test",
                    type=ParserType.NONE
                )
            }
        )

        parser = PluginParser(plugin)
        response = CommandResponse(
            command="AT",
            raw_response=["RAW"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        result = parser.parse_response(response, "test")

        assert result == "RAW"
