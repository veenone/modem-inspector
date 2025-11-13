"""Log data models for communication logging.

This module defines immutable data structures for log entries, providing
structured representation of commands, responses, and serial port events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import json


@dataclass(frozen=True)
class LogEntry:
    """Immutable log entry for communication logging.

    Captures all information about a communication event (command, response,
    port event, error) with timestamp and structured data. Frozen dataclass
    ensures log entries cannot be modified after creation.

    Attributes:
        timestamp: When the event occurred (ISO 8601)
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        source: Component name (SerialHandler, ATExecutor, etc.)
        message: Human-readable message describing the event
        details: Additional structured data (arbitrary dict)
        port: Serial port name (optional)
        command: AT command sent (optional)
        response: Response received (optional)
        status: Response status (SUCCESS, ERROR, TIMEOUT) (optional)
        execution_time: Command execution time in seconds (optional)
        retry_count: Number of retry attempts (optional)
        error: Error message if applicable (optional)

    Example:
        >>> entry = LogEntry(
        ...     timestamp=datetime.now(),
        ...     level="INFO",
        ...     source="ATExecutor",
        ...     message="Command executed successfully",
        ...     port="COM3",
        ...     command="AT+CGMI",
        ...     response="Quectel",
        ...     status="SUCCESS",
        ...     execution_time=0.123
        ... )
        >>> entry.to_string()
        '2025-01-12 10:30:15.234 | INFO | ATExecutor | Command executed successfully'
    """

    timestamp: datetime
    level: str  # DEBUG, INFO, WARNING, ERROR
    source: str  # Component name
    message: str
    details: Optional[Dict[str, Any]] = None

    # Optional fields for command/response logging
    port: Optional[str] = None
    command: Optional[str] = None
    response: Optional[str] = None
    status: Optional[str] = None
    execution_time: Optional[float] = None
    retry_count: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for serialization.

        Returns:
            Dictionary with all fields, ISO format for timestamp

        Example:
            >>> entry.to_dict()
            {
                'timestamp': '2025-01-12T10:30:15.234567',
                'level': 'INFO',
                'source': 'ATExecutor',
                'message': 'Command executed successfully',
                'port': 'COM3',
                'command': 'AT+CGMI',
                'response': 'Quectel',
                'status': 'SUCCESS',
                'execution_time': 0.123,
                'retry_count': 0,
                'error': None,
                'details': None
            }
        """
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'source': self.source,
            'message': self.message,
            'details': self.details,
            'port': self.port,
            'command': self.command,
            'response': self.response,
            'status': self.status,
            'execution_time': self.execution_time,
            'retry_count': self.retry_count,
            'error': self.error
        }

    def to_string(self) -> str:
        """Format log entry as human-readable string.

        Returns:
            Formatted string: "YYYY-MM-DD HH:MM:SS.mmm | LEVEL | SOURCE | MESSAGE"

        Example:
            >>> entry.to_string()
            '2025-01-12 10:30:15.234 | INFO | ATExecutor | Command executed successfully'
        """
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        base = f"{timestamp_str} | {self.level:7} | {self.source:15} | {self.message}"

        # Add optional details for command/response logging
        if self.command:
            base += f" | CMD: {self.command}"
        if self.status:
            base += f" | STATUS: {self.status}"
        if self.execution_time is not None:
            base += f" | TIME: {self.execution_time:.3f}s"
        if self.retry_count is not None and self.retry_count > 0:
            base += f" | RETRIES: {self.retry_count}"
        if self.error:
            base += f" | ERROR: {self.error}"

        return base

    def to_json(self) -> str:
        """Convert log entry to JSON string.

        Returns:
            JSON string representation

        Example:
            >>> entry.to_json()
            '{"timestamp": "2025-01-12T10:30:15.234567", "level": "INFO", ...}'
        """
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create LogEntry from dictionary.

        Args:
            data: Dictionary with log entry fields

        Returns:
            LogEntry instance

        Example:
            >>> data = {
            ...     'timestamp': '2025-01-12T10:30:15.234567',
            ...     'level': 'INFO',
            ...     'source': 'ATExecutor',
            ...     'message': 'Test message'
            ... }
            >>> entry = LogEntry.from_dict(data)
        """
        # Parse timestamp if string
        timestamp = data['timestamp']
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            timestamp=timestamp,
            level=data['level'],
            source=data['source'],
            message=data['message'],
            details=data.get('details'),
            port=data.get('port'),
            command=data.get('command'),
            response=data.get('response'),
            status=data.get('status'),
            execution_time=data.get('execution_time'),
            retry_count=data.get('retry_count'),
            error=data.get('error')
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'LogEntry':
        """Create LogEntry from JSON string.

        Args:
            json_str: JSON string with log entry fields

        Returns:
            LogEntry instance

        Example:
            >>> json_str = '{"timestamp": "2025-01-12T10:30:15.234567", ...}'
            >>> entry = LogEntry.from_json(json_str)
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
