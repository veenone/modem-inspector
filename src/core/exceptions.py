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
