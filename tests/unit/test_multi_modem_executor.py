"""Unit tests for MultiModemExecutor - concurrent multi-modem testing.

Tests concurrent execution, connection management, failure isolation,
and thread safety.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from dataclasses import FrozenInstanceError

from src.core.multi_modem_executor import MultiModemExecutor, ModemConnection
from src.core.serial_handler import SerialHandler
from src.core.at_executor import ATExecutor
from src.core.command_response import CommandResponse, ResponseStatus
from src.core.exceptions import SerialPortError, ATCommandError


class TestModemConnection:
    """Test ModemConnection dataclass."""

    def test_creation(self):
        """Test ModemConnection creation."""
        handler = MagicMock(spec=SerialHandler)
        executor = MagicMock(spec=ATExecutor)

        conn = ModemConnection(
            port="/dev/ttyUSB0",
            handler=handler,
            executor=executor,
            connected=True
        )

        assert conn.port == "/dev/ttyUSB0"
        assert conn.handler == handler
        assert conn.executor == executor
        assert conn.connected is True

    def test_immutability(self):
        """Test ModemConnection is immutable (frozen dataclass)."""
        handler = MagicMock(spec=SerialHandler)
        executor = MagicMock(spec=ATExecutor)

        conn = ModemConnection(
            port="/dev/ttyUSB0",
            handler=handler,
            executor=executor,
            connected=True
        )

        # Frozen dataclass should prevent modification
        with pytest.raises(FrozenInstanceError):
            conn.port = "/dev/ttyUSB1"


class TestMultiModemExecutorInit:
    """Test MultiModemExecutor initialization."""

    def test_default_init(self):
        """Test initialization with default parameters."""
        executor = MultiModemExecutor()

        assert executor.max_workers == 5
        assert executor.default_timeout == 30.0
        assert len(executor._connections) == 0

    def test_custom_init(self):
        """Test initialization with custom parameters."""
        executor = MultiModemExecutor(max_workers=10, default_timeout=60.0)

        assert executor.max_workers == 10
        assert executor.default_timeout == 60.0
        assert len(executor._connections) == 0

    def test_invalid_max_workers(self):
        """Test initialization with invalid max_workers."""
        with pytest.raises(ValueError, match="max_workers must be positive"):
            MultiModemExecutor(max_workers=0)

        with pytest.raises(ValueError, match="max_workers must be positive"):
            MultiModemExecutor(max_workers=-1)

    def test_invalid_timeout(self):
        """Test initialization with invalid timeout."""
        with pytest.raises(ValueError, match="default_timeout must be positive"):
            MultiModemExecutor(default_timeout=0)

        with pytest.raises(ValueError, match="default_timeout must be positive"):
            MultiModemExecutor(default_timeout=-1)


class TestModemManagement:
    """Test modem connection management."""

    @pytest.fixture
    def executor(self):
        """Create MultiModemExecutor instance."""
        return MultiModemExecutor(max_workers=3)

    @patch('src.core.multi_modem_executor.SerialHandler')
    @patch('src.core.multi_modem_executor.ATExecutor')
    def test_add_modem(self, mock_at_executor_class, mock_serial_class, executor):
        """Test adding a modem."""
        mock_handler = MagicMock(spec=SerialHandler)
        mock_serial_class.return_value = mock_handler

        mock_at_exec = MagicMock(spec=ATExecutor)
        mock_at_executor_class.return_value = mock_at_exec

        executor.add_modem("/dev/ttyUSB0", baud_rate=115200)

        # Verify handler created with correct parameters
        mock_serial_class.assert_called_once_with("/dev/ttyUSB0", baud_rate=115200)

        # Verify executor created
        mock_at_executor_class.assert_called_once_with(mock_handler, default_timeout=30.0)

        # Verify connection added
        assert "/dev/ttyUSB0" in executor._connections
        conn = executor._connections["/dev/ttyUSB0"]
        assert conn.port == "/dev/ttyUSB0"
        assert conn.handler == mock_handler
        assert conn.executor == mock_at_exec
        assert conn.connected is False

    @patch('src.core.multi_modem_executor.SerialHandler')
    @patch('src.core.multi_modem_executor.ATExecutor')
    def test_add_duplicate_modem(self, mock_at_executor_class, mock_serial_class, executor):
        """Test adding duplicate modem raises error."""
        executor.add_modem("/dev/ttyUSB0")

        with pytest.raises(ValueError, match="Modem .* already added"):
            executor.add_modem("/dev/ttyUSB0")

    def test_remove_modem(self, executor):
        """Test removing a modem."""
        # Add modem first
        mock_handler = MagicMock(spec=SerialHandler)
        mock_executor_obj = MagicMock(spec=ATExecutor)

        conn = ModemConnection(
            port="/dev/ttyUSB0",
            handler=mock_handler,
            executor=mock_executor_obj,
            connected=True
        )
        executor._connections["/dev/ttyUSB0"] = conn

        # Remove modem
        executor.remove_modem("/dev/ttyUSB0")

        # Verify handler closed
        mock_handler.close.assert_called_once()

        # Verify connection removed
        assert "/dev/ttyUSB0" not in executor._connections

    def test_remove_nonexistent_modem(self, executor):
        """Test removing nonexistent modem raises error."""
        with pytest.raises(KeyError, match="Modem .* not found"):
            executor.remove_modem("/dev/ttyUSB0")

    def test_get_modems_empty(self, executor):
        """Test get_modems with no modems."""
        modems = executor.get_modems()
        assert modems == []

    def test_get_modems(self, executor):
        """Test get_modems returns list of ports."""
        # Add modems
        for i in range(3):
            conn = ModemConnection(
                port=f"/dev/ttyUSB{i}",
                handler=MagicMock(),
                executor=MagicMock(),
                connected=False
            )
            executor._connections[f"/dev/ttyUSB{i}"] = conn

        modems = executor.get_modems()
        assert sorted(modems) == ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"]


class TestConnectionManagement:
    """Test connection management."""

    @pytest.fixture
    def executor(self):
        """Create MultiModemExecutor with mock modems."""
        exec_obj = MultiModemExecutor(max_workers=3)

        # Add 3 mock modems
        for i in range(3):
            mock_handler = MagicMock(spec=SerialHandler)
            mock_at_exec = MagicMock(spec=ATExecutor)

            conn = ModemConnection(
                port=f"/dev/ttyUSB{i}",
                handler=mock_handler,
                executor=mock_at_exec,
                connected=False
            )
            exec_obj._connections[f"/dev/ttyUSB{i}"] = conn

        return exec_obj

    def test_connect_all_success(self, executor):
        """Test connecting all modems successfully."""
        # Mock all handlers to succeed
        for conn in executor._connections.values():
            conn.handler.open = MagicMock()

        result = executor.connect_all()

        # Verify all opened
        for conn in executor._connections.values():
            conn.handler.open.assert_called_once()

        # Verify all succeeded
        assert result == {
            "/dev/ttyUSB0": True,
            "/dev/ttyUSB1": True,
            "/dev/ttyUSB2": True
        }

    def test_connect_all_partial_failure(self, executor):
        """Test connect_all with some failures (failure isolation)."""
        # Mock first modem to fail, others succeed
        ports = list(executor._connections.keys())
        executor._connections[ports[0]].handler.open = MagicMock(
            side_effect=SerialPortError("Failed to open")
        )
        executor._connections[ports[1]].handler.open = MagicMock()
        executor._connections[ports[2]].handler.open = MagicMock()

        result = executor.connect_all()

        # Verify failure isolated (others still connected)
        assert result[ports[0]] is False
        assert result[ports[1]] is True
        assert result[ports[2]] is True

    def test_disconnect_all(self, executor):
        """Test disconnecting all modems."""
        # Set all as connected
        for conn in executor._connections.values():
            conn.handler.close = MagicMock()

        executor.disconnect_all()

        # Verify all closed
        for conn in executor._connections.values():
            conn.handler.close.assert_called_once()

    def test_disconnect_all_with_errors(self, executor):
        """Test disconnect_all handles errors gracefully."""
        ports = list(executor._connections.keys())

        # First modem raises error on close
        executor._connections[ports[0]].handler.close = MagicMock(
            side_effect=SerialPortError("Failed to close")
        )
        executor._connections[ports[1]].handler.close = MagicMock()
        executor._connections[ports[2]].handler.close = MagicMock()

        # Should not raise exception
        executor.disconnect_all()

        # Verify all close attempts made
        for conn in executor._connections.values():
            conn.handler.close.assert_called_once()


class TestCommandExecution:
    """Test concurrent command execution."""

    @pytest.fixture
    def executor(self):
        """Create MultiModemExecutor with mock modems."""
        exec_obj = MultiModemExecutor(max_workers=3)

        # Add 3 mock modems
        for i in range(3):
            mock_handler = MagicMock(spec=SerialHandler)
            mock_at_exec = MagicMock(spec=ATExecutor)

            # Create mock response
            mock_response = CommandResponse(
                command="AT",
                raw_response=["OK"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1,
                retry_count=0
            )
            mock_at_exec.execute_command = MagicMock(return_value=mock_response)

            conn = ModemConnection(
                port=f"/dev/ttyUSB{i}",
                handler=mock_handler,
                executor=mock_at_exec,
                connected=True
            )
            exec_obj._connections[f"/dev/ttyUSB{i}"] = conn

        return exec_obj

    def test_execute_on_all_success(self, executor):
        """Test executing command on all modems successfully."""
        result = executor.execute_on_all("AT")

        # Verify all executed
        assert len(result) == 3
        for port in ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"]:
            assert port in result
            assert result[port].status == ResponseStatus.SUCCESS
            assert result[port].command == "AT"

        # Verify all executors called
        for conn in executor._connections.values():
            conn.executor.execute_command.assert_called_once_with("AT", timeout=None)

    def test_execute_on_all_with_timeout(self, executor):
        """Test execute_on_all with custom timeout."""
        executor.execute_on_all("AT+CGMI", timeout=10.0)

        # Verify timeout passed to all executors
        for conn in executor._connections.values():
            conn.executor.execute_command.assert_called_once_with("AT+CGMI", timeout=10.0)

    def test_execute_on_all_partial_failure(self, executor):
        """Test execute_on_all with some failures (failure isolation)."""
        ports = list(executor._connections.keys())

        # First modem fails
        error_response = CommandResponse(
            command="AT",
            raw_response=["ERROR"],
            status=ResponseStatus.ERROR,
            execution_time=0.1,
            retry_count=0
        )
        executor._connections[ports[0]].executor.execute_command = MagicMock(
            return_value=error_response
        )

        result = executor.execute_on_all("AT")

        # Verify failure isolated
        assert result[ports[0]].status == ResponseStatus.ERROR
        assert result[ports[1]].status == ResponseStatus.SUCCESS
        assert result[ports[2]].status == ResponseStatus.SUCCESS

    def test_execute_on_all_empty(self):
        """Test execute_on_all with no modems."""
        executor = MultiModemExecutor()
        result = executor.execute_on_all("AT")
        assert result == {}

    def test_execute_batch_on_all_success(self, executor):
        """Test executing batch commands on all modems."""
        commands = ["AT", "AT+CGMI", "AT+CGMM"]
        result = executor.execute_batch_on_all(commands)

        # Verify all modems executed all commands
        assert len(result) == 3
        for port in ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"]:
            assert port in result
            assert len(result[port]) == 3
            for i, cmd in enumerate(commands):
                assert result[port][i].command == cmd
                assert result[port][i].status == ResponseStatus.SUCCESS

    def test_execute_batch_on_all_with_timeout(self, executor):
        """Test execute_batch_on_all with custom timeout."""
        commands = ["AT", "AT+CGMI"]

        # Update mocks to check timeout
        for conn in executor._connections.values():
            conn.executor.execute_command = MagicMock(
                return_value=CommandResponse(
                    command="AT",
                    raw_response=["OK"],
                    status=ResponseStatus.SUCCESS,
                    execution_time=0.1,
                    retry_count=0
                )
            )

        executor.execute_batch_on_all(commands, timeout=15.0)

        # Verify timeout passed to all executors for all commands
        for conn in executor._connections.values():
            assert conn.executor.execute_command.call_count == 2
            calls = conn.executor.execute_command.call_args_list
            for i, cmd in enumerate(commands):
                assert calls[i] == call(cmd, timeout=15.0)

    def test_execute_batch_on_all_empty_commands(self, executor):
        """Test execute_batch_on_all with empty command list."""
        result = executor.execute_batch_on_all([])

        # Should return empty dict
        assert len(result) == 3
        for port in result.keys():
            assert result[port] == []

    def test_concurrent_execution_actually_parallel(self, executor):
        """Test that execution is actually concurrent (parallel)."""
        # Mock slow execution (100ms per command)
        execution_times = []

        def slow_execute(cmd, timeout=None):
            start = time.time()
            time.sleep(0.1)
            execution_times.append(time.time() - start)
            return CommandResponse(
                command=cmd,
                raw_response=["OK"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1,
                retry_count=0
            )

        for conn in executor._connections.values():
            conn.executor.execute_command = MagicMock(side_effect=slow_execute)

        # Execute on all 3 modems
        start = time.time()
        executor.execute_on_all("AT")
        total_time = time.time() - start

        # If sequential: ~300ms, if parallel: ~100ms
        # Allow some overhead, but should be much closer to 100ms
        assert total_time < 0.2, f"Expected parallel execution ~100ms, got {total_time*1000:.0f}ms"


class TestThreadSafety:
    """Test thread safety."""

    @pytest.fixture
    def executor(self):
        """Create MultiModemExecutor."""
        return MultiModemExecutor(max_workers=5)

    @patch('src.core.multi_modem_executor.SerialHandler')
    @patch('src.core.multi_modem_executor.ATExecutor')
    def test_concurrent_add_modem(self, mock_at_executor_class, mock_serial_class, executor):
        """Test concurrent add_modem calls are thread-safe."""
        mock_serial_class.return_value = MagicMock(spec=SerialHandler)
        mock_at_executor_class.return_value = MagicMock(spec=ATExecutor)

        # Add modems concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=executor.add_modem,
                args=(f"/dev/ttyUSB{i}",)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all added
        assert len(executor._connections) == 10

    def test_concurrent_execute(self, executor):
        """Test concurrent execute_on_all calls are thread-safe."""
        # Add mock modems
        for i in range(5):
            mock_handler = MagicMock(spec=SerialHandler)
            mock_at_exec = MagicMock(spec=ATExecutor)
            mock_at_exec.execute_command = MagicMock(
                return_value=CommandResponse(
                    command="AT",
                    raw_response=["OK"],
                    status=ResponseStatus.SUCCESS,
                    execution_time=0.1,
                    retry_count=0
                )
            )

            conn = ModemConnection(
                port=f"/dev/ttyUSB{i}",
                handler=mock_handler,
                executor=mock_at_exec,
                connected=True
            )
            executor._connections[f"/dev/ttyUSB{i}"] = conn

        # Execute concurrently from multiple threads
        results = []

        def execute_task():
            result = executor.execute_on_all("AT")
            results.append(result)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=execute_task)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all executions completed
        assert len(results) == 10
        for result in results:
            assert len(result) == 5


class TestContextManager:
    """Test context manager support."""

    @patch('src.core.multi_modem_executor.SerialHandler')
    @patch('src.core.multi_modem_executor.ATExecutor')
    def test_context_manager(self, mock_at_executor_class, mock_serial_class):
        """Test context manager cleans up resources."""
        mock_handler = MagicMock(spec=SerialHandler)
        mock_serial_class.return_value = mock_handler
        mock_at_executor_class.return_value = MagicMock(spec=ATExecutor)

        with MultiModemExecutor() as executor:
            executor.add_modem("/dev/ttyUSB0")
            executor.add_modem("/dev/ttyUSB1")

        # Verify both handlers closed
        assert mock_handler.close.call_count == 2

    @patch('src.core.multi_modem_executor.SerialHandler')
    @patch('src.core.multi_modem_executor.ATExecutor')
    def test_context_manager_with_exception(self, mock_at_executor_class, mock_serial_class):
        """Test context manager cleans up even on exception."""
        mock_handler = MagicMock(spec=SerialHandler)
        mock_serial_class.return_value = mock_handler
        mock_at_executor_class.return_value = MagicMock(spec=ATExecutor)

        with pytest.raises(RuntimeError):
            with MultiModemExecutor() as executor:
                executor.add_modem("/dev/ttyUSB0")
                raise RuntimeError("Test exception")

        # Verify handler still closed despite exception
        mock_handler.close.assert_called_once()


class TestGetStatistics:
    """Test statistics gathering."""

    @pytest.fixture
    def executor(self):
        """Create MultiModemExecutor with mock modems."""
        exec_obj = MultiModemExecutor(max_workers=3)

        # Add 2 connected, 1 disconnected
        for i in range(3):
            mock_handler = MagicMock(spec=SerialHandler)
            mock_at_exec = MagicMock(spec=ATExecutor)

            conn = ModemConnection(
                port=f"/dev/ttyUSB{i}",
                handler=mock_handler,
                executor=mock_at_exec,
                connected=(i < 2)  # First two connected
            )
            exec_obj._connections[f"/dev/ttyUSB{i}"] = conn

        return exec_obj

    def test_get_statistics(self, executor):
        """Test get_statistics returns correct counts."""
        stats = executor.get_statistics()

        assert stats["total_modems"] == 3
        assert stats["connected_modems"] == 2
        assert stats["disconnected_modems"] == 1
        assert stats["max_workers"] == 3

    def test_get_statistics_empty(self):
        """Test get_statistics with no modems."""
        executor = MultiModemExecutor()
        stats = executor.get_statistics()

        assert stats["total_modems"] == 0
        assert stats["connected_modems"] == 0
        assert stats["disconnected_modems"] == 0
        assert stats["max_workers"] == 5
