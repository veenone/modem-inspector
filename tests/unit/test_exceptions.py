"""Unit tests for custom exception hierarchy.

Tests all custom exceptions including:
- Inheritance hierarchy
- Custom attributes
- String formatting
- Context preservation
"""

import pytest
from src.core.exceptions import (
    ModemInspectorError,
    SerialPortError,
    SerialPortBusyError,
    ConnectionTimeoutError,
    ATCommandError,
    BufferOverflowError,
    PluginError,
    PluginValidationError,
    PluginNotFoundError,
    ParserError
)
from src.core.command_response import CommandResponse, ResponseStatus


class TestModemInspectorError:
    """Test base exception class."""

    def test_is_exception(self):
        """Test ModemInspectorError inherits from Exception."""
        assert issubclass(ModemInspectorError, Exception)

    def test_raise_and_catch(self):
        """Test raising and catching base exception."""
        with pytest.raises(ModemInspectorError):
            raise ModemInspectorError("Test error")

    def test_message(self):
        """Test error message is preserved."""
        error = ModemInspectorError("Custom message")
        assert str(error) == "Custom message"


class TestSerialPortError:
    """Test SerialPortError and its subclasses."""

    def test_inherits_from_base(self):
        """Test SerialPortError inherits from ModemInspectorError."""
        assert issubclass(SerialPortError, ModemInspectorError)

    def test_create_with_port(self):
        """Test creating error with port info."""
        error = SerialPortError("Port not found", port="/dev/ttyUSB0")

        assert error.port == "/dev/ttyUSB0"
        assert error.os_error is None
        assert "Port not found" in str(error)
        assert "/dev/ttyUSB0" in str(error)

    def test_create_with_os_error(self):
        """Test creating error with underlying OS error."""
        os_error = PermissionError("Access denied")
        error = SerialPortError(
            "Cannot open port",
            port="COM3",
            os_error=os_error
        )

        assert error.port == "COM3"
        assert error.os_error == os_error
        assert "Cannot open port" in str(error)
        assert "COM3" in str(error)
        assert "Access denied" in str(error)

    def test_str_without_os_error(self):
        """Test string formatting without OS error."""
        error = SerialPortError("Connection failed", port="/dev/ttyACM0")
        result = str(error)

        assert result == "Connection failed (port: /dev/ttyACM0)"

    def test_str_with_os_error(self):
        """Test string formatting with OS error."""
        os_error = IOError("Device not ready")
        error = SerialPortError("Read failed", port="COM5", os_error=os_error)
        result = str(error)

        assert "Read failed" in result
        assert "COM5" in result
        assert "Device not ready" in result

    def test_catch_as_base(self):
        """Test catching SerialPortError as ModemInspectorError."""
        with pytest.raises(ModemInspectorError):
            raise SerialPortError("Test", port="COM1")


class TestSerialPortBusyError:
    """Test SerialPortBusyError."""

    def test_inherits_from_serial_port_error(self):
        """Test inheritance hierarchy."""
        assert issubclass(SerialPortBusyError, SerialPortError)
        assert issubclass(SerialPortBusyError, ModemInspectorError)

    def test_create_and_catch(self):
        """Test creating and catching port busy error."""
        with pytest.raises(SerialPortBusyError):
            raise SerialPortBusyError("Port in use", port="COM3")

    def test_attributes_inherited(self):
        """Test port and os_error attributes inherited from parent."""
        error = SerialPortBusyError("Busy", port="/dev/ttyUSB0")
        assert error.port == "/dev/ttyUSB0"


class TestConnectionTimeoutError:
    """Test ConnectionTimeoutError."""

    def test_inherits_from_serial_port_error(self):
        """Test inheritance hierarchy."""
        assert issubclass(ConnectionTimeoutError, SerialPortError)

    def test_create_and_format(self):
        """Test creating and formatting timeout error."""
        error = ConnectionTimeoutError("Timeout after 5s", port="COM1")

        assert "Timeout after 5s" in str(error)
        assert "COM1" in str(error)


class TestBufferOverflowError:
    """Test BufferOverflowError."""

    def test_inherits_from_serial_port_error(self):
        """Test inheritance hierarchy."""
        assert issubclass(BufferOverflowError, SerialPortError)

    def test_create_and_catch(self):
        """Test creating and catching overflow error."""
        with pytest.raises(BufferOverflowError):
            raise BufferOverflowError("Buffer full", port="/dev/ttyUSB1")


class TestATCommandError:
    """Test ATCommandError."""

    def test_inherits_from_base(self):
        """Test ATCommandError inherits from ModemInspectorError."""
        assert issubclass(ATCommandError, ModemInspectorError)

    def test_create_with_response(self):
        """Test creating error with CommandResponse."""
        response = CommandResponse(
            command="AT+INVALID",
            raw_response=["ERROR"],
            status=ResponseStatus.ERROR,
            execution_time=0.05
        )

        error = ATCommandError(
            "Command failed",
            command="AT+INVALID",
            response=response
        )

        assert error.command == "AT+INVALID"
        assert error.response == response
        assert error.response.status == ResponseStatus.ERROR

    def test_str_formatting(self):
        """Test string formatting with command context."""
        response = CommandResponse(
            command="AT+CEREG?",
            raw_response=["+CME ERROR: 30"],
            status=ResponseStatus.ERROR,
            execution_time=0.05
        )

        error = ATCommandError("Network error", command="AT+CEREG?", response=response)
        result = str(error)

        assert "Network error" in result
        assert "AT+CEREG?" in result
        assert "error" in result.lower()

    def test_catch_as_base(self):
        """Test catching as ModemInspectorError."""
        response = CommandResponse(
            command="AT",
            raw_response=["ERROR"],
            status=ResponseStatus.ERROR,
            execution_time=0.05
        )

        with pytest.raises(ModemInspectorError):
            raise ATCommandError("Test", command="AT", response=response)


class TestPluginError:
    """Test PluginError base class."""

    def test_inherits_from_base(self):
        """Test PluginError inherits from ModemInspectorError."""
        assert issubclass(PluginError, ModemInspectorError)

    def test_create_and_catch(self):
        """Test creating and catching plugin error."""
        with pytest.raises(PluginError):
            raise PluginError("Plugin problem")


class TestPluginValidationError:
    """Test PluginValidationError."""

    def test_inherits_from_plugin_error(self):
        """Test inheritance hierarchy."""
        assert issubclass(PluginValidationError, PluginError)
        assert issubclass(PluginValidationError, ModemInspectorError)

    def test_create_without_errors(self):
        """Test creating validation error without error list."""
        error = PluginValidationError(
            "Invalid plugin",
            file_path="/path/to/plugin.yaml"
        )

        assert error.file_path == "/path/to/plugin.yaml"
        assert error.errors == []

    def test_create_with_errors(self):
        """Test creating validation error with error list."""
        errors = [
            "Missing required field: metadata.vendor",
            "Invalid command format: line 23"
        ]

        error = PluginValidationError(
            "Validation failed",
            file_path="/plugins/bad.yaml",
            errors=errors
        )

        assert error.file_path == "/plugins/bad.yaml"
        assert error.errors == errors
        assert len(error.errors) == 2

    def test_str_without_errors(self):
        """Test string formatting without error list."""
        error = PluginValidationError(
            "Invalid schema",
            file_path="/plugin.yaml"
        )

        result = str(error)
        assert "Invalid schema" in result
        assert "/plugin.yaml" in result
        assert "No details" in result

    def test_str_with_errors(self):
        """Test string formatting with error list."""
        errors = [
            "Error 1",
            "Error 2",
            "Error 3"
        ]

        error = PluginValidationError(
            "Validation failed",
            file_path="/bad.yaml",
            errors=errors
        )

        result = str(error)
        assert "Validation failed" in result
        assert "/bad.yaml" in result
        assert "Error 1" in result
        assert "Error 2" in result
        assert "Error 3" in result


class TestPluginNotFoundError:
    """Test PluginNotFoundError."""

    def test_inherits_from_plugin_error(self):
        """Test inheritance hierarchy."""
        assert issubclass(PluginNotFoundError, PluginError)

    def test_create_without_available(self):
        """Test creating error without available plugin list."""
        error = PluginNotFoundError(
            vendor="unknown",
            model="modem"
        )

        assert error.vendor == "unknown"
        assert error.model == "modem"
        assert error.available == []

    def test_create_with_available(self):
        """Test creating error with available plugins."""
        available = ["quectel.ec200u", "nordic.nrf9160", "simcom.sim7600"]

        error = PluginNotFoundError(
            vendor="acme",
            model="roadrunner",
            available=available
        )

        assert error.vendor == "acme"
        assert error.model == "roadrunner"
        assert error.available == available

    def test_str_without_suggestions(self):
        """Test string formatting without suggestions."""
        error = PluginNotFoundError(vendor="test", model="device")
        result = str(error)

        assert "test.device" in result
        assert "not found" in result.lower()

    def test_str_with_suggestions(self):
        """Test string formatting with suggestions."""
        available = [
            "quectel.ec200u",
            "quectel.ec25",
            "nordic.nrf9160",
            "simcom.sim7600",
            "ublox.sara"
        ]

        error = PluginNotFoundError(
            vendor="acme",
            model="modem",
            available=available
        )

        result = str(error)
        assert "acme.modem" in result
        assert "Available plugins" in result
        assert "quectel.ec200u" in result

    def test_str_limits_suggestions(self):
        """Test suggestions limited to 5 items."""
        available = [f"vendor.model{i}" for i in range(20)]

        error = PluginNotFoundError(
            vendor="test",
            model="device",
            available=available
        )

        result = str(error)
        # Should only show first 5
        assert "vendor.model0" in result
        assert "vendor.model4" in result
        assert "..." in result  # Indicates more available


class TestParserError:
    """Test ParserError."""

    def test_inherits_from_plugin_error(self):
        """Test inheritance hierarchy."""
        assert issubclass(ParserError, PluginError)

    def test_create_without_response(self):
        """Test creating parser error without response."""
        error = ParserError(
            "Parse failed",
            parser_name="signal_parser",
            parser_type="regex"
        )

        assert error.parser_name == "signal_parser"
        assert error.parser_type == "regex"
        assert error.response is None

    def test_create_with_response(self):
        """Test creating parser error with response."""
        error = ParserError(
            "Pattern mismatch",
            parser_name="csq_parser",
            parser_type="regex",
            response="+CSQ: invalid"
        )

        assert error.parser_name == "csq_parser"
        assert error.parser_type == "regex"
        assert error.response == "+CSQ: invalid"

    def test_str_formatting(self):
        """Test string formatting."""
        error = ParserError(
            "Extraction failed",
            parser_name="imei_parser",
            parser_type="regex"
        )

        result = str(error)
        assert "Extraction failed" in result
        assert "imei_parser" in result
        assert "regex" in result


class TestExceptionHierarchy:
    """Test overall exception hierarchy."""

    def test_all_inherit_from_base(self):
        """Test all custom exceptions inherit from ModemInspectorError."""
        all_exceptions = [
            SerialPortError,
            SerialPortBusyError,
            ConnectionTimeoutError,
            ATCommandError,
            BufferOverflowError,
            PluginError,
            PluginValidationError,
            PluginNotFoundError,
            ParserError
        ]

        for exc_class in all_exceptions:
            assert issubclass(exc_class, ModemInspectorError)
            assert issubclass(exc_class, Exception)

    def test_catch_all_with_base(self):
        """Test catching all custom exceptions with base class."""
        all_exceptions = [
            SerialPortError("test", port="COM1"),
            ATCommandError("test", command="AT", response=CommandResponse(
                command="AT",
                raw_response=[],
                status=ResponseStatus.ERROR,
                execution_time=0.05
            )),
            PluginValidationError("test", file_path="/path"),
            ParserError("test", parser_name="p", parser_type="t")
        ]

        for error in all_exceptions:
            with pytest.raises(ModemInspectorError):
                raise error

    def test_specific_catch_still_works(self):
        """Test specific exception catching still works."""
        with pytest.raises(SerialPortBusyError):
            raise SerialPortBusyError("Busy", port="COM1")

        # Should not catch different exception type
        with pytest.raises(ATCommandError):
            response = CommandResponse(
                command="AT",
                raw_response=[],
                status=ResponseStatus.ERROR,
                execution_time=0.05
            )
            raise ATCommandError("Error", command="AT", response=response)
