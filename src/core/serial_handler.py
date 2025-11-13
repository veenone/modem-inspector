"""Serial port I/O handler for AT command communication.

This module provides a cross-platform serial communication interface
with robust error handling and port discovery capabilities.
"""

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
import threading
import time

import serial
from serial.tools import list_ports

from src.core.exceptions import (
    SerialPortError,
    SerialPortBusyError,
    ConnectionTimeoutError,
    BufferOverflowError
)

# Avoid circular import for type hints
if TYPE_CHECKING:
    from src.logging.communication_logger import CommunicationLogger


@dataclass
class PortInfo:
    """Serial port information from discovery.

    Attributes:
        device: Port device path (e.g., '/dev/ttyUSB0', 'COM3')
        description: Human-readable port description
        hwid: Hardware identifier (USB VID:PID, etc.)
    """
    device: str
    description: str
    hwid: str


class SerialHandler:
    """Manages serial port connection lifecycle and raw I/O operations.

    Provides low-level serial communication interface with thread safety
    for multi-modem scenarios. Wraps pyserial exceptions in custom types.

    Example:
        >>> handler = SerialHandler('/dev/ttyUSB0', baud_rate=115200)
        >>> handler.open()
        >>> handler.write('AT')
        >>> response = handler.read_until('OK', timeout=5.0)
        >>> handler.close()
    """

    def __init__(self,
                 port: str,
                 baud_rate: int = 115200,
                 timeout: float = 1.0,
                 logger: Optional['CommunicationLogger'] = None,
                 **kwargs):
        """Initialize handler with port configuration.

        Args:
            port: Serial port device path
            baud_rate: Baud rate (default 115200)
            timeout: Read timeout in seconds (default 1.0)
            logger: Optional CommunicationLogger for logging port events (default None)
            **kwargs: Additional arguments passed to serial.Serial
        """
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.logger = logger
        self.kwargs = kwargs
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()
        self._open_time: Optional[float] = None  # Track session duration

    def open(self) -> None:
        """Open serial port and configure settings.

        Raises:
            SerialPortError: Port doesn't exist or permission denied
            SerialPortBusyError: Port already in use
            ConnectionTimeoutError: Open timeout exceeded
        """
        with self._lock:
            if self._serial is not None and self._serial.is_open:
                return  # Already open

            try:
                self._serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baud_rate,
                    timeout=self.timeout,
                    **self.kwargs
                )
                self._open_time = time.time()

                # Log successful port open
                if self.logger:
                    self.logger.log_port_event(
                        event="Port opened",
                        port=self.port,
                        details={
                            "baud_rate": self.baud_rate,
                            "timeout": self.timeout,
                            **self.kwargs
                        },
                        level="INFO"
                    )

            except serial.SerialException as e:
                error_msg = str(e).lower()

                # Log port open error
                if self.logger:
                    self.logger.log_error(
                        source="SerialHandler",
                        error=f"Failed to open port: {e}",
                        details={"port": self.port, "error_type": type(e).__name__}
                    )

                if 'permission denied' in error_msg or 'access denied' in error_msg:
                    raise SerialPortError(
                        f"Permission denied accessing port {self.port}",
                        self.port,
                        e
                    )
                elif 'busy' in error_msg or 'in use' in error_msg:
                    raise SerialPortBusyError(
                        f"Port {self.port} is already in use",
                        self.port,
                        e
                    )
                elif 'timeout' in error_msg:
                    raise ConnectionTimeoutError(
                        f"Timeout opening port {self.port}",
                        self.port,
                        e
                    )
                else:
                    raise SerialPortError(
                        f"Failed to open port {self.port}: {e}",
                        self.port,
                        e
                    )
            except Exception as e:
                # Log unexpected error
                if self.logger:
                    self.logger.log_error(
                        source="SerialHandler",
                        error=f"Unexpected error opening port: {e}",
                        details={"port": self.port, "error_type": type(e).__name__}
                    )

                raise SerialPortError(
                    f"Unexpected error opening port {self.port}: {e}",
                    self.port,
                    e
                )

    def close(self) -> None:
        """Close serial port and release resources.

        Safe to call multiple times; does nothing if port is already closed.
        """
        with self._lock:
            if self._serial is not None and self._serial.is_open:
                try:
                    self._serial.close()

                    # Log port close with session duration
                    if self.logger:
                        session_duration = None
                        if self._open_time:
                            session_duration = time.time() - self._open_time

                        self.logger.log_port_event(
                            event="Port closed",
                            port=self.port,
                            details={
                                "session_duration_seconds": session_duration
                            } if session_duration else None,
                            level="INFO"
                        )
                except Exception as e:
                    # Log close error
                    if self.logger:
                        self.logger.log_error(
                            source="SerialHandler",
                            error=f"Error closing port: {e}",
                            details={"port": self.port}
                        )
                finally:
                    self._open_time = None

    def write(self, data: str) -> int:
        """Write string to serial port.

        Automatically appends \\r\\n terminator to the data.

        Args:
            data: String to write (terminator added automatically)

        Returns:
            Number of bytes written

        Raises:
            SerialPortError: Port not open or write failed
        """
        with self._lock:
            if self._serial is None or not self._serial.is_open:
                raise SerialPortError(
                    "Cannot write to closed port",
                    self.port,
                    None
                )

            try:
                # Add terminator and encode
                message = f"{data}\r\n"
                bytes_data = message.encode('utf-8')
                bytes_written = self._serial.write(bytes_data)
                self._serial.flush()  # Ensure data is sent
                return bytes_written
            except serial.SerialException as e:
                raise SerialPortError(
                    f"Failed to write to port {self.port}: {e}",
                    self.port,
                    e
                )
            except Exception as e:
                raise SerialPortError(
                    f"Unexpected error writing to port {self.port}: {e}",
                    self.port,
                    e
                )

    def read_until(self,
                   terminator: str = 'OK',
                   timeout: float = 30.0) -> List[str]:
        """Read lines until terminator or timeout.

        Reads lines from the serial port until a line containing the
        terminator is found, or the timeout is exceeded.

        Args:
            terminator: Stop reading when line contains this
            timeout: Maximum time to wait in seconds

        Returns:
            List of response lines (including terminator line)

        Raises:
            TimeoutError: Read timeout exceeded
            SerialPortError: Port not open or read failed
        """
        with self._lock:
            if self._serial is None or not self._serial.is_open:
                raise SerialPortError(
                    "Cannot read from closed port",
                    self.port,
                    None
                )

            lines = []
            start_time = time.time()

            try:
                while True:
                    # Check timeout
                    elapsed = time.time() - start_time
                    if elapsed > timeout:
                        raise TimeoutError(
                            f"Read timeout after {elapsed:.2f}s waiting for '{terminator}'"
                        )

                    # Read one line
                    line_bytes = self._serial.readline()
                    if not line_bytes:
                        # No data available, continue waiting
                        time.sleep(0.01)  # Small delay to prevent busy-wait
                        continue

                    # Decode and strip whitespace
                    line = line_bytes.decode('utf-8', errors='replace').strip()
                    if not line:
                        continue  # Skip empty lines

                    lines.append(line)

                    # Check for terminator
                    if terminator in line:
                        return lines

            except TimeoutError:
                raise  # Re-raise timeout as-is
            except serial.SerialException as e:
                raise SerialPortError(
                    f"Failed to read from port {self.port}: {e}",
                    self.port,
                    e
                )
            except Exception as e:
                raise SerialPortError(
                    f"Unexpected error reading from port {self.port}: {e}",
                    self.port,
                    e
                )

    def is_connected(self) -> bool:
        """Check if port is currently open and connected.

        Returns:
            True if port is open, False otherwise
        """
        with self._lock:
            return self._serial is not None and self._serial.is_open

    def flush_buffers(self) -> None:
        """Flush input and output buffers.

        Clears any pending data in the serial port buffers.

        Raises:
            SerialPortError: Port not open or flush failed
        """
        with self._lock:
            if self._serial is None or not self._serial.is_open:
                raise SerialPortError(
                    "Cannot flush buffers on closed port",
                    self.port,
                    None
                )

            try:
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
            except serial.SerialException as e:
                raise SerialPortError(
                    f"Failed to flush buffers on port {self.port}: {e}",
                    self.port,
                    e
                )

    @staticmethod
    def discover_ports() -> List[PortInfo]:
        """Enumerate available serial ports.

        Cross-platform port discovery using pyserial's list_ports.

        Returns:
            List of PortInfo objects with path, description, hwid

        Example:
            >>> ports = SerialHandler.discover_ports()
            >>> for port in ports:
            ...     print(f"{port.device}: {port.description}")
            /dev/ttyUSB0: USB Serial Port
            /dev/ttyUSB1: USB Serial Port
        """
        ports = []
        for port_info in list_ports.comports():
            ports.append(PortInfo(
                device=port_info.device,
                description=port_info.description or "Unknown",
                hwid=port_info.hwid or "Unknown"
            ))
        return ports

    def __enter__(self):
        """Context manager entry: open port."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: close port."""
        self.close()
        return False

    def __repr__(self) -> str:
        """String representation of handler."""
        status = "open" if self.is_connected() else "closed"
        return f"SerialHandler(port='{self.port}', baud={self.baud_rate}, status={status})"
