"""History manager for persisting recent inspections.

Provides JSON-based persistence for recent inspection history with automatic
file management and error handling.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class HistoryManager:
    """Manages persistent history of recent inspections.

    Stores up to 10 most recent inspection sessions in JSON format in user's
    home directory. Handles file I/O errors gracefully.

    Example:
        >>> manager = HistoryManager()
        >>> manager.save_inspection(
        ...     plugin_vendor="quectel",
        ...     plugin_model="ec200u",
        ...     port="COM3",
        ...     command_count=15,
        ...     success_count=14,
        ...     duration=45.2
        ... )
        >>> history = manager.load_history()
        >>> print(len(history))  # At most 10 entries
    """

    MAX_HISTORY_ENTRIES = 10
    HISTORY_DIR = Path.home() / ".modem-inspector"
    HISTORY_FILE = HISTORY_DIR / "history.json"

    def __init__(self):
        """Initialize history manager.

        Creates history directory if it doesn't exist.
        """
        try:
            self.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            # If we can't create directory, operations will fail gracefully
            pass

    def save_inspection(
        self,
        plugin_vendor: str,
        plugin_model: str,
        port: str,
        command_count: int,
        success_count: int,
        duration: float
    ) -> bool:
        """Save inspection to history.

        Args:
            plugin_vendor: Plugin vendor name
            plugin_model: Plugin model name
            port: Serial port used
            command_count: Total commands executed
            success_count: Number of successful commands
            duration: Execution duration in seconds

        Returns:
            True if saved successfully, False on error

        Example:
            >>> manager.save_inspection(
            ...     plugin_vendor="quectel",
            ...     plugin_model="ec200u",
            ...     port="COM3",
            ...     command_count=15,
            ...     success_count=14,
            ...     duration=45.2
            ... )
            True
        """
        try:
            # Load existing history
            history = self.load_history()

            # Create new entry
            entry = {
                "timestamp": datetime.now().isoformat(),
                "plugin": {
                    "vendor": plugin_vendor,
                    "model": plugin_model
                },
                "port": port,
                "command_count": command_count,
                "success_count": success_count,
                "duration": duration
            }

            # Add to beginning (most recent first)
            history.insert(0, entry)

            # Limit to MAX_HISTORY_ENTRIES
            if len(history) > self.MAX_HISTORY_ENTRIES:
                history = history[:self.MAX_HISTORY_ENTRIES]

            # Save to file
            with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            return True

        except (PermissionError, OSError, IOError) as e:
            # File I/O error - fail gracefully
            return False

        except Exception as e:
            # Unexpected error - fail gracefully
            return False

    def load_history(self) -> List[Dict]:
        """Load inspection history from file.

        Returns:
            List of history entries (most recent first), empty list on error

        Example:
            >>> manager = HistoryManager()
            >>> history = manager.load_history()
            >>> for entry in history:
            ...     print(entry["timestamp"], entry["plugin"]["vendor"])
        """
        try:
            # Check if file exists
            if not self.HISTORY_FILE.exists():
                return []

            # Read and parse JSON
            with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)

            # Validate structure
            if not isinstance(history, list):
                return []

            return history

        except (FileNotFoundError, PermissionError, OSError, IOError):
            # File doesn't exist or can't be read
            return []

        except json.JSONDecodeError:
            # Corrupted JSON - return empty list
            return []

        except Exception:
            # Unexpected error - fail gracefully
            return []

    def get_recent_ports(self, limit: int = 5) -> List[str]:
        """Get list of recently used ports.

        Args:
            limit: Maximum number of ports to return

        Returns:
            List of unique port names (most recent first)

        Example:
            >>> manager = HistoryManager()
            >>> ports = manager.get_recent_ports(limit=3)
            >>> print(ports)  # ['COM3', '/dev/ttyUSB0', 'COM4']
        """
        history = self.load_history()
        ports = []
        seen = set()

        for entry in history:
            port = entry.get("port")
            if port and port not in seen:
                ports.append(port)
                seen.add(port)

            if len(ports) >= limit:
                break

        return ports

    def get_recent_plugins(self, limit: int = 5) -> List[Dict[str, str]]:
        """Get list of recently used plugins.

        Args:
            limit: Maximum number of plugins to return

        Returns:
            List of plugin dicts with 'vendor' and 'model' keys

        Example:
            >>> manager = HistoryManager()
            >>> plugins = manager.get_recent_plugins(limit=3)
            >>> for plugin in plugins:
            ...     print(f"{plugin['vendor']} {plugin['model']}")
        """
        history = self.load_history()
        plugins = []
        seen = set()

        for entry in history:
            plugin = entry.get("plugin")
            if plugin:
                key = (plugin.get("vendor"), plugin.get("model"))
                if key not in seen and all(key):
                    plugins.append(plugin)
                    seen.add(key)

                if len(plugins) >= limit:
                    break

        return plugins

    def clear_history(self) -> bool:
        """Clear all history.

        Returns:
            True if cleared successfully, False on error
        """
        try:
            if self.HISTORY_FILE.exists():
                self.HISTORY_FILE.unlink()
            return True
        except (PermissionError, OSError):
            return False

    def get_statistics(self) -> Dict:
        """Get statistics from history.

        Returns:
            Dict with total_inspections, total_commands, avg_success_rate

        Example:
            >>> manager = HistoryManager()
            >>> stats = manager.get_statistics()
            >>> print(f"Success rate: {stats['avg_success_rate']:.1f}%")
        """
        history = self.load_history()

        if not history:
            return {
                "total_inspections": 0,
                "total_commands": 0,
                "avg_success_rate": 0.0
            }

        total_commands = sum(entry.get("command_count", 0) for entry in history)
        total_success = sum(entry.get("success_count", 0) for entry in history)

        avg_success_rate = (total_success / total_commands * 100) if total_commands > 0 else 0.0

        return {
            "total_inspections": len(history),
            "total_commands": total_commands,
            "avg_success_rate": avg_success_rate
        }
