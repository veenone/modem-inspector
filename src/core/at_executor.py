"""AT command execution orchestration layer.

This module provides high-level AT command execution with timeout,
retry logic, and response parsing.
"""

from typing import List, Optional
import time
import threading

from src.core.serial_handler import SerialHandler
from src.core.command_response import CommandResponse, ResponseStatus
from src.core.exceptions import ATCommandError


class ATExecutor:
    """Orchestrates AT command execution with timeout, retry, and response capture.

    Provides high-level interface for executing AT commands with automatic
    retry on timeout, response parsing, and execution history tracking.

    Example:
        >>> handler = SerialHandler('/dev/ttyUSB0')
        >>> handler.open()
        >>> executor = ATExecutor(handler, default_timeout=30.0, retry_count=3)
        >>> response = executor.execute_command('AT+CGMI')
        >>> print(response.get_response_text())
        Quectel
        OK
        >>> handler.close()
    """

    def __init__(self,
                 serial_handler: SerialHandler,
                 default_timeout: float = 30.0,
                 retry_count: int = 3,
                 retry_delay: float = 1.0):
        """Initialize executor with serial handler and defaults.

        Args:
            serial_handler: SerialHandler instance for I/O
            default_timeout: Default timeout in seconds (default 30.0)
            retry_count: Default number of retry attempts (default 3)
            retry_delay: Base delay between retries in seconds (default 1.0)
        """
        self.serial_handler = serial_handler
        self.default_timeout = default_timeout
        self.default_retry_count = retry_count
        self.retry_delay = retry_delay
        self._history: List[CommandResponse] = []
        self._history_lock = threading.Lock()

    def execute_command(self,
                       command: str,
                       timeout: Optional[float] = None,
                       retry: Optional[int] = None) -> CommandResponse:
        """Execute single AT command with retry logic.

        Sends AT command to modem and waits for response with automatic
        retry on timeout. Uses exponential backoff for retry delays.

        Args:
            command: AT command string (e.g., "AT+CGMI")
            timeout: Override default timeout in seconds
            retry: Override default retry count

        Returns:
            CommandResponse with status, response, timing

        Raises:
            ATCommandError: Command returned ERROR
            TimeoutError: All retry attempts timed out

        Example:
            >>> response = executor.execute_command('AT')
            >>> assert response.is_successful()
            >>> assert 'OK' in response.get_response_text()
        """
        timeout = timeout if timeout is not None else self.default_timeout
        retry_count = retry if retry is not None else self.default_retry_count

        response = self._execute_with_retry(command, timeout, retry_count)

        # Add to history
        with self._history_lock:
            self._history.append(response)

        return response

    def execute_batch(self,
                     commands: List[str],
                     timeout: Optional[float] = None) -> List[CommandResponse]:
        """Execute multiple commands in sequence.

        Executes commands one by one, continuing even if some fail.
        Each command uses the same timeout value.

        Args:
            commands: List of AT command strings
            timeout: Timeout per command (uses default if not specified)

        Returns:
            List of CommandResponse objects (one per command)

        Note:
            Continues on error; check each response status individually

        Example:
            >>> responses = executor.execute_batch(['AT', 'AT+CGMI', 'AT+CGMR'])
            >>> for response in responses:
            ...     if response.is_successful():
            ...         print(f"{response.command}: OK")
        """
        responses = []
        for command in commands:
            try:
                response = self.execute_command(command, timeout=timeout)
                responses.append(response)
            except Exception as e:
                # Create error response
                error_response = CommandResponse(
                    command=command,
                    raw_response=[str(e)],
                    status=ResponseStatus.ERROR,
                    execution_time=0.0,
                    error_message=str(e)
                )
                responses.append(error_response)

        return responses

    def get_history(self) -> List[CommandResponse]:
        """Get execution history for this session.

        Returns:
            List of all CommandResponse objects from this executor instance

        Example:
            >>> executor.execute_command('AT')
            >>> executor.execute_command('AT+CGMI')
            >>> history = executor.get_history()
            >>> print(f"Executed {len(history)} commands")
        """
        with self._history_lock:
            return self._history.copy()

    def clear_history(self) -> None:
        """Clear execution history.

        Removes all stored CommandResponse objects from history.
        """
        with self._history_lock:
            self._history.clear()

    def _execute_with_retry(self,
                           command: str,
                           timeout: float,
                           retry_count: int) -> CommandResponse:
        """Execute command with retry logic and exponential backoff.

        Args:
            command: AT command to execute
            timeout: Timeout in seconds
            retry_count: Number of retry attempts

        Returns:
            CommandResponse with execution result

        Raises:
            TimeoutError: All retries exhausted
        """
        last_exception = None
        attempt = 0

        while attempt <= retry_count:
            try:
                start_time = time.time()

                # Write command
                self.serial_handler.write(command)

                # Read response until terminator
                response_lines = self.serial_handler.read_until(
                    terminator='OK',
                    timeout=timeout
                )

                execution_time = time.time() - start_time

                # Parse response
                parsed_response = self._parse_response(
                    command=command,
                    lines=response_lines,
                    execution_time=execution_time,
                    retry_count=attempt
                )

                return parsed_response

            except TimeoutError as e:
                last_exception = e
                attempt += 1

                # Exponential backoff: 1s, 2s, 4s
                if attempt <= retry_count:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    time.sleep(delay)

        # All retries exhausted
        execution_time = time.time() - start_time
        return CommandResponse(
            command=command,
            raw_response=[],
            status=ResponseStatus.TIMEOUT,
            execution_time=execution_time,
            retry_count=retry_count,
            error_message=f"Timeout after {retry_count} retries: {last_exception}"
        )

    def _parse_response(self,
                       command: str,
                       lines: List[str],
                       execution_time: float,
                       retry_count: int) -> CommandResponse:
        """Parse AT command response lines.

        Detects response terminators (OK, ERROR, +CME ERROR, +CMS ERROR)
        and strips command echo if present.

        Args:
            command: Original AT command
            lines: Response lines from serial port
            execution_time: Time taken to execute
            retry_count: Number of retries performed

        Returns:
            Parsed CommandResponse
        """
        # Strip echo (first line that matches command)
        stripped_lines = self._strip_echo(command, lines)

        # Detect response status
        status = ResponseStatus.SUCCESS
        error_code = None
        error_message = None

        for line in stripped_lines:
            line_upper = line.upper()

            # Check for error responses
            if line_upper == 'ERROR':
                status = ResponseStatus.ERROR
                error_message = "Generic ERROR response"
            elif line_upper.startswith('+CME ERROR'):
                status = ResponseStatus.ERROR
                # Parse error code: "+CME ERROR: 123"
                parts = line.split(':', 1)
                if len(parts) > 1:
                    error_code = parts[1].strip()
                    error_message = f"CME Error: {error_code}"
                else:
                    error_message = "CME Error (no code)"
            elif line_upper.startswith('+CMS ERROR'):
                status = ResponseStatus.ERROR
                # Parse error code: "+CMS ERROR: 500"
                parts = line.split(':', 1)
                if len(parts) > 1:
                    error_code = parts[1].strip()
                    error_message = f"CMS Error: {error_code}"
                else:
                    error_message = "CMS Error (no code)"

        return CommandResponse(
            command=command,
            raw_response=stripped_lines,
            status=status,
            execution_time=execution_time,
            error_code=error_code,
            error_message=error_message,
            retry_count=retry_count
        )

    def _strip_echo(self, command: str, lines: List[str]) -> List[str]:
        """Strip command echo from response lines.

        Modems often echo the command back. Remove the first line
        if it matches the command.

        Args:
            command: Original AT command
            lines: Response lines

        Returns:
            Lines with echo removed
        """
        if not lines:
            return lines

        # Check if first line is echo
        if lines[0].strip().upper() == command.strip().upper():
            return lines[1:]

        return lines

    def __repr__(self) -> str:
        """String representation of executor."""
        return (f"ATExecutor(handler={self.serial_handler.port}, "
                f"timeout={self.default_timeout}s, "
                f"retries={self.default_retry_count}, "
                f"history={len(self._history)} commands)")
