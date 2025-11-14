"""Plugin management CLI commands.

Provides command-line interface for plugin discovery, validation, testing,
and information display.
"""

import sys
from pathlib import Path
from typing import Optional
from src.core.plugin_manager import PluginManager
from src.core.plugin_validator import PluginValidator
from src.core.serial_handler import SerialHandler
from src.core.at_executor import ATExecutor


def list_plugins_command(vendor: Optional[str] = None, category: Optional[str] = None) -> int:
    """List all discovered plugins with optional filtering.

    Args:
        vendor: Optional vendor filter (case-insensitive).
        category: Optional category filter.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        manager = PluginManager()
        plugins = manager.discover_plugins()

        if not plugins:
            print("No plugins found.")
            return 0

        # Apply filters
        if vendor:
            plugins = [p for p in plugins if p.metadata.vendor.lower() == vendor.lower()]
        if category:
            plugins = [p for p in plugins if p.metadata.category == category]

        if not plugins:
            print(f"No plugins found matching filters (vendor={vendor}, category={category})")
            return 0

        # Display table header
        print(f"\nFound {len(plugins)} plugin(s):\n")
        print(f"{'Vendor':<15} {'Model':<20} {'Category':<15} {'Version':<10} {'Commands':<10} {'Path'}")
        print("=" * 110)

        # Display plugins
        for plugin in plugins:
            commands_count = len(plugin.get_all_commands())
            # Get plugin file path if available
            plugin_files = list(Path("src/plugins").rglob(f"{plugin.metadata.model}.yaml"))
            plugin_path = str(plugin_files[0]) if plugin_files else "N/A"

            print(f"{plugin.metadata.vendor:<15} {plugin.metadata.model:<20} {plugin.metadata.category:<15} "
                  f"{plugin.metadata.version:<10} {commands_count:<10} {plugin_path}")

        print()
        return 0

    except Exception as e:
        print(f"Error listing plugins: {e}", file=sys.stderr)
        return 1


def plugin_info_command(plugin_id: str) -> int:
    """Show detailed information about a specific plugin.

    Args:
        plugin_id: Plugin identifier in format "vendor.model".

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        # Parse vendor.model
        if '.' not in plugin_id:
            print(f"Error: Plugin ID must be in format 'vendor.model' (got '{plugin_id}')", file=sys.stderr)
            return 1

        vendor, model = plugin_id.split('.', 1)

        # Load plugin
        manager = PluginManager()
        manager.discover_plugins()
        plugin = manager.get_plugin(vendor, model)

        if not plugin:
            print(f"Error: Plugin '{plugin_id}' not found", file=sys.stderr)
            return 1

        # Display plugin information
        print(f"\n{'='*70}")
        print(f"Plugin: {plugin.metadata.vendor}.{plugin.metadata.model}")
        print(f"{'='*70}\n")

        # Metadata
        print("Metadata:")
        print(f"  Vendor:         {plugin.metadata.vendor}")
        print(f"  Model:          {plugin.metadata.model}")
        print(f"  Category:       {plugin.metadata.category}")
        print(f"  Version:        {plugin.metadata.version}")
        if plugin.metadata.author:
            print(f"  Author:         {plugin.metadata.author}")
        if plugin.metadata.compatible_with:
            print(f"  Compatible:     {plugin.metadata.compatible_with}")
        if plugin.metadata.variants:
            print(f"  Variants:       {', '.join(plugin.metadata.variants)}")

        # Connection
        print(f"\nConnection:")
        print(f"  Default Baud:   {plugin.connection.default_baud}")
        print(f"  Data Bits:      {plugin.connection.data_bits}")
        print(f"  Parity:         {plugin.connection.parity}")
        print(f"  Stop Bits:      {plugin.connection.stop_bits}")
        print(f"  Flow Control:   {plugin.connection.flow_control}")
        if plugin.connection.init_sequence:
            print(f"  Init Sequence:  {len(plugin.connection.init_sequence)} command(s)")

        # Commands by category
        print(f"\nCommands:")
        for category, cmds in plugin.commands.items():
            print(f"  {category}: {len(cmds)} command(s)")
            for cmd in cmds[:3]:  # Show first 3 commands per category
                critical = " [CRITICAL]" if getattr(cmd, 'critical', False) else ""
                quick = " [QUICK]" if getattr(cmd, 'quick', False) else ""
                print(f"    - {cmd.cmd:20} {cmd.description}{critical}{quick}")
            if len(cmds) > 3:
                print(f"    ... and {len(cmds) - 3} more")

        # Parsers
        if plugin.parsers:
            print(f"\nParsers: {len(plugin.parsers)}")
            for parser_name, parser_def in list(plugin.parsers.items())[:5]:
                print(f"  - {parser_name:20} (type: {parser_def.type.value})")
            if len(plugin.parsers) > 5:
                print(f"  ... and {len(plugin.parsers) - 5} more")

        # Validation
        if plugin.validation:
            print(f"\nValidation:")
            if plugin.validation.required_responses:
                print(f"  Required:       {len(plugin.validation.required_responses)} command(s)")
            if plugin.validation.expected_manufacturer:
                print(f"  Manufacturer:   {plugin.validation.expected_manufacturer}")
            if plugin.validation.expected_model_pattern:
                print(f"  Model Pattern:  {plugin.validation.expected_model_pattern}")

        print(f"\n{'='*70}\n")
        return 0

    except Exception as e:
        print(f"Error showing plugin info: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def validate_plugin_command(file_path: str) -> int:
    """Validate a plugin YAML file.

    Args:
        file_path: Path to plugin YAML file.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            return 1

        print(f"Validating plugin: {file_path}")
        print("=" * 70)

        validator = PluginValidator()
        is_valid, errors, warnings = validator.validate_file(path)

        if is_valid:
            print(f"[OK] Schema validation: PASSED")
            if warnings:
                print(f"\nWarnings ({len(warnings)}):")
                for warning in warnings:
                    print(f"  [!] {warning}")
            else:
                print("[OK] No warnings")
            print("\n[OK] Plugin is valid\n")
            return 0
        else:
            print(f"[X] Schema validation: FAILED")
            print(f"\nErrors ({len(errors)}):")
            for error in errors:
                print(f"  [X] {error}")
            print()
            return 1

    except Exception as e:
        print(f"Error validating plugin: {e}", file=sys.stderr)
        return 1


def test_plugin_command(file_path: str, port: str, baud: int = 115200) -> int:
    """Test plugin against real hardware.

    Args:
        file_path: Path to plugin YAML file.
        port: Serial port device.
        baud: Baud rate (default: 115200).

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            return 1

        print(f"Testing plugin: {file_path}")
        print(f"Port: {port} @ {baud} baud")
        print("=" * 70)

        # Load plugin
        manager = PluginManager()
        plugin = manager.load_plugin(path)
        print(f"[OK] Plugin loaded: {plugin.metadata.vendor}.{plugin.metadata.model}")

        # Open serial port
        print(f"\nConnecting to {port}...")
        handler = SerialHandler(port, baud_rate=baud)
        handler.open()
        print("[OK] Port opened")

        # Create executor
        executor = ATExecutor(handler)

        # Test plugin
        print("\nRunning hardware tests...")
        validator = PluginValidator()
        result = validator.test_plugin(plugin, handler, executor)

        # Display results
        print(f"\nTest Results:")
        print(f"  Passed:  {len(result.passed_commands)} command(s)")
        print(f"  Failed:  {len(result.failed_commands)} command(s)")
        print(f"  Success: {result.success_rate():.1%}")

        if result.validation_passed:
            print("  [OK] Validation: PASSED")
        else:
            print("  [X] Validation: FAILED")

        if result.validation_errors:
            print(f"\nValidation Errors:")
            for error in result.validation_errors:
                print(f"  [X] {error}")

        # Close handler
        handler.close()
        print("\n" + "=" * 70 + "\n")

        return 0 if result.validation_passed else 1

    except Exception as e:
        print(f"Error testing plugin: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def validate_all_plugins_command() -> int:
    """Validate all plugins in plugin directories.

    Returns:
        Exit code (0 if all valid, 1 if any invalid).
    """
    try:
        print("Validating all plugins...")
        print("=" * 70)

        # Find all plugin files
        plugin_files = list(Path("src/plugins").rglob("*.yaml"))
        if not plugin_files:
            print("No plugin files found in src/plugins/")
            return 0

        validator = PluginValidator()
        valid_count = 0
        invalid_count = 0
        warning_count = 0

        for plugin_file in plugin_files:
            is_valid, errors, warnings = validator.validate_file(plugin_file)

            if is_valid:
                status = "[OK] VALID"
                valid_count += 1
                if warnings:
                    status += f" ({len(warnings)} warning(s))"
                    warning_count += len(warnings)
            else:
                status = "[X] INVALID"
                invalid_count += 1

            print(f"{str(plugin_file):<60} {status}")

            # Show errors
            if errors:
                for error in errors:
                    print(f"  [X] {error}")

        # Summary
        print("\n" + "=" * 70)
        print(f"Summary:")
        print(f"  Total:    {len(plugin_files)} file(s)")
        print(f"  Valid:    {valid_count}")
        print(f"  Invalid:  {invalid_count}")
        print(f"  Warnings: {warning_count}")
        print()

        return 0 if invalid_count == 0 else 1

    except Exception as e:
        print(f"Error validating plugins: {e}", file=sys.stderr)
        return 1


def create_plugin_template_command(
    vendor: str,
    model: str,
    category: str = "other",
    output_path: Optional[str] = None,
    author: Optional[str] = None,
    overwrite: bool = False
) -> int:
    """Generate a plugin template.

    Args:
        vendor: Vendor name.
        model: Model name.
        category: Plugin category (default: "other").
        output_path: Optional output file path. If None, prints to stdout.
        author: Optional author name.
        overwrite: If True, overwrite existing file.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    try:
        from src.core.plugin_generator import PluginGenerator

        generator = PluginGenerator()

        # Determine output path
        if output_path:
            output = Path(output_path)
        else:
            # Default path: src/plugins/vendor/model.yaml
            output = Path(f"src/plugins/{vendor}/{model}.yaml")

        print(f"Generating plugin template...")
        print(f"  Vendor:   {vendor}")
        print(f"  Model:    {model}")
        print(f"  Category: {category}")
        if author:
            print(f"  Author:   {author}")
        print("=" * 70)

        # Generate template
        yaml_content = generator.generate_template(
            vendor=vendor,
            model=model,
            category=category,
            output_path=output,
            author=author,
            overwrite=overwrite
        )

        # If no output path, print to stdout
        if not output_path:
            print("\n" + yaml_content)

        # Show vendor-specific commands info
        vendor_cmds = generator.list_vendor_commands(vendor)
        if vendor_cmds:
            print(f"\n[OK] Added {sum(len(cmds) for cmds in vendor_cmds.values())} vendor-specific commands for {vendor}")
        else:
            supported = generator.list_supported_vendors()
            if supported:
                print(f"\n[INFO] No vendor-specific commands for '{vendor}'")
                print(f"       Supported vendors: {', '.join(supported)}")

        print("\n[OK] Template generated successfully")
        print(f"\nNext steps:")
        print(f"  1. Review and customize the generated template")
        print(f"  2. Add vendor-specific AT commands to the commands section")
        print(f"  3. Define parsers for complex responses")
        print(f"  4. Update validation rules")
        print(f"  5. Validate: py main.py --validate-plugin {output}")
        print()

        return 0

    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Use --overwrite to replace existing file", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error generating template: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
