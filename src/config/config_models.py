"""Configuration data models for Modem Inspector.

This module defines immutable configuration dataclasses with sensible defaults
for zero-config operation. All dataclasses are frozen for immutability.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class ValidationLevel(Enum):
    """Plugin validation strictness level."""
    STRICT = "strict"
    WARNING = "warning"
    OFF = "off"


class SyncMode(Enum):
    """Repository synchronization mode."""
    AUTO = "auto"
    MANUAL = "manual"
    OFF = "off"


class ReportFormat(Enum):
    """Report output format."""
    CSV = "csv"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"


class LogLevel(Enum):
    """Logging level."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class SerialConfig:
    """Serial port configuration."""
    default_baud: int = 115200
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1000  # milliseconds


@dataclass(frozen=True)
class PluginsConfig:
    """Plugin system configuration."""
    directories: List[str] = field(default_factory=lambda: [
        "./plugins",
        "./custom_plugins",
        "~/.modem-inspector/plugins"
    ])
    auto_discover: bool = True
    validation_level: ValidationLevel = ValidationLevel.WARNING


@dataclass(frozen=True)
class RepositoryConfig:
    """Central repository configuration."""
    enabled: bool = False
    api_url: Optional[str] = None
    api_token: Optional[str] = None
    sync_mode: SyncMode = SyncMode.MANUAL


@dataclass(frozen=True)
class ReportingConfig:
    """Report generation configuration."""
    default_format: ReportFormat = ReportFormat.CSV
    output_directory: str = "./reports"
    timestamp_format: str = "%Y%m%d_%H%M%S"


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""
    level: LogLevel = LogLevel.INFO
    file_path: Optional[str] = None
    console_output: bool = True


@dataclass(frozen=True)
class ParallelConfig:
    """Parallel testing configuration."""
    enabled: bool = False
    max_workers: int = 5
    worker_timeout: int = 600  # seconds


@dataclass(frozen=True)
class Config:
    """Complete configuration object with all sections."""
    serial: SerialConfig = field(default_factory=SerialConfig)
    plugins: PluginsConfig = field(default_factory=PluginsConfig)
    repository: RepositoryConfig = field(default_factory=RepositoryConfig)
    reporting: ReportingConfig = field(default_factory=ReportingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    parallel: ParallelConfig = field(default_factory=ParallelConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation with nested sections.
        """
        def convert_value(obj: Any) -> Any:
            """Recursively convert dataclass and enum values."""
            if isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, '__dataclass_fields__'):
                return {k: convert_value(v) for k, v in asdict(obj).items()}
            elif isinstance(obj, list):
                return [convert_value(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_value(v) for k, v in obj.items()}
            return obj

        return convert_value(asdict(self))

    def mask_sensitive(self) -> 'Config':
        """Return copy with sensitive fields masked.

        Masks api_token and similar sensitive fields, showing only last 4 characters.

        Returns:
            New Config instance with masked sensitive data.
        """
        def mask_value(value: Optional[str]) -> Optional[str]:
            """Mask string showing only last 4 characters."""
            if value is None or len(value) <= 4:
                return value
            return '*' * (len(value) - 4) + value[-4:]

        masked_repository = RepositoryConfig(
            enabled=self.repository.enabled,
            api_url=self.repository.api_url,
            api_token=mask_value(self.repository.api_token),
            sync_mode=self.repository.sync_mode
        )

        return Config(
            serial=self.serial,
            plugins=self.plugins,
            repository=masked_repository,
            reporting=self.reporting,
            logging=self.logging,
            parallel=self.parallel
        )
