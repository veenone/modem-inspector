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

    args = parser.parse_args()

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
