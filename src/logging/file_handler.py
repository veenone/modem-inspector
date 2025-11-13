"""File handler for logging with automatic rotation.

This module provides a FileHandler class for writing log entries to files
with automatic rotation when size limits are exceeded. Uses thread-safe
operations and buffered I/O for performance.
"""

from pathlib import Path
from threading import Lock
from typing import Optional
import os
import shutil
from datetime import datetime

from src.logging.log_models import LogEntry


class FileHandler:
    """Thread-safe file handler with automatic log rotation.

    Writes log entries to file with buffered I/O for performance. Automatically
    rotates log files when they exceed the maximum size, keeping a configurable
    number of backup files.

    Attributes:
        log_file_path: Path to the current log file
        max_size_bytes: Maximum file size in bytes before rotation
        backup_count: Number of backup files to keep

    Example:
        >>> handler = FileHandler("~/.modem-inspector/logs/comm.log", max_size_mb=10, backup_count=5)
        >>> handler.write(log_entry)
        >>> handler.close()
    """

    def __init__(self, log_file_path: str, max_size_mb: int = 10, backup_count: int = 5):
        """Initialize FileHandler with path and rotation settings.

        Creates the log directory if it doesn't exist. Opens the log file
        in append mode with buffering enabled.

        Args:
            log_file_path: Path to log file (supports ~ expansion)
            max_size_mb: Maximum file size in MB before rotation (default: 10)
            backup_count: Number of rotated backups to keep (default: 5)

        Raises:
            OSError: If log directory cannot be created or file cannot be opened
        """
        self.log_file_path = Path(log_file_path).expanduser().resolve()
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self._lock = Lock()
        self._file_handle: Optional[object] = None
        self._is_closed = False

        # Create log directory if it doesn't exist
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open file in append mode with buffering
        self._open_file()

    def _open_file(self) -> None:
        """Open log file in append mode with UTF-8 encoding.

        Uses buffered I/O for performance. Creates file if it doesn't exist.
        """
        try:
            self._file_handle = open(
                self.log_file_path,
                mode='a',
                encoding='utf-8',
                buffering=8192  # 8KB buffer for performance
            )
        except OSError as e:
            # Log to stderr if file cannot be opened
            import sys
            print(f"ERROR: Failed to open log file {self.log_file_path}: {e}", file=sys.stderr)
            self._file_handle = None

    def write(self, entry: LogEntry) -> bool:
        """Write log entry to file with automatic rotation.

        Thread-safe operation using a lock. Checks file size before writing
        and rotates if necessary. Handles write errors gracefully.

        Args:
            entry: LogEntry to write to file

        Returns:
            True if write successful, False if write failed

        Example:
            >>> success = handler.write(log_entry)
            >>> if not success:
            ...     print("Write failed")
        """
        if self._is_closed or self._file_handle is None:
            return False

        with self._lock:
            try:
                # Check if rotation is needed before writing
                self._rotate_if_needed()

                # Write log entry as formatted string
                log_line = entry.to_string() + '\n'
                self._file_handle.write(log_line)

                # Periodic flush (every write for reliability)
                self._file_handle.flush()

                return True

            except OSError as e:
                # Handle write errors gracefully - don't crash
                import sys
                print(f"ERROR: Failed to write log entry: {e}", file=sys.stderr)
                return False

    def _rotate_if_needed(self) -> None:
        """Check file size and rotate if exceeds maximum.

        Renames current log file to .log.1, shifts existing backups
        (.log.1 -> .log.2, etc.), and opens a new log file. Deletes
        oldest backup if backup_count exceeded.

        Thread-safe: Caller must hold self._lock.
        """
        if self._file_handle is None:
            return

        try:
            # Get current file size
            current_size = os.path.getsize(self.log_file_path)

            if current_size < self.max_size_bytes:
                return  # No rotation needed

            # Close current file
            self._file_handle.close()

            # Rotate backup files (.log.4 -> .log.5, .log.3 -> .log.4, etc.)
            for i in range(self.backup_count - 1, 0, -1):
                src = Path(f"{self.log_file_path}.{i}")
                dst = Path(f"{self.log_file_path}.{i + 1}")

                if src.exists():
                    if dst.exists():
                        dst.unlink()  # Remove old backup
                    src.rename(dst)

            # Delete oldest backup if it exists
            oldest_backup = Path(f"{self.log_file_path}.{self.backup_count + 1}")
            if oldest_backup.exists():
                oldest_backup.unlink()

            # Rename current log to .log.1
            backup_path = Path(f"{self.log_file_path}.1")
            if backup_path.exists():
                backup_path.unlink()
            self.log_file_path.rename(backup_path)

            # Open new log file
            self._open_file()

        except OSError as e:
            # Rotation failed - try to continue with current file
            import sys
            print(f"WARNING: Log rotation failed: {e}", file=sys.stderr)

            # Try to reopen current file
            if self._file_handle is None or self._file_handle.closed:
                self._open_file()

    def flush(self) -> None:
        """Flush buffered writes to disk.

        Forces immediate write of all buffered data. Thread-safe operation.
        """
        if self._file_handle is None or self._is_closed:
            return

        with self._lock:
            try:
                if self._file_handle and not self._file_handle.closed:
                    self._file_handle.flush()
                    os.fsync(self._file_handle.fileno())
            except OSError as e:
                import sys
                print(f"ERROR: Failed to flush log file: {e}", file=sys.stderr)

    def close(self) -> None:
        """Close log file and flush all buffers.

        Ensures all buffered data is written to disk before closing.
        Thread-safe operation. Idempotent - safe to call multiple times.
        """
        if self._is_closed:
            return

        with self._lock:
            if self._file_handle and not self._file_handle.closed:
                try:
                    self._file_handle.flush()
                    self._file_handle.close()
                except OSError as e:
                    import sys
                    print(f"ERROR: Failed to close log file: {e}", file=sys.stderr)
                finally:
                    self._file_handle = None
                    self._is_closed = True

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures file is closed."""
        self.close()
        return False
