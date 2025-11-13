# Communication Logging

Comprehensive guide to the communication logging feature in Modem Inspector.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [CLI Logging](#cli-logging)
- [GUI Logging](#gui-logging)
- [Configuration](#configuration)
- [Log File Format](#log-file-format)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

## Overview

The communication logging feature captures all AT command communications between Modem Inspector and connected modems. This provides:

- **Debugging**: Troubleshoot communication failures and timing issues
- **Analysis**: Understand modem behavior and response patterns
- **Compliance**: Create audit trails for regulatory requirements
- **Development**: Support plugin development with real communication samples

### Key Features

- Real-time logging of commands, responses, and port events
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Multiple output destinations (file, console, GUI viewer)
- Automatic log file rotation (10MB default, 5 backups)
- Search and filter capabilities in GUI
- Structured, parseable log format

## Quick Start

### CLI Example

```bash
# Enable logging with defaults
python main.py --cli --port COM3 --command "AT+CGMI" --log

# Custom log file and level
python main.py --cli --port COM3 --command "AT" --log --log-file ~/my_comm.log --log-level DEBUG

# Log to console (stderr) as well
python main.py --cli --port COM3 --command "AT+CGMI" --log --log-to-console
```

### GUI Example

1. Launch GUI: `python main.py --gui`
2. Go to **Settings** → **Logging** tab
3. Check **"Enable Communication Logging"**
4. Configure log level and file path
5. Click **OK** to apply
6. View logs in the **Communication Logs** tab

## CLI Logging

### Command-Line Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--log` | Enable communication logging | Disabled |
| `--log-file PATH` | Path to log file | `~/.modem-inspector/logs/comm_YYYYMMDD_HHMMSS.log` |
| `--log-level LEVEL` | Log verbosity (DEBUG, INFO, WARNING, ERROR) | INFO |
| `--log-to-console` | Output logs to console (stderr) | Disabled |

### Examples

**Basic Logging:**
```bash
python main.py --cli --port COM3 --command "AT" --log
```

**Debug Level Logging:**
```bash
python main.py --cli --port /dev/ttyUSB0 --command "AT+CGMI" --log --log-level DEBUG
```

**Custom Log File:**
```bash
python main.py --cli --port COM3 --command "AT" --log --log-file ./test_logs/session1.log
```

**Console Output:**
```bash
python main.py --cli --port COM3 --command "AT" --log --log-to-console
```

### Log File Location

When using `--log` without `--log-file`, logs are saved to:

- **Windows**: `C:\Users\<username>\.modem-inspector\logs\comm_YYYYMMDD_HHMMSS.log`
- **Linux/Mac**: `~/.modem-inspector/logs/comm_YYYYMMDD_HHMMSS.log`

The log file path is displayed at the end of execution when using `--verbose`.

## GUI Logging

### Enabling Logging

1. Open **Settings** (gear icon or menu)
2. Navigate to **Logging** tab
3. Check **"Enable Communication Logging"**
4. Configure options:
   - **Log Level**: Select verbosity (DEBUG, INFO, WARNING, ERROR)
   - **Log to File**: Enable file logging with custom path
   - **Log to Console**: Enable console output (stderr)
5. Click **OK** to apply settings

### Log Viewer

The GUI includes a real-time log viewer with the following features:

**Filtering:**
- **Level Filter**: Dropdown to show only specific log levels (All, DEBUG, INFO, WARNING, ERROR)
- **Search**: Text search across log messages, commands, and responses

**Color Coding:**
- DEBUG: Gray
- INFO: Blue
- WARNING: Orange/Yellow
- ERROR: Red

**Controls:**
- **Clear Display**: Clear viewer (does not delete log file)
- **Save Log**: Export visible (filtered) entries to a file
- **Open Log File**: Open current log file in system text editor

**Performance:**
- Displays last 1000 entries (configurable)
- Auto-scroll to newest entries
- Non-blocking updates (100ms polling interval)

### Settings Tab Controls

| Control | Description |
|---------|-------------|
| Enable Communication Logging | Master switch for logging feature |
| Log Level | Verbosity: DEBUG (most detailed) to ERROR (least detailed) |
| Log to File | Write logs to file with automatic rotation |
| Log File Path | Custom file path (with Browse button) |
| Log to Console | Output logs to console (stderr) in addition to file |
| Open Log Directory | Open log directory in file explorer |

## Configuration

### Configuration File

Logging settings can be configured in `config.yaml`:

```yaml
logging:
  enabled: false                    # Enable logging
  level: INFO                       # DEBUG, INFO, WARNING, ERROR
  log_to_file: false                # Write to file
  log_to_console: true             # Output to console
  log_file_path: null              # Auto-generated if null
  max_file_size_mb: 10             # Rotation size (MB)
  backup_count: 5                   # Number of backup files
```

### Log Levels

| Level | Usage | Captures |
|-------|-------|----------|
| **DEBUG** | Detailed troubleshooting | All events + internal state, port config |
| **INFO** | Normal operation | Commands, responses, port events |
| **WARNING** | Important events | Retries, timeouts, recoverable errors |
| **ERROR** | Failures only | Command errors, port failures, exceptions |

### File Rotation

Automatic log rotation prevents disk space issues:

- **Rotation Trigger**: File exceeds `max_file_size_mb` (default: 10MB)
- **Backup Files**: Keeps last `backup_count` files (default: 5)
- **Naming**: `log_file.log.1`, `log_file.log.2`, etc.
- **Oldest File**: Automatically deleted when limit exceeded

## Log File Format

### Structure

Each log entry follows this format:

```
YYYY-MM-DD HH:MM:SS.mmm | LEVEL   | SOURCE          | MESSAGE | [OPTIONAL_FIELDS]
```

### Example Entries

**Port Open:**
```
2025-01-12 10:30:15.123 | INFO    | SerialHandler   | Port opened | DETAILS: {"baud_rate": 115200, "timeout": 30}
```

**Command Sent:**
```
2025-01-12 10:30:15.234 | INFO    | ATExecutor      | Sending command | CMD: AT+CGMI
```

**Response Received:**
```
2025-01-12 10:30:15.456 | INFO    | ATExecutor      | Received response | CMD: AT+CGMI | STATUS: SUCCESS | TIME: 0.123s
```

**Command Retry:**
```
2025-01-12 10:30:20.789 | WARNING | ATExecutor      | Command timeout, retry attempt 1/3 | CMD: AT+CGMR
```

**Port Close:**
```
2025-01-12 10:35:45.123 | INFO    | SerialHandler   | Port closed | DETAILS: {"session_duration_seconds": 329.0}
```

### Optional Fields

| Field | Description | Example |
|-------|-------------|---------|
| `CMD` | AT command sent | `AT+CGMI` |
| `STATUS` | Response status | `SUCCESS`, `ERROR`, `TIMEOUT` |
| `TIME` | Execution time | `0.123s` |
| `RETRIES` | Retry count | `RETRIES: 2` |
| `ERROR` | Error message | `ERROR: Timeout` |
| `DETAILS` | Structured data (JSON) | `{"baud_rate": 115200}` |

### Parsing Logs

Logs use a consistent structure for programmatic parsing:

```python
import re
from datetime import datetime

# Parse log line
pattern = r'^(\S+ \S+\.\d+) \| (\S+)\s+\| (\S+)\s+\| (.+)$'
match = re.match(pattern, log_line)

if match:
    timestamp_str, level, source, message = match.groups()
    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")

    # Extract optional fields from message
    if '| CMD:' in message:
        command = message.split('| CMD:')[1].split('|')[0].strip()
```

## Advanced Usage

### Programmatic Access

Use `CommunicationLogger` directly in Python code:

```python
from src.logging import CommunicationLogger
from src.config.config_models import LogLevel

# Initialize logger
logger = CommunicationLogger(
    log_level=LogLevel.DEBUG,
    enable_file=True,
    enable_console=True,
    log_file_path="./my_session.log",
    max_file_size_mb=10,
    backup_count=5
)

# Log AT command
logger.log_command(port="COM3", command="AT+CGMI")

# Log response
logger.log_response(
    port="COM3",
    response="Quectel",
    status="SUCCESS",
    execution_time=0.123,
    command="AT+CGMI"
)

# Log port event
logger.log_port_event(
    event="Port opened",
    port="COM3",
    details={"baud_rate": 115200}
)

# Log error
logger.log_error(
    source="ATExecutor",
    error="Command timeout",
    details={"command": "AT+CGMR"}
)

# Close logger (flush buffers)
logger.close()
```

### Integration with SerialHandler and ATExecutor

```python
from src.core import SerialHandler, ATExecutor
from src.logging import CommunicationLogger
from src.config.config_models import LogLevel

# Create logger
logger = CommunicationLogger(
    log_level=LogLevel.INFO,
    enable_file=True,
    log_file_path="./test_session.log"
)

# Pass logger to SerialHandler and ATExecutor
handler = SerialHandler("COM3", baud_rate=115200, logger=logger)
handler.open()

executor = ATExecutor(handler, default_timeout=30.0, logger=logger)

# Commands are automatically logged
response = executor.execute_command("AT+CGMI")

# Close everything
handler.close()
logger.close()
```

### Custom Log Formats

For custom log formats, use `LogEntry.to_dict()` for JSON export:

```python
entries = logger.get_entries()

# Export as JSON
import json
with open('logs.json', 'w') as f:
    json_entries = [e.to_dict() for e in entries]
    json.dump(json_entries, f, indent=2)
```

## Troubleshooting

### Common Issues

#### Logging Not Working

**Symptom**: No log file created or no entries in GUI viewer

**Solutions**:
1. Verify logging is enabled in settings or via `--log` flag
2. Check file path is writable: `--log-file ~/test.log`
3. Verify log level allows the events you expect (use DEBUG for all events)
4. Check console for error messages about logging initialization

#### Permission Denied

**Symptom**: "Failed to initialize logger: Permission denied"

**Solutions**:
1. Use a different log directory: `--log-file ~/logs/comm.log`
2. Create log directory manually: `mkdir -p ~/.modem-inspector/logs`
3. Check directory permissions: `chmod 755 ~/.modem-inspector/logs`
4. On Windows, avoid system directories (use user home directory)

#### Log File Too Large

**Symptom**: Single log file grows very large

**Solutions**:
1. Adjust rotation size: Set `max_file_size_mb: 5` in config.yaml
2. Reduce log level: Use INFO or WARNING instead of DEBUG
3. Enable automatic rotation (enabled by default)
4. Manually archive old logs periodically

#### Missing Log Entries

**Symptom**: Some log entries are missing

**Solutions**:
1. Check log level filter - some entries may be filtered out
2. Verify logger was properly closed (`logger.close()`) to flush buffers
3. Check disk space - logging stops if disk is full
4. In GUI, check that logging was started (`start_logging()` called)

#### GUI Log Viewer Not Updating

**Symptom**: Log viewer shows no entries or doesn't update

**Solutions**:
1. Verify logger is set: `log_viewer.set_logger(logger)`
2. Verify logging is started: `log_viewer.start_logging()`
3. Check that logger has entries: `logger.get_entries()`
4. Restart logging: Stop and start logging again

#### Console Output Interference

**Symptom**: Log output mixes with command output

**Solutions**:
1. Logs go to stderr, command output to stdout (already separated)
2. Redirect stderr to file: `python main.py ... 2> logs.txt`
3. Use file logging only: Omit `--log-to-console` flag
4. Filter stderr in shell: `python main.py ... 2>&1 | grep -v "INFO"`

### Performance Issues

#### High CPU Usage

**Symptom**: High CPU usage when logging is enabled

**Solutions**:
1. Reduce log level to INFO or WARNING
2. Disable console logging (only log to file)
3. Increase polling interval in GUI (modify `_poll_logs()`)
4. Limit displayed entries in GUI (default: 1000)

#### Slow File Writes

**Symptom**: Logging slows down command execution

**Solutions**:
1. Logging uses buffered I/O and should have <5% overhead
2. Use SSD instead of HDD for log files
3. Reduce log verbosity (use WARNING or ERROR level)
4. Check disk I/O performance with system tools

### Getting Help

If you encounter issues not covered here:

1. Check the issue tracker: https://github.com/your-repo/modem-inspector/issues
2. Enable DEBUG logging to get detailed information
3. Include log snippets (sanitized) in bug reports
4. Provide platform information (OS, Python version)

## Best Practices

### For Debugging

1. Use DEBUG level for detailed troubleshooting
2. Enable both file and console logging
3. Keep logs for the duration of the debugging session
4. Search logs for specific commands or error patterns

### For Production Use

1. Use INFO level for normal operation
2. Enable log rotation to manage disk space
3. Archive logs periodically for compliance
4. Monitor log directory size

### For Development

1. Use DEBUG level during plugin development
2. Export logs as JSON for automated analysis
3. Use programmatic logging API for custom integrations
4. Test with various log levels to validate filtering

### Security Considerations

1. Log files may contain sensitive modem data
2. Secure log files with appropriate permissions
3. Sanitize logs before sharing (remove serial numbers, IMEIs)
4. Implement log retention policies per compliance requirements
5. Encrypt archived logs if required by policy

---

For more information, see:
- [README.md](../README.md) - General usage
- [Configuration Management](configuration.md) - Config file reference
- [API Documentation](api.md) - Programmatic usage
