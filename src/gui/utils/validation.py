"""Input validation utilities for GUI forms.

Provides validation functions for user inputs in GUI settings and configuration.
All validation functions return (is_valid: bool, error_message: str) tuples.
"""

from pathlib import Path
from typing import Tuple


def validate_baud_rate(value: str) -> Tuple[bool, str]:
    """Validate baud rate input.

    Args:
        value: Baud rate as string from user input

    Returns:
        Tuple of (is_valid, error_message)
        - (True, "") if valid
        - (False, error_message) if invalid

    Valid Range: 300 to 921600 bps

    Example:
        >>> is_valid, error = validate_baud_rate("115200")
        >>> assert is_valid and error == ""
        >>> is_valid, error = validate_baud_rate("999999")
        >>> assert not is_valid
    """
    try:
        baud = int(value)
    except ValueError:
        return False, "Baud rate must be a number"

    if baud < 300:
        return False, "Baud rate must be at least 300"
    if baud > 921600:
        return False, "Baud rate must not exceed 921600"

    # Check if it's a standard baud rate
    standard_rates = [300, 1200, 2400, 4800, 9600, 19200, 38400,
                     57600, 115200, 230400, 460800, 921600]
    if baud not in standard_rates:
        # Warning but still valid
        return True, f"Warning: {baud} is not a standard baud rate"

    return True, ""


def validate_timeout(value: str) -> Tuple[bool, str]:
    """Validate timeout input.

    Args:
        value: Timeout in seconds as string from user input

    Returns:
        Tuple of (is_valid, error_message)

    Valid Range: 1 to 600 seconds (10 minutes)

    Example:
        >>> is_valid, error = validate_timeout("30")
        >>> assert is_valid
        >>> is_valid, error = validate_timeout("700")
        >>> assert not is_valid
    """
    try:
        timeout = float(value)
    except ValueError:
        return False, "Timeout must be a number"

    if timeout < 1:
        return False, "Timeout must be at least 1 second"
    if timeout > 600:
        return False, "Timeout must not exceed 600 seconds (10 minutes)"

    return True, ""


def validate_retry_count(value: str) -> Tuple[bool, str]:
    """Validate retry count input.

    Args:
        value: Retry count as string from user input

    Returns:
        Tuple of (is_valid, error_message)

    Valid Range: 0 to 10 retries

    Example:
        >>> is_valid, error = validate_retry_count("3")
        >>> assert is_valid
    """
    try:
        retries = int(value)
    except ValueError:
        return False, "Retry count must be a whole number"

    if retries < 0:
        return False, "Retry count cannot be negative"
    if retries > 10:
        return False, "Retry count must not exceed 10"

    return True, ""


def validate_retry_delay(value: str) -> Tuple[bool, str]:
    """Validate retry delay input.

    Args:
        value: Retry delay in milliseconds as string

    Returns:
        Tuple of (is_valid, error_message)

    Valid Range: 100 to 10000 milliseconds (0.1 to 10 seconds)

    Example:
        >>> is_valid, error = validate_retry_delay("1000")
        >>> assert is_valid
    """
    try:
        delay = int(value)
    except ValueError:
        return False, "Retry delay must be a number"

    if delay < 100:
        return False, "Retry delay must be at least 100ms"
    if delay > 10000:
        return False, "Retry delay must not exceed 10000ms (10 seconds)"

    return True, ""


def validate_port_path(value: str) -> Tuple[bool, str]:
    """Validate serial port path.

    Args:
        value: Port path from user selection

    Returns:
        Tuple of (is_valid, error_message)

    Accepts: Windows (COM1-COM256), Linux/Mac (/dev/tty*)

    Example:
        >>> is_valid, error = validate_port_path("COM3")
        >>> assert is_valid
        >>> is_valid, error = validate_port_path("/dev/ttyUSB0")
        >>> assert is_valid
    """
    if not value or not value.strip():
        return False, "Port path cannot be empty"

    value = value.strip()

    # Windows COM ports
    if value.upper().startswith("COM"):
        try:
            port_num = int(value[3:])
            if 1 <= port_num <= 256:
                return True, ""
            else:
                return False, "COM port number must be between 1 and 256"
        except ValueError:
            return False, "Invalid COM port format (expected COM1, COM2, etc.)"

    # Linux/Mac /dev/tty* ports
    if value.startswith("/dev/tty"):
        return True, ""

    return False, "Port path must be COMx (Windows) or /dev/tty* (Linux/Mac)"


def validate_directory_path(value: str) -> Tuple[bool, str]:
    """Validate directory path for reports/logs.

    Args:
        value: Directory path from user input

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> is_valid, error = validate_directory_path("./reports")
        >>> # Result depends on if directory exists/is writable
    """
    if not value or not value.strip():
        return False, "Directory path cannot be empty"

    value = value.strip()

    try:
        path = Path(value)

        # Check if path exists
        if not path.exists():
            return True, f"Warning: Directory '{value}' does not exist (will be created)"

        # Check if it's actually a directory
        if not path.is_dir():
            return False, f"Path '{value}' exists but is not a directory"

        # Check if writable (try to create a temp file)
        try:
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True, ""
        except (PermissionError, OSError):
            return False, f"Directory '{value}' is not writable"

    except Exception as e:
        return False, f"Invalid path: {e}"


def validate_positive_integer(value: str, min_val: int = 1, max_val: int = None) -> Tuple[bool, str]:
    """Validate generic positive integer input.

    Args:
        value: Number as string
        min_val: Minimum allowed value (default 1)
        max_val: Maximum allowed value (optional)

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> is_valid, error = validate_positive_integer("5", min_val=1, max_val=10)
        >>> assert is_valid
    """
    try:
        num = int(value)
    except ValueError:
        return False, "Value must be a whole number"

    if num < min_val:
        return False, f"Value must be at least {min_val}"

    if max_val is not None and num > max_val:
        return False, f"Value must not exceed {max_val}"

    return True, ""
