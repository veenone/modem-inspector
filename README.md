# Modem Inspector

A Python-based modem inspection tool with plugin-based architecture for vendor-specific AT command execution and reporting.

## MVP Features

The Modem Inspector MVP provides a complete foundation for automated modem testing:

### Core Components

1. **Configuration Management**
   - Zero-config operation with sensible defaults
   - YAML-based configuration
   - Immutable configuration data models

2. **AT Command Engine**
   - Cross-platform serial communication (pyserial)
   - Automatic retry with exponential backoff
   - Response parsing for OK/ERROR/CME/CMS responses
   - Command execution history tracking

3. **Plugin Architecture**
   - YAML-based plugin definitions
   - No code changes needed for new modems
   - Automatic plugin discovery
   - Vendor/model auto-selection

4. **Report Generation**
   - CSV format reports
   - Command execution results with timing
   - Error tracking and retry statistics

5. **Communication Logging**
   - Real-time AT command and response logging
   - Configurable log levels (DEBUG, INFO, WARNING, ERROR)
   - Multiple output destinations (file, console, GUI viewer)
   - Automatic log rotation with configurable size limits
   - Search and filter capabilities in GUI

## Quick Start

### Installation

```bash
# Install dependencies (including GUI support)
pip install -r requirements.txt
```

### GUI Mode (Default)

```bash
# Launch GUI application (default)
python main.py

# Or explicitly launch GUI
python main.py --gui
```

The GUI provides:
- **Port Discovery & Connection**: Visual port selection with auto-refresh
- **Plugin Auto-Detection**: Automatic modem identification via AT commands
- **Command Execution**: Real-time progress with color-coded logging
- **Results Visualization**: Tabbed results organized by command category
- **Report Generation**: Export results to CSV format

### CLI Mode

```bash
# Discover ports
python main.py --cli --discover-ports

# Execute single command
python main.py --cli --port COM3 --command "AT+CGMI"

# Execute with verbose output
python main.py --cli --port /dev/ttyUSB0 --command "AT+CGMM" --verbose

# Enable communication logging
python main.py --cli --port COM3 --command "AT+CGMI" --log

# Logging with custom options
python main.py --cli --port COM3 --command "AT" --log --log-level DEBUG --log-to-console

# Custom log file
python main.py --cli --port COM3 --command "AT+CGMR" --log --log-file ~/my_session.log
```

### Run Integration Test

```bash
# Test all components
python test_mvp.py
```

## Project Structure

```
modem-inspector/
├── src/
│   ├── config/          # Configuration management
│   │   ├── config_models.py
│   │   ├── config_manager.py
│   │   └── defaults.py
│   ├── core/            # Core components
│   │   ├── command_response.py
│   │   ├── exceptions.py
│   │   ├── serial_handler.py
│   │   ├── at_executor.py
│   │   ├── plugin.py
│   │   └── plugin_manager.py
│   ├── logging/         # Communication logging
│   │   ├── log_models.py
│   │   ├── file_handler.py
│   │   └── communication_logger.py
│   ├── gui/             # GUI components
│   │   ├── frames/
│   │   │   ├── log_viewer_frame.py
│   │   │   └── ...
│   │   └── dialogs/
│   │       ├── settings_dialog.py
│   │       └── ...
│   ├── plugins/         # Plugin definitions
│   │   ├── quectel/
│   │   │   └── lte_cat1/
│   │   │       └── ec200u.yaml
│   │   ├── nordic/
│   │   │   └── nrf9160.yaml
│   │   └── sample/
│   │       └── basic_modem.yaml
│   └── reports/         # Report generation
│       ├── report_models.py
│       └── csv_reporter.py
├── docs/                # Documentation
│   └── logging.md       # Logging guide
├── main.py              # CLI entry point
├── test_mvp.py          # Integration test
└── requirements.txt
```

## Plugin System

Plugins are YAML files defining vendor-specific AT commands and parsers:

```yaml
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"

connection:
  default_baud: 115200

commands:
  basic:
    - cmd: "AT"
      description: "Test command"
      category: "basic"
      quick: true

parsers:
  signal_parser:
    name: "signal_parser"
    type: "regex"
    pattern: "\\+CSQ:\\s*(\\d+),(\\d+)"
    groups: ["rssi", "ber"]
```

## Example Usage

```python
from src.config import ConfigManager
from src.core import SerialHandler, ATExecutor
from src.core.plugin_manager import PluginManager
from src.reports import CSVReporter

# Initialize
ConfigManager.initialize()
manager = PluginManager()
plugins = manager.discover_plugins()

# Select plugin
plugin = manager.get_plugin('quectel', 'ec200u')

# Execute commands (with real hardware)
handler = SerialHandler('/dev/ttyUSB0')
handler.open()
executor = ATExecutor(handler)

for cmd_def in plugin.get_commands_by_category('basic'):
    response = executor.execute_command(cmd_def.cmd)
    print(f"{response.command}: {response.status.value}")

# Generate report
reporter = CSVReporter()
result = reporter.generate(
    executor.get_history(),
    Path('./report.csv')
)
print(f"Report saved: {result.output_path}")

handler.close()
```

## Supported Modems

Current plugin library includes:

- **Quectel EC200U** (LTE Cat 1): 15 commands, 11 parsers
- **Nordic nRF9160** (IoT SiP): 9 commands, 5 parsers
- **Sample Basic Modem**: Minimal template

## Architecture

The system follows a layered architecture:

```
Configuration (YAML) → Plugin Manager → AT Executor → Serial Handler → Modem Hardware
                                    ↓
                                Reports
```

### Key Design Principles

- **Zero-config operation**: Works without configuration files
- **Immutable data models**: Frozen dataclasses prevent modification
- **Plugin-first**: All vendor logic in YAML plugins
- **Cross-platform**: Single codebase for Linux/Windows/macOS
- **Type-safe**: Comprehensive type hints throughout

## Requirements

### Core Dependencies
- Python 3.7+
- pyserial >= 3.5
- pyyaml >= 6.0

### GUI Mode (Optional)
Additional dependencies required for GUI mode:
- customtkinter >= 5.0.0 (modern GUI framework)
- pillow >= 9.0.0 (image support)
- darkdetect >= 0.7.0 (dark mode detection)

Install all dependencies including GUI support:
```bash
pip install -r requirements.txt
```

## Communication Logging

The logging feature provides comprehensive tracking of all AT command communications:

### Features
- **Real-time Capture**: Logs all commands, responses, and port events with timestamps
- **Log Levels**: DEBUG, INFO, WARNING, ERROR for flexible verbosity control
- **Multiple Outputs**: File logging with rotation, console output (stderr), GUI viewer
- **Automatic Rotation**: Configurable file size limits (default: 10MB) with backup retention
- **Structured Format**: ISO 8601 timestamps, consistent fields, parseable format
- **GUI Viewer**: Real-time display with search, filter, color coding, and export

### CLI Usage

```bash
# Basic logging
python main.py --cli --port COM3 --command "AT+CGMI" --log

# Debug level with console output
python main.py --cli --port COM3 --command "AT" --log --log-level DEBUG --log-to-console

# Custom log file
python main.py --cli --port COM3 --command "AT+CGMR" --log --log-file ~/session.log
```

### GUI Usage

1. Open **Settings** → **Logging** tab
2. Check **"Enable Communication Logging"**
3. Configure log level and output options
4. View logs in the **Communication Logs** tab with real-time updates

For detailed documentation, see [docs/logging.md](docs/logging.md).

## GUI Interface

The GUI provides a complete graphical interface for modem inspection:

### Features
- **Port Management**: Visual port selection with auto-refresh and connection status
- **Plugin Selection**:
  - Auto-detection via AT+CGMI/AT+CGMM commands
  - Manual selection from available plugins
  - Category-based command filtering with Quick Scan mode
- **Execution Control**:
  - Real-time progress bar with ETA
  - Color-coded logging (blue=command, green=success, red=error)
  - Graceful cancellation support
  - Execution summary with statistics
- **Results Display**:
  - Tabbed results organized by command category
  - Search functionality with highlighting
  - Export to CSV reports
- **Communication Logs** (NEW):
  - Real-time log viewer with color-coded entries
  - Search and filter by log level
  - Export visible logs to file
  - Open log file in editor
- **Settings & Help**:
  - Configuration dialog for serial/report/logging settings
  - Built-in help documentation
  - Inspection history tracking

### Architecture
- **CustomTkinter**: Modern GUI framework
- **Threaded Execution**: Non-blocking command execution
- **Queue-based Communication**: Thread-safe progress updates
- **MVC Pattern**: Clean separation of concerns

## Development Status

**MVP + GUI + Logging Complete**: All core components, GUI interface, and communication logging implemented

### Completed
- ✅ Configuration Management
- ✅ AT Command Engine (serial I/O, retry logic)
- ✅ Plugin Architecture (YAML-based plugins)
- ✅ Report Generation (CSV format)
- ✅ **Communication Logging** (NEW)
  - ✅ Real-time command/response logging
  - ✅ Configurable log levels (DEBUG, INFO, WARNING, ERROR)
  - ✅ File logging with automatic rotation
  - ✅ Console output (stderr)
  - ✅ GUI log viewer with search/filter
  - ✅ CLI logging flags (--log, --log-file, --log-level)
- ✅ **GUI Interface** (CustomTkinter-based)
  - ✅ Port discovery and connection management
  - ✅ Plugin auto-detection and manual selection
  - ✅ Threaded command execution with real-time updates
  - ✅ Results visualization with search
  - ✅ Report generation dialog
  - ✅ Communication logs viewer (NEW)
  - ✅ Settings and help dialogs (with logging tab)
  - ✅ History management

### Future Enhancements
- Parser Layer (feature extraction with confidence scoring)
- Additional report formats (HTML, JSON, Markdown)
- Plugin schema validation (jsonschema)
- Hardware testing framework
- Unit and integration tests for logging module

## Testing

Run the integration test to verify all components:

```bash
python test_mvp.py
```

Expected output:
```
[OK] Configuration loaded
[OK] Plugins loaded (3 plugins)
[OK] Plugin selected (quectel.ec200u)
[OK] Commands executed (5 commands)
[OK] Report generated
```

## Contributing

New modem support can be added by creating YAML plugin files in `src/plugins/`.
No Python code changes required.

## License

This project is part of the Modem Inspector suite for automated modem testing
and inspection.
