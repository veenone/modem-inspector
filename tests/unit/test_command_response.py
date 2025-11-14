"""Unit tests for CommandResponse data model.

Tests the immutable CommandResponse dataclass including:
- Immutability (frozen=True)
- Automatic timestamp generation
- Helper methods (get_response_text, is_successful)
- String representation
"""

import pytest
import time
from dataclasses import FrozenInstanceError
from src.core.command_response import CommandResponse, ResponseStatus


class TestResponseStatus:
    """Test ResponseStatus enum."""

    def test_status_values(self):
        """Test enum values are correct."""
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.ERROR.value == "error"
        assert ResponseStatus.TIMEOUT.value == "timeout"

    def test_status_members(self):
        """Test all expected enum members exist."""
        assert len(ResponseStatus) == 3
        assert ResponseStatus.SUCCESS in ResponseStatus
        assert ResponseStatus.ERROR in ResponseStatus
        assert ResponseStatus.TIMEOUT in ResponseStatus


class TestCommandResponse:
    """Test CommandResponse dataclass."""

    def test_create_minimal_response(self):
        """Test creating response with minimal required fields."""
        response = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05
        )

        assert response.command == "AT"
        assert response.raw_response == ["OK"]
        assert response.status == ResponseStatus.SUCCESS
        assert response.execution_time == 0.05
        assert response.error_code is None
        assert response.error_message is None
        assert response.retry_count == 0
        assert isinstance(response.timestamp, float)
        assert response.timestamp > 0

    def test_create_full_response(self):
        """Test creating response with all fields."""
        response = CommandResponse(
            command="AT+CEREG?",
            raw_response=["+CEREG: 0,1", "ERROR"],
            status=ResponseStatus.ERROR,
            execution_time=0.15,
            error_code="123",
            error_message="Network error",
            retry_count=2,
            timestamp=1234567890.0
        )

        assert response.command == "AT+CEREG?"
        assert response.raw_response == ["+CEREG: 0,1", "ERROR"]
        assert response.status == ResponseStatus.ERROR
        assert response.execution_time == 0.15
        assert response.error_code == "123"
        assert response.error_message == "Network error"
        assert response.retry_count == 2
        assert response.timestamp == 1234567890.0

    def test_immutability(self):
        """Test response cannot be modified after creation (frozen=True)."""
        response = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05
        )

        # Attempt to modify should raise FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            response.command = "AT+CGMI"

        with pytest.raises(FrozenInstanceError):
            response.status = ResponseStatus.ERROR

        with pytest.raises(FrozenInstanceError):
            response.retry_count = 5

    def test_automatic_timestamp(self):
        """Test timestamp is generated automatically."""
        before = time.time()
        response = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05
        )
        after = time.time()

        # Timestamp should be between before and after
        assert before <= response.timestamp <= after

    def test_get_response_text_single_line(self):
        """Test get_response_text with single line response."""
        response = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05
        )

        assert response.get_response_text() == "OK"

    def test_get_response_text_multi_line(self):
        """Test get_response_text with multi-line response."""
        response = CommandResponse(
            command="AT+CGMI",
            raw_response=["Quectel", "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.12
        )

        assert response.get_response_text() == "Quectel\nOK"

    def test_get_response_text_empty(self):
        """Test get_response_text with empty response."""
        response = CommandResponse(
            command="AT",
            raw_response=[],
            status=ResponseStatus.TIMEOUT,
            execution_time=30.0
        )

        assert response.get_response_text() == ""

    def test_get_response_text_with_special_chars(self):
        """Test get_response_text preserves special characters."""
        response = CommandResponse(
            command="AT+CGMI",
            raw_response=["Line 1\r\n", "Line 2\t", "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.08
        )

        assert response.get_response_text() == "Line 1\r\n\nLine 2\t\nOK"

    def test_is_successful_true(self):
        """Test is_successful returns True for SUCCESS status."""
        response = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05
        )

        assert response.is_successful() is True

    def test_is_successful_false_error(self):
        """Test is_successful returns False for ERROR status."""
        response = CommandResponse(
            command="AT+INVALID",
            raw_response=["ERROR"],
            status=ResponseStatus.ERROR,
            execution_time=0.05
        )

        assert response.is_successful() is False

    def test_is_successful_false_timeout(self):
        """Test is_successful returns False for TIMEOUT status."""
        response = CommandResponse(
            command="AT+COPS=?",
            raw_response=[],
            status=ResponseStatus.TIMEOUT,
            execution_time=30.0
        )

        assert response.is_successful() is False

    def test_str_success(self):
        """Test string representation for success response."""
        response = CommandResponse(
            command="AT+CGMI",
            raw_response=["Quectel", "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.123
        )

        result = str(response)
        assert "[success]" in result
        assert "AT+CGMI" in result
        assert "2 lines" in result
        assert "0.123s" in result

    def test_str_error_with_code(self):
        """Test string representation for error with code."""
        response = CommandResponse(
            command="AT+CEREG?",
            raw_response=["+CME ERROR: 30"],
            status=ResponseStatus.ERROR,
            execution_time=0.05,
            error_code="30",
            error_message="No network service"
        )

        result = str(response)
        assert "[error]" in result
        assert "AT+CEREG?" in result
        assert "30" in result
        assert "No network service" in result
        assert "0.05" in result

    def test_str_error_without_code(self):
        """Test string representation for error without code."""
        response = CommandResponse(
            command="AT+INVALID",
            raw_response=["ERROR"],
            status=ResponseStatus.ERROR,
            execution_time=0.05
        )

        result = str(response)
        assert "[error]" in result
        assert "AT+INVALID" in result
        assert "0.05" in result

    def test_str_timeout(self):
        """Test string representation for timeout."""
        response = CommandResponse(
            command="AT+COPS=?",
            raw_response=[],
            status=ResponseStatus.TIMEOUT,
            execution_time=30.0,
            retry_count=3
        )

        result = str(response)
        assert "[timeout]" in result
        assert "AT+COPS=?" in result
        assert "3 retries" in result
        assert "30.0" in result

    def test_equality(self):
        """Test response equality comparison."""
        response1 = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05,
            timestamp=1234567890.0
        )

        response2 = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05,
            timestamp=1234567890.0
        )

        # Frozen dataclasses with same values should be equal
        assert response1 == response2

    def test_inequality(self):
        """Test response inequality."""
        response1 = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05
        )

        response2 = CommandResponse(
            command="AT+CGMI",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05
        )

        assert response1 != response2

    def test_not_hashable(self):
        """Test response is not hashable due to list field.

        CommandResponse contains raw_response which is a list.
        Lists are mutable and therefore not hashable.
        This is expected behavior - responses should not be used as dict keys.
        """
        response = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.05,
            timestamp=1234567890.0
        )

        # Should not be able to hash (contains list)
        with pytest.raises(TypeError, match="unhashable type"):
            hash(response)

        # Should not be able to add to set
        with pytest.raises(TypeError, match="unhashable type"):
            {response}

        # Should not be able to use as dict key
        with pytest.raises(TypeError, match="unhashable type"):
            {response: "value"}

    def test_large_response(self):
        """Test handling large multi-line responses."""
        large_response = [f"Line {i}" for i in range(1000)]
        large_response.append("OK")

        response = CommandResponse(
            command="AT+LARGE",
            raw_response=large_response,
            status=ResponseStatus.SUCCESS,
            execution_time=1.5
        )

        assert len(response.raw_response) == 1001
        assert response.get_response_text().count('\n') == 1000

    def test_execution_time_precision(self):
        """Test execution time maintains precision."""
        response = CommandResponse(
            command="AT",
            raw_response=["OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.001234567
        )

        # Should preserve precision
        assert response.execution_time == 0.001234567

    def test_unicode_response(self):
        """Test handling Unicode characters in responses."""
        response = CommandResponse(
            command="AT+CGMI",
            raw_response=["Manufacturer: Société™", "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        )

        text = response.get_response_text()
        assert "Société™" in text

    def test_retry_count_values(self):
        """Test various retry count values."""
        for retry_count in [0, 1, 2, 3, 10]:
            response = CommandResponse(
                command="AT",
                raw_response=["OK"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.05,
                retry_count=retry_count
            )
            assert response.retry_count == retry_count
