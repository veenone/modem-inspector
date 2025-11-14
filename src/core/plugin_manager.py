"""Plugin manager for discovering and loading modem plugins.

This module provides plugin lifecycle management including discovery,
loading, caching, and selection capabilities.
"""

from pathlib import Path
from typing import List, Dict, Optional
import yaml

from src.core.plugin import (
    Plugin,
    PluginMetadata,
    PluginConnection,
    CommandDefinition,
    ParserDefinition,
    PluginValidation,
    ParserType
)
from src.core.exceptions import PluginError, PluginValidationError, PluginNotFoundError


class PluginManager:
    """Manages plugin discovery, loading, caching, and selection.

    Provides centralized plugin management with support for multiple
    plugin directories and automatic caching.

    Example:
        >>> manager = PluginManager(['./src/plugins'])
        >>> manager.discover_plugins()
        >>> plugin = manager.get_plugin('quectel', 'ec200u')
        >>> print(f"Loaded plugin: {plugin}")
    """

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """Initialize plugin manager with search directories.

        Args:
            plugin_dirs: List of directories to search for plugins.
                        Defaults to ['./src/plugins'] if not provided.
        """
        if plugin_dirs is None:
            plugin_dirs = ['./src/plugins']

        self.plugin_dirs = [Path(d) for d in plugin_dirs]
        self._cache: Dict[str, Plugin] = {}  # key: "vendor.model"
        self._loaded = False

    def discover_plugins(self) -> List[Plugin]:
        """Discover and load all plugins from configured directories.

        Recursively scans plugin directories for .yaml files and
        loads valid plugins into cache.

        Returns:
            List of successfully loaded Plugin objects

        Example:
            >>> manager = PluginManager()
            >>> plugins = manager.discover_plugins()
            >>> print(f"Found {len(plugins)} plugins")
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            # Recursively find all .yaml files
            for yaml_file in plugin_dir.rglob('*.yaml'):
                try:
                    plugin = self.load_plugin(yaml_file)
                    plugin_key = f"{plugin.metadata.vendor}.{plugin.metadata.model}"
                    self._cache[plugin_key] = plugin
                    discovered.append(plugin)
                except Exception as e:
                    # Log error but continue with other plugins
                    print(f"Warning: Failed to load plugin {yaml_file}: {e}")
                    continue

        self._loaded = True
        return discovered

    def load_plugin(self, file_path: Path) -> Plugin:
        """Load and validate plugin from YAML file.

        Args:
            file_path: Path to plugin YAML file

        Returns:
            Loaded and validated Plugin object

        Raises:
            PluginValidationError: Plugin file is invalid
            PluginError: Error loading plugin file

        Example:
            >>> manager = PluginManager()
            >>> plugin = manager.load_plugin(Path('./src/plugins/quectel/lte_cat1/ec200u.yaml'))
            >>> print(plugin.metadata.vendor)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                raise PluginValidationError(
                    "Empty plugin file",
                    str(file_path),
                    ["File contains no data"]
                )

            # Parse metadata
            metadata_data = data.get('metadata', {})
            metadata = PluginMetadata(
                vendor=metadata_data.get('vendor', ''),
                model=metadata_data.get('model', ''),
                category=metadata_data.get('category', 'other'),
                version=metadata_data.get('version', '1.0.0'),
                author=metadata_data.get('author'),
                compatible_with=metadata_data.get('compatible_with'),
                variants=metadata_data.get('variants')
            )

            # Parse connection
            conn_data = data.get('connection', {})
            connection = PluginConnection(
                default_baud=conn_data.get('default_baud', 115200),
                data_bits=conn_data.get('data_bits', 8),
                parity=conn_data.get('parity', 'N'),
                stop_bits=conn_data.get('stop_bits', 1),
                flow_control=conn_data.get('flow_control', False),
                init_sequence=conn_data.get('init_sequence')
            )

            # Parse commands
            commands_data = data.get('commands', {})
            commands = {}
            for category, cmd_list in commands_data.items():
                commands[category] = [
                    CommandDefinition(
                        cmd=cmd.get('cmd', ''),
                        description=cmd.get('description', ''),
                        category=cmd.get('category', category),
                        timeout=cmd.get('timeout'),
                        parser=cmd.get('parser'),
                        critical=cmd.get('critical', False),
                        quick=cmd.get('quick', False),
                        expected_format=cmd.get('expected_format')
                    )
                    for cmd in cmd_list
                ]

            # Parse parsers
            parsers_data = data.get('parsers', {})
            parsers = {}
            for name, parser_def in parsers_data.items():
                parser_type_str = parser_def.get('type', 'none')
                parser_type = ParserType(parser_type_str)

                parsers[name] = ParserDefinition(
                    name=name,
                    type=parser_type,
                    pattern=parser_def.get('pattern'),
                    groups=parser_def.get('groups'),
                    json_path=parser_def.get('json_path'),
                    module=parser_def.get('module'),
                    function=parser_def.get('function'),
                    unit=parser_def.get('unit'),
                    output_format=parser_def.get('output_format')
                )

            # Parse validation (optional)
            validation = None
            if 'validation' in data:
                val_data = data['validation']
                validation = PluginValidation(
                    required_responses=val_data.get('required_responses'),
                    expected_manufacturer=val_data.get('expected_manufacturer'),
                    expected_model_pattern=val_data.get('expected_model_pattern')
                )

            # Create plugin
            plugin = Plugin(
                metadata=metadata,
                connection=connection,
                commands=commands,
                parsers=parsers,
                validation=validation,
                file_path=str(file_path)
            )

            return plugin

        except yaml.YAMLError as e:
            raise PluginValidationError(
                f"Invalid YAML syntax: {e}",
                str(file_path),
                [str(e)]
            )
        except Exception as e:
            raise PluginError(f"Failed to load plugin: {e}")

    def get_plugin(self, vendor: str, model: str) -> Optional[Plugin]:
        """Retrieve cached plugin by vendor and model.

        Case-insensitive matching for vendor and model.

        Args:
            vendor: Vendor name (e.g., "quectel")
            model: Model name (e.g., "ec200u")

        Returns:
            Plugin object if found, None otherwise

        Example:
            >>> manager = PluginManager()
            >>> manager.discover_plugins()
            >>> plugin = manager.get_plugin('quectel', 'ec200u')
            >>> if plugin:
            ...     print(f"Found: {plugin}")
        """
        if not self._loaded:
            self.discover_plugins()

        # Case-insensitive lookup
        vendor_lower = vendor.lower()
        model_lower = model.lower()

        for key, plugin in self._cache.items():
            if (plugin.metadata.vendor.lower() == vendor_lower and
                plugin.metadata.model.lower() == model_lower):
                return plugin

        return None

    def get_all_plugins(self) -> List[Plugin]:
        """Get all discovered plugins.

        Returns:
            List of all Plugin objects in cache

        Example:
            >>> manager = PluginManager()
            >>> manager.discover_plugins()
            >>> all_plugins = manager.get_all_plugins()
            >>> print(f"Total plugins: {len(all_plugins)}")
        """
        if not self._loaded:
            self.discover_plugins()
        return list(self._cache.values())

    def list_plugins(self,
                    vendor: Optional[str] = None,
                    category: Optional[str] = None) -> List[Plugin]:
        """List available plugins with optional filtering.

        Args:
            vendor: Filter by vendor (optional)
            category: Filter by category (optional)

        Returns:
            List of Plugin objects matching filters

        Example:
            >>> manager = PluginManager()
            >>> manager.discover_plugins()
            >>> quectel_plugins = manager.list_plugins(vendor='quectel')
            >>> for plugin in quectel_plugins:
            ...     print(f"{plugin.metadata.vendor}.{plugin.metadata.model}")
        """
        plugins = self.get_all_plugins()

        # Apply filters
        if vendor:
            vendor_lower = vendor.lower()
            plugins = [p for p in plugins
                      if p.metadata.vendor.lower() == vendor_lower]

        if category:
            category_lower = category.lower()
            plugins = [p for p in plugins
                      if p.metadata.category.lower() == category_lower]

        return plugins

    def reload_plugins(self) -> List[Plugin]:
        """Clear cache and reload all plugins.

        Returns:
            List of reloaded Plugin objects

        Example:
            >>> manager = PluginManager()
            >>> plugins = manager.reload_plugins()
            >>> print(f"Reloaded {len(plugins)} plugins")
        """
        self._cache.clear()
        self._loaded = False
        return self.discover_plugins()

    def select_plugin_auto(self,
                          manufacturer: str,
                          model: str) -> Optional[Plugin]:
        """Automatically select plugin based on modem responses.

        Matches manufacturer and model from AT+CGMI/AT+CGMM responses
        to plugin metadata. Uses fuzzy matching for compatibility.

        Args:
            manufacturer: Response from AT+CGMI
            model: Response from AT+CGMM

        Returns:
            Best matching Plugin or None

        Example:
            >>> manager = PluginManager()
            >>> manager.discover_plugins()
            >>> plugin = manager.select_plugin_auto('Quectel', 'EC200U-CN')
            >>> if plugin:
            ...     print(f"Auto-selected: {plugin}")
        """
        if not self._loaded:
            self.discover_plugins()

        manufacturer_lower = manufacturer.lower()
        model_lower = model.lower()

        # Try exact match first
        for plugin in self._cache.values():
            vendor_match = plugin.metadata.vendor.lower() in manufacturer_lower
            model_match = plugin.metadata.model.lower() in model_lower

            if vendor_match and model_match:
                return plugin

        # Try vendor match with model variants
        for plugin in self._cache.values():
            vendor_match = plugin.metadata.vendor.lower() in manufacturer_lower

            if vendor_match and plugin.metadata.variants:
                for variant in plugin.metadata.variants:
                    if variant.lower() in model_lower:
                        return plugin

        return None

    def __repr__(self) -> str:
        """String representation of manager."""
        return (f"PluginManager({len(self.plugin_dirs)} dirs, "
                f"{len(self._cache)} plugins loaded)")
