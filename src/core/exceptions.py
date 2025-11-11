"""Custom exception hierarchy for Modem Inspector.

This module defines all custom exceptions used throughout the AT Command Engine,
providing structured error handling with relevant context for debugging.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.command_response import CommandResponse


class ModemInspectorError(Exception):
    """Base exception for all modem inspector errors.

    All custom exceptions inherit from this base class to allow
    catching all tool-specific errors with a single except clause.
    """
    pass


class SerialPortError(ModemInspectorError):
    """Serial port communication error.

    Raised when serial port operations fail (open, read, write).
    Captures port identifier and underlying OS error for diagnostics.

    Attributes:
        port: Serial port identifier (e.g., '/dev/ttyUSB0', 'COM3')
        os_error: Original exception from pyserial or OS (if available)
    """

    def __init__(self, message: str, port: str, os_error: Optional[Exception] = None):
        """Initialize SerialPortError.

        Args:
            message: Human-readable error description
            port: Serial port identifier
            os_error: Original exception from pyserial/OS
        """
        super().__init__(message)
        self.port = port
        self.os_error = os_error

    def __str__(self) -> str:
        """Format error message with port context."""
        base_msg = super().__str__()
        if self.os_error:
            return f"{base_msg} (port: {self.port}, cause: {self.os_error})"
        return f"{base_msg} (port: {self.port})"


class SerialPortBusyError(SerialPortError):
    """Port is already in use by another process.

    Raised when attempting to open a serial port that is already
    in use by another application or process instance.
    """
    pass


class ConnectionTimeoutError(SerialPortError):
    """Connection attempt timed out.

    Raised when serial port connection cannot be established
    within the configured timeout period.
    """
    pass


class ATCommandError(ModemInspectorError):
    """AT command execution error.

    Raised when an AT command fails (ERROR response or invalid format).
    Captures the command and response for analysis.

    Attributes:
        command: AT command string that failed
        response: CommandResponse object with error details
    """

    def __init__(self, message: str, command: str, response: 'CommandResponse'):
        """Initialize ATCommandError.

        Args:
            message: Human-readable error description
            command: AT command string that failed
            response: CommandResponse with error details
        """
        super().__init__(message)
        self.command = command
        self.response = response

    def __str__(self) -> str:
        """Format error message with command context."""
        base_msg = super().__str__()
        return f"{base_msg} (command: {self.command}, status: {self.response.status.value})"


class BufferOverflowError(SerialPortError):
    """Serial buffer overflow detected.

    Raised when the serial port buffer overflows due to excessive
    data or slow reading. This typically indicates the modem is
    sending data faster than it can be processed.
    """
    pass


class PluginError(ModemInspectorError):
    """Base exception for plugin system errors.

    All plugin-related exceptions inherit from this base class.
    """
    pass


class PluginValidationError(PluginError):
    """Plugin fails schema or semantic validation.

    Raised when a plugin YAML file fails validation checks.

    Attributes:
        file_path: Path to the invalid plugin file
        errors: List of validation error messages
    """

    def __init__(self, message: str, file_path: str, errors: Optional[list] = None):
        """Initialize PluginValidationError.

        Args:
            message: Human-readable error description
            file_path: Path to invalid plugin file
            errors: List of specific validation errors
        """
        super().__init__(message)
        self.file_path = file_path
        self.errors = errors or []

    def __str__(self) -> str:
        """Format error message with file path and errors."""
        base_msg = super().__str__()
        error_list = '\n  - '.join(self.errors) if self.errors else 'No details'
        return f"{base_msg} (file: {self.file_path})\nErrors:\n  - {error_list}"


class PluginNotFoundError(PluginError):
    """Requested plugin does not exist.

    Raised when attempting to load a plugin that cannot be found.

    Attributes:
        vendor: Requested vendor name
        model: Requested model name
        available: List of available plugin identifiers
    """

    def __init__(self, vendor: str, model: str, available: Optional[list] = None):
        """Initialize PluginNotFoundError.

        Args:
            vendor: Requested vendor name
            model: Requested model name
            available: List of available plugin names
        """
        super().__init__(f"Plugin not found: {vendor}.{model}")
        self.vendor = vendor
        self.model = model
        self.available = available or []

    def __str__(self) -> str:
        """Format error message with suggestions."""
        base_msg = super().__str__()
        if self.available:
            suggestions = ', '.join(self.available[:5])
            return f"{base_msg}\nAvailable plugins: {suggestions}..."
        return base_msg


class ParserError(PluginError):
    """Parser execution failed.

    Raised when a plugin parser fails to process a response.

    Attributes:
        parser_name: Name of the parser that failed
        parser_type: Type of parser (regex, json, custom)
        response: Original response that failed to parse
    """

    def __init__(self, message: str, parser_name: str, parser_type: str,
                 response: Optional[str] = None):
        """Initialize ParserError.

        Args:
            message: Human-readable error description
            parser_name: Name of the parser that failed
            parser_type: Type of parser
            response: Response that failed to parse (optional)
        """
        super().__init__(message)
        self.parser_name = parser_name
        self.parser_type = parser_type
        self.response = response

    def __str__(self) -> str:
        """Format error message with parser details."""
        base_msg = super().__str__()
        return f"{base_msg} (parser: {self.parser_name}, type: {self.parser_type})"
