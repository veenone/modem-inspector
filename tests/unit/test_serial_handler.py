"""Unit tests for SerialHandler with mocked pyserial.

Tests the SerialHandler class using mocked serial.Serial to avoid
hardware dependencies. Covers all 7 public methods and error scenarios.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import threading
import time
import serial

from src.core.serial_handler import SerialHandler, PortInfo
from src.core.exceptions import (
    SerialPortError,
    SerialPortBusyError,
    ConnectionTimeoutError,
    BufferOverflowError
)


class TestPortInfo:
    """Test PortInfo dataclass."""

    def test_create_port_info(self):
        """Test creating PortInfo."""
        info = PortInfo(
            device="/dev/ttyUSB0",
            description="USB Serial Port",
            hwid="USB VID:PID=1234:5678"
        )

        assert info.device == "/dev/ttyUSB0"
        assert info.description == "USB Serial Port"
        assert info.hwid == "USB VID:PID=1234:5678"

    def test_port_info_equality(self):
        """Test PortInfo equality."""
        info1 = PortInfo("/dev/ttyUSB0", "Port", "HW123")
        info2 = PortInfo("/dev/ttyUSB0", "Port", "HW123")

        assert info1 == info2


class TestSerialHandlerInit:
    """Test SerialHandler initialization."""

    def test_init_minimal(self):
        """Test initialization with minimal arguments."""
        handler = SerialHandler("/dev/ttyUSB0")

        assert handler.port == "/dev/ttyUSB0"
        assert handler.baud_rate == 115200
        assert handler.timeout == 1.0
        assert handler.logger is None
        assert handler._serial is None

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        handler = SerialHandler(
            port="COM3",
            baud_rate=9600,
            timeout=5.0
        )

        assert handler.port == "COM3"
        assert handler.baud_rate == 9600
        assert handler.timeout == 5.0

    def test_init_with_logger(self):
        """Test initialization with logger."""
        mock_logger = Mock()
        handler = SerialHandler("/dev/ttyUSB0", logger=mock_logger)

        assert handler.logger == mock_logger

    def test_init_with_kwargs(self):
        """Test initialization with extra serial parameters."""
        handler = SerialHandler(
            "/dev/ttyUSB0",
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE
        )

        assert handler.kwargs["bytesize"] == serial.EIGHTBITS
        assert handler.kwargs["parity"] == serial.PARITY_NONE


class TestSerialHandlerOpen:
    """Test SerialHandler.open() method."""

    @patch('serial.Serial')
    def test_open_success(self, mock_serial_class):
        """Test successful port opening."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0", baud_rate=115200)
        handler.open()

        mock_serial_class.assert_called_once_with(
            port="/dev/ttyUSB0",
            baudrate=115200,
            timeout=1.0
        )
        assert handler._serial == mock_serial
        assert handler._open_time is not None

    @patch('serial.Serial')
    def test_open_already_open(self, mock_serial_class):
        """Test opening already open port (no-op)."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()

        # Reset mock and open again
        mock_serial_class.reset_mock()
        handler.open()

        # Should not create new Serial instance
        mock_serial_class.assert_not_called()

    @patch('serial.Serial')
    def test_open_permission_denied(self, mock_serial_class):
        """Test opening port with permission denied error."""
        mock_serial_class.side_effect = serial.SerialException("Permission denied")

        handler = SerialHandler("/dev/ttyUSB0")

        with pytest.raises(SerialPortError) as exc_info:
            handler.open()

        assert "Permission denied" in str(exc_info.value)
        assert exc_info.value.port == "/dev/ttyUSB0"

    @patch('serial.Serial')
    def test_open_port_busy(self, mock_serial_class):
        """Test opening port that's already in use."""
        mock_serial_class.side_effect = serial.SerialException("Port is busy")

        handler = SerialHandler("COM3")

        with pytest.raises(SerialPortBusyError) as exc_info:
            handler.open()

        assert "already in use" in str(exc_info.value)
        assert exc_info.value.port == "COM3"

    @patch('serial.Serial')
    def test_open_timeout(self, mock_serial_class):
        """Test opening port with timeout."""
        mock_serial_class.side_effect = serial.SerialException("Timeout")

        handler = SerialHandler("/dev/ttyUSB0")

        with pytest.raises(ConnectionTimeoutError) as exc_info:
            handler.open()

        assert "Timeout" in str(exc_info.value)

    @patch('serial.Serial')
    def test_open_generic_error(self, mock_serial_class):
        """Test opening port with generic error."""
        mock_serial_class.side_effect = serial.SerialException("Unknown error")

        handler = SerialHandler("/dev/ttyUSB0")

        with pytest.raises(SerialPortError) as exc_info:
            handler.open()

        assert "Failed to open port" in str(exc_info.value)
        assert exc_info.value.os_error is not None

    @patch('serial.Serial')
    def test_open_unexpected_exception(self, mock_serial_class):
        """Test opening port with unexpected exception."""
        mock_serial_class.side_effect = ValueError("Unexpected")

        handler = SerialHandler("/dev/ttyUSB0")

        with pytest.raises(SerialPortError) as exc_info:
            handler.open()

        assert "Unexpected error" in str(exc_info.value)

    @patch('serial.Serial')
    def test_open_with_logger(self, mock_serial_class):
        """Test opening port logs success."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        mock_logger = Mock()
        handler = SerialHandler("/dev/ttyUSB0", logger=mock_logger)
        handler.open()

        mock_logger.log_port_event.assert_called_once()
        call_args = mock_logger.log_port_event.call_args
        assert call_args[1]["event"] == "Port opened"
        assert call_args[1]["port"] == "/dev/ttyUSB0"
        assert call_args[1]["level"] == "INFO"

    @patch('serial.Serial')
    def test_open_with_logger_error(self, mock_serial_class):
        """Test opening port logs error on failure."""
        mock_serial_class.side_effect = serial.SerialException("Test error")

        mock_logger = Mock()
        handler = SerialHandler("/dev/ttyUSB0", logger=mock_logger)

        with pytest.raises(SerialPortError):
            handler.open()

        mock_logger.log_error.assert_called_once()


class TestSerialHandlerClose:
    """Test SerialHandler.close() method."""

    @patch('serial.Serial')
    def test_close_success(self, mock_serial_class):
        """Test successful port closing."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        handler.close()

        mock_serial.close.assert_called_once()

    @patch('serial.Serial')
    def test_close_not_open(self, mock_serial_class):
        """Test closing port that's not open (no-op)."""
        handler = SerialHandler("/dev/ttyUSB0")
        handler.close()  # Should not raise

    @patch('serial.Serial')
    def test_close_multiple_times(self, mock_serial_class):
        """Test closing port multiple times is safe."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()

        # Close multiple times
        handler.close()
        mock_serial.is_open = False  # Simulate closed state
        handler.close()  # Should not raise

    @patch('serial.Serial')
    def test_close_with_error(self, mock_serial_class):
        """Test closing port handles errors gracefully."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.close.side_effect = Exception("Close error")
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        handler.close()  # Should not raise

    @patch('serial.Serial')
    def test_close_with_logger(self, mock_serial_class):
        """Test closing port logs with session duration."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        mock_logger = Mock()
        handler = SerialHandler("/dev/ttyUSB0", logger=mock_logger)
        handler.open()

        time.sleep(0.1)  # Small delay for duration
        handler.close()

        # Check close log was called
        log_calls = [call for call in mock_logger.log_port_event.call_args_list
                    if call[1].get("event") == "Port closed"]
        assert len(log_calls) == 1
        assert "session_duration_seconds" in log_calls[0][1]["details"]


class TestSerialHandlerWrite:
    """Test SerialHandler.write() method."""

    @patch('serial.Serial')
    def test_write_success(self, mock_serial_class):
        """Test successful write."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write.return_value = 5
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        bytes_written = handler.write("AT")

        # Should write "AT\r\n" (4 bytes + encoding)
        mock_serial.write.assert_called_once()
        written_data = mock_serial.write.call_args[0][0]
        assert written_data == b"AT\r\n"
        mock_serial.flush.assert_called_once()

    @patch('serial.Serial')
    def test_write_not_open(self, mock_serial_class):
        """Test writing to closed port raises error."""
        handler = SerialHandler("/dev/ttyUSB0")

        with pytest.raises(SerialPortError) as exc_info:
            handler.write("AT")

        assert "closed port" in str(exc_info.value)

    @patch('serial.Serial')
    def test_write_serial_exception(self, mock_serial_class):
        """Test write handles serial exception."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write.side_effect = serial.SerialException("Write error")
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()

        with pytest.raises(SerialPortError) as exc_info:
            handler.write("AT")

        assert "Failed to write" in str(exc_info.value)

    @patch('serial.Serial')
    def test_write_unexpected_exception(self, mock_serial_class):
        """Test write handles unexpected exception."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.write.side_effect = ValueError("Unexpected")
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()

        with pytest.raises(SerialPortError) as exc_info:
            handler.write("AT")

        assert "Unexpected error" in str(exc_info.value)

    @patch('serial.Serial')
    def test_write_adds_terminator(self, mock_serial_class):
        """Test write automatically adds \\r\\n terminator."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        handler.write("AT+CGMI")

        written_data = mock_serial.write.call_args[0][0]
        assert written_data.endswith(b"\r\n")


class TestSerialHandlerReadUntil:
    """Test SerialHandler.read_until() method."""

    @patch('serial.Serial')
    def test_read_until_success(self, mock_serial_class):
        """Test successful read_until."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        # Simulate reading lines
        mock_serial.readline.side_effect = [
            b"Quectel\r\n",
            b"OK\r\n"
        ]
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        lines = handler.read_until("OK", timeout=5.0)

        assert len(lines) == 2
        assert lines[0] == "Quectel"
        assert lines[1] == "OK"

    @patch('serial.Serial')
    def test_read_until_not_open(self, mock_serial_class):
        """Test reading from closed port raises error."""
        handler = SerialHandler("/dev/ttyUSB0")

        with pytest.raises(SerialPortError) as exc_info:
            handler.read_until("OK")

        assert "closed port" in str(exc_info.value)

    @patch('serial.Serial')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_read_until_timeout(self, mock_sleep, mock_serial_class):
        """Test read_until timeout."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        # Simulate timeout (readline returns empty bytes)
        mock_serial.readline.return_value = b""
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()

        # Should raise TimeoutError
        with pytest.raises(TimeoutError) as exc_info:
            handler.read_until("OK", timeout=0.1)

        assert "timeout" in str(exc_info.value).lower()

    @patch('serial.Serial')
    def test_read_until_custom_terminator(self, mock_serial_class):
        """Test read_until with custom terminator."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.readline.side_effect = [
            b"+CSQ: 25,99\r\n",
            b"OK\r\n"
        ]
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        lines = handler.read_until("OK", timeout=5.0)

        assert len(lines) == 2
        assert lines[0] == "+CSQ: 25,99"
        assert lines[1] == "OK"

    @patch('serial.Serial')
    def test_read_until_strips_whitespace(self, mock_serial_class):
        """Test read_until strips whitespace."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.readline.side_effect = [
            b"  Quectel  \r\n",
            b"\tOK\t\r\n"
        ]
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        lines = handler.read_until("OK")

        assert lines[0] == "Quectel"
        assert lines[1] == "OK"


class TestSerialHandlerIsConnected:
    """Test SerialHandler.is_connected() method."""

    @patch('serial.Serial')
    def test_is_connected_true(self, mock_serial_class):
        """Test is_connected returns True when connected."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()

        assert handler.is_connected() is True

    def test_is_connected_false_not_opened(self):
        """Test is_connected returns False when not opened."""
        handler = SerialHandler("/dev/ttyUSB0")

        assert handler.is_connected() is False

    @patch('serial.Serial')
    def test_is_connected_false_after_close(self, mock_serial_class):
        """Test is_connected returns False after close."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        assert handler.is_connected() is True

        mock_serial.is_open = False
        handler.close()
        assert handler.is_connected() is False


class TestSerialHandlerFlushBuffers:
    """Test SerialHandler.flush_buffers() method."""

    @patch('serial.Serial')
    def test_flush_buffers_success(self, mock_serial_class):
        """Test successful buffer flushing."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()
        handler.flush_buffers()

        mock_serial.reset_input_buffer.assert_called_once()
        mock_serial.reset_output_buffer.assert_called_once()

    @patch('serial.Serial')
    def test_flush_buffers_not_open(self, mock_serial_class):
        """Test flushing buffers when port not open raises error."""
        handler = SerialHandler("/dev/ttyUSB0")

        with pytest.raises(SerialPortError) as exc_info:
            handler.flush_buffers()

        assert "closed port" in str(exc_info.value)


class TestSerialHandlerDiscoverPorts:
    """Test SerialHandler.discover_ports() static method."""

    @patch('serial.tools.list_ports.comports')
    def test_discover_ports_success(self, mock_comports):
        """Test successful port discovery."""
        # Mock port info objects
        mock_port1 = Mock()
        mock_port1.device = "/dev/ttyUSB0"
        mock_port1.description = "USB Serial"
        mock_port1.hwid = "USB VID:PID=1234:5678"

        mock_port2 = Mock()
        mock_port2.device = "/dev/ttyUSB1"
        mock_port2.description = "USB Modem"
        mock_port2.hwid = "USB VID:PID=8765:4321"

        mock_comports.return_value = [mock_port1, mock_port2]

        ports = SerialHandler.discover_ports()

        assert len(ports) == 2
        assert ports[0].device == "/dev/ttyUSB0"
        assert ports[0].description == "USB Serial"
        assert ports[1].device == "/dev/ttyUSB1"

    @patch('serial.tools.list_ports.comports')
    def test_discover_ports_empty(self, mock_comports):
        """Test port discovery with no ports."""
        mock_comports.return_value = []

        ports = SerialHandler.discover_ports()

        assert len(ports) == 0


class TestSerialHandlerThreadSafety:
    """Test SerialHandler thread safety."""

    @patch('serial.Serial')
    def test_concurrent_write(self, mock_serial_class):
        """Test concurrent writes are thread-safe."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")
        handler.open()

        results = []
        errors = []

        def write_thread(command):
            try:
                handler.write(command)
                results.append(command)
            except Exception as e:
                errors.append(e)

        # Start multiple threads writing simultaneously
        threads = []
        for i in range(10):
            t = threading.Thread(target=write_thread, args=(f"AT+CMD{i}",))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All writes should succeed
        assert len(results) == 10
        assert len(errors) == 0

    @patch('serial.Serial')
    def test_concurrent_open_close(self, mock_serial_class):
        """Test concurrent open/close operations are safe."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial_class.return_value = mock_serial

        handler = SerialHandler("/dev/ttyUSB0")

        errors = []

        def open_close_thread():
            try:
                handler.open()
                time.sleep(0.01)
                handler.close()
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=open_close_thread)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should not have errors (lock prevents race conditions)
        assert len(errors) == 0
