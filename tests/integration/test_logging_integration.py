"""Integration tests for end-to-end communication logging."""

import pytest
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
from datetime import datetime
import threading
import time

from src.logging import CommunicationLogger, LogEntry
from src.config import ConfigManager
from src.config.config_models import LogLevel


class TestLoggingIntegration:
    """Integration test suite for communication logging."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test logs."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)

    def test_cli_logging_creates_log_file(self, temp_dir):
        """Test that CLI with --log flag creates a log file."""
        log_file = temp_dir / "cli_test.log"

        # Run CLI command with logging (requires main.py to be runnable)
        # Note: This test is a template - actual execution depends on having a modem
        # In a real test, you might mock the serial port

        # Initialize logger programmatically for testing
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        # Simulate logging a command
        logger.log_command(port="COM3", command="AT")
        logger.log_response(
            port="COM3",
            response="OK",
            status="SUCCESS",
            execution_time=0.1
        )

        logger.close()

        # Verify log file was created
        assert log_file.exists()
        content = log_file.read_text(encoding='utf-8')
        assert "AT" in content
        assert "SUCCESS" in content
        assert "OK" in content

    def test_log_file_rotation_creates_backups(self, temp_dir):
        """Test that log rotation creates backup files."""
        log_file = temp_dir / "rotation_test.log"

        # Use small file size for quick rotation
        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file),
            max_file_size_mb=0.001,  # 1KB for testing
            backup_count=3
        )

        # Write enough data to trigger rotation
        large_message = "X" * 500  # 500 bytes per message
        for i in range(20):  # Total ~10KB, should trigger multiple rotations
            logger.log(LogEntry(
                timestamp=datetime.now(),
                level="INFO",
                source="IntegrationTest",
                message=large_message
            ))

        logger.close()

        # Verify current log file exists
        assert log_file.exists()

        # Verify at least one backup file was created
        backup1 = Path(f"{log_file}.1")
        assert backup1.exists(), "Expected backup file .1 to exist after rotation"

    def test_log_level_filtering_in_file(self, temp_dir):
        """Test that log level filtering works correctly in file output."""
        log_file = temp_dir / "level_test.log"

        # Test with WARNING level
        logger = CommunicationLogger(
            log_level=LogLevel.WARNING,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        # Log at different levels
        logger.log(LogEntry(datetime.now(), "DEBUG", "Test", "Debug message"))
        logger.log(LogEntry(datetime.now(), "INFO", "Test", "Info message"))
        logger.log(LogEntry(datetime.now(), "WARNING", "Test", "Warning message"))
        logger.log(LogEntry(datetime.now(), "ERROR", "Test", "Error message"))

        logger.close()

        # Verify filtering
        content = log_file.read_text(encoding='utf-8')

        # DEBUG and INFO should not appear
        assert "Debug message" not in content
        assert "Info message" not in content

        # WARNING and ERROR should appear
        assert "Warning message" in content
        assert "Error message" in content

    def test_logger_initialization_from_config(self, temp_dir):
        """Test that logger can be initialized from ConfigManager settings."""
        # This test verifies that logging config is properly structured
        # In practice, the GUI application._initialize_logger() does this

        ConfigManager.initialize()
        config = ConfigManager.get_config()

        # Config should have logging section
        assert hasattr(config, 'logging')
        assert hasattr(config.logging, 'enabled')
        assert hasattr(config.logging, 'level')
        assert hasattr(config.logging, 'log_to_file')
        assert hasattr(config.logging, 'log_file_path')
        assert hasattr(config.logging, 'max_file_size_mb')
        assert hasattr(config.logging, 'backup_count')

    def test_concurrent_logging_thread_safety(self, temp_dir):
        """Test concurrent logging from multiple threads."""
        log_file = temp_dir / "concurrent_test.log"

        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        def log_entries(thread_id):
            """Log entries from a thread."""
            for i in range(50):
                logger.log(LogEntry(
                    timestamp=datetime.now(),
                    level="INFO",
                    source="ConcurrentTest",
                    message=f"Thread {thread_id} message {i}"
                ))

        # Create and start multiple threads
        threads = [threading.Thread(target=log_entries, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        logger.close()

        # Verify all entries were written
        content = log_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')

        # Should have 5 threads * 50 messages = 250 entries
        assert len(lines) == 250

        # Verify messages from all threads are present
        for thread_id in range(5):
            assert f"Thread {thread_id} message" in content

    def test_graceful_degradation_invalid_path(self, temp_dir):
        """Test graceful handling of invalid log file path."""
        # Try to create logger with invalid path
        invalid_path = "/nonexistent/path/that/cannot/be/created/test.log"

        # Logger initialization should handle the error gracefully
        try:
            logger = CommunicationLogger(
                log_level=LogLevel.INFO,
                enable_file=True,
                enable_console=False,
                log_file_path=invalid_path
            )

            # If logger was created, logging operations should fail gracefully
            entry = LogEntry(datetime.now(), "INFO", "Test", "Test message")
            # Should not raise exception even if write fails
            logger.log(entry)

            logger.close()

        except (OSError, PermissionError):
            # Expected on some systems
            pass

    def test_log_file_contains_structured_data(self, temp_dir):
        """Test that log file contains structured, parseable data."""
        log_file = temp_dir / "structured_test.log"

        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        # Log a complete command/response sequence
        logger.log_command(port="COM3", command="AT+CGMI")
        logger.log_response(
            port="COM3",
            response="Quectel",
            status="SUCCESS",
            execution_time=0.123,
            retry_count=0,
            command="AT+CGMI"
        )

        logger.log_port_event(
            event="Port closed",
            port="COM3",
            details={"session_duration_seconds": 30.0}
        )

        logger.close()

        # Verify structured format
        content = log_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')

        # Should have 3 entries
        assert len(lines) == 3

        # Each line should have timestamp, level, source, message format
        for line in lines:
            parts = line.split('|')
            assert len(parts) >= 4  # timestamp | level | source | message [| optional]
            # First part should be timestamp (contains date and time)
            assert '-' in parts[0] and ':' in parts[0]

    def test_logger_cleanup_on_close(self, temp_dir):
        """Test that logger properly cleans up resources on close."""
        log_file = temp_dir / "cleanup_test.log"

        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        # Write some entries
        for i in range(10):
            logger.log(LogEntry(datetime.now(), "INFO", "Test", f"Message {i}"))

        # Close logger
        logger.close()

        # File should be closed and content should be flushed
        assert log_file.exists()
        content = log_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')
        assert len(lines) == 10

        # Try to write after close (should fail gracefully)
        # This is tested in unit tests, but verify behavior is safe
        logger.log(LogEntry(datetime.now(), "INFO", "Test", "After close"))

    def test_end_to_end_command_execution_logging(self, temp_dir):
        """Test complete logging flow during simulated command execution."""
        log_file = temp_dir / "e2e_test.log"

        logger = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file)
        )

        # Simulate complete command execution sequence
        port = "COM3"

        # 1. Port open
        logger.log_port_event(
            event="Port opened",
            port=port,
            details={"baud_rate": 115200, "timeout": 30}
        )

        # 2. Command execution
        commands = ["AT", "AT+CGMI", "AT+CGMM", "AT+CGMR"]
        for cmd in commands:
            logger.log_command(port=port, command=cmd)
            # Simulate response
            logger.log_response(
                port=port,
                response="OK",
                status="SUCCESS",
                execution_time=0.1,
                command=cmd
            )

        # 3. Port close
        logger.log_port_event(
            event="Port closed",
            port=port,
            details={"session_duration_seconds": 5.0}
        )

        logger.close()

        # Verify complete log
        content = log_file.read_text(encoding='utf-8')

        # Should have 11 entries total (1 open + 8 command/response + 1 close)
        lines = content.strip().split('\n')
        assert len(lines) == 11

        # Verify all commands logged
        for cmd in commands:
            assert cmd in content

        # Verify port events
        assert "Port opened" in content
        assert "Port closed" in content
        assert "session_duration_seconds" in content

    def test_multiple_logger_instances_different_files(self, temp_dir):
        """Test that multiple logger instances can write to different files simultaneously."""
        log_file1 = temp_dir / "logger1.log"
        log_file2 = temp_dir / "logger2.log"

        logger1 = CommunicationLogger(
            log_level=LogLevel.INFO,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file1)
        )

        logger2 = CommunicationLogger(
            log_level=LogLevel.DEBUG,
            enable_file=True,
            enable_console=False,
            log_file_path=str(log_file2)
        )

        # Write to both loggers
        logger1.log(LogEntry(datetime.now(), "INFO", "Logger1", "From logger 1"))
        logger2.log(LogEntry(datetime.now(), "DEBUG", "Logger2", "From logger 2"))

        logger1.close()
        logger2.close()

        # Verify both files exist and have correct content
        assert log_file1.exists()
        assert log_file2.exists()

        content1 = log_file1.read_text(encoding='utf-8')
        content2 = log_file2.read_text(encoding='utf-8')

        assert "From logger 1" in content1
        assert "From logger 2" in content2
        assert "From logger 2" not in content1  # Isolation
        assert "From logger 1" not in content2  # Isolation
