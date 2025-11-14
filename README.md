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

6. **Parser Layer** ⭐ NEW
   - Universal parser for standard 3GPP AT commands
   - Vendor-specific parser extensions (Quectel, Nordic, SIMCom)
   - Confidence scoring (0.0-1.0) for all extracted features
   - Immutable data models with comprehensive feature schema
   - Graceful error handling and conflict resolution
   - JSON serialization for integration with reporting

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

### Parser Layer Usage

```bash
# Run parser demonstration with mock data
python test_parser_basic.py

# Run comprehensive integration example
python examples/parser_integration_example.py

# Using parser in your code
from src.core import ATExecutor, SerialHandler
from src.parsers import FeatureExtractor

# Execute AT commands
executor = ATExecutor(serial_handler)
responses = {
    "AT+CGMI": executor.execute_command("AT+CGMI"),
    "AT+CGMM": executor.execute_command("AT+CGMM"),
    # ... more commands
}

# Extract features with confidence scoring
extractor = FeatureExtractor()
features = extractor.extract_features(responses, plugin)

# Access parsed data
print(f"Manufacturer: {features.basic_info.manufacturer}")
print(f"Confidence: {features.basic_info.manufacturer_confidence}")

# Filter high-confidence features
high_conf = features.get_high_confidence_features(threshold=0.7)

# Export to JSON
json_data = features.to_dict()
```

### Run Integration Tests

```bash
# Test all components
python test_mvp.py

# Test parser integration
python -m pytest tests/integration/test_parser_at_integration.py -v
```

## Project Structure

```
modem-inspector/
├── src/
│   ├── config/          # Configuration management
│   │   ├── config_models.py
│   │   ├── config_manager.py
│   │   └── defaults.py
│   ├── core/            # Core AT Command Engine
│   │   ├── command_response.py
│   │   ├── exceptions.py
│   │   ├── serial_handler.py
│   │   ├── at_executor.py
│   │   ├── multi_modem_executor.py
│   │   ├── plugin.py
│   │   └── plugin_manager.py
│   ├── parsers/         # Feature extraction layer ⭐ NEW
│   │   ├── feature_model.py      # Immutable data models
│   │   ├── base_parser.py        # Abstract vendor interface
│   │   ├── universal.py          # Standard 3GPP parser
│   │   ├── vendor_specific.py    # Vendor dispatcher
│   │   ├── feature_extractor.py  # Orchestrator
│   │   └── vendors/              # Vendor-specific parsers
│   │       ├── quectel_parser.py
│   │       ├── nordic_parser.py
│   │       └── simcom_parser.py
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
├── examples/            # Usage examples
│   └── parser_integration_example.py
├── tests/               # Test suite
│   ├── unit/
│   └── integration/
│       └── test_parser_at_integration.py
├── docs/                # Documentation
│   └── logging.md       # Logging guide
├── main.py              # CLI entry point
├── test_mvp.py          # Integration test
├── test_parser_basic.py # Parser demo
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

The GUI provides a complete graphical interface for modem inspection with a modern, responsive design.

### Launching the GUI

```bash
# Default mode - launches GUI
python main.py

# Explicit GUI mode
python main.py --gui
```

### Main Components

#### 1. Connection Frame
- **Port Discovery**: Auto-detect available serial ports
- **Refresh Button**: Update port list without restarting
- **Status Indicator**: Visual connection status (gray/green/red)
- **Baud Rate Selection**: Standard baud rates (115200 default)
- **Connect/Disconnect**: One-click connection management

#### 2. Plugin Frame
- **Auto-Detection**: Execute AT+CGMI/AT+CGMM to identify modem
- **Manual Selection**: Dropdown with searchable plugin list
- **Plugin Info**: Display vendor, model, version, command count
- **Command Categories**: Visual category selection with counts

#### 3. Execution & Results Tab

**Execution Panel:**
- Real-time progress bar with percentage
- Command counter (e.g., "5 / 15 commands")
- Elapsed time and estimated time remaining
- Color-coded progress log:
  - 🔵 Blue: Command sent
  - ✅ Green: Success response
  - ❌ Red: Error response
  - ⟳ Yellow: Retry attempt
- Start/Cancel buttons with state management
- Auto-scroll to latest command

**Results Panel:**
- Tabbed display organized by command category
- Results table with columns:
  - Command name
  - Status (SUCCESS/ERROR/TIMEOUT)
  - Execution time (ms)
  - Raw response text
- Search box with real-time highlighting
- Copy to Clipboard button
- Export button (opens Report Dialog)
- Pagination for 100+ results (20 per page)

#### 4. Command Categories Tab
- Visual checklist of all command categories
- Command count per category
- "Select All" / "Deselect All" buttons
- "Quick Scan Only" filter checkbox
- Real-time command count updates

#### 5. Communication Logs Tab
- Real-time log viewer with timestamps
- Color-coded log levels:
  - DEBUG: Gray
  - INFO: Blue
  - WARNING: Yellow
  - ERROR: Red
- Search and filter functionality
- Clear logs button
- Export logs to file
- Open log directory button
- Auto-scroll to latest entry

### Dialogs

#### Settings Dialog
Accessible via menu bar: **Settings**

**Serial Tab:**
- Baud Rate (300-921600 bps)
- Timeout (1-600 seconds)
- Retry Attempts (0-10)
- Retry Delay (100-10000 ms)

**Reports Tab:**
- Output Directory (with Browse button)
- Default Format (CSV, HTML, JSON, Markdown)

**Logging Tab:**
- Enable/Disable Communication Logging
- Log Level (DEBUG, INFO, WARNING, ERROR)
- Log to File checkbox
- Log File Path (with Browse button)
- Log to Console checkbox
- Open Log Directory button
- Max File Size (MB)
- Backup Count

**Actions:**
- **Save**: Apply settings with validation
- **Reset to Defaults**: Restore factory settings
- **Cancel**: Close without saving

#### Report Dialog
Accessible via Results panel: **Export** button

**Features:**
- Format selection (CSV, HTML, JSON, Markdown)
- Format options:
  - ☑ Include raw responses
  - ☑ Include timestamps
- Output path selector with Browse button
- Default filename with timestamp
- Generate button with progress indicator
- Background generation (non-blocking)
- File overwrite confirmation
- Success message with file size
- Open Report button (launches in default app)

#### Help Dialog
Accessible via menu bar: **Help → Help**

**Features:**
- Searchable table of contents
- Formatted help content
- Offline operation (no network required)
- Topics:
  - Getting Started
  - Connection Management
  - Plugin Usage
  - Command Execution
  - Results Interpretation
  - Settings Configuration
  - Troubleshooting

### Menu Bar

**File Menu:**
- Exit: Graceful shutdown with resource cleanup

**Settings:**
- Opens Settings Dialog

**Help Menu:**
- Help: Opens Help Dialog
- About: Version and copyright information

### Workflow Example

1. **Launch**: `python main.py`
2. **Connect**: Select port → Click "Connect"
3. **Detect**: Click "Auto-Detect" (or select plugin manually)
4. **Configure**: Select command categories in "Command Categories" tab
5. **Execute**: Click "Start" in Execution & Results tab
6. **Monitor**: Watch real-time progress and logs
7. **Review**: Examine results by category
8. **Export**: Click "Export" → Configure format → "Generate"
9. **View Logs**: Switch to "Communication Logs" tab for detailed AT traces

### Keyboard Shortcuts

- **Ctrl+Q**: Exit application
- **Ctrl+S**: Open Settings (when implemented)
- **F1**: Open Help (when implemented)
- **Ctrl+R**: Refresh port list (when focused)

### Testing

For comprehensive GUI testing procedures, see:
- [GUI Testing Guide](docs/gui_testing_guide.md) - Manual test cases and procedures

### Architecture

**Technology Stack:**
- **CustomTkinter**: Modern GUI framework with native look and feel
- **Threading**: Background command execution (never blocks UI)
- **Queue**: Thread-safe communication between worker and UI threads
- **MVC Pattern**: Clean separation of concerns

**Key Components:**
```
Application (Controller)
├── ConnectionFrame (View)
│   └── SerialHandler (Model)
├── PluginFrame (View)
│   └── PluginManager (Model)
├── ExecutionFrame (View)
│   └── ATExecutor (Model)
├── ResultsFrame (View)
│   └── CommandResponse (Model)
└── LogViewerFrame (View)
    └── CommunicationLogger (Model)
```

**Threading Model:**
- Main thread: UI updates only
- Worker threads: AT command execution, file I/O
- Queue-based communication: Progress updates, results
- Safe callbacks: All UI updates via `after()` method

### Troubleshooting

**GUI Won't Launch:**
```bash
# Check dependencies
pip install -r requirements.txt

# Test import
python -c "from src.gui.application import Application; print('OK')"
```

**Port Not Detected:**
- Ensure USB cable connected
- Check device drivers installed (Windows: Device Manager)
- Try manual port selection
- Use CLI to verify: `python main.py --cli --discover-ports`

**Execution Hangs:**
- Restart application
- Check serial port not in use by another application
- Verify correct baud rate for your modem
- Enable logging for diagnostics

**Settings Not Saved:**
- Check config.yaml file permissions
- Verify output directory exists and is writable
- Check console for error messages

For more troubleshooting tips, see [GUI Testing Guide](docs/gui_testing_guide.md).

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
