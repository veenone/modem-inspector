"""Configuration manager for Modem Inspector.

Provides singleton access to application configuration with support for
defaults, file loading, and environment variable overrides.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
import os
import yaml
from copy import deepcopy
import signal
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

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


class ConfigFileEventHandler(FileSystemEventHandler):
    """File system event handler for config.yaml changes."""

    def __init__(self, config_manager: 'ConfigManager', config_path: Path):
        """Initialize event handler.

        Args:
            config_manager: ConfigManager instance to reload.
            config_path: Path to config.yaml being watched.
        """
        super().__init__()
        self.config_manager = config_manager
        self.config_path = config_path
        self._last_reload_time = 0
        self._debounce_seconds = 2.0  # Debounce to avoid multiple reloads

    def on_modified(self, event):
        """Handle file modification events.

        Args:
            event: File system event.
        """
        # Only react to config.yaml modifications
        if not isinstance(event, FileModifiedEvent):
            return

        event_path = Path(event.src_path).resolve()
        config_path = self.config_path.resolve()

        if event_path != config_path:
            return

        # Debounce: avoid multiple reloads for same change
        import time
        current_time = time.time()
        if current_time - self._last_reload_time < self._debounce_seconds:
            return

        self._last_reload_time = current_time

        # Reload configuration
        print(f"Configuration file changed: {self.config_path}")
        success = self.config_manager.reload(self.config_path)
        if success:
            print("Configuration reloaded successfully")
        else:
            print("Configuration reload failed - using previous configuration")


class ConfigManager:
    """Singleton configuration manager.

    Provides centralized access to validated configuration with layered loading:
    1. Load defaults
    2. Load from file (if exists)
    3. Apply environment variable overrides
    4. Validate configuration against JSON schema
    5. Decrypt sensitive fields (if encryption enabled)
    6. Return validated Config object
    """

    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None
    _config_source: Dict[str, str] = {}  # Track source of each config value
    _config_path: Optional[Path] = None  # Path to loaded config file
    _file_observer: Optional[Observer] = None  # File watcher observer
    _watch_enabled: bool = False  # Whether file watching is enabled
    _reload_callbacks: List[Callable[[], None]] = []  # Callbacks on successful reload
    _reload_error_callbacks: List[Callable[[str], None]] = []  # Callbacks on failed reload

    def __init__(self):
        """Private constructor. Use instance() or initialize() class methods."""
        if ConfigManager._instance is not None:
            raise RuntimeError("Use ConfigManager.instance() instead of constructor")

    @classmethod
    def instance(cls) -> 'ConfigManager':
        """Get singleton instance of ConfigManager.

        Returns:
            ConfigManager: Singleton instance.

        Raises:
            RuntimeError: If not yet initialized.
        """
        if cls._instance is None:
            raise RuntimeError("ConfigManager not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def initialize(cls,
                   config_path: Optional[Path] = None,
                   skip_validation: bool = False,
                   enable_hot_reload: bool = True) -> 'ConfigManager':
        """Initialize ConfigManager with configuration.

        Args:
            config_path: Optional path to config.yaml. If None, searches default paths.
            skip_validation: Skip schema validation (for testing or when schema not available).
            enable_hot_reload: Enable automatic configuration reload on file changes (default: True).

        Returns:
            ConfigManager: Initialized singleton instance.

        Process:
            1. Load defaults from defaults.py
            2. Search for and load config.yaml if exists
            3. Apply environment variable overrides
            4. Validate against JSON schema
            5. Decrypt sensitive fields (if encryption enabled)
            6. Return Config object
            7. Start file watcher if enabled
            8. Register SIGHUP handler (Unix only)
        """
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            ConfigManager._instance = cls._instance

        # Initialize source tracking
        cls._instance._config_source = {}

        # Step 1: Load defaults
        default_config = get_default_config()
        config_dict = default_config.to_dict()
        cls._instance._mark_source(config_dict, "default")

        # Step 2: Load from file if exists
        if config_path is None:
            config_path = cls._search_config_paths()

        if config_path and config_path.exists():
            try:
                file_config = cls._load_from_file(config_path)
                config_dict = cls._merge_configs(config_dict, file_config)
                cls._instance._mark_source(file_config, "file")
                cls._instance._config_path = config_path
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
                print("Using defaults only")

        # Step 3: Apply environment variable overrides
        env_overrides = cls._apply_env_overrides()
        if env_overrides:
            config_dict = cls._merge_configs(config_dict, env_overrides)
            cls._instance._mark_source(env_overrides, "env")

        # Step 4: Validate configuration
        if not skip_validation:
            is_valid, validation_errors = ConfigSchema.validate_config(config_dict, strict=False)
            if not is_valid:
                error_msg = "Configuration validation failed:\n" + "\n".join(
                    f"  - {error}" for error in validation_errors
                )
                raise ValueError(error_msg)

        # Step 5: Decrypt sensitive fields (if encryption enabled)
        encryption_config = config_dict.get('encryption', {})
        encryption_enabled = encryption_config.get('enabled', False)
        if encryption_enabled:
            encryption_key_path = encryption_config.get('key_path')
            key_path = Path(encryption_key_path) if encryption_key_path else None
            encryption = ConfigEncryption(enabled=True, key_path=key_path)
            config_dict = encryption.decrypt_sensitive_fields(config_dict)

        # Step 6: Convert dict to Config object
        cls._instance._config = cls._dict_to_config(config_dict)

        # Step 7: Start file watcher if enabled and config file exists
        if enable_hot_reload and cls._instance._config_path:
            cls._instance.enable_hot_reload()

        # Step 8: Register SIGHUP handler for manual reload (Unix only)
        cls._instance._register_sighup_handler()

        return cls._instance

    @staticmethod
    def _search_config_paths() -> Optional[Path]:
        """Search for config.yaml in standard locations.

        Search order:
            1. ./config.yaml (current directory)
            2. ~/.modem-inspector/config.yaml (user home directory)

        Returns:
            Path to found config file or None if not found.
        """
        search_paths = [
            Path("./config.yaml"),
            Path.home() / ".modem-inspector" / "config.yaml"
        ]

        for path in search_paths:
            if path.exists() and path.is_file():
                return path

        return None

    @staticmethod
    def _load_from_file(path: Path) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Args:
            path: Path to config.yaml file.

        Returns:
            Configuration dictionary.

        Raises:
            FileNotFoundError: If file doesn't exist.
            yaml.YAMLError: If YAML parsing fails.
        """
        with open(path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)

        if config_dict is None:
            config_dict = {}

        return config_dict

    @staticmethod
    def _apply_env_overrides() -> Dict[str, Any]:
        """Apply environment variable overrides.

        Environment variables use format: MODEM_INSPECTOR_SECTION_KEY
        Examples:
            MODEM_INSPECTOR_SERIAL_BAUD=9600
            MODEM_INSPECTOR_PLUGINS_AUTO_DISCOVER=true
            MODEM_INSPECTOR_REPOSITORY_ENABLED=1

        Supports:
            - Nested sections (SECTION_KEY)
            - Boolean values: "true", "false", "1", "0", "yes", "no" (case-insensitive)
            - Integer values: numeric strings
            - List values: comma-delimited "value1,value2,value3"

        Returns:
            Dictionary with environment overrides.
        """
        overrides = {}
        prefix = "MODEM_INSPECTOR_"

        for env_name, env_value in os.environ.items():
            if not env_name.startswith(prefix):
                continue

            # Parse: MODEM_INSPECTOR_SERIAL_BAUD -> ["serial", "baud"]
            parts = env_name[len(prefix):].lower().split('_', 1)
            if len(parts) != 2:
                continue

            section, key = parts

            # Initialize section if needed
            if section not in overrides:
                overrides[section] = {}

            # Convert value to appropriate type
            overrides[section][key] = ConfigManager._parse_env_value(env_value)

        return overrides

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Parse environment variable value to appropriate Python type.

        Args:
            value: String value from environment variable.

        Returns:
            Parsed value (bool, int, list, or str).
        """
        # Boolean values
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        if value.lower() in ('false', '0', 'no', 'off'):
            return False

        # Integer values
        try:
            return int(value)
        except ValueError:
            pass

        # List values (comma-delimited)
        if ',' in value:
            return [v.strip() for v in value.split(',')]

        # String value
        return value

    @staticmethod
    def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary.
            override: Override configuration dictionary.

        Returns:
            Merged configuration (override takes precedence).
        """
        merged = deepcopy(base)

        for section, section_values in override.items():
            if section not in merged:
                merged[section] = {}

            if isinstance(section_values, dict):
                for key, value in section_values.items():
                    merged[section][key] = value
            else:
                merged[section] = section_values

        return merged

    def _mark_source(self, config: Dict[str, Any], source: str):
        """Mark source of configuration values.

        Args:
            config: Configuration dictionary.
            source: Source label ("default", "file", "env").
        """
        for section, section_values in config.items():
            if isinstance(section_values, dict):
                for key in section_values.keys():
                    self._config_source[f"{section}.{key}"] = source

    @staticmethod
    def _dict_to_config(config_dict: Dict[str, Any]) -> Config:
        """Convert configuration dictionary to Config object.

        Args:
            config_dict: Configuration dictionary.

        Returns:
            Config object with all sections.
        """
        # Helper to convert enum strings to enum values
        def get_enum(enum_class, value, default):
            if isinstance(value, str):
                try:
                    # Try lowercase first (for most enums)
                    return enum_class(value.lower())
                except (ValueError, KeyError):
                    try:
                        # Try uppercase for LogLevel
                        return enum_class(value.upper())
                    except (ValueError, KeyError):
                        return default
            return value if value else default

        # Serial section
        serial_dict = config_dict.get('serial', {})
        serial = SerialConfig(
            default_baud=serial_dict.get('default_baud', 115200),
            timeout=serial_dict.get('timeout', 30),
            retry_attempts=serial_dict.get('retry_attempts', 3),
            retry_delay=serial_dict.get('retry_delay', 1000)
        )

        # Plugins section
        plugins_dict = config_dict.get('plugins', {})
        plugins = PluginsConfig(
            directories=plugins_dict.get('directories', ["./plugins", "./custom_plugins", "~/.modem-inspector/plugins"]),
            auto_discover=plugins_dict.get('auto_discover', True),
            validation_level=get_enum(ValidationLevel, plugins_dict.get('validation_level'), ValidationLevel.WARNING)
        )

        # Repository section
        repo_dict = config_dict.get('repository', {})
        repository = RepositoryConfig(
            enabled=repo_dict.get('enabled', False),
            api_url=repo_dict.get('api_url'),
            api_token=repo_dict.get('api_token'),
            sync_mode=get_enum(SyncMode, repo_dict.get('sync_mode'), SyncMode.MANUAL)
        )

        # Reporting section
        report_dict = config_dict.get('reporting', {})
        reporting = ReportingConfig(
            default_format=get_enum(ReportFormat, report_dict.get('default_format'), ReportFormat.CSV),
            output_directory=report_dict.get('output_directory', './reports'),
            timestamp_format=report_dict.get('timestamp_format', '%Y%m%d_%H%M%S')
        )

        # Logging section
        log_dict = config_dict.get('logging', {})
        logging = LoggingConfig(
            enabled=log_dict.get('enabled', False),
            level=get_enum(LogLevel, log_dict.get('level'), LogLevel.INFO),
            log_to_file=log_dict.get('log_to_file', False),
            log_to_console=log_dict.get('log_to_console', True),
            log_file_path=log_dict.get('log_file_path'),
            max_file_size_mb=log_dict.get('max_file_size_mb', 10),
            backup_count=log_dict.get('backup_count', 5)
        )

        # Parallel section
        parallel_dict = config_dict.get('parallel', {})
        parallel = ParallelConfig(
            enabled=parallel_dict.get('enabled', False),
            max_workers=parallel_dict.get('max_workers', 5),
            worker_timeout=parallel_dict.get('worker_timeout', 600)
        )

        # Encryption section
        encryption_dict = config_dict.get('encryption', {})
        encryption = EncryptionConfig(
            enabled=encryption_dict.get('enabled', False),
            key_path=encryption_dict.get('key_path')
        )

        return Config(
            serial=serial,
            plugins=plugins,
            repository=repository,
            reporting=reporting,
            logging=logging,
            parallel=parallel,
            encryption=encryption
        )

    def get_config(self) -> Config:
        """Get current configuration object.

        Returns:
            Config: Current configuration.

        Raises:
            RuntimeError: If configuration not loaded.
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call initialize() first.")
        return self._config

    def reload(self, config_path: Optional[Path] = None) -> bool:
        """Reload configuration from file and environment.

        Args:
            config_path: Optional path to config.yaml. If None, uses current config path or searches.

        Returns:
            True if reload successful, False if reload failed (config rolled back).

        Note:
            If new configuration is invalid, previous valid configuration is preserved.
            Calls registered reload callbacks on successful reload.
            Calls registered error callbacks on failed reload.
        """
        # Use current config path if not specified
        if config_path is None:
            config_path = self._config_path

        # Save current config for rollback
        old_config = self._config
        old_source = self._config_source.copy()
        old_config_path = self._config_path

        # Temporarily disable hot reload to avoid recursion
        was_watching = self._watch_enabled
        if was_watching:
            self.disable_hot_reload()

        try:
            # Re-initialize with new config (disable hot reload to avoid double-start)
            ConfigManager.initialize(config_path, skip_validation=False, enable_hot_reload=False)

            # Re-enable hot reload if it was enabled before
            if was_watching and self._config_path:
                self.enable_hot_reload()

            # Call reload callbacks
            self._call_reload_callbacks()

            return True
        except Exception as e:
            # Rollback to previous valid config
            error_msg = str(e)
            print(f"Error reloading configuration: {error_msg}")
            print("Rolling back to previous configuration")
            self._config = old_config
            self._config_source = old_source
            self._config_path = old_config_path

            # Re-enable hot reload if it was enabled before
            if was_watching and self._config_path:
                self.enable_hot_reload()

            # Call error callbacks
            self._call_reload_error_callbacks(error_msg)

            return False

    def validate(self) -> List[str]:
        """Validate current configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        if self._config is None:
            return ["Configuration not loaded"]

        config_dict = self._config.to_dict()
        is_valid, errors = ConfigSchema.validate_config(config_dict, strict=False)
        return errors

    def show_config(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """Show current configuration with source metadata.

        Args:
            mask_sensitive: Whether to mask sensitive fields (default: True).

        Returns:
            Dictionary with configuration and source metadata for each field.

        Example:
            {
                "serial": {
                    "default_baud": {"value": 115200, "source": "default"},
                    "timeout": {"value": 30, "source": "file"}
                },
                "repository": {
                    "api_token": {"value": "****abc123", "source": "env"}
                }
            }
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call initialize() first.")

        # Get config dict (with or without masking)
        config = self._config.mask_sensitive() if mask_sensitive else self._config
        config_dict = config.to_dict()

        # Add source metadata
        result = {}
        for section, section_values in config_dict.items():
            result[section] = {}
            if isinstance(section_values, dict):
                for key, value in section_values.items():
                    source_key = f"{section}.{key}"
                    source = self._config_source.get(source_key, "unknown")
                    result[section][key] = {
                        "value": value,
                        "source": source
                    }
            else:
                result[section] = {
                    "value": section_values,
                    "source": self._config_source.get(section, "unknown")
                }

        return result

    def enable_hot_reload(self) -> bool:
        """Enable automatic configuration reload on file changes.

        Returns:
            True if hot reload enabled successfully, False otherwise.

        Note:
            Requires a config file path to be set (from initialization).
            Uses watchdog library to monitor config.yaml for changes.
            Detects changes within 2 seconds (with debouncing).
        """
        if not self._config_path:
            print("Warning: Cannot enable hot reload - no config file loaded")
            return False

        if self._watch_enabled:
            return True  # Already enabled

        try:
            # Create event handler
            event_handler = ConfigFileEventHandler(self, self._config_path)

            # Create observer and watch config directory
            self._file_observer = Observer()
            watch_dir = self._config_path.parent
            self._file_observer.schedule(event_handler, str(watch_dir), recursive=False)
            self._file_observer.start()

            self._watch_enabled = True
            return True
        except Exception as e:
            print(f"Error enabling hot reload: {e}")
            return False

    def disable_hot_reload(self):
        """Disable automatic configuration reload on file changes."""
        if not self._watch_enabled:
            return

        if self._file_observer:
            self._file_observer.stop()
            self._file_observer.join(timeout=2.0)
            self._file_observer = None

        self._watch_enabled = False

    def is_hot_reload_enabled(self) -> bool:
        """Check if hot reload is currently enabled.

        Returns:
            True if hot reload is enabled, False otherwise.
        """
        return self._watch_enabled

    def register_reload_callback(self, callback: Callable[[], None]):
        """Register callback to be called after successful configuration reload.

        Args:
            callback: Function to call after reload. Should take no arguments.

        Example:
            def on_config_reload():
                print("Configuration reloaded!")
                # Update application state...

            ConfigManager.instance().register_reload_callback(on_config_reload)
        """
        if callback not in self._reload_callbacks:
            self._reload_callbacks.append(callback)

    def unregister_reload_callback(self, callback: Callable[[], None]):
        """Unregister a reload callback.

        Args:
            callback: Function to unregister.
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)

    def register_reload_error_callback(self, callback: Callable[[str], None]):
        """Register callback to be called when configuration reload fails.

        Args:
            callback: Function to call on reload error. Receives error message string.

        Example:
            def on_config_reload_error(error_msg):
                print(f"Configuration reload failed: {error_msg}")
                # Show error notification...

            ConfigManager.instance().register_reload_error_callback(on_config_reload_error)
        """
        if callback not in self._reload_error_callbacks:
            self._reload_error_callbacks.append(callback)

    def unregister_reload_error_callback(self, callback: Callable[[str], None]):
        """Unregister a reload error callback.

        Args:
            callback: Function to unregister.
        """
        if callback in self._reload_error_callbacks:
            self._reload_error_callbacks.remove(callback)

    def _call_reload_callbacks(self):
        """Call all registered reload callbacks."""
        for callback in self._reload_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in reload callback: {e}")

    def _call_reload_error_callbacks(self, error_msg: str):
        """Call all registered reload error callbacks.

        Args:
            error_msg: Error message describing the reload failure.
        """
        for callback in self._reload_error_callbacks:
            try:
                callback(error_msg)
            except Exception as e:
                print(f"Error in reload error callback: {e}")

    def _register_sighup_handler(self):
        """Register SIGHUP signal handler for manual reload (Unix only).

        On Unix systems, sending SIGHUP to the process will trigger a config reload.
        Example: kill -HUP <pid>
        """
        # Only available on Unix systems
        if not hasattr(signal, 'SIGHUP'):
            return

        def sighup_handler(signum, frame):
            """Handle SIGHUP signal."""
            print("Received SIGHUP signal - reloading configuration")
            success = self.reload()
            if success:
                print("Configuration reloaded successfully via SIGHUP")
            else:
                print("Configuration reload failed via SIGHUP")

        try:
            signal.signal(signal.SIGHUP, sighup_handler)
        except Exception as e:
            print(f"Warning: Could not register SIGHUP handler: {e}")

    @classmethod
    def reset(cls):
        """Reset singleton instance (for testing)."""
        # Stop file watcher if running
        if cls._instance and cls._instance._watch_enabled:
            cls._instance.disable_hot_reload()

        cls._instance = None
        cls._config = None
        cls._config_path = None
        cls._file_observer = None
        cls._watch_enabled = False
        cls._reload_callbacks = []
        cls._reload_error_callbacks = []
        if hasattr(cls, '_config_source'):
            cls._config_source = {}
