"""Configuration manager for Modem Inspector.

Provides singleton access to application configuration with support for
defaults, file loading, and environment variable overrides.
"""

from pathlib import Path
from typing import Optional
import os

from src.config.config_models import Config
from src.config.defaults import get_default_config


class ConfigManager:
    """Singleton configuration manager.

    Provides centralized access to validated configuration with layered loading:
    1. Load defaults
    2. Load from file (if exists)
    3. Apply environment variable overrides
    4. Validate configuration
    5. Return validated Config object
    """

    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None

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
                   skip_validation: bool = False) -> 'ConfigManager':
        """Initialize ConfigManager with configuration.

        Args:
            config_path: Optional path to config.yaml. If None, uses defaults.
            skip_validation: Skip schema validation (for testing).

        Returns:
            ConfigManager: Initialized singleton instance.

        Process:
            1. Load defaults from defaults.py
            2. Load config.yaml if exists (NOT IMPLEMENTED YET - MVP uses defaults)
            3. Apply environment overrides (NOT IMPLEMENTED YET - MVP uses defaults)
            4. Validate against schema (NOT IMPLEMENTED YET - MVP skips validation)
            5. Return Config object
        """
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            ConfigManager._instance = cls._instance

        # MVP: Just use defaults for now
        # TODO: Implement file loading, env overrides, validation
        cls._instance._config = get_default_config()

        return cls._instance

    def get_config(self) -> Config:
        """Get current configuration object.

        Returns:
            Config: Current configuration.
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call initialize() first.")
        return self._config

    @classmethod
    def reset(cls):
        """Reset singleton instance (for testing)."""
        cls._instance = None
        cls._config = None
