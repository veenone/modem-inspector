"""Unit tests for LogEntry dataclass."""

import pytest
from datetime import datetime
import json

from src.logging.log_models import LogEntry


class TestLogEntry:
    """Test suite for LogEntry dataclass."""

    def test_log_entry_creation(self):
        """Test basic LogEntry creation."""
        timestamp = datetime.now()
        entry = LogEntry(
            timestamp=timestamp,
            level="INFO",
            source="TestSource",
            message="Test message"
        )

        assert entry.timestamp == timestamp
        assert entry.level == "INFO"
        assert entry.source == "TestSource"
        assert entry.message == "Test message"
        assert entry.details is None
        assert entry.port is None

    def test_log_entry_with_optional_fields(self):
        """Test LogEntry with all optional fields."""
        timestamp = datetime.now()
        entry = LogEntry(
            timestamp=timestamp,
            level="DEBUG",
            source="ATExecutor",
            message="Command executed",
            details={"key": "value"},
            port="COM3",
            command="AT+CGMI",
            response="Quectel",
            status="SUCCESS",
            execution_time=0.123,
            retry_count=0,
            error=None
        )

        assert entry.command == "AT+CGMI"
        assert entry.response == "Quectel"
        assert entry.status == "SUCCESS"
        assert entry.execution_time == 0.123
        assert entry.retry_count == 0

    def test_log_entry_immutable(self):
        """Test that LogEntry is frozen (immutable)."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level="INFO",
            source="Test",
            message="Test"
        )

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            entry.level = "DEBUG"

    def test_to_dict(self):
        """Test LogEntry.to_dict() serialization."""
        timestamp = datetime.now()
        entry = LogEntry(
            timestamp=timestamp,
            level="INFO",
            source="TestSource",
            message="Test message",
            port="COM3",
            command="AT",
            response="OK"
        )

        result = entry.to_dict()

        assert isinstance(result, dict)
        assert result["level"] == "INFO"
        assert result["source"] == "TestSource"
        assert result["message"] == "Test message"
        assert result["port"] == "COM3"
        assert result["command"] == "AT"
        assert result["response"] == "OK"
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)  # ISO 8601 string

    def test_to_string(self):
        """Test LogEntry.to_string() formatting."""
        timestamp = datetime(2025, 1, 12, 10, 30, 15, 123000)
        entry = LogEntry(
            timestamp=timestamp,
            level="INFO",
            source="ATExecutor",
            message="Command executed",
            command="AT+CGMI",
            status="SUCCESS",
            execution_time=0.123,
            retry_count=2
        )

        result = entry.to_string()

        assert "2025-01-12 10:30:15.123" in result
        assert "INFO" in result
        assert "ATExecutor" in result
        assert "Command executed" in result
        assert "CMD: AT+CGMI" in result
        assert "STATUS: SUCCESS" in result
        assert "TIME: 0.123s" in result
        assert "RETRIES: 2" in result

    def test_to_json(self):
        """Test LogEntry.to_json() serialization."""
        timestamp = datetime.now()
        entry = LogEntry(
            timestamp=timestamp,
            level="WARNING",
            source="SerialHandler",
            message="Port timeout"
        )

        result = entry.to_json()

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["level"] == "WARNING"
        assert parsed["source"] == "SerialHandler"
        assert parsed["message"] == "Port timeout"

    def test_from_dict(self):
        """Test LogEntry.from_dict() deserialization."""
        data = {
            "timestamp": "2025-01-12T10:30:15.123000",
            "level": "ERROR",
            "source": "ATExecutor",
            "message": "Command failed",
            "details": None,
            "port": "COM3",
            "command": "AT+CGMR",
            "response": None,
            "status": "TIMEOUT",
            "execution_time": 30.0,
            "retry_count": 3,
            "error": "Timeout after 3 retries"
        }

        entry = LogEntry.from_dict(data)

        assert entry.level == "ERROR"
        assert entry.source == "ATExecutor"
        assert entry.message == "Command failed"
        assert entry.port == "COM3"
        assert entry.command == "AT+CGMR"
        assert entry.status == "TIMEOUT"
        assert entry.execution_time == 30.0
        assert entry.retry_count == 3
        assert entry.error == "Timeout after 3 retries"

    def test_from_json(self):
        """Test LogEntry.from_json() deserialization."""
        json_str = json.dumps({
            "timestamp": "2025-01-12T10:30:15.123000",
            "level": "DEBUG",
            "source": "SerialHandler",
            "message": "Data received",
            "details": {"bytes": 128},
            "port": "COM3",
            "command": None,
            "response": None,
            "status": None,
            "execution_time": None,
            "retry_count": None,
            "error": None
        })

        entry = LogEntry.from_json(json_str)

        assert entry.level == "DEBUG"
        assert entry.source == "SerialHandler"
        assert entry.message == "Data received"
        assert entry.details == {"bytes": 128}
        assert entry.port == "COM3"

    def test_round_trip_serialization(self):
        """Test that serialization and deserialization produce equivalent objects."""
        timestamp = datetime(2025, 1, 12, 10, 30, 15, 123000)
        original = LogEntry(
            timestamp=timestamp,
            level="INFO",
            source="TestSource",
            message="Test message",
            port="COM3",
            command="AT",
            response="OK",
            status="SUCCESS",
            execution_time=0.5,
            retry_count=0
        )

        # Round trip via dict
        dict_data = original.to_dict()
        from_dict = LogEntry.from_dict(dict_data)

        assert from_dict.level == original.level
        assert from_dict.source == original.source
        assert from_dict.message == original.message
        assert from_dict.port == original.port
        assert from_dict.command == original.command
        assert from_dict.response == original.response
        assert from_dict.status == original.status
        assert from_dict.execution_time == original.execution_time
        assert from_dict.retry_count == original.retry_count

        # Round trip via JSON
        json_data = original.to_json()
        from_json = LogEntry.from_json(json_data)

        assert from_json.level == original.level
        assert from_json.source == original.source
        assert from_json.message == original.message
