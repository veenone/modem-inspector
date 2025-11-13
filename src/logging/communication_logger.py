"""Communication logger for AT command logging.

This module provides the CommunicationLogger class, a central coordinator
for logging AT command communications. Manages multiple output destinations
(file, console, in-memory buffer) with log level filtering and convenience
methods for common logging operations.
"""

from datetime import datetime
from collections import deque
from threading import Lock
from typing import Optional, List, Dict, Any
import sys

from src.logging.log_models import LogEntry
from src.logging.file_handler import FileHandler
from src.config.config_models import LogLevel


class CommunicationLogger:
    """Central coordinator for communication logging.

    Manages logging of AT command communications to multiple destinations:
    file (with rotation), console (stderr), and in-memory buffer (for GUI).
    Provides log level filtering and convenience methods for common operations.

    Attributes:
        log_level: Current log level (DEBUG, INFO, WARNING, ERROR)
        enable_file: Whether file logging is enabled
        enable_console: Whether console logging is enabled
        log_file_path: Path to log file (if file logging enabled)

    Example:
        >>> logger = CommunicationLogger(
        ...     log_level=LogLevel.INFO,
        ...     enable_file=True,
        ...     enable_console=True,
        ...     log_file_path="~/.modem-inspector/logs/comm.log"
        ... )
        >>> logger.log_command(port="COM3", command="AT+CGMI")
        >>> logger.log_response(port="COM3", response="Quectel", status="SUCCESS", execution_time=0.123)
        >>> logger.close()
    """

    # Log level priorities for filtering
    _LEVEL_PRIORITY = {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 2,
        "ERROR": 3
    }

    def __init__(
        self,
        log_level: LogLevel = LogLevel.INFO,
        enable_file: bool = False,
        enable_console: bool = True,
        log_file_path: Optional[str] = None,
        max_file_size_mb: int = 10,
        backup_count: int = 5
    ):
        """Initialize CommunicationLogger with output destinations and log level.

        Args:
            log_level: Log level for filtering (default: INFO)
            enable_file: Enable file logging (default: False)
            enable_console: Enable console logging to stderr (default: True)
            log_file_path: Path to log file (required if enable_file=True)
            max_file_size_mb: Maximum file size before rotation (default: 10)
            backup_count: Number of backup files to keep (default: 5)

        Raises:
            ValueError: If enable_file=True but log_file_path is None
        """
        self.log_level = log_level.value if isinstance(log_level, LogLevel) else log_level
        self.enable_file = enable_file
        self.enable_console = enable_console
        self.log_file_path = log_file_path

        # Thread safety
        self._lock = Lock()

        # In-memory buffer for GUI (last 1000 entries)
        self._buffer: deque = deque(maxlen=1000)

        # File handler (if file logging enabled)
        self._file_handler: Optional[FileHandler] = None
        if self.enable_file:
            if not log_file_path:
                raise ValueError("log_file_path required when enable_file=True")
            try:
                self._file_handler = FileHandler(
                    log_file_path=log_file_path,
                    max_size_mb=max_file_size_mb,
                    backup_count=backup_count
                )
            except OSError as e:
                print(f"WARNING: Failed to initialize file logging: {e}", file=sys.stderr)
                self._file_handler = None

    def log(self, entry: LogEntry) -> None:
        """Log an entry to all enabled destinations with level filtering.

        Filters based on current log level, then writes to file (if enabled),
        console (if enabled), and in-memory buffer for GUI.

        Args:
            entry: LogEntry to log

        Example:
            >>> entry = LogEntry(
            ...     timestamp=datetime.now(),
            ...     level="INFO",
            ...     source="ATExecutor",
            ...     message="Command executed"
            ... )
            >>> logger.log(entry)
        """
        # Filter by log level
        if not self._should_log(entry.level):
            return

        with self._lock:
            # Add to in-memory buffer for GUI
            self._buffer.append(entry)

            # Write to file if enabled
            if self._file_handler:
                self._file_handler.write(entry)

            # Write to console if enabled
            if self.enable_console:
                self._write_to_console(entry)

    def _should_log(self, entry_level: str) -> bool:
        """Check if entry should be logged based on current log level.

        Args:
            entry_level: Log level of the entry (DEBUG, INFO, WARNING, ERROR)

        Returns:
            True if entry_level >= current log_level, False otherwise
        """
        entry_priority = self._LEVEL_PRIORITY.get(entry_level, 0)
        current_priority = self._LEVEL_PRIORITY.get(self.log_level, 0)
        return entry_priority >= current_priority

    def _write_to_console(self, entry: LogEntry) -> None:
        """Write log entry to console (stderr).

        Args:
            entry: LogEntry to write
        """
        try:
            print(entry.to_string(), file=sys.stderr)
        except Exception as e:
            # Silently fail console writes to avoid cascading errors
            pass

    def log_command(self, port: str, command: str) -> None:
        """Log AT command sent to modem (convenience method).

        Args:
            port: Serial port name (e.g., "COM3")
            command: AT command sent (e.g., "AT+CGMI")

        Example:
            >>> logger.log_command(port="COM3", command="AT+CGMI")
        """
        entry = LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            source="ATExecutor",
            message=f"Sending command",
            port=port,
            command=command
        )
        self.log(entry)

    def log_response(
        self,
        port: str,
        response: str,
        status: str,
        execution_time: float,
        retry_count: int = 0,
        command: Optional[str] = None
    ) -> None:
        """Log response received from modem (convenience method).

        Args:
            port: Serial port name (e.g., "COM3")
            response: Response text received
            status: Response status (SUCCESS, ERROR, TIMEOUT)
            execution_time: Command execution time in seconds
            retry_count: Number of retry attempts (default: 0)
            command: Original command (optional)

        Example:
            >>> logger.log_response(
            ...     port="COM3",
            ...     response="Quectel",
            ...     status="SUCCESS",
            ...     execution_time=0.123,
            ...     command="AT+CGMI"
            ... )
        """
        # Determine log level based on status
        if status == "SUCCESS":
            level = "INFO"
        elif status == "TIMEOUT":
            level = "WARNING"
        else:
            level = "ERROR"

        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            source="ATExecutor",
            message=f"Received response",
            port=port,
            command=command,
            response=response,
            status=status,
            execution_time=execution_time,
            retry_count=retry_count
        )
        self.log(entry)

    def log_port_event(
        self,
        event: str,
        port: str,
        details: Optional[Dict[str, Any]] = None,
        level: str = "INFO"
    ) -> None:
        """Log serial port event (convenience method).

        Args:
            event: Event description (e.g., "Port opened", "Port closed")
            port: Serial port name
            details: Additional event details (optional)
            level: Log level (default: INFO)

        Example:
            >>> logger.log_port_event(
            ...     event="Port opened",
            ...     port="COM3",
            ...     details={"baud": 115200, "timeout": 30}
            ... )
        """
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            source="SerialHandler",
            message=event,
            port=port,
            details=details
        )
        self.log(entry)

    def log_error(
        self,
        source: str,
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log error event (convenience method).

        Args:
            source: Component name where error occurred
            error: Error message
            details: Additional error details (optional)

        Example:
            >>> logger.log_error(
            ...     source="SerialHandler",
            ...     error="Failed to open port",
            ...     details={"port": "COM3", "exception": "PermissionError"}
            ... )
        """
        entry = LogEntry(
            timestamp=datetime.now(),
            level="ERROR",
            source=source,
            message="Error occurred",
            error=error,
            details=details
        )
        self.log(entry)

    def set_level(self, level: LogLevel) -> None:
        """Change log level dynamically.

        Args:
            level: New log level (DEBUG, INFO, WARNING, ERROR)

        Example:
            >>> logger.set_level(LogLevel.DEBUG)
        """
        self.log_level = level.value if isinstance(level, LogLevel) else level

    def get_entries(self, limit: Optional[int] = None) -> List[LogEntry]:
        """Get log entries from in-memory buffer for GUI.

        Args:
            limit: Maximum number of entries to return (default: all)

        Returns:
            List of LogEntry objects (most recent first)

        Example:
            >>> entries = logger.get_entries(limit=100)
            >>> for entry in entries:
            ...     print(entry.to_string())
        """
        with self._lock:
            entries = list(self._buffer)
            if limit:
                entries = entries[-limit:]
            return entries

    def clear_buffer(self) -> None:
        """Clear in-memory buffer (for GUI "Clear Log" button).

        Does not affect file logs - only clears the GUI display buffer.

        Example:
            >>> logger.clear_buffer()
        """
        with self._lock:
            self._buffer.clear()

    def flush(self) -> None:
        """Flush all buffered writes to disk.

        Forces immediate write of file handler buffers.
        """
        if self._file_handler:
            self._file_handler.flush()

    def close(self) -> None:
        """Close all handlers and flush buffers.

        Call this when shutting down the application to ensure all logs
        are written to disk.

        Example:
            >>> logger.close()
        """
        if self._file_handler:
            self._file_handler.close()
            self._file_handler = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures logger is closed."""
        self.close()
        return False
