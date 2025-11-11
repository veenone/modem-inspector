"""AT command response data model.

This module defines the immutable CommandResponse dataclass and ResponseStatus enum,
providing a structured representation of AT command execution results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import time


class ResponseStatus(Enum):
    """AT command response status.

    Indicates the outcome of command execution:
    - SUCCESS: Command executed successfully (OK response)
    - ERROR: Command failed (ERROR, +CME ERROR, or +CMS ERROR)
    - TIMEOUT: Command timed out (no response within timeout period)
    """
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class CommandResponse:
    """Immutable AT command response.

    Captures all information about an AT command execution, including
    the command, response, timing, and any errors. Frozen dataclass
    ensures response cannot be modified after creation.

    Attributes:
        command: AT command string sent (e.g., "AT+CGMI")
        raw_response: Response lines from modem (without echo)
        status: Success, error, or timeout
        execution_time: Seconds from command send to response receive
        error_code: Error code from +CME ERROR or +CMS ERROR (if applicable)
        error_message: Human-readable error description (if applicable)
        retry_count: Number of retry attempts performed (0 if first attempt succeeded)
        timestamp: Unix timestamp when response was created
    """

    command: str
    raw_response: List[str]
    status: ResponseStatus
    execution_time: float
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)

    def get_response_text(self) -> str:
        """Join response lines into single string.

        Returns:
            Response lines joined with newlines

        Example:
            >>> response = CommandResponse(
            ...     command="AT+CGMI",
            ...     raw_response=["Quectel", "OK"],
            ...     status=ResponseStatus.SUCCESS,
            ...     execution_time=0.15
            ... )
            >>> response.get_response_text()
            'Quectel\\nOK'
        """
        return '\n'.join(self.raw_response)

    def is_successful(self) -> bool:
        """Check if command succeeded.

        Returns:
            True if status is SUCCESS, False otherwise

        Example:
            >>> response = CommandResponse(
            ...     command="AT",
            ...     raw_response=["OK"],
            ...     status=ResponseStatus.SUCCESS,
            ...     execution_time=0.05
            ... )
            >>> response.is_successful()
            True
        """
        return self.status == ResponseStatus.SUCCESS

    def __str__(self) -> str:
        """Format response for display.

        Returns:
            Human-readable response summary
        """
        if self.status == ResponseStatus.SUCCESS:
            return f"[{self.status.value}] {self.command} -> {len(self.raw_response)} lines ({self.execution_time:.3f}s)"
        elif self.status == ResponseStatus.ERROR:
            error_info = f" ({self.error_code}: {self.error_message})" if self.error_code else ""
            return f"[{self.status.value}] {self.command}{error_info} ({self.execution_time:.3f}s)"
        else:  # TIMEOUT
            return f"[{self.status.value}] {self.command} (after {self.retry_count} retries, {self.execution_time:.3f}s)"
