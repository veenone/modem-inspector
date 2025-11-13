"""Unit tests for CommunicationLogger."""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from unittest.mock import Mock, patch

from src.logging.communication_logger import CommunicationLogger
from src.logging.log_models import LogEntry
from src.config.config_models import LogLevel


class TestCommunicationLogger:
    """Test suite for CommunicationLogger class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test logs."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_logger_creation_file_only(self, temp_dir):
        """Test logger creation with file logging only."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        assert logger.log_level == "INFO"
        assert logger.enable_file is True
        assert logger.enable_console is False
        assert logger._file_handler is not None

        logger.close()

    def test_logger_creation_console_only(self):
        """Test logger creation with console logging only."""
        logger = CommunicationLogger(
            log_level=LogLevel.DEBUG,
            enable_file=False,
            enable_console=True
        )

        assert logger.log_level == "DEBUG"
        assert logger.enable_file is False
        assert logger.enable_console is True
        assert logger._file_handler is None

        logger.close()

    def test_logger_no_file_path_raises(self):
        """Test that creating logger with enable_file=True but no path raises error."""
        with pytest.raises(ValueError):
            CommunicationLogger(
                log_level=LogLevel.INFO,
                enable_file=True,
                enable_console=False,
                log_file_path=None  # Missing required path
            )

    def test_log_level_filtering_info(self, temp_dir):
        """Test log level filtering for INFO level."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        # Log entries at different levels
        logger.log(LogEntry(datetime.now(), "DEBUG", "Test", "Debug message"))
        logger.log(LogEntry(datetime.now(), "INFO", "Test", "Info message"))
        logger.log(LogEntry(datetime.now(), "WARNING", "Test", "Warning message"))
        logger.log(LogEntry(datetime.now(), "ERROR", "Test", "Error message"))

        logger.close()

        # Check file content
        content = log_file.read_text(encoding='utf-8')

        # DEBUG should be filtered out
        assert "Debug message" not in content
        # INFO, WARNING, ERROR should be logged
        assert "Info message" in content
        assert "Warning message" in content
        assert "Error message" in content

    def test_log_level_filtering_warning(self, temp_dir):
        """Test log level filtering for WARNING level."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.WARNING,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        logger.log(LogEntry(datetime.now(), "DEBUG", "Test", "Debug"))
        logger.log(LogEntry(datetime.now(), "INFO", "Test", "Info"))
        logger.log(LogEntry(datetime.now(), "WARNING", "Test", "Warning"))
        logger.log(LogEntry(datetime.now(), "ERROR", "Test", "Error"))

        logger.close()

        content = log_file.read_text(encoding='utf-8')

        # Only WARNING and ERROR should be logged
        assert "Debug" not in content
        assert "Info" not in content
        assert "Warning" in content
        assert "Error" in content

    def test_log_command_convenience_method(self, temp_dir):
        """Test log_command() convenience method."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        logger.log_command(port="COM3", command="AT+CGMI")
        logger.close()

        content = log_file.read_text(encoding='utf-8')
        assert "COM3" in content
        assert "AT+CGMI" in content
        assert "CMD: AT+CGMI" in content

    def test_log_response_convenience_method(self, temp_dir):
        """Test log_response() convenience method."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        logger.log_response(
            port="COM3",
            response="Quectel",
            status="SUCCESS",
            execution_time=0.123,
            retry_count=0,
            command="AT+CGMI"
        )
        logger.close()

        content = log_file.read_text(encoding='utf-8')
        assert "Quectel" in content
        assert "SUCCESS" in content
        assert "0.123" in content

    def test_log_port_event_convenience_method(self, temp_dir):
        """Test log_port_event() convenience method."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        logger.log_port_event(
            event="Port opened",
            port="COM3",
            details={"baud": 115200},
            level="INFO"
        )
        logger.close()

        content = log_file.read_text(encoding='utf-8')
        assert "Port opened" in content
        assert "COM3" in content

    def test_log_error_convenience_method(self, temp_dir):
        """Test log_error() convenience method."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.ERROR,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        logger.log_error(
            source="ATExecutor",
            error="Command timeout",
            details={"command": "AT+CGMR"}
        )
        logger.close()

        content = log_file.read_text(encoding='utf-8')
        assert "ERROR" in content
        assert "ATExecutor" in content
        assert "Command timeout" in content

    def test_set_level(self, temp_dir):
        """Test changing log level dynamically."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        # Initially INFO level
        logger.log(LogEntry(datetime.now(), "DEBUG", "Test", "Debug1"))
        logger.log(LogEntry(datetime.now(), "INFO", "Test", "Info1"))

        # Change to DEBUG level
        logger.set_level(LogLevel.DEBUG)

        logger.log(LogEntry(datetime.now(), "DEBUG", "Test", "Debug2"))
        logger.log(LogEntry(datetime.now(), "INFO", "Test", "Info2"))

        logger.close()

        content = log_file.read_text(encoding='utf-8')

        # First DEBUG filtered out, second DEBUG included
        assert "Debug1" not in content
        assert "Debug2" in content
        assert "Info1" in content
        assert "Info2" in content

    def test_in_memory_buffer(self):
        """Test in-memory buffer for GUI access."""
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=False,
            enable_console=False
        )

        # Log some entries
        for i in range(5):
            logger.log(LogEntry(datetime.now(), "INFO", "Test", f"Message {i}"))

        # Get entries
        entries = logger.get_entries()

        assert len(entries) == 5
        assert entries[0].message == "Message 0"
        assert entries[4].message == "Message 4"

        logger.close()

    def test_get_entries_with_limit(self):
        """Test getting limited number of entries from buffer."""
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=False,
            enable_console=False
        )

        # Log 10 entries
        for i in range(10):
            logger.log(LogEntry(datetime.now(), "INFO", "Test", f"Message {i}"))

        # Get only last 3
        entries = logger.get_entries(limit=3)

        assert len(entries) == 3
        assert entries[0].message == "Message 7"
        assert entries[2].message == "Message 9"

        logger.close()

    def test_clear_buffer(self):
        """Test clearing the in-memory buffer."""
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=False,
            enable_console=False
        )

        # Log entries
        for i in range(5):
            logger.log(LogEntry(datetime.now(), "INFO", "Test", f"Message {i}"))

        assert len(logger.get_entries()) == 5

        # Clear buffer
        logger.clear_buffer()

        assert len(logger.get_entries()) == 0

        logger.close()

    def test_buffer_max_size(self):
        """Test that buffer is limited to 1000 entries."""
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=False,
            enable_console=False
        )

        # Log 1500 entries
        for i in range(1500):
            logger.log(LogEntry(datetime.now(), "INFO", "Test", f"Message {i}"))

        entries = logger.get_entries()

        # Should only keep last 1000
        assert len(entries) == 1000
        # Should have messages 500-1499
        assert entries[0].message == "Message 500"
        assert entries[999].message == "Message 1499"

        logger.close()

    @patch('sys.stderr')
    def test_console_output(self, mock_stderr):
        """Test console output to stderr."""
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=False,
            enable_console=True
        )

        logger.log(LogEntry(datetime.now(), "INFO", "Test", "Console message"))

        logger.close()

        # Console output should have been called
        # Note: Actual verification depends on mock implementation

    def test_flush(self, temp_dir):
        """Test explicit flush operation."""
        log_file = temp_dir / "test.log"
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        logger.log(LogEntry(datetime.now(), "INFO", "Test", "Test message"))
        logger.flush()

        # File should have content
        content = log_file.read_text(encoding='utf-8')
        assert "Test message" in content

        logger.close()

    def test_context_manager(self, temp_dir):
        """Test CommunicationLogger as context manager."""
        log_file = temp_dir / "test.log"

        with CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        ) as logger:
            logger.log(LogEntry(datetime.now(), "INFO", "Test", "Context message"))

        # Logger should be closed after context
        content = log_file.read_text(encoding='utf-8')
        assert "Context message" in content
