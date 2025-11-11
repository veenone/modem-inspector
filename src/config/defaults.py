"""Default configuration values for zero-config operation.

This module provides sensible defaults for all configuration sections,
allowing the application to run without a config.yaml file.
"""

from src.config.config_models import (
    Config,
    SerialConfig,
    PluginsConfig,
    RepositoryConfig,
    ReportingConfig,
    LoggingConfig,
    ParallelConfig,
    ValidationLevel,
    SyncMode,
    ReportFormat,
    LogLevel
)


def get_default_config() -> Config:
    """Get default configuration with sensible values for zero-config operation.

    Returns:
        Config: Complete configuration with all defaults populated.

    Default Values:
        - Serial: 115200 baud (most common), 30s timeout, 3 retry attempts
        - Plugins: Auto-discover from ./plugins, ./custom_plugins, ~/.modem-inspector/plugins
        - Repository: Disabled by default (offline-first approach)
        - Reporting: CSV format, ./reports directory
        - Logging: INFO level, console output enabled
        - Parallel: Disabled by default (single modem testing)
    """
    return Config(
        serial=SerialConfig(
            default_baud=115200,  # Most common baud rate for modern modems
            timeout=30,  # 30 seconds provides good balance
            retry_attempts=3,  # Standard retry count
            retry_delay=1000  # 1 second between retries
        ),
        plugins=PluginsConfig(
            directories=[
                "./plugins",  # Project local plugins
                "./custom_plugins",  # Custom user plugins
                "~/.modem-inspector/plugins"  # User home directory plugins
            ],
            auto_discover=True,  # Automatically find and load plugins
            validation_level=ValidationLevel.WARNING  # Warn but don't fail
        ),
        repository=RepositoryConfig(
            enabled=False,  # Offline-first: local operation by default
            api_url=None,  # No default API URL
            api_token=None,  # No default token
            sync_mode=SyncMode.MANUAL  # Explicit sync when enabled
        ),
        reporting=ReportingConfig(
            default_format=ReportFormat.CSV,  # CSV most compatible
            output_directory="./reports",  # Local reports directory
            timestamp_format="%Y%m%d_%H%M%S"  # YYYYMMDD_HHMMSS format
        ),
        logging=LoggingConfig(
            level=LogLevel.INFO,  # INFO level for normal operation
            file_path=None,  # No log file by default (console only)
            console_output=True  # Output to console
        ),
        parallel=ParallelConfig(
            enabled=False,  # Single modem testing by default
            max_workers=5,  # Reasonable default for parallel mode
            worker_timeout=600  # 10 minutes per modem
        )
    )
