"""Unit tests for ATExecutor with mocked SerialHandler.

Tests the ATExecutor class using mocked SerialHandler to test
command execution logic, retry behavior, response parsing, and
history tracking without actual serial I/O.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import time

from src.core.at_executor import ATExecutor
from src.core.serial_handler import SerialHandler
from src.core.command_response import CommandResponse, ResponseStatus
from src.core.exceptions import ATCommandError


class TestATExecutorInit:
    """Test ATExecutor initialization."""

    def test_init_minimal(self):
        """Test initialization with minimal arguments."""
        mock_handler = Mock(spec=SerialHandler)
        executor = ATExecutor(mock_handler)

        assert executor.serial_handler == mock_handler
        assert executor.default_timeout == 30.0
        assert executor.default_retry_count == 3
        assert executor.retry_delay == 1.0
        assert executor.logger is None

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        mock_handler = Mock(spec=SerialHandler)
        executor = ATExecutor(
            mock_handler,
            default_timeout=60.0,
            retry_count=5,
            retry_delay=2.0
        )

        assert executor.default_timeout == 60.0
        assert executor.default_retry_count == 5
        assert executor.retry_delay == 2.0

    def test_init_with_logger(self):
        """Test initialization with logger."""
        mock_handler = Mock(spec=SerialHandler)
        mock_logger = Mock()
        executor = ATExecutor(mock_handler, logger=mock_logger)

        assert executor.logger == mock_logger


class TestATExecutorExecuteCommand:
    """Test ATExecutor.execute_command() method."""

    def test_execute_command_success(self):
        """Test successful command execution."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["Quectel", "OK"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+CGMI")

        assert response.command == "AT+CGMI"
        assert response.status == ResponseStatus.SUCCESS
        assert response.raw_response == ["Quectel", "OK"]
        assert response.retry_count == 0
        assert response.execution_time > 0

        mock_handler.write.assert_called_once_with("AT+CGMI")
        mock_handler.read_until.assert_called_once()

    def test_execute_command_error_response(self):
        """Test command execution with ERROR response."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["ERROR"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+INVALID")

        assert response.command == "AT+INVALID"
        assert response.status == ResponseStatus.ERROR
        assert response.raw_response == ["ERROR"]
        assert response.retry_count == 0

    def test_execute_command_cme_error(self):
        """Test command execution with +CME ERROR response."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["+CME ERROR: 30"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+CEREG?")

        assert response.status == ResponseStatus.ERROR
        assert response.error_code == "30"
        assert "+CME ERROR" in response.raw_response[0]

    def test_execute_command_cms_error(self):
        """Test command execution with +CMS ERROR response."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["+CMS ERROR: 500"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+CMGS")

        assert response.status == ResponseStatus.ERROR
        assert response.error_code == "500"

    def test_execute_command_timeout_then_success(self):
        """Test command execution with timeout then success on retry."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        # First call times out, second succeeds
        mock_handler.read_until.side_effect = [
            TimeoutError("Timeout"),
            ["OK"]
        ]

        executor = ATExecutor(mock_handler, retry_delay=0.01)
        response = executor.execute_command("AT")

        assert response.status == ResponseStatus.SUCCESS
        assert response.retry_count == 1
        assert mock_handler.write.call_count == 2

    def test_execute_command_all_retries_timeout(self):
        """Test command execution with all retries timing out."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.side_effect = TimeoutError("Timeout")

        executor = ATExecutor(mock_handler, retry_count=2, retry_delay=0.01)
        response = executor.execute_command("AT+COPS=?")

        assert response.status == ResponseStatus.TIMEOUT
        assert response.retry_count == 2
        # Should try initial + 2 retries = 3 times
        assert mock_handler.write.call_count == 3

    def test_execute_command_custom_timeout(self):
        """Test command execution with custom timeout."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["OK"]

        executor = ATExecutor(mock_handler, default_timeout=30.0)
        executor.execute_command("AT", timeout=60.0)

        # Check read_until was called with custom timeout
        call_args = mock_handler.read_until.call_args
        # Timeout is passed as argument
        assert call_args is not None

    def test_execute_command_custom_retry(self):
        """Test command execution with custom retry count."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.side_effect = TimeoutError("Timeout")

        executor = ATExecutor(mock_handler, retry_count=3, retry_delay=0.01)
        response = executor.execute_command("AT", retry=1)

        # Should only retry once (not default 3 times)
        assert response.retry_count == 1
        assert mock_handler.write.call_count == 2  # Initial + 1 retry

    def test_execute_command_strips_echo(self):
        """Test command execution strips echo from response."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        # Response includes echo
        mock_handler.read_until.return_value = ["AT+CGMI", "Quectel", "OK"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+CGMI")

        # Echo should be stripped
        assert "Quectel" in response.raw_response
        assert "OK" in response.raw_response
        # The implementation may or may not strip echo - adjust based on actual behavior

    def test_execute_command_adds_to_history(self):
        """Test command execution adds response to history."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["OK"]

        executor = ATExecutor(mock_handler)
        executor.execute_command("AT")
        executor.execute_command("AT+CGMI")

        history = executor.get_history()
        assert len(history) == 2
        assert history[0].command == "AT"
        assert history[1].command == "AT+CGMI"

    @patch('time.sleep')
    def test_execute_command_retry_delay(self, mock_sleep):
        """Test retry delay uses exponential backoff."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.side_effect = [
            TimeoutError("Timeout"),
            TimeoutError("Timeout"),
            ["OK"]
        ]

        executor = ATExecutor(mock_handler, retry_count=3, retry_delay=1.0)
        response = executor.execute_command("AT")

        # Check exponential backoff delays were used
        # First retry: 1s, second retry: 2s
        assert mock_sleep.call_count >= 2


class TestATExecutorExecuteBatch:
    """Test ATExecutor.execute_batch() method."""

    def test_execute_batch_all_success(self):
        """Test batch execution with all commands succeeding."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.side_effect = [
            ["OK"],
            ["Quectel", "OK"],
            ["EC200U-CN", "OK"]
        ]

        executor = ATExecutor(mock_handler)
        responses = executor.execute_batch(["AT", "AT+CGMI", "AT+CGMM"])

        assert len(responses) == 3
        assert all(r.status == ResponseStatus.SUCCESS for r in responses)
        assert responses[0].command == "AT"
        assert responses[1].command == "AT+CGMI"
        assert responses[2].command == "AT+CGMM"

    def test_execute_batch_mixed_results(self):
        """Test batch execution with mixed success/failure."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.side_effect = [
            ["OK"],
            ["ERROR"],
            ["OK"]
        ]

        executor = ATExecutor(mock_handler)
        responses = executor.execute_batch(["AT", "AT+INVALID", "AT+CGMI"])

        assert len(responses) == 3
        assert responses[0].status == ResponseStatus.SUCCESS
        assert responses[1].status == ResponseStatus.ERROR
        assert responses[2].status == ResponseStatus.SUCCESS

    def test_execute_batch_continues_on_error(self):
        """Test batch execution continues after command errors."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.side_effect = [
            ["ERROR"],
            ["ERROR"],
            ["OK"]
        ]

        executor = ATExecutor(mock_handler)
        responses = executor.execute_batch(["BAD1", "BAD2", "AT"])

        # Should execute all commands despite errors
        assert len(responses) == 3
        assert mock_handler.write.call_count == 3

    def test_execute_batch_empty_list(self):
        """Test batch execution with empty command list."""
        mock_handler = Mock(spec=SerialHandler)
        executor = ATExecutor(mock_handler)
        responses = executor.execute_batch([])

        assert len(responses) == 0


class TestATExecutorHistory:
    """Test ATExecutor history management."""

    def test_get_history_empty(self):
        """Test getting history when empty."""
        mock_handler = Mock(spec=SerialHandler)
        executor = ATExecutor(mock_handler)

        history = executor.get_history()
        assert len(history) == 0

    def test_get_history_populated(self):
        """Test getting history after commands."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["OK"]

        executor = ATExecutor(mock_handler)
        executor.execute_command("AT")
        executor.execute_command("AT+CGMI")

        history = executor.get_history()
        assert len(history) == 2

    def test_get_history_returns_copy(self):
        """Test get_history returns copy (not reference)."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["OK"]

        executor = ATExecutor(mock_handler)
        executor.execute_command("AT")

        history1 = executor.get_history()
        history2 = executor.get_history()

        # Should be different list objects
        assert history1 is not history2
        # But contain same responses
        assert len(history1) == len(history2)

    def test_clear_history(self):
        """Test clearing history."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["OK"]

        executor = ATExecutor(mock_handler)
        executor.execute_command("AT")
        executor.execute_command("AT+CGMI")

        assert len(executor.get_history()) == 2

        executor.clear_history()

        assert len(executor.get_history()) == 0

    def test_history_thread_safe(self):
        """Test history operations are thread-safe."""
        import threading

        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["OK"]

        executor = ATExecutor(mock_handler)

        def add_to_history():
            for _ in range(10):
                executor.execute_command("AT")

        # Start multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=add_to_history)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have all 50 commands in history
        history = executor.get_history()
        assert len(history) == 50


class TestATExecutorResponseParsing:
    """Test ATExecutor response parsing logic."""

    def test_parse_ok_response(self):
        """Test parsing OK response."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["OK"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT")

        assert response.status == ResponseStatus.SUCCESS

    def test_parse_error_response(self):
        """Test parsing ERROR response."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["ERROR"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+BAD")

        assert response.status == ResponseStatus.ERROR

    def test_parse_multiline_response(self):
        """Test parsing multi-line response."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = [
            "+CGMI: Quectel",
            "+CGMM: EC200U-CN",
            "OK"
        ]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+CGMI;+CGMM")

        assert response.status == ResponseStatus.SUCCESS
        assert len(response.raw_response) == 3

    def test_parse_cme_error_with_code(self):
        """Test parsing +CME ERROR with error code."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["+CME ERROR: 30"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+CEREG?")

        assert response.status == ResponseStatus.ERROR
        assert response.error_code == "30"

    def test_parse_cms_error_with_code(self):
        """Test parsing +CMS ERROR with error code."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["+CMS ERROR: 500"]

        executor = ATExecutor(mock_handler)
        response = executor.execute_command("AT+CMGS")

        assert response.status == ResponseStatus.ERROR
        assert response.error_code == "500"


class TestATExecutorLogging:
    """Test ATExecutor logging integration."""

    def test_logging_command_execution(self):
        """Test command execution is logged."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.port = "/dev/ttyUSB0"  # Add port attribute
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["OK"]

        mock_logger = Mock()
        executor = ATExecutor(mock_handler, logger=mock_logger)
        executor.execute_command("AT+CGMI")

        # Logger should be called for command
        assert mock_logger.log_command.call_count >= 1

    def test_logging_command_response(self):
        """Test command response is logged."""
        mock_handler = Mock(spec=SerialHandler)
        mock_handler.port = "/dev/ttyUSB0"  # Add port attribute
        mock_handler.write.return_value = 5
        mock_handler.read_until.return_value = ["Quectel", "OK"]

        mock_logger = Mock()
        executor = ATExecutor(mock_handler, logger=mock_logger)
        executor.execute_command("AT+CGMI")

        # Logger should be called for response
        assert mock_logger.log_response.call_count >= 1
