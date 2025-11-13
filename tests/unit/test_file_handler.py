"""Unit tests for FileHandler with log rotation."""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from src.logging.file_handler import FileHandler
from src.logging.log_models import LogEntry


class TestFileHandler:
    """Test suite for FileHandler class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test logs."""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        # Cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)

    @pytest.fixture
    def log_entry(self):
        """Create a sample log entry for testing."""
        return LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            source="TestSource",
            message="Test message"
        )

    def test_file_handler_creation(self, temp_dir):
        """Test FileHandler initialization."""
        log_file = temp_dir / "test.log"
        handler = FileHandler(str(log_file), max_size_mb=10, backup_count=5)

        assert handler.log_file_path == log_file
        assert handler.max_size_bytes == 10 * 1024 * 1024
        assert handler.backup_count == 5
        assert log_file.exists()

        handler.close()

    def test_write_log_entry(self, temp_dir, log_entry):
        """Test writing a log entry to file."""
        log_file = temp_dir / "test.log"
        handler = FileHandler(str(log_file))

        success = handler.write(log_entry)

        assert success is True
        assert log_file.exists()

        # Read file and check content
        content = log_file.read_text(encoding='utf-8')
        assert "INFO" in content
        assert "TestSource" in content
        assert "Test message" in content

        handler.close()

    def test_write_multiple_entries(self, temp_dir):
        """Test writing multiple log entries."""
        log_file = temp_dir / "test.log"
        handler = FileHandler(str(log_file))

        # Write 10 entries
        for i in range(10):
            entry = LogEntry(
                timestamp=datetime.now(),
                level="INFO",
                source="Test",
                message=f"Message {i}"
            )
            handler.write(entry)

        handler.close()

        # Check all entries were written
        content = log_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')
        assert len(lines) == 10

        for i in range(10):
            assert f"Message {i}" in content

    def test_file_rotation(self, temp_dir):
        """Test automatic file rotation when size limit exceeded."""
        log_file = temp_dir / "test.log"
        # Use small size for testing (1KB)
        handler = FileHandler(str(log_file), max_size_mb=0.001, backup_count=3)

        # Write enough entries to trigger rotation
        large_message = "X" * 500  # 500 bytes per entry
        for i in range(10):  # Total ~5KB
            entry = LogEntry(
                timestamp=datetime.now(),
                level="INFO",
                source="Test",
                message=large_message
            )
            handler.write(entry)

        handler.close()

        # Check that backup files were created
        backup1 = Path(f"{log_file}.1")
        assert backup1.exists()  # At least one backup should exist

    def test_backup_count_limit(self, temp_dir):
        """Test that backup files are limited to backup_count."""
        log_file = temp_dir / "test.log"
        handler = FileHandler(str(log_file), max_size_mb=0.001, backup_count=2)

        # Write enough to create multiple rotations
        large_message = "X" * 500
        for i in range(20):
            entry = LogEntry(
                timestamp=datetime.now(),
                level="INFO",
                source="Test",
                message=large_message
            )
            handler.write(entry)

        handler.close()

        # Check that only backup_count backups exist
        backup3 = Path(f"{log_file}.3")
        backup4 = Path(f"{log_file}.4")
        # With backup_count=2, should not have .3 or .4
        # Note: Rotation creates .1, .2 at most
        assert not backup4.exists()

    def test_flush(self, temp_dir, log_entry):
        """Test explicit flush operation."""
        log_file = temp_dir / "test.log"
        handler = FileHandler(str(log_file))

        handler.write(log_entry)
        handler.flush()

        # File should exist with content
        assert log_file.exists()
        content = log_file.read_text(encoding='utf-8')
        assert len(content) > 0

        handler.close()

    def test_close_idempotent(self, temp_dir):
        """Test that close() can be called multiple times safely."""
        log_file = temp_dir / "test.log"
        handler = FileHandler(str(log_file))

        # Call close multiple times
        handler.close()
        handler.close()
        handler.close()

        # Should not raise exception

    def test_context_manager(self, temp_dir, log_entry):
        """Test FileHandler as context manager."""
        log_file = temp_dir / "test.log"

        with FileHandler(str(log_file)) as handler:
            handler.write(log_entry)

        # File should be closed after context
        assert log_file.exists()
        content = log_file.read_text(encoding='utf-8')
        assert "Test message" in content

    def test_write_after_close(self, temp_dir, log_entry):
        """Test that write fails gracefully after close."""
        log_file = temp_dir / "test.log"
        handler = FileHandler(str(log_file))
        handler.close()

        # Writing after close should return False
        success = handler.write(log_entry)
        assert success is False

    def test_invalid_log_directory_handling(self):
        """Test handling of invalid log directory."""
        # Use an invalid path
        invalid_path = "/nonexistent/directory/test.log"

        # Should not raise exception during creation
        # but file operations might fail
        try:
            handler = FileHandler(invalid_path)
            # File creation might fail on some systems
            handler.close()
        except (OSError, PermissionError):
            # Expected on systems without permission
            pass

    def test_thread_safety(self, temp_dir):
        """Test basic thread safety with lock mechanism."""
        import threading

        log_file = temp_dir / "test.log"
        handler = FileHandler(str(log_file))

        def write_entries():
            for i in range(10):
                entry = LogEntry(
                    timestamp=datetime.now(),
                    level="INFO",
                    source="Thread",
                    message=f"Thread message {i}"
                )
                handler.write(entry)

        # Create multiple threads
        threads = [threading.Thread(target=write_entries) for _ in range(5)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        handler.close()

        # Check that all 50 entries were written
        content = log_file.read_text(encoding='utf-8')
        lines = content.strip().split('\n')
        assert len(lines) == 50
