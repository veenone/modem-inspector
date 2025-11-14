"""Configuration status widget for displaying hot reload status.

Provides a compact status indicator showing configuration reload status,
config file path, and last reload timestamp.
"""

import customtkinter as ctk
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.config.config_manager import ConfigManager


class ConfigStatusWidget(ctk.CTkFrame):
    """Widget displaying configuration hot reload status.

    Shows:
    - Hot reload enabled/disabled status with colored indicator
    - Config file path
    - Last reload timestamp
    - Tooltip with additional details

    Example:
        >>> widget = ConfigStatusWidget(parent)
        >>> widget.pack(side="left", padx=5)
        >>> widget.update_status()
    """

    def __init__(self, master, **kwargs):
        """Initialize config status widget.

        Args:
            master: Parent widget
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(master, **kwargs)

        self.last_reload_time: Optional[datetime] = None
        self._setup_ui()
        self._register_reload_callback()
        self.update_status()

    def _setup_ui(self):
        """Set up UI components."""
        # Container frame with minimal padding
        self.configure(fg_color="transparent")

        # Status indicator (colored dot)
        self.status_indicator = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color="gray",
            width=20
        )
        self.status_indicator.pack(side="left", padx=(0, 5))

        # Status text label
        self.status_label = ctk.CTkLabel(
            self,
            text="Config: Checking...",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.status_label.pack(side="left")

        # Bind hover events for tooltip
        self._bind_tooltip_events()

    def _bind_tooltip_events(self):
        """Bind mouse hover events for tooltip display."""
        # Tooltip window (created on demand)
        self.tooltip: Optional[ctk.CTkToplevel] = None

        # Bind events to both indicator and label
        for widget in [self.status_indicator, self.status_label, self]:
            widget.bind("<Enter>", self._show_tooltip)
            widget.bind("<Leave>", self._hide_tooltip)

    def _show_tooltip(self, event=None):
        """Show tooltip with detailed config information."""
        if self.tooltip is not None:
            return  # Already showing

        try:
            config_manager = ConfigManager.instance()

            # Create tooltip window
            self.tooltip = ctk.CTkToplevel(self)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_attributes("-topmost", True)

            # Position tooltip near cursor
            x = self.winfo_pointerx() + 10
            y = self.winfo_pointery() + 10
            self.tooltip.wm_geometry(f"+{x}+{y}")

            # Tooltip content frame
            content_frame = ctk.CTkFrame(self.tooltip, corner_radius=6)
            content_frame.pack(fill="both", expand=True, padx=2, pady=2)

            # Build tooltip text
            info_lines = []

            # Hot reload status
            is_enabled = config_manager.is_hot_reload_enabled()
            status_text = "✓ Enabled" if is_enabled else "✗ Disabled"
            info_lines.append(f"Hot Reload: {status_text}")

            # Config file path
            if config_manager._config_path:
                config_path = config_manager._config_path
                info_lines.append(f"File: {config_path}")

                # Last modified time
                if config_path.exists():
                    mtime = datetime.fromtimestamp(config_path.stat().st_mtime)
                    info_lines.append(f"Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                info_lines.append("File: Using defaults only")

            # Last reload time
            if self.last_reload_time:
                info_lines.append(f"Last Reload: {self.last_reload_time.strftime('%H:%M:%S')}")

            # Display tooltip text
            tooltip_text = "\n".join(info_lines)
            tooltip_label = ctk.CTkLabel(
                content_frame,
                text=tooltip_text,
                font=ctk.CTkFont(size=11),
                justify="left"
            )
            tooltip_label.pack(padx=10, pady=8)

        except Exception as e:
            # If config manager not initialized or error, show minimal tooltip
            if self.tooltip:
                self.tooltip.destroy()
                self.tooltip = None

    def _hide_tooltip(self, event=None):
        """Hide tooltip."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def _register_reload_callback(self):
        """Register callback to be notified of config reloads."""
        try:
            config_manager = ConfigManager.instance()
            config_manager.register_reload_callback(self._on_config_reloaded)
            config_manager.register_reload_error_callback(self._on_config_reload_failed)
        except RuntimeError:
            # ConfigManager not initialized yet - will update when update_status() called
            pass

    def _on_config_reloaded(self):
        """Callback when configuration is reloaded."""
        self.last_reload_time = datetime.now()
        self.update_status()

        # Show toast notification
        self._show_reload_notification(success=True)

    def _show_reload_notification(self, success: bool):
        """Show toast notification for reload event.

        Args:
            success: Whether reload was successful
        """
        # Create notification window
        notification = ctk.CTkToplevel(self)
        notification.wm_overrideredirect(True)
        notification.wm_attributes("-topmost", True)

        # Position in bottom-right corner
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        notification.wm_geometry(f"300x80+{screen_width - 320}+{screen_height - 120}")

        # Notification content
        content_frame = ctk.CTkFrame(notification, corner_radius=8)
        content_frame.pack(fill="both", expand=True, padx=2, pady=2)

        if success:
            title = "✓ Configuration Reloaded"
            message = "Configuration updated successfully"
            color = "green"
        else:
            title = "✗ Configuration Reload Failed"
            message = "Configuration remains unchanged"
            color = "red"

        title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=color
        )
        title_label.pack(pady=(10, 5))

        message_label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=ctk.CTkFont(size=11)
        )
        message_label.pack(pady=(0, 10))

        # Auto-dismiss after 3 seconds
        notification.after(3000, notification.destroy)

    def update_status(self):
        """Update status display with current config manager state."""
        try:
            config_manager = ConfigManager.instance()

            # Update hot reload status
            is_enabled = config_manager.is_hot_reload_enabled()

            if is_enabled:
                self.status_indicator.configure(text_color="green")
                self.status_label.configure(
                    text="Config: Auto-reload ✓",
                    text_color="white"
                )
            else:
                self.status_indicator.configure(text_color="orange")
                self.status_label.configure(
                    text="Config: Manual",
                    text_color="gray"
                )

        except RuntimeError:
            # ConfigManager not initialized
            self.status_indicator.configure(text_color="red")
            self.status_label.configure(
                text="Config: Not loaded",
                text_color="red"
            )

    def _on_config_reload_failed(self, error_message: str):
        """Callback when configuration reload fails.

        Args:
            error_message: Error message describing failure
        """
        self.update_status()
        self._show_reload_notification(success=False)
