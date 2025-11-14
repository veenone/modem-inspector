"""Interactive configuration wizard for Modem Inspector.

Guides users through setup via command-line prompts with validation,
testing, and encryption support.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import sys
import re

try:
    from ruamel.yaml import YAML
    HAS_RUAMEL = True
except ImportError:
    import yaml
    HAS_RUAMEL = False

from src.config.config_models import (
    Config,
    SerialConfig,
    PluginsConfig,
    RepositoryConfig,
    ReportingConfig,
    LoggingConfig,
    ParallelConfig,
    EncryptionConfig,
    ValidationLevel,
    SyncMode,
    ReportFormat,
    LogLevel
)
from src.config.defaults import get_default_config
from src.config.config_schema import ConfigSchema
from src.config.config_encryption import ConfigEncryption


class ConfigWizard:
    """Interactive configuration setup wizard.

    Guides users through configuration via command-line prompts,
    validates inputs, tests connections, and saves configuration
    with encryption support and helpful comments.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize wizard.

        Args:
            config_path: Path to save configuration (default: ./config.yaml)
        """
        self.config_path = config_path or Path("./config.yaml")
        self.schema = ConfigSchema()

    def run_interactive_setup(self) -> bool:
        """Run full interactive setup wizard.

        Returns:
            True if configuration was created successfully, False otherwise
        """
        print("\n" + "=" * 70)
        print("  Modem Inspector - Configuration Setup Wizard")
        print("=" * 70)
        print()
        print("This wizard will guide you through setting up Modem Inspector.")
        print("Press Ctrl+C at any time to cancel.\n")

        # Check for existing configuration
        if self.config_path.exists():
            print(f"Existing configuration found: {self.config_path}")
            action = self._prompt_choice(
                "What would you like to do?",
                ["Modify existing configuration", "Create new configuration", "Cancel"],
                default=1
            )

            if action == 3:  # Cancel
                print("\nSetup cancelled.")
                return False
            elif action == 2:  # Create new
                backup_path = self.config_path.with_suffix('.yaml.bak')
                print(f"\nBacking up existing config to {backup_path}")
                self.config_path.rename(backup_path)

        try:
            # Get defaults for suggestions
            defaults = get_default_config()

            # Prompt for each section
            print("\n--- Serial Port Settings ---")
            serial_config = self._prompt_serial_settings(defaults.serial)

            print("\n--- Plugin Settings ---")
            plugins_config = self._prompt_plugin_settings(defaults.plugins)

            print("\n--- Repository Settings ---")
            repository_config = self._prompt_repository_settings(defaults.repository)

            print("\n--- Reporting Settings ---")
            reporting_config = self._prompt_reporting_settings(defaults.reporting)

            print("\n--- Logging Settings ---")
            logging_config = self._prompt_logging_settings(defaults.logging)

            print("\n--- Parallel Execution Settings ---")
            parallel_config = self._prompt_parallel_settings(defaults.parallel)

            print("\n--- Encryption Settings ---")
            encryption_config = self._prompt_encryption_settings(defaults.encryption)

            # Create complete config
            config = Config(
                serial=serial_config,
                plugins=plugins_config,
                repository=repository_config,
                reporting=reporting_config,
                logging=logging_config,
                parallel=parallel_config,
                encryption=encryption_config
            )

            # Test configuration
            print("\n--- Testing Configuration ---")
            if self._test_configuration(config):
                print("[OK] Configuration tests passed")
            else:
                if not self._prompt_yes_no("\nSome tests failed. Continue anyway?", default=False):
                    print("\nSetup cancelled.")
                    return False

            # Save configuration
            print("\n--- Saving Configuration ---")
            self._save_config(config)

            # Display summary
            print("\n" + "=" * 70)
            print("  Configuration Saved Successfully!")
            print("=" * 70)
            print(f"\nConfiguration file: {self.config_path.absolute()}")
            print("\nSummary:")
            print(f"  Serial baud rate: {config.serial.default_baud}")
            print(f"  Plugin directories: {len(config.plugins.directories)}")
            print(f"  Repository sync: {'Enabled' if config.repository.enabled else 'Disabled'}")
            print(f"  Report format: {config.reporting.format.value}")
            print(f"  Logging: {'Enabled' if config.logging.enabled else 'Disabled'}")
            print(f"  Encryption: {'Enabled' if config.encryption.enabled else 'Disabled'}")

            print("\nYou can now run 'python main.py' to start Modem Inspector.")
            print()

            return True

        except KeyboardInterrupt:
            print("\n\nSetup cancelled by user.")
            return False
        except Exception as e:
            print(f"\n\nError during setup: {e}")
            return False

    def _prompt_serial_settings(self, defaults: SerialConfig) -> SerialConfig:
        """Prompt for serial port settings.

        Args:
            defaults: Default serial configuration for suggestions

        Returns:
            SerialConfig with user-provided values
        """
        baud = self._prompt_baud_rate(
            "Default baud rate",
            default=defaults.default_baud
        )

        timeout = self._prompt_int(
            "Default timeout (seconds)",
            default=defaults.default_timeout,
            min_value=1,
            max_value=300
        )

        retry_attempts = self._prompt_int(
            "Retry attempts on timeout",
            default=defaults.retry_attempts,
            min_value=0,
            max_value=10
        )

        retry_delay = self._prompt_int(
            "Retry delay (milliseconds)",
            default=defaults.retry_delay_ms,
            min_value=100,
            max_value=10000
        )

        return SerialConfig(
            default_baud=baud,
            default_timeout=timeout,
            retry_attempts=retry_attempts,
            retry_delay_ms=retry_delay
        )

    def _prompt_plugin_settings(self, defaults: PluginsConfig) -> PluginsConfig:
        """Prompt for plugin settings.

        Args:
            defaults: Default plugin configuration

        Returns:
            PluginsConfig with user-provided values
        """
        print("Plugin directories (comma-separated):")
        print(f"  Default: {', '.join(defaults.directories)}")

        dirs_input = input("Plugin directories [press Enter for default]: ").strip()
        if dirs_input:
            directories = [d.strip() for d in dirs_input.split(',')]
        else:
            directories = defaults.directories

        auto_discover = self._prompt_yes_no(
            "Auto-discover plugins on startup?",
            default=defaults.auto_discover
        )

        validation_level = self._prompt_choice(
            "Plugin validation level",
            ["ERROR (loose validation)", "WARNING (moderate)", "STRICT (strict)"],
            default=2
        )

        validation_map = {
            1: ValidationLevel.ERROR,
            2: ValidationLevel.WARNING,
            3: ValidationLevel.STRICT
        }

        return PluginsConfig(
            directories=directories,
            auto_discover=auto_discover,
            validation_level=validation_map[validation_level]
        )

    def _prompt_repository_settings(self, defaults: RepositoryConfig) -> RepositoryConfig:
        """Prompt for repository settings.

        Args:
            defaults: Default repository configuration

        Returns:
            RepositoryConfig with user-provided values
        """
        enabled = self._prompt_yes_no(
            "Enable plugin repository sync?",
            default=defaults.enabled
        )

        if not enabled:
            return RepositoryConfig(enabled=False)

        api_url = self._prompt_url(
            "Repository API URL",
            default=defaults.api_url or "https://plugins.example.com/api"
        )

        api_token = input("Repository API token [optional]: ").strip() or None

        sync_mode_choice = self._prompt_choice(
            "Sync mode",
            ["MANUAL (sync on command)", "AUTO (automatic updates)"],
            default=1
        )

        sync_mode = SyncMode.MANUAL if sync_mode_choice == 1 else SyncMode.AUTO

        return RepositoryConfig(
            enabled=enabled,
            api_url=api_url,
            api_token=api_token,
            sync_mode=sync_mode
        )

    def _prompt_reporting_settings(self, defaults: ReportingConfig) -> ReportingConfig:
        """Prompt for reporting settings.

        Args:
            defaults: Default reporting configuration

        Returns:
            ReportingConfig with user-provided values
        """
        format_choice = self._prompt_choice(
            "Report format",
            ["CSV", "JSON", "HTML"],
            default=1
        )

        format_map = {1: ReportFormat.CSV, 2: ReportFormat.JSON, 3: ReportFormat.HTML}
        report_format = format_map[format_choice]

        output_dir = input(
            f"Output directory [default: {defaults.output_directory}]: "
        ).strip() or defaults.output_directory

        return ReportingConfig(
            format=report_format,
            output_directory=output_dir,
            timestamp_format=defaults.timestamp_format
        )

    def _prompt_logging_settings(self, defaults: LoggingConfig) -> LoggingConfig:
        """Prompt for logging settings.

        Args:
            defaults: Default logging configuration

        Returns:
            LoggingConfig with user-provided values
        """
        enabled = self._prompt_yes_no(
            "Enable communication logging?",
            default=defaults.enabled
        )

        if not enabled:
            return LoggingConfig(enabled=False)

        level_choice = self._prompt_choice(
            "Log level",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            default=2
        )

        level_map = {
            1: LogLevel.DEBUG,
            2: LogLevel.INFO,
            3: LogLevel.WARNING,
            4: LogLevel.ERROR
        }
        log_level = level_map[level_choice]

        log_to_file = self._prompt_yes_no("Log to file?", default=True)
        log_to_console = self._prompt_yes_no("Log to console?", default=True)

        return LoggingConfig(
            enabled=enabled,
            level=log_level,
            log_to_file=log_to_file,
            log_to_console=log_to_console,
            max_file_size_mb=defaults.max_file_size_mb,
            backup_count=defaults.backup_count
        )

    def _prompt_parallel_settings(self, defaults: ParallelConfig) -> ParallelConfig:
        """Prompt for parallel execution settings.

        Args:
            defaults: Default parallel configuration

        Returns:
            ParallelConfig with user-provided values
        """
        enabled = self._prompt_yes_no(
            "Enable parallel modem testing?",
            default=defaults.enabled
        )

        if not enabled:
            return ParallelConfig(enabled=False)

        max_workers = self._prompt_int(
            "Maximum parallel workers",
            default=defaults.max_workers,
            min_value=1,
            max_value=32
        )

        return ParallelConfig(
            enabled=enabled,
            max_workers=max_workers,
            worker_timeout=defaults.worker_timeout
        )

    def _prompt_encryption_settings(self, defaults: EncryptionConfig) -> EncryptionConfig:
        """Prompt for encryption settings.

        Args:
            defaults: Default encryption configuration

        Returns:
            EncryptionConfig with user-provided values
        """
        enabled = self._prompt_yes_no(
            "Enable encryption for sensitive data (API tokens)?",
            default=False
        )

        if not enabled:
            return EncryptionConfig(enabled=False)

        key_path = input(
            f"Encryption key path [default: {defaults.key_path}]: "
        ).strip() or defaults.key_path

        return EncryptionConfig(enabled=enabled, key_path=key_path)

    def _test_configuration(self, config: Config) -> bool:
        """Test configuration for common issues.

        Args:
            config: Configuration to test

        Returns:
            True if all tests pass, False if any fail
        """
        all_passed = True

        # Test 1: Validate against schema
        print("  [1/3] Validating configuration schema...")
        is_valid, errors = self.schema.validate_config(config.to_dict())
        if is_valid:
            print("    [OK] Schema validation passed")
        else:
            print(f"    [WARN] Schema validation warnings: {len(errors)}")
            for error in errors[:3]:  # Show first 3 errors
                print(f"      - {error}")
            all_passed = False

        # Test 2: Check plugin directories exist
        print("  [2/3] Checking plugin directories...")
        missing_dirs = []
        for plugin_dir in config.plugins.directories:
            if not Path(plugin_dir).expanduser().exists():
                missing_dirs.append(plugin_dir)

        if missing_dirs:
            print(f"    [WARN] Plugin directories not found: {missing_dirs}")
            print("      These will be created on first run")
        else:
            print("    [OK] Plugin directories exist")

        # Test 3: Test repository connectivity (if enabled)
        print("  [3/3] Testing repository connectivity...")
        if config.repository.enabled and config.repository.api_url:
            try:
                import requests
                response = requests.get(config.repository.api_url, timeout=5)
                if response.status_code < 400:
                    print("    [OK] Repository is reachable")
                else:
                    print(f"    [WARN] Repository returned status {response.status_code}")
                    all_passed = False
            except Exception as e:
                print(f"    [WARN] Could not reach repository: {e}")
                all_passed = False
        else:
            print("    [SKIP] Repository sync disabled")

        return all_passed

    def _save_config(self, config: Config) -> None:
        """Save configuration to YAML with comments.

        Args:
            config: Configuration to save
        """
        config_dict = config.to_dict()

        # Encrypt sensitive fields if encryption enabled
        if config.encryption.enabled:
            print("  Encrypting sensitive fields...")
            encryption = ConfigEncryption(
                enabled=True,
                key_path=config.encryption.key_path
            )
            config_dict = encryption.encrypt_sensitive_fields(config_dict)

        # Save with comments
        if HAS_RUAMEL:
            self._save_with_ruamel(config_dict)
        else:
            self._save_with_pyyaml(config_dict)

        print(f"  Configuration saved to {self.config_path}")

    def _save_with_ruamel(self, config_dict: Dict[str, Any]) -> None:
        """Save configuration using ruamel.yaml (preserves comments).

        Args:
            config_dict: Configuration dictionary
        """
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.preserve_quotes = True

        with open(self.config_path, 'w') as f:
            f.write("# Modem Inspector Configuration\n")
            f.write("# Generated by setup wizard\n\n")
            yaml.dump(config_dict, f)

    def _save_with_pyyaml(self, config_dict: Dict[str, Any]) -> None:
        """Save configuration using PyYAML (no comments).

        Args:
            config_dict: Configuration dictionary
        """
        with open(self.config_path, 'w') as f:
            f.write("# Modem Inspector Configuration\n")
            f.write("# Generated by setup wizard\n\n")
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    # Helper prompting methods

    def _prompt_yes_no(self, question: str, default: bool = True) -> bool:
        """Prompt for yes/no answer.

        Args:
            question: Question to ask
            default: Default value if user presses Enter

        Returns:
            True for yes, False for no
        """
        default_str = "Y/n" if default else "y/N"
        while True:
            answer = input(f"{question} [{default_str}]: ").strip().lower()
            if not answer:
                return default
            if answer in ('y', 'yes', '1', 'true'):
                return True
            if answer in ('n', 'no', '0', 'false'):
                return False
            print("  Please enter yes or no")

    def _prompt_int(self, question: str, default: int, min_value: int = None,
                   max_value: int = None) -> int:
        """Prompt for integer value with validation.

        Args:
            question: Question to ask
            default: Default value
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Integer value
        """
        while True:
            answer = input(f"{question} [default: {default}]: ").strip()
            if not answer:
                return default

            try:
                value = int(answer)
                if min_value is not None and value < min_value:
                    print(f"  Value must be >= {min_value}")
                    continue
                if max_value is not None and value > max_value:
                    print(f"  Value must be <= {max_value}")
                    continue
                return value
            except ValueError:
                print("  Please enter a valid integer")

    def _prompt_baud_rate(self, question: str, default: int) -> int:
        """Prompt for baud rate with validation.

        Args:
            question: Question to ask
            default: Default baud rate

        Returns:
            Valid baud rate
        """
        valid_bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

        while True:
            answer = input(f"{question} [default: {default}]: ").strip()
            if not answer:
                return default

            try:
                baud = int(answer)
                is_valid, _ = self.schema.validate_baud_rate(baud)
                if is_valid:
                    return baud
                print(f"  Invalid baud rate. Valid options: {valid_bauds}")
            except ValueError:
                print("  Please enter a valid baud rate")

    def _prompt_url(self, question: str, default: str = None) -> Optional[str]:
        """Prompt for URL with validation.

        Args:
            question: Question to ask
            default: Default URL

        Returns:
            Valid URL or None
        """
        while True:
            prompt_str = f"{question}"
            if default:
                prompt_str += f" [default: {default}]"
            prompt_str += ": "

            answer = input(prompt_str).strip()
            if not answer and default:
                return default
            if not answer:
                return None

            is_valid, error = self.schema.validate_url(answer)
            if is_valid:
                return answer
            print(f"  Invalid URL: {error}")

    def _prompt_choice(self, question: str, choices: List[str], default: int = 1) -> int:
        """Prompt for choice from list.

        Args:
            question: Question to ask
            choices: List of choices
            default: Default choice index (1-based)

        Returns:
            Selected choice index (1-based)
        """
        print(f"\n{question}")
        for i, choice in enumerate(choices, 1):
            marker = "*" if i == default else " "
            print(f"  {marker} {i}. {choice}")

        while True:
            answer = input(f"Choice [default: {default}]: ").strip()
            if not answer:
                return default

            try:
                choice = int(answer)
                if 1 <= choice <= len(choices):
                    return choice
                print(f"  Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print("  Please enter a valid number")


def main():
    """Run configuration wizard."""
    wizard = ConfigWizard()
    success = wizard.run_interactive_setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
