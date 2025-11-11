"""Modem Inspector - AT Command Engine CLI.

Basic command-line interface for testing the AT Command Engine.
"""

import argparse
import sys
from typing import Optional

from src.core import SerialHandler, ATExecutor, PortInfo
from src.config import ConfigManager


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


def execute_command(port: str, baud: int, command: str, timeout: float, verbose: bool) -> int:
    """Execute single AT command on specified port.

    Args:
        port: Serial port device path
        baud: Baud rate
        command: AT command to execute
        timeout: Command timeout in seconds
        verbose: Enable verbose output

    Returns:
        Exit code (0 for success, 1 for error)
    """
    handler = None
    try:
        # Initialize handler
        if verbose:
            print(f"Opening port {port} at {baud} baud...")

        handler = SerialHandler(port, baud_rate=baud)
        handler.open()

        if verbose:
            print(f"Port opened successfully")

        # Create executor
        executor = ATExecutor(handler, default_timeout=timeout)

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
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Modem Inspector - AT Command Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --discover-ports
  %(prog)s --port COM3 --command "AT"
  %(prog)s --port /dev/ttyUSB0 --baud 9600 --command "AT+CGMI" --verbose
        """
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

    args = parser.parse_args()

    # Initialize configuration
    try:
        ConfigManager.initialize()
        if args.verbose:
            print("Configuration loaded")
    except Exception as e:
        print(f"Warning: Failed to load configuration: {e}", file=sys.stderr)

    # Handle discover-ports
    if args.discover_ports:
        discover_ports()
        return 0

    # Handle command execution
    if args.command:
        if not args.port:
            print("Error: --port is required when executing commands", file=sys.stderr)
            return 1

        return execute_command(
            port=args.port,
            baud=args.baud,
            command=args.command,
            timeout=args.timeout,
            verbose=args.verbose
        )

    # No action specified
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())
