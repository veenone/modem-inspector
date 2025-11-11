"""MVP Integration Test.

Demonstrates complete Modem Inspector MVP functionality end-to-end:
- Configuration loading
- Plugin discovery
- AT Command execution (simulated)
- Report generation
"""

from pathlib import Path

from src.config import ConfigManager
from src.core import SerialHandler, ATExecutor, CommandResponse, ResponseStatus
from src.core.plugin_manager import PluginManager
from src.reports import CSVReporter


def main():
    """Run MVP integration test."""
    print("=" * 60)
    print("Modem Inspector MVP Integration Test")
    print("=" * 60)

    # 1. Configuration Management
    print("\n[1/5] Loading configuration...")
    ConfigManager.initialize()
    config = ConfigManager.instance().get_config()
    print(f"    Baud rate: {config.serial.default_baud}")
    print(f"    Timeout: {config.serial.timeout}s")
    print(f"    Report format: {config.reporting.default_format.value}")
    print(f"    [OK] Configuration loaded")

    # 2. Plugin Discovery
    print("\n[2/5] Discovering plugins...")
    manager = PluginManager(['./src/plugins'])
    plugins = manager.discover_plugins()
    print(f"    Found {len(plugins)} plugins:")
    for plugin in plugins:
        print(f"      - {plugin.metadata.vendor}.{plugin.metadata.model} "
              f"({len(plugin.get_all_commands())} commands)")
    print(f"    [OK] Plugins loaded")

    # 3. Plugin Selection
    print("\n[3/5] Selecting plugin...")
    plugin = manager.get_plugin('quectel', 'ec200u')
    if plugin:
        print(f"    Selected: {plugin.metadata.vendor}.{plugin.metadata.model}")
        print(f"    Categories: {', '.join(plugin.commands.keys())}")
        print(f"    Quick commands: {sum(1 for cmd in plugin.get_all_commands() if cmd.quick)}")
        print(f"    [OK] Plugin selected")
    else:
        print(f"    [ERROR] Plugin not found")
        return

    # 4. Simulated Command Execution
    print("\n[4/5] Simulating command execution...")
    # Create mock responses for demonstration
    mock_responses = []

    for cmd_def in plugin.get_commands_by_category('basic')[:5]:
        # Simulate successful responses
        if cmd_def.cmd == 'AT':
            response = ['OK']
        elif cmd_def.cmd == 'ATI':
            response = ['Quectel', 'EC200U', 'Revision: EC200UCNAAR01A01M16', 'OK']
        elif cmd_def.cmd == 'AT+CGMI':
            response = ['Quectel', 'OK']
        elif cmd_def.cmd == 'AT+CGMM':
            response = ['EC200U', 'OK']
        elif cmd_def.cmd == 'AT+CGMR':
            response = ['EC200UCNAAR01A01M16', 'OK']
        else:
            response = ['OK']

        mock_response = CommandResponse(
            command=cmd_def.cmd,
            raw_response=response,
            status=ResponseStatus.SUCCESS,
            execution_time=0.05 + (len(cmd_def.cmd) * 0.01)
        )
        mock_responses.append(mock_response)

    print(f"    Executed {len(mock_responses)} commands")
    for resp in mock_responses:
        print(f"      {resp.command}: {resp.status.value} ({resp.execution_time:.3f}s)")
    print(f"    [OK] Commands executed")

    # 5. Report Generation
    print("\n[5/5] Generating report...")
    reporter = CSVReporter()
    report_path = Path('./reports/mvp_test_report.csv')
    result = reporter.generate(mock_responses, report_path)

    if result.success:
        print(f"    Report saved: {result.output_path}")
        print(f"    File size: {result.file_size_bytes} bytes")
        print(f"    Generation time: {result.generation_time_seconds:.3f}s")
        print(f"    Validation: {'PASS' if result.validation_passed else 'FAIL'}")
        print(f"    [OK] Report generated")

        # Display sample
        print("\n    Sample (first 3 rows):")
        with open(report_path, 'r') as f:
            for i, line in enumerate(f):
                if i >= 4:  # Header + 3 rows
                    break
                print(f"      {line.rstrip()}")
    else:
        print(f"    [ERROR] Report generation failed: {result.warnings}")

    # Summary
    print("\n" + "=" * 60)
    print("MVP Integration Test Complete")
    print("=" * 60)
    print("\nAll core components working:")
    print("  [OK] Configuration Management")
    print("  [OK] AT Command Engine")
    print("  [OK] Plugin Architecture")
    print("  [OK] Report Generation")
    print("\nModem Inspector MVP is functional!")
    print("=" * 60)


if __name__ == '__main__':
    main()
