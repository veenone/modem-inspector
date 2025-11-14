"""Main GUI application window.

Provides the main application window integrating all frames, dialogs, and
managing application lifecycle.
"""

import customtkinter as ctk
import tkinter as tk
from typing import Optional
from pathlib import Path
from datetime import datetime
from src.gui.frames.connection_frame import ConnectionFrame
from src.gui.frames.plugin_frame import PluginFrame
from src.gui.frames.execution_frame import ExecutionFrame
from src.gui.frames.results_frame import ResultsFrame
from src.gui.frames.log_viewer_frame import LogViewerFrame
from src.gui.widgets import CategoryChecklist
from src.gui.dialogs import SettingsDialog, ReportDialog, HelpDialog, ErrorDialog
from src.gui.utils.history_manager import HistoryManager
from src.core.serial_handler import SerialHandler
from src.core.at_executor import ATExecutor
from src.core.plugin_manager import PluginManager
from src.core.plugin import Plugin
from src.config.config_manager import ConfigManager
from src.logging import CommunicationLogger


class Application(ctk.CTk):
    """Main GUI application window.

    Integrates all frames and manages application state and lifecycle.

    Example:
        >>> app = Application()
        >>> app.mainloop()
    """

    def __init__(self):
        """Initialize application."""
        super().__init__()

        # Initialize core components
        ConfigManager.initialize()
        self.plugin_manager = PluginManager()
        self.history_manager = HistoryManager()

        # Discover plugins on startup
        try:
            self.plugin_manager.discover_plugins()
            print(f"Discovered {len(self.plugin_manager.get_all_plugins())} plugins")
        except Exception as e:
            print(f"Warning: Plugin discovery failed: {e}")

        # State
        self.serial_handler: Optional[SerialHandler] = None
        self.at_executor: Optional[ATExecutor] = None
        self.current_plugin: Optional[Plugin] = None
        self.logger: Optional[CommunicationLogger] = None

        # Setup window
        self.title("Modem Inspector - GUI")
        self.geometry("1200x800")

        # Configure appearance
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        # Setup UI
        self._setup_ui()
        self._setup_menu()

        # Load and display recent history
        self._load_recent_history()

        # Set window close protocol
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _setup_ui(self):
        """Set up UI layout."""
        # Configure grid - side-by-side layout at top, tabview below
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Connection + Plugin (side-by-side)
        self.grid_rowconfigure(1, weight=1)  # Tabview

        # Bottom section: Create tabview first so we can pass category checklist to plugin frame
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

        # Execution & Results tab
        self.tabview.add("Execution & Results")
        exec_results_tab = self.tabview.tab("Execution & Results")
        exec_results_tab.grid_columnconfigure(0, weight=1)
        exec_results_tab.grid_columnconfigure(1, weight=1)
        exec_results_tab.grid_rowconfigure(0, weight=1)

        # Execution Frame
        self.execution_frame = ExecutionFrame(
            exec_results_tab,
            on_execution_complete=self._on_execution_complete
        )
        self.execution_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Results Frame
        self.results_frame = ResultsFrame(
            exec_results_tab,
            on_export=self._on_export_clicked
        )
        self.results_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # Command Categories tab
        self.tabview.add("Command Categories")
        categories_tab = self.tabview.tab("Command Categories")
        categories_tab.grid_columnconfigure(0, weight=1)
        categories_tab.grid_rowconfigure(0, weight=1)

        # Create CategoryChecklist in the tab
        self.category_checklist = CategoryChecklist(
            categories_tab,
            on_change=self._on_categories_changed
        )
        self.category_checklist.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Communication Logs tab
        self.tabview.add("Communication Logs")
        logs_tab = self.tabview.tab("Communication Logs")
        logs_tab.grid_columnconfigure(0, weight=1)
        logs_tab.grid_rowconfigure(0, weight=1)

        # Log Viewer Frame
        self.log_viewer_frame = LogViewerFrame(logs_tab)
        self.log_viewer_frame.grid(row=0, column=0, sticky="nsew")

        # Connection Frame (left side)
        self.connection_frame = ConnectionFrame(
            self,
            on_connect=self._on_connected,
            on_disconnect=self._on_disconnected
        )
        self.connection_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        # Plugin Frame (right side) - pass category_checklist reference
        self.plugin_frame = PluginFrame(
            self,
            plugin_manager=self.plugin_manager,
            category_checklist=self.category_checklist,
            on_plugin_selected=self._on_plugin_selected
        )
        self.plugin_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

    def _setup_menu(self):
        """Setup menu bar."""
        # Create menu bar using tkinter.Menu (CustomTkinter doesn't have native menu support)
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self._on_exit)

        # Settings menu
        menubar.add_command(label="Settings", command=self.show_settings)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Help", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)

    def _on_exit(self):
        """Handle application exit."""
        # Cleanup resources
        if self.serial_handler:
            try:
                self.serial_handler.close()
            except Exception:
                pass

        if self.logger:
            try:
                self.logger.close()
            except Exception:
                pass

        # Close window
        self.quit()
        self.destroy()

    def _show_about(self):
        """Show about dialog."""
        from tkinter import messagebox
        messagebox.showinfo(
            "About Modem Inspector",
            "Modem Inspector - GUI\n\n"
            "Version: 1.0.0\n\n"
            "A comprehensive tool for inspecting and analyzing modem capabilities "
            "through AT command execution and plugin-based feature detection.\n\n"
            "© 2024 Modem Inspector Project"
        )

    def _load_recent_history(self):
        """Load and display recent inspection history."""
        try:
            history = self.history_manager.load_history()
            if history:
                print(f"Loaded {len(history)} recent inspections")
                # Could display in a status bar or recent inspections panel
                # For now, just log to console
        except Exception as e:
            print(f"Warning: Failed to load history: {e}")

    def _initialize_logger(self):
        """Initialize communication logger based on config settings."""
        try:
            config = ConfigManager.get_config()
            logging_config = config.logging

            # Only initialize if logging is enabled in config
            if not logging_config.enabled:
                self.logger = None
                return

            # Generate log file path if needed
            log_file_path = logging_config.log_file_path
            if logging_config.log_to_file and not log_file_path:
                log_dir = Path.home() / ".modem-inspector" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                log_file_path = str(log_dir / f"comm_{timestamp}.log")

            # Initialize logger
            self.logger = CommunicationLogger(
                log_level=logging_config.level,
                enable_file=logging_config.log_to_file,
                enable_console=logging_config.log_to_console,
                log_file_path=log_file_path,
                max_file_size_mb=logging_config.max_file_size_mb,
                backup_count=logging_config.backup_count
            )

        except Exception as e:
            # If logger initialization fails, continue without logging
            print(f"Warning: Failed to initialize logger: {e}")
            self.logger = None

    def _on_connected(self, port: str, handler: SerialHandler):
        """Handle serial port connection.

        Args:
            port: Connected port name
            handler: SerialHandler instance
        """
        # Initialize logger based on config
        self._initialize_logger()

        self.serial_handler = handler
        self.at_executor = ATExecutor(handler, logger=self.logger)

        # Set logger in SerialHandler (if logger exists)
        if self.logger:
            self.serial_handler.logger = self.logger

        # Set logger in log viewer and start logging
        if self.logger:
            self.log_viewer_frame.set_logger(self.logger)
            self.log_viewer_frame.start_logging()

        # Enable plugin auto-detection
        self.plugin_frame.set_at_executor(self.at_executor)

        # Update state
        self._update_execution_state()

    def _on_disconnected(self):
        """Handle serial port disconnection."""
        # Stop logging
        if self.logger:
            self.log_viewer_frame.stop_logging()
            self.logger.close()
            self.logger = None

        self.serial_handler = None
        self.at_executor = None

        # Disable plugin auto-detection
        self.plugin_frame.set_at_executor(None)

        # Update state
        self._update_execution_state()

    def _on_plugin_selected(self, plugin: Plugin):
        """Handle plugin selection.

        Args:
            plugin: Selected Plugin instance
        """
        self.current_plugin = plugin
        self._update_execution_state()

    def _on_categories_changed(self):
        """Handle category selection change."""
        # Update plugin frame's command count display
        self.plugin_frame._update_command_count()
        # Update execution state
        self._update_execution_state()

    def _update_execution_state(self):
        """Update execution frame state based on connection and plugin."""
        if not self.at_executor or not self.current_plugin:
            self.execution_frame.set_ready(None, None)
            return

        # Get selected categories and commands
        selected_categories = self.category_checklist.get_selected_categories()
        is_quick_only = self.category_checklist.is_quick_scan_only()

        # Filter commands from selected categories
        # plugin.commands is a dict: {category_name: [CommandDefinition, ...]}
        commands = []
        for category in selected_categories:
            if category in self.current_plugin.commands:
                for cmd in self.current_plugin.commands[category]:
                    if is_quick_only and not cmd.quick:
                        continue
                    commands.append(cmd)

        self.execution_frame.set_ready(self.at_executor, commands)

    def _on_execution_complete(self, results):
        """Handle execution completion.

        Args:
            results: List of execution results
        """
        # Display results
        self.results_frame.display_results(results)

        # Save to history
        if self.current_plugin and self.serial_handler:
            success_count = sum(
                1 for r in results
                if "response" in r and r["response"].is_success()
            )

            self.history_manager.save_inspection(
                plugin_vendor=self.current_plugin.metadata.vendor,
                plugin_model=self.current_plugin.metadata.model,
                port=self.connection_frame.get_current_port() or "unknown",
                command_count=len(results),
                success_count=success_count,
                duration=0  # Would calculate from execution time
            )

    def _on_export_clicked(self):
        """Handle export button click."""
        results = self.results_frame.get_results()
        if not results:
            return

        dialog = ReportDialog(self, execution_results=results)
        dialog.wait_window()

    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self)
        dialog.wait_window()

    def show_help(self):
        """Show help dialog."""
        dialog = HelpDialog(self)
        dialog.wait_window()

    def run(self):
        """Run the application."""
        self.mainloop()


def main():
    """Main entry point for GUI application."""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
