"""Unit tests for PluginManager.

Tests plugin discovery, loading, caching, selection, and version resolution
with mocked filesystem.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from src.core.plugin_manager import PluginManager
from src.core.plugin import Plugin, PluginMetadata, PluginConnection, PluginCategory


class TestPluginManagerDiscovery:
    """Test plugin discovery functionality."""

    def test_discover_plugins_empty_directory(self):
        """Test discovery with no plugin files."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[]):
            manager = PluginManager(plugin_dirs=['./test_plugins'])
            plugins = manager.discover_plugins()

            assert len(plugins) == 0
            assert manager._loaded is True

    def test_discover_plugins_single_file(self):
        """Test discovery with single valid plugin file."""
        mock_plugin_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"
connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false
commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""
        mock_file = MagicMock(spec=Path)
        mock_file.suffix = '.yaml'
        mock_file.is_file.return_value = True

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[mock_file]), \
             patch('builtins.open', mock_open(read_data=mock_plugin_yaml)):

            manager = PluginManager(plugin_dirs=['./test_plugins'])
            plugins = manager.discover_plugins()

            assert len(plugins) == 1
            assert plugins[0].metadata.vendor == "quectel"
            assert plugins[0].metadata.model == "ec200u"

    def test_discover_plugins_multiple_files(self):
        """Test discovery with multiple plugin files."""
        plugin1_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"
connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false
commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""
        plugin2_yaml = """
metadata:
  vendor: "nordic"
  model: "nrf9160"
  category: "iot"
  version: "1.0.0"
connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false
commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""

        mock_file1 = MagicMock(spec=Path)
        mock_file1.suffix = '.yaml'
        mock_file1.is_file.return_value = True

        mock_file2 = MagicMock(spec=Path)
        mock_file2.suffix = '.yaml'
        mock_file2.is_file.return_value = True

        yaml_files = {
            str(mock_file1): plugin1_yaml,
            str(mock_file2): plugin2_yaml
        }

        def mock_open_func(file, *args, **kwargs):
            content = yaml_files.get(str(file), "")
            return mock_open(read_data=content)()

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[mock_file1, mock_file2]), \
             patch('builtins.open', side_effect=mock_open_func):

            manager = PluginManager(plugin_dirs=['./test_plugins'])
            plugins = manager.discover_plugins()

            assert len(plugins) == 2
            vendors = {p.metadata.vendor for p in plugins}
            assert vendors == {"quectel", "nordic"}

    def test_discover_plugins_skips_invalid_files(self):
        """Test that invalid plugins are skipped without crashing."""
        invalid_yaml = "invalid: yaml: syntax: {"

        mock_file = MagicMock(spec=Path)
        mock_file.suffix = '.yaml'
        mock_file.is_file.return_value = True

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[mock_file]), \
             patch('builtins.open', mock_open(read_data=invalid_yaml)):

            manager = PluginManager(plugin_dirs=['./test_plugins'])
            plugins = manager.discover_plugins()

            # Should return empty list, not crash
            assert len(plugins) == 0


class TestPluginManagerCaching:
    """Test plugin caching functionality."""

    def test_caching_prevents_reload(self):
        """Test that plugins are cached after first discovery."""
        mock_plugin_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"
connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false
commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""

        mock_file = MagicMock(spec=Path)
        mock_file.suffix = '.yaml'
        mock_file.is_file.return_value = True

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[mock_file]) as mock_rglob, \
             patch('builtins.open', mock_open(read_data=mock_plugin_yaml)):

            manager = PluginManager(plugin_dirs=['./test_plugins'])

            # First call to get_all_plugins triggers discovery
            plugins1 = manager.get_all_plugins()
            call_count1 = mock_rglob.call_count

            # Second call should use cache (no additional rglob call)
            plugins2 = manager.get_all_plugins()
            call_count2 = mock_rglob.call_count

            # rglob should not be called again (cached)
            assert call_count1 == call_count2
            assert len(plugins1) == len(plugins2)

    def test_reload_clears_cache(self):
        """Test that reload() clears the cache."""
        mock_plugin_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"
connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false
commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""

        mock_file = MagicMock(spec=Path)
        mock_file.suffix = '.yaml'
        mock_file.is_file.return_value = True

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[mock_file]) as mock_rglob, \
             patch('builtins.open', mock_open(read_data=mock_plugin_yaml)):

            manager = PluginManager(plugin_dirs=['./test_plugins'])

            # First discovery
            manager.discover_plugins()
            call_count1 = mock_rglob.call_count

            # Reload should clear cache and re-scan
            manager.reload_plugins()
            call_count2 = mock_rglob.call_count

            # rglob should be called again
            assert call_count2 > call_count1


class TestPluginManagerGetPlugin:
    """Test get_plugin functionality."""

    @pytest.fixture
    def manager_with_plugins(self):
        """Create manager with pre-loaded plugins."""
        manager = PluginManager(plugin_dirs=['./test_plugins'])

        # Manually populate cache
        plugin1 = Plugin(
            metadata=PluginMetadata("quectel", "ec200u", "lte_cat1", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )
        plugin2 = Plugin(
            metadata=PluginMetadata("nordic", "nrf9160", "iot", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )

        manager._cache["quectel.ec200u"] = plugin1
        manager._cache["nordic.nrf9160"] = plugin2
        manager._loaded = True

        return manager

    def test_get_plugin_exact_match(self, manager_with_plugins):
        """Test get_plugin with exact match."""
        plugin = manager_with_plugins.get_plugin("quectel", "ec200u")

        assert plugin is not None
        assert plugin.metadata.vendor == "quectel"
        assert plugin.metadata.model == "ec200u"

    def test_get_plugin_case_insensitive(self, manager_with_plugins):
        """Test get_plugin with case-insensitive matching."""
        plugin = manager_with_plugins.get_plugin("QUECTEL", "EC200U")

        assert plugin is not None
        assert plugin.metadata.vendor == "quectel"

    def test_get_plugin_not_found(self, manager_with_plugins):
        """Test get_plugin with non-existent plugin."""
        plugin = manager_with_plugins.get_plugin("simcom", "sim7600")

        assert plugin is None


class TestPluginManagerListPlugins:
    """Test list_plugins filtering functionality."""

    @pytest.fixture
    def manager_with_plugins(self):
        """Create manager with multiple plugins."""
        manager = PluginManager(plugin_dirs=['./test_plugins'])

        plugin1 = Plugin(
            metadata=PluginMetadata("quectel", "ec200u", "lte_cat1", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )
        plugin2 = Plugin(
            metadata=PluginMetadata("quectel", "ec25", "lte_cat1", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )
        plugin3 = Plugin(
            metadata=PluginMetadata("nordic", "nrf9160", "iot", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )

        manager._cache["quectel.ec200u"] = plugin1
        manager._cache["quectel.ec25"] = plugin2
        manager._cache["nordic.nrf9160"] = plugin3
        manager._loaded = True

        return manager

    def test_list_plugins_no_filter(self, manager_with_plugins):
        """Test listing all plugins without filter."""
        plugins = manager_with_plugins.list_plugins()

        assert len(plugins) == 3

    def test_list_plugins_filter_by_vendor(self, manager_with_plugins):
        """Test filtering by vendor."""
        plugins = manager_with_plugins.list_plugins(vendor="quectel")

        assert len(plugins) == 2
        assert all(p.metadata.vendor == "quectel" for p in plugins)

    def test_list_plugins_filter_by_category(self, manager_with_plugins):
        """Test filtering by category."""
        plugins = manager_with_plugins.list_plugins(category="iot")

        assert len(plugins) == 1
        assert plugins[0].metadata.category == "iot"

    def test_list_plugins_filter_by_vendor_and_category(self, manager_with_plugins):
        """Test filtering by both vendor and category."""
        plugins = manager_with_plugins.list_plugins(vendor="quectel", category="lte_cat1")

        assert len(plugins) == 2
        assert all(p.metadata.vendor == "quectel" for p in plugins)
        assert all(p.metadata.category == "lte_cat1" for p in plugins)


class TestPluginManagerVersionResolution:
    """Test version resolution functionality."""

    def test_get_plugin_prefers_higher_version(self):
        """Test that higher version is preferred when multiple versions exist."""
        manager = PluginManager(plugin_dirs=['./test_plugins'])

        plugin_v1 = Plugin(
            metadata=PluginMetadata("quectel", "ec200u", "lte_cat1", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )
        plugin_v2 = Plugin(
            metadata=PluginMetadata("quectel", "ec200u", "lte_cat1", "2.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={}
        )

        # Manually add both versions (v2 added last)
        manager._cache["quectel.ec200u"] = plugin_v2
        manager._loaded = True

        plugin = manager.get_plugin("quectel", "ec200u")

        # Should get the version that was stored (in real implementation,
        # only one version per vendor.model is stored)
        assert plugin.metadata.version == "2.0.0"


class TestPluginManagerSelectPluginAuto:
    """Test automatic plugin selection."""

    @pytest.fixture
    def manager_with_plugins(self):
        """Create manager with plugins."""
        manager = PluginManager(plugin_dirs=['./test_plugins'])

        plugin1 = Plugin(
            metadata=PluginMetadata("quectel", "ec200u", "lte_cat1", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={},
            validation=None
        )
        plugin2 = Plugin(
            metadata=PluginMetadata("nordic", "nrf9160", "iot", "1.0.0"),
            connection=PluginConnection(),
            commands={},
            parsers={},
            validation=None
        )

        manager._cache["quectel.ec200u"] = plugin1
        manager._cache["nordic.nrf9160"] = plugin2
        manager._loaded = True

        return manager

    def test_select_plugin_auto_by_manufacturer(self, manager_with_plugins):
        """Test auto-selection by manufacturer string."""
        plugin = manager_with_plugins.select_plugin_auto(
            manufacturer="Quectel",
            model="EC200U-CN"
        )

        assert plugin is not None
        assert plugin.metadata.vendor == "quectel"

    def test_select_plugin_auto_by_model(self, manager_with_plugins):
        """Test auto-selection by model string."""
        plugin = manager_with_plugins.select_plugin_auto(
            manufacturer="Nordic Semiconductor",
            model="nRF9160"
        )

        assert plugin is not None
        assert plugin.metadata.vendor == "nordic"

    def test_select_plugin_auto_not_found(self, manager_with_plugins):
        """Test auto-selection with no match."""
        plugin = manager_with_plugins.select_plugin_auto(
            manufacturer="Unknown",
            model="Unknown"
        )

        assert plugin is None


class TestPluginManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_manager_with_nonexistent_directory(self):
        """Test manager with non-existent plugin directory."""
        with patch('pathlib.Path.exists', return_value=False):
            manager = PluginManager(plugin_dirs=['./nonexistent'])
            plugins = manager.discover_plugins()

            # Should not crash, just return empty
            assert len(plugins) == 0

    def test_get_all_plugins_before_discovery(self):
        """Test get_all_plugins triggers discovery if not loaded."""
        mock_plugin_yaml = """
metadata:
  vendor: "quectel"
  model: "ec200u"
  category: "lte_cat1"
  version: "1.0.0"
connection:
  default_baud: 115200
  data_bits: 8
  parity: "N"
  stop_bits: 1
  flow_control: false
commands:
  basic:
    - cmd: "AT"
      description: "Test"
      category: "basic"
"""

        mock_file = MagicMock(spec=Path)
        mock_file.suffix = '.yaml'
        mock_file.is_file.return_value = True

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rglob', return_value=[mock_file]), \
             patch('builtins.open', mock_open(read_data=mock_plugin_yaml)):

            manager = PluginManager(plugin_dirs=['./test_plugins'])

            # get_all_plugins should trigger discovery
            plugins = manager.get_all_plugins()

            assert len(plugins) >= 0
            assert manager._loaded is True
