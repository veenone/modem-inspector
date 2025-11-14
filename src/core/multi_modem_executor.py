"""Multi-modem concurrent command execution.

This module provides support for executing AT commands across multiple
modems concurrently using a thread pool for parallel execution.
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import threading

from src.core.serial_handler import SerialHandler
from src.core.at_executor import ATExecutor
from src.core.command_response import CommandResponse


@dataclass
class ModemConnection:
    """Represents a single modem connection.

    Attributes:
        port: Serial port device path
        handler: SerialHandler instance
        executor: ATExecutor instance
        baud_rate: Baud rate for connection
        identifier: Optional human-readable identifier
    """
    port: str
    handler: SerialHandler
    executor: ATExecutor
    baud_rate: int = 115200
    identifier: Optional[str] = None


class MultiModemExecutor:
    """Manages concurrent AT command execution across multiple modems.

    Provides thread-pool based concurrent execution with automatic
    resource management and failure isolation.

    Example:
        >>> mm_executor = MultiModemExecutor(max_workers=5)
        >>> mm_executor.add_modem("/dev/ttyUSB0", identifier="Modem1")
        >>> mm_executor.add_modem("/dev/ttyUSB1", identifier="Modem2")
        >>> mm_executor.connect_all()
        >>> results = mm_executor.execute_on_all("AT+CGMI")
        >>> mm_executor.disconnect_all()
    """

    def __init__(self, max_workers: int = 5, default_timeout: float = 30.0):
        """Initialize multi-modem executor.

        Args:
            max_workers: Maximum number of concurrent modem connections (default 5)
            default_timeout: Default timeout for commands in seconds (default 30.0)
        """
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self._connections: Dict[str, ModemConnection] = {}
        self._lock = threading.Lock()

    def add_modem(self,
                  port: str,
                  baud_rate: int = 115200,
                  identifier: Optional[str] = None,
                  **kwargs) -> None:
        """Add modem to connection pool.

        Args:
            port: Serial port device path
            baud_rate: Baud rate for connection (default 115200)
            identifier: Optional human-readable identifier (defaults to port)
            **kwargs: Additional arguments passed to SerialHandler

        Raises:
            ValueError: Port already added
        """
        with self._lock:
            if port in self._connections:
                raise ValueError(f"Port {port} already added")

            handler = SerialHandler(port, baud_rate=baud_rate, **kwargs)
            executor = ATExecutor(handler, default_timeout=self.default_timeout)

            connection = ModemConnection(
                port=port,
                handler=handler,
                executor=executor,
                baud_rate=baud_rate,
                identifier=identifier or port
            )

            self._connections[port] = connection

    def remove_modem(self, port: str) -> None:
        """Remove modem from connection pool.

        Automatically disconnects if connected.

        Args:
            port: Serial port to remove

        Raises:
            KeyError: Port not found
        """
        with self._lock:
            if port not in self._connections:
                raise KeyError(f"Port {port} not found")

            connection = self._connections[port]

            # Close connection if open
            if connection.handler.is_connected():
                connection.handler.close()

            del self._connections[port]

    def get_modem(self, port: str) -> ModemConnection:
        """Get modem connection by port.

        Args:
            port: Serial port

        Returns:
            ModemConnection for the port

        Raises:
            KeyError: Port not found
        """
        with self._lock:
            if port not in self._connections:
                raise KeyError(f"Port {port} not found")
            return self._connections[port]

    def list_modems(self) -> List[str]:
        """List all added modem ports.

        Returns:
            List of port names
        """
        with self._lock:
            return list(self._connections.keys())

    def connect_all(self) -> Dict[str, bool]:
        """Connect to all modems concurrently.

        Returns:
            Dictionary mapping port to success status
        """
        results = {}

        def connect_modem(port: str) -> tuple:
            """Connect to single modem."""
            try:
                connection = self.get_modem(port)
                connection.handler.open()
                return (port, True)
            except Exception as e:
                return (port, False)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(connect_modem, port): port
                      for port in self.list_modems()}

            for future in as_completed(futures):
                port, success = future.result()
                results[port] = success

        return results

    def disconnect_all(self) -> None:
        """Disconnect from all modems."""
        with self._lock:
            for connection in self._connections.values():
                try:
                    if connection.handler.is_connected():
                        connection.handler.close()
                except Exception:
                    pass  # Ignore close errors

    def execute_on_all(self,
                      command: str,
                      timeout: Optional[float] = None,
                      retry: Optional[int] = None) -> Dict[str, CommandResponse]:
        """Execute command on all connected modems concurrently.

        Args:
            command: AT command to execute
            timeout: Override default timeout
            retry: Override default retry count

        Returns:
            Dictionary mapping port to CommandResponse

        Note:
            Only executes on modems that are currently connected.
            Failed modems are isolated and don't affect others.
        """
        results = {}

        def execute_on_modem(port: str) -> tuple:
            """Execute command on single modem."""
            try:
                connection = self.get_modem(port)
                if not connection.handler.is_connected():
                    return (port, None)

                response = connection.executor.execute_command(
                    command,
                    timeout=timeout,
                    retry=retry
                )
                return (port, response)
            except Exception as e:
                # Return error response for failed execution
                from src.core.command_response import ResponseStatus
                error_response = CommandResponse(
                    command=command,
                    raw_response=[str(e)],
                    status=ResponseStatus.ERROR,
                    execution_time=0.0
                )
                return (port, error_response)

        # Execute concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(execute_on_modem, port): port
                      for port in self.list_modems()}

            for future in as_completed(futures):
                port, response = future.result()
                if response is not None:
                    results[port] = response

        return results

    def execute_on_modem(self,
                        port: str,
                        command: str,
                        timeout: Optional[float] = None,
                        retry: Optional[int] = None) -> CommandResponse:
        """Execute command on specific modem.

        Args:
            port: Port to execute on
            command: AT command to execute
            timeout: Override default timeout
            retry: Override default retry count

        Returns:
            CommandResponse from execution

        Raises:
            KeyError: Port not found
            RuntimeError: Modem not connected
        """
        connection = self.get_modem(port)

        if not connection.handler.is_connected():
            raise RuntimeError(f"Modem on port {port} is not connected")

        return connection.executor.execute_command(
            command,
            timeout=timeout,
            retry=retry
        )

    def execute_batch_on_all(self,
                            commands: List[str],
                            timeout: Optional[float] = None,
                            retry: Optional[int] = None) -> Dict[str, List[CommandResponse]]:
        """Execute batch of commands on all modems concurrently.

        Args:
            commands: List of AT commands to execute
            timeout: Override default timeout
            retry: Override default retry count

        Returns:
            Dictionary mapping port to list of CommandResponses
        """
        results = {}

        def execute_batch_on_modem(port: str) -> tuple:
            """Execute batch on single modem."""
            try:
                connection = self.get_modem(port)
                if not connection.handler.is_connected():
                    return (port, [])

                responses = connection.executor.execute_batch(
                    commands,
                    timeout=timeout,
                    retry=retry
                )
                return (port, responses)
            except Exception:
                return (port, [])

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(execute_batch_on_modem, port): port
                      for port in self.list_modems()}

            for future in as_completed(futures):
                port, responses = future.result()
                if responses:
                    results[port] = responses

        return results

    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all modems.

        Returns:
            Dictionary mapping port to connection status (True = connected)
        """
        with self._lock:
            return {port: conn.handler.is_connected()
                   for port, conn in self._connections.items()}

    def get_modem_count(self) -> int:
        """Get number of added modems.

        Returns:
            Count of modems in pool
        """
        with self._lock:
            return len(self._connections)

    def get_connected_count(self) -> int:
        """Get number of currently connected modems.

        Returns:
            Count of connected modems
        """
        status = self.get_connection_status()
        return sum(1 for connected in status.values() if connected)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnects all modems."""
        self.disconnect_all()
        return False
