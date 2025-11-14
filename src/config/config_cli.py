"""Configuration management CLI commands.

Provides command-line interface for configuration operations including
validation, generation, encryption, and interactive setup.
"""

import sys
import json
from pathlib import Path
from typing import Optional
from src.config.config_manager import ConfigManager
from src.config.config_wizard import ConfigWizard
from src.config.config_encryption import ConfigEncryption
from src.config.config_schema import ConfigSchema


def show_config_command(mask_sensitive: bool = True) -> int:
    """Display current configuration with sources.

    Args:
        mask_sensitive: Mask sensitive fields (default True)

    Returns:
        Exit code (0 for success)
    """
    try:
        manager = ConfigManager.instance()
        config_dict = manager.show_config(mask_sensitive=mask_sensitive)

        print("\n" + "=" * 70)
        print("  Current Configuration")
        print("=" * 70)

        _print_config_section("Serial Settings", config_dict.get("serial", {}))
        _print_config_section("Plugin Settings", config_dict.get("plugins", {}))
        _print_config_section("Repository Settings", config_dict.get("repository", {}))
        _print_config_section("Reporting Settings", config_dict.get("reporting", {}))
        _print_config_section("Logging Settings", config_dict.get("logging", {}))
        _print_config_section("Parallel Settings", config_dict.get("parallel", {}))
        _print_config_section("Encryption Settings", config_dict.get("encryption", {}))

        print()
        return 0

    except Exception as e:
        print(f"Error showing configuration: {e}", file=sys.stderr)
        return 1


def _print_config_section(title: str, section: dict) -> None:
    """Print configuration section."""
    print(f"\n{title}:")
    for key, value in section.items():
        if key == "_source":
            continue
        source = section.get("_source", {}).get(key, "unknown")
        print(f"  {key}: {value} (source: {source})")


def validate_config_command(config_path: Optional[str] = None) -> int:
    """Validate configuration file.

    Args:
        config_path: Path to config file (default: use ConfigManager)

    Returns:
        Exit code (0 if valid, 1 if invalid)
    """
    try:
        if config_path:
            # Validate specific file
            import yaml
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
        else:
            # Validate current configuration
            manager = ConfigManager.instance()
            config_dict = manager.get_config().to_dict()

        # Validate against schema
        schema = ConfigSchema()
        is_valid, errors = schema.validate_config(config_dict)

        print("\n" + "=" * 70)
        print("  Configuration Validation")
        print("=" * 70)

        if is_valid:
            print("\n[OK] Configuration is valid")
            print()
            return 0
        else:
            print(f"\n[ERROR] Configuration has {len(errors)} error(s):\n")
            for i, error in enumerate(errors, 1):
                print(f"{i}. {error}")
            print()
            return 1

    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error validating configuration: {e}", file=sys.stderr)
        return 1


def generate_config_command(output_path: str = "./config.yaml", force: bool = False) -> int:
    """Generate default configuration file.

    Args:
        output_path: Path to output file
        force: Overwrite existing file

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        output_file = Path(output_path)

        # Check if file exists
        if output_file.exists() and not force:
            print(f"Error: File already exists: {output_path}", file=sys.stderr)
            print("Use --force to overwrite", file=sys.stderr)
            return 1

        # Get default config
        from src.config.defaults import get_default_config
        config = get_default_config()

        # Save to YAML
        import yaml
        with open(output_file, 'w') as f:
            f.write("# Modem Inspector Configuration\n")
            f.write("# Generated with default values\n\n")
            yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

        print(f"\n[OK] Default configuration generated: {output_file}")
        print("\nNext steps:")
        print("  1. Review and customize the configuration")
        print("  2. Run 'python main.py --validate-config' to validate")
        print("  3. Run 'python main.py --setup' for interactive setup")
        print()
        return 0

    except Exception as e:
        print(f"Error generating configuration: {e}", file=sys.stderr)
        return 1


def reset_config_command(backup: bool = True) -> int:
    """Reset configuration to defaults.

    Args:
        backup: Create backup of existing config

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        config_path = Path("./config.yaml")

        # Backup existing config
        if config_path.exists() and backup:
            backup_path = config_path.with_suffix('.yaml.bak')
            print(f"Backing up existing config to {backup_path}")
            config_path.rename(backup_path)

        # Generate new default config
        return generate_config_command(str(config_path), force=True)

    except Exception as e:
        print(f"Error resetting configuration: {e}", file=sys.stderr)
        return 1


def setup_command() -> int:
    """Launch interactive configuration wizard.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        wizard = ConfigWizard()
        success = wizard.run_interactive_setup()
        return 0 if success else 1

    except Exception as e:
        print(f"Error running setup wizard: {e}", file=sys.stderr)
        return 1


def encrypt_value_command(value: str, key_path: Optional[str] = None) -> int:
    """Encrypt a value for use in configuration.

    Args:
        value: Value to encrypt
        key_path: Optional custom key path

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Use default key path if not specified
        if not key_path:
            from src.config.defaults import get_default_config
            key_path = get_default_config().encryption.key_path

        # Encrypt value
        encryption = ConfigEncryption(enabled=True, key_path=key_path)
        encrypted = encryption.encrypt_value(value)

        print(f"\nEncrypted value:")
        print(f"  {encrypted}")
        print(f"\nYou can use this in your config.yaml file:")
        print(f"  api_token: {encrypted}")
        print(f"\nEncryption key: {key_path}")
        print()
        return 0

    except Exception as e:
        print(f"Error encrypting value: {e}", file=sys.stderr)
        return 1


def rotate_key_command(config_path: str = "./config.yaml") -> int:
    """Rotate encryption key and re-encrypt all sensitive fields.

    Args:
        config_path: Path to configuration file

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        import yaml

        # Load config
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)

        # Get encryption settings
        encryption_config = config_dict.get("encryption", {})
        if not encryption_config.get("enabled"):
            print("Error: Encryption is not enabled in configuration", file=sys.stderr)
            return 1

        key_path = encryption_config.get("key_path")

        # Rotate key
        print("Rotating encryption key...")
        encryption = ConfigEncryption(enabled=True, key_path=key_path)
        config_dict = encryption.rotate_key(config_dict)

        # Save updated config
        print("Saving updated configuration...")
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        print(f"\n[OK] Key rotated successfully")
        print(f"Old key backed up to: {key_path}.old")
        print()
        return 0

    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error rotating key: {e}", file=sys.stderr)
        return 1


def test_config_command(config_path: Optional[str] = None) -> int:
    """Test configuration comprehensively.

    Tests:
    - YAML syntax
    - Schema validation
    - Serial port accessibility
    - Plugin directory existence
    - Repository API connectivity

    Args:
        config_path: Path to config file (default: current config)

    Returns:
        Exit code (0 if all tests pass, 1 if any fail)
    """
    try:
        print("\n" + "=" * 70)
        print("  Configuration Test Suite")
        print("=" * 70)

        all_passed = True

        # Test 1: YAML syntax
        print("\n[1/5] Testing YAML syntax...")
        if config_path:
            import yaml
            try:
                with open(config_path, 'r') as f:
                    config_dict = yaml.safe_load(f)
                print("  [OK] YAML syntax is valid")
            except yaml.YAMLError as e:
                print(f"  [FAIL] YAML syntax error: {e}")
                all_passed = False
                return 1
        else:
            config_dict = ConfigManager.instance().get_config().to_dict()
            print("  [OK] Using loaded configuration")

        # Test 2: Schema validation
        print("\n[2/5] Testing schema validation...")
        schema = ConfigSchema()
        is_valid, errors = schema.validate_config(config_dict)
        if is_valid:
            print("  [OK] Schema validation passed")
        else:
            print(f"  [FAIL] Schema validation failed ({len(errors)} errors)")
            for error in errors[:3]:
                print(f"    - {error}")
            all_passed = False

        # Test 3: Serial ports
        print("\n[3/5] Testing serial port accessibility...")
        from src.core import SerialHandler
        ports = SerialHandler.discover_ports()
        if ports:
            print(f"  [OK] Found {len(ports)} serial port(s)")
        else:
            print("  [WARN] No serial ports found")

        # Test 4: Plugin directories
        print("\n[4/5] Testing plugin directories...")
        plugin_dirs = config_dict.get("plugins", {}).get("directories", [])
        missing_dirs = []
        for plugin_dir in plugin_dirs:
            if not Path(plugin_dir).expanduser().exists():
                missing_dirs.append(plugin_dir)

        if not missing_dirs:
            print(f"  [OK] All {len(plugin_dirs)} plugin directories exist")
        else:
            print(f"  [WARN] {len(missing_dirs)} plugin directories not found:")
            for missing in missing_dirs:
                print(f"    - {missing}")

        # Test 5: Repository connectivity
        print("\n[5/5] Testing repository connectivity...")
        repo_config = config_dict.get("repository", {})
        if repo_config.get("enabled") and repo_config.get("api_url"):
            try:
                import requests
                response = requests.get(repo_config["api_url"], timeout=5)
                if response.status_code < 400:
                    print("  [OK] Repository is reachable")
                else:
                    print(f"  [WARN] Repository returned status {response.status_code}")
            except Exception as e:
                print(f"  [WARN] Could not reach repository: {e}")
        else:
            print("  [SKIP] Repository sync not enabled")

        # Summary
        print("\n" + "=" * 70)
        if all_passed:
            print("  All tests passed!")
        else:
            print("  Some tests failed - see details above")
        print("=" * 70)
        print()

        return 0 if all_passed else 1

    except Exception as e:
        print(f"Error testing configuration: {e}", file=sys.stderr)
        return 1


def config_help_command() -> int:
    """Display configuration help documentation.

    Returns:
        Exit code (0 for success)
    """
    help_text = """
Configuration Management Help
=============================

Configuration File: config.yaml
Default Location: ./config.yaml or ~/.modem-inspector/config.yaml

Sections:
---------
1. serial - Serial port settings
   - default_baud: Baud rate (9600-921600)
   - default_timeout: Timeout in seconds
   - retry_attempts: Number of retries on timeout
   - retry_delay_ms: Delay between retries (milliseconds)

2. plugins - Plugin management
   - directories: List of plugin directories
   - auto_discover: Auto-discover plugins on startup (true/false)
   - validation_level: ERROR, WARNING, or STRICT

3. repository - Plugin repository sync
   - enabled: Enable repository sync (true/false)
   - api_url: Repository API URL
   - api_token: API authentication token (can be encrypted)
   - sync_mode: MANUAL or AUTO

4. reporting - Report generation
   - format: CSV, JSON, or HTML
   - output_directory: Directory for generated reports
   - timestamp_format: Timestamp format for filenames

5. logging - Communication logging
   - enabled: Enable logging (true/false)
   - level: DEBUG, INFO, WARNING, or ERROR
   - log_to_file: Log to file (true/false)
   - log_to_console: Log to console (true/false)

6. parallel - Parallel execution
   - enabled: Enable parallel testing (true/false)
   - max_workers: Maximum parallel workers
   - worker_timeout: Worker timeout in seconds

7. encryption - Sensitive data encryption
   - enabled: Enable encryption (true/false)
   - key_path: Path to encryption key file

Environment Variables:
---------------------
Override configuration with MODEM_INSPECTOR_SECTION_KEY format:
  MODEM_INSPECTOR_SERIAL_DEFAULT_BAUD=115200
  MODEM_INSPECTOR_PLUGINS_AUTO_DISCOVER=true
  MODEM_INSPECTOR_REPOSITORY_API_URL=https://api.example.com

Commands:
--------
  --show-config          Show current configuration
  --validate-config      Validate configuration file
  --generate-config      Generate default configuration
  --reset-config         Reset to defaults (with backup)
  --setup                Launch interactive setup wizard
  --encrypt-value VALUE  Encrypt a value for configuration
  --rotate-key           Rotate encryption key
  --test-config          Run comprehensive configuration tests
  --config-help          Show this help message

Examples:
--------
  # Interactive setup
  python main.py --setup

  # Validate configuration
  python main.py --validate-config

  # Encrypt API token
  python main.py --encrypt-value "my-secret-token"

  # Show current config
  python main.py --show-config

For more information, see docs/configuration_reference.md
"""
    print(help_text)
    return 0


def config_schema_command(output_file: Optional[str] = None) -> int:
    """Output JSON schema for IDE autocomplete.

    Args:
        output_file: Optional file to write schema to

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        schema = ConfigSchema()
        schema_dict = schema.get_schema()

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(schema_dict, f, indent=2)
            print(f"JSON schema written to: {output_file}")
        else:
            print(json.dumps(schema_dict, indent=2))

        return 0

    except Exception as e:
        print(f"Error outputting schema: {e}", file=sys.stderr)
        return 1
