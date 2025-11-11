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

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Port Discovery

```bash
# List available serial ports
python main.py --discover-ports
```

### Execute AT Commands

```bash
# Execute single command
python main.py --port COM3 --command "AT+CGMI"

# Execute with verbose output
python main.py --port /dev/ttyUSB0 --command "AT+CGMM" --verbose
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

- Python 3.7+
- pyserial >= 3.5
- pyyaml >= 6.0

## Development Status

**MVP Complete**: All core components implemented and tested

### Completed
- ✅ Configuration Management
- ✅ AT Command Engine (serial I/O, retry logic)
- ✅ Plugin Architecture (YAML-based plugins)
- ✅ Report Generation (CSV format)

### Future Enhancements
- Parser Layer (feature extraction with confidence scoring)
- Additional report formats (HTML, JSON, Markdown)
- Plugin schema validation (jsonschema)
- Hardware testing framework
- Web UI for interactive testing

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
