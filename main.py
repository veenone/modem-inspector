"""Modem Inspector - AT Command Engine CLI.

Basic command-line interface for testing the AT Command Engine.
"""

import argparse
import sys
from typing import Optional
from pathlib import Path
from datetime import datetime

from src.core import SerialHandler, ATExecutor, PortInfo
from src.config import ConfigManager
from src.config.config_models import LogLevel
from src.logging import CommunicationLogger


def discover_ports() -> None:
    """Discover and display available serial ports."""
    print("Discovering serial ports...")
    ports = SerialHandler.discover_ports()

    if not ports:
        print("No serial ports found.")
        return

    print(f"\nFound {len(ports)} port(s):")
    for port in ports:
        print(f"  {port.device}")
        print(f"    Description: {port.description}")
        print(f"    Hardware ID: {port.hwid}")
        print()


def execute_command(
    port: str,
    baud: int,
    command: str,
    timeout: float,
    verbose: bool,
    logger: Optional[CommunicationLogger] = None
) -> int:
    """Execute single AT command on specified port.

    Args:
        port: Serial port device path
        baud: Baud rate
        command: AT command to execute
        timeout: Command timeout in seconds
        verbose: Enable verbose output
        logger: Optional CommunicationLogger for logging (default None)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    handler = None
    try:
        # Initialize handler with logger
        if verbose:
            print(f"Opening port {port} at {baud} baud...")

        handler = SerialHandler(port, baud_rate=baud, logger=logger)
        handler.open()

        if verbose:
            print(f"Port opened successfully")

        # Create executor with logger
        executor = ATExecutor(handler, default_timeout=timeout, logger=logger)

        # Execute command
        if verbose:
            print(f"Executing: {command}")

        response = executor.execute_command(command)

        # Display results
        print(f"\n{'='*60}")
        print(f"Command: {response.command}")
        print(f"Status: {response.status.value}")
        print(f"Execution time: {response.execution_time:.3f}s")
        if response.retry_count > 0:
            print(f"Retries: {response.retry_count}")

        print(f"\nResponse:")
        print(response.get_response_text())
        print(f"{'='*60}\n")

        return 0 if response.is_successful() else 1

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        if handler is not None:
            handler.close()
            if verbose:
                print("Port closed")


def main() -> int:
    """Main entry point - supports both CLI and GUI modes."""
    parser = argparse.ArgumentParser(
        description="Modem Inspector - AT Command Engine (CLI/GUI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                                    # Launch GUI (default)
  %(prog)s --gui                                              # Launch GUI explicitly
  %(prog)s --cli --discover-ports                             # CLI: Discover ports
  %(prog)s --cli --port COM3 --command "AT"                  # CLI: Execute command
  %(prog)s --cli --port /dev/ttyUSB0 --baud 9600 --command "AT+CGMI" --verbose

  # Logging examples:
  %(prog)s --cli --port COM3 --command "AT" --log                  # Enable logging with defaults
  %(prog)s --cli --port COM3 --command "AT" --log --log-file ~/comm.log
  %(prog)s --cli --port COM3 --command "AT" --log --log-level DEBUG --log-to-console
        """
    )

    parser.add_argument(
        '--gui',
        action='store_true',
        help='Launch GUI mode (default if no arguments provided)'
    )

    parser.add_argument(
        '--cli',
        action='store_true',
        help='Use CLI mode for command execution'
    )

    parser.add_argument(
        '--discover-ports',
        action='store_true',
        help='Discover and list available serial ports'
    )

    parser.add_argument(
        '--port',
        type=str,
        help='Serial port device (e.g., COM3, /dev/ttyUSB0)'
    )

    parser.add_argument(
        '--baud',
        type=int,
        default=115200,
        help='Baud rate (default: 115200)'
    )

    parser.add_argument(
        '--command',
        type=str,
        help='AT command to execute (e.g., "AT+CGMI")'
    )

    parser.add_argument(
        '--timeout',
        type=float,
        default=30.0,
        help='Command timeout in seconds (default: 30)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    # Logging arguments
    parser.add_argument(
        '--log',
        action='store_true',
        help='Enable communication logging'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        metavar='PATH',
        help='Path to log file (default: ~/.modem-inspector/logs/comm_YYYYMMDD_HHMMSS.log)'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Log level (default: INFO)'
    )

    parser.add_argument(
        '--log-to-console',
        action='store_true',
        help='Output logs to console (stderr) in addition to file'
    )

    # Configuration management arguments
    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Show current configuration with sources'
    )

    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='Validate configuration file'
    )

    parser.add_argument(
        '--generate-config',
        action='store_true',
        help='Generate default configuration file'
    )

    parser.add_argument(
        '--reset-config',
        action='store_true',
        help='Reset configuration to defaults (creates backup)'
    )

    parser.add_argument(
        '--setup',
        action='store_true',
        help='Launch interactive configuration wizard'
    )

    parser.add_argument(
        '--encrypt-value',
        type=str,
        metavar='VALUE',
        help='Encrypt a value for use in configuration'
    )

    parser.add_argument(
        '--rotate-key',
        action='store_true',
        help='Rotate encryption key and re-encrypt sensitive fields'
    )

    parser.add_argument(
        '--test-config',
        action='store_true',
        help='Run comprehensive configuration tests'
    )

    parser.add_argument(
        '--config-help',
        action='store_true',
        help='Show configuration help and documentation'
    )

    parser.add_argument(
        '--config-schema',
        action='store_true',
        help='Output JSON schema for configuration'
    )

    # Plugin management arguments
    parser.add_argument(
        '--list-plugins',
        action='store_true',
        help='List all discovered plugins'
    )

    parser.add_argument(
        '--plugin-info',
        type=str,
        metavar='VENDOR.MODEL',
        help='Show detailed information about a specific plugin (e.g., quectel.ec200u)'
    )

    parser.add_argument(
        '--validate-plugin',
        type=str,
        metavar='FILE',
        help='Validate a plugin YAML file'
    )

    parser.add_argument(
        '--test-plugin',
        type=str,
        metavar='FILE',
        help='Test plugin against real hardware (requires --port)'
    )

    parser.add_argument(
        '--validate-all-plugins',
        action='store_true',
        help='Validate all plugins in plugin directories'
    )

    parser.add_argument(
        '--vendor',
        type=str,
        help='Filter plugins by vendor (use with --list-plugins)'
    )

    parser.add_argument(
        '--category',
        type=str,
        help='Filter plugins by category (use with --list-plugins)'
    )

    parser.add_argument(
        '--create-plugin-template',
        nargs=2,
        metavar=('VENDOR', 'MODEL'),
        help='Generate a plugin template (e.g., --create-plugin-template myvendor mymodel)'
    )

    parser.add_argument(
        '--plugin-category',
        type=str,
        default='other',
        help='Category for template generation (default: other)'
    )

    parser.add_argument(
        '--output',
        type=str,
        metavar='FILE',
        help='Output file path for template generation'
    )

    parser.add_argument(
        '--author',
        type=str,
        help='Author name for plugin template'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing file (use with --create-plugin-template)'
    )

    args = parser.parse_args()

    # Check for configuration management commands first (before mode determination)
    from src.config import config_cli

    if args.show_config:
        return config_cli.show_config_command(mask_sensitive=True)

    if args.validate_config:
        return config_cli.validate_config_command()

    if args.generate_config:
        return config_cli.generate_config_command()

    if args.reset_config:
        return config_cli.reset_config_command()

    if args.setup:
        return config_cli.setup_command()

    if args.encrypt_value:
        return config_cli.encrypt_value_command(args.encrypt_value)

    if args.rotate_key:
        return config_cli.rotate_key_command()

    if args.test_config:
        return config_cli.test_config_command()

    if args.config_help:
        return config_cli.config_help_command()

    if args.config_schema:
        return config_cli.config_schema_command()

    # Check for plugin management commands
    from src.core import plugin_cli

    if args.list_plugins:
        return plugin_cli.list_plugins_command(vendor=args.vendor, category=args.category)

    if args.plugin_info:
        return plugin_cli.plugin_info_command(args.plugin_info)

    if args.validate_plugin:
        return plugin_cli.validate_plugin_command(args.validate_plugin)

    if args.test_plugin:
        if not args.port:
            print("Error: --test-plugin requires --port argument", file=sys.stderr)
            return 1
        return plugin_cli.test_plugin_command(args.test_plugin, args.port, args.baud)

    if args.validate_all_plugins:
        return plugin_cli.validate_all_plugins_command()

    if args.create_plugin_template:
        vendor, model = args.create_plugin_template
        return plugin_cli.create_plugin_template_command(
            vendor=vendor,
            model=model,
            category=args.plugin_category,
            output_path=args.output,
            author=args.author,
            overwrite=args.overwrite
        )

    # Determine mode: GUI is default if no CLI-specific args
    cli_mode = args.cli or args.discover_ports or args.command

    # Launch GUI mode
    if args.gui or not cli_mode:
        try:
            from src.gui.application import main as gui_main
            return gui_main()
        except ImportError as e:
            print("Error: GUI dependencies not installed.", file=sys.stderr)
            print("Please install GUI dependencies: pip install -r requirements.txt", file=sys.stderr)
            print(f"Details: {e}", file=sys.stderr)
            return 1

    # CLI mode - initialize configuration
    try:
        ConfigManager.initialize()
        if args.verbose:
            print("Configuration loaded")
    except Exception as e:
        print(f"Warning: Failed to load configuration: {e}", file=sys.stderr)

    # Initialize logger if --log flag provided
    logger = None
    if args.log:
        try:
            # Generate default log file path if not specified
            log_file_path = args.log_file
            if not log_file_path:
                log_dir = Path.home() / ".modem-inspector" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_path = str(log_dir / f"comm_{timestamp}.log")

            # Parse log level
            try:
                log_level = LogLevel[args.log_level]
            except KeyError:
                log_level = LogLevel.INFO

            # Initialize CommunicationLogger
            logger = CommunicationLogger(
                log_level=log_level,
                enable_file=True,
                enable_console=args.log_to_console,
                log_file_path=log_file_path,
                max_file_size_mb=10,
                backup_count=5
            )

            if args.verbose:
                print(f"Logging enabled: {log_file_path}")

        except Exception as e:
            print(f"Warning: Failed to initialize logger: {e}", file=sys.stderr)
            logger = None

    # Handle discover-ports
    if args.discover_ports:
        discover_ports()
        return 0

    # Handle command execution
    if args.command:
        if not args.port:
            print("Error: --port is required when executing commands", file=sys.stderr)
            return 1

        try:
            exit_code = execute_command(
                port=args.port,
                baud=args.baud,
                command=args.command,
                timeout=args.timeout,
                verbose=args.verbose,
                logger=logger
            )

            # Display log file location on exit if logging enabled
            if logger and args.verbose:
                print(f"\nLog file: {logger.log_file_path}")

            return exit_code

        finally:
            # Close logger to flush buffers
            if logger:
                logger.close()

    # No action specified
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
