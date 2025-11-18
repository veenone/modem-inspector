"""Settings dialog for configuration management.

Provides modal dialog for viewing and editing application settings.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from src.config.config_manager import ConfigManager
from src.config.config_models import LogLevel
from src.gui.utils.validation import validate_baud_rate, validate_timeout, validate_retry_count, validate_retry_delay, validate_directory_path


class SettingsDialog(ctk.CTkToplevel):
    """Modal dialog for application settings.

    Displays current configuration with tabs for Serial, Reports, and Advanced settings.

    Example:
        >>> dialog = SettingsDialog(parent)
        >>> dialog.wait_window()  # Wait for dialog to close
    """

    def __init__(self, parent, **kwargs):
        """Initialize settings dialog.

        Args:
            parent: Parent window
            **kwargs: Additional CTkToplevel arguments
        """
        super().__init__(parent, **kwargs)

        self.title("Settings")
        self.geometry("600x550")
        self.resizable(True, True)
        self.minsize(500, 450)  # Set minimum size

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up UI components."""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Application Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=20)

        # Tabview for settings categories
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Serial settings tab
        self.tabview.add("Serial")
        serial_frame = self.tabview.tab("Serial")

        ctk.CTkLabel(serial_frame, text="Baud Rate:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.baud_entry = ctk.CTkEntry(serial_frame, placeholder_text="115200")
        self.baud_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(serial_frame, text="Timeout (s):").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.timeout_entry = ctk.CTkEntry(serial_frame, placeholder_text="30")
        self.timeout_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(serial_frame, text="Retry Attempts:").grid(row=2, column=0, sticky="w", padx=10, pady=10)
        self.retry_attempts_entry = ctk.CTkEntry(serial_frame, placeholder_text="3")
        self.retry_attempts_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(serial_frame, text="Retry Delay (ms):").grid(row=3, column=0, sticky="w", padx=10, pady=10)
        self.retry_delay_entry = ctk.CTkEntry(serial_frame, placeholder_text="1000")
        self.retry_delay_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=10)

        serial_frame.grid_columnconfigure(1, weight=1)

        # Reports settings tab
        self.tabview.add("Reports")
        reports_frame = self.tabview.tab("Reports")

        ctk.CTkLabel(reports_frame, text="Output Directory:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.output_dir_entry = ctk.CTkEntry(reports_frame, placeholder_text="./reports")
        self.output_dir_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        browse_dir_button = ctk.CTkButton(
            reports_frame,
            text="Browse",
            width=80,
            command=self._on_browse_output_dir
        )
        browse_dir_button.grid(row=0, column=2, sticky="w", padx=10, pady=10)

        reports_frame.grid_columnconfigure(1, weight=1)

        # Logging settings tab
        self.tabview.add("Logging")
        logging_frame = self.tabview.tab("Logging")
        logging_frame.grid_columnconfigure(1, weight=1)
        logging_frame.grid_columnconfigure(2, weight=0)  # Configure column 2 for Browse button

        # Enable logging checkbox
        self.logging_enabled_var = ctk.BooleanVar(value=False)
        self.logging_enabled_checkbox = ctk.CTkCheckBox(
            logging_frame,
            text="Enable Communication Logging",
            variable=self.logging_enabled_var,
            command=self._on_logging_enabled_changed
        )
        self.logging_enabled_checkbox.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        # Log level
        ctk.CTkLabel(logging_frame, text="Log Level:").grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.log_level_combo = ctk.CTkComboBox(
            logging_frame,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="disabled"
        )
        self.log_level_combo.grid(row=1, column=1, sticky="ew", padx=10, pady=10)
        self.log_level_combo.set("INFO")

        # Log to file checkbox
        self.log_to_file_var = ctk.BooleanVar(value=False)
        self.log_to_file_checkbox = ctk.CTkCheckBox(
            logging_frame,
            text="Log to File",
            variable=self.log_to_file_var,
            command=self._on_log_to_file_changed,
            state="disabled"
        )
        self.log_to_file_checkbox.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        # Log file path
        ctk.CTkLabel(logging_frame, text="Log File Path:").grid(row=3, column=0, sticky="w", padx=10, pady=10)
        self.log_file_entry = ctk.CTkEntry(
            logging_frame,
            placeholder_text="~/.modem-inspector/logs/comm_YYYYMMDD_HHMMSS.log",
            state="disabled"
        )
        self.log_file_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=10)

        self.browse_button = ctk.CTkButton(
            logging_frame,
            text="Browse",
            width=80,
            command=self._on_browse_log_file,
            state="disabled"
        )
        self.browse_button.grid(row=3, column=2, sticky="w", padx=10, pady=10)

        # Log to console checkbox
        self.log_to_console_var = ctk.BooleanVar(value=True)
        self.log_to_console_checkbox = ctk.CTkCheckBox(
            logging_frame,
            text="Log to Console (stderr)",
            variable=self.log_to_console_var,
            state="disabled"
        )
        self.log_to_console_checkbox.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        # Open log directory button
        self.open_log_dir_button = ctk.CTkButton(
            logging_frame,
            text="Open Log Directory",
            width=150,
            command=self._on_open_log_dir,
            state="disabled"
        )
        self.open_log_dir_button.grid(row=5, column=0, columnspan=3, sticky="w", padx=10, pady=20)

        # Advanced settings tab
        self.tabview.add("Advanced")
        advanced_frame = self.tabview.tab("Advanced")
        advanced_frame.grid_columnconfigure(1, weight=1)

        info_label = ctk.CTkLabel(
            advanced_frame,
            text="Advanced settings are configured via config.yaml file.",
            wraplength=400
        )
        info_label.grid(row=0, column=0, columnspan=2, pady=20, padx=20)

        # Hot reload status section
        hot_reload_frame = ctk.CTkFrame(advanced_frame)
        hot_reload_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        hot_reload_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hot_reload_frame,
            text="Hot Reload Status:",
            font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.hot_reload_status_label = ctk.CTkLabel(
            hot_reload_frame,
            text="Checking...",
            text_color="gray"
        )
        self.hot_reload_status_label.grid(row=0, column=1, sticky="w", padx=10, pady=10)

        # Config file path
        ctk.CTkLabel(
            hot_reload_frame,
            text="Config File:"
        ).grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.config_path_label = ctk.CTkLabel(
            hot_reload_frame,
            text="Not loaded",
            text_color="gray"
        )
        self.config_path_label.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Hot reload toggle button
        self.toggle_hot_reload_button = ctk.CTkButton(
            hot_reload_frame,
            text="Enable Hot Reload",
            width=150,
            command=self._on_toggle_hot_reload
        )
        self.toggle_hot_reload_button.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=10)

        # Update hot reload status
        self._update_hot_reload_status()

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        reset_button = ctk.CTkButton(
            button_frame,
            text="Reset to Defaults",
            width=140,
            command=self._on_reset
        )
        reset_button.pack(side="left", padx=5)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=self.destroy
        )
        cancel_button.pack(side="right", padx=5)

        ok_button = ctk.CTkButton(
            button_frame,
            text="Save",
            width=100,
            command=self._on_ok
        )
        ok_button.pack(side="right", padx=5)

    def _load_settings(self):
        """Load current settings."""
        try:
            config = ConfigManager.instance().get_config()

            # Load serial settings
            self.baud_entry.insert(0, str(config.serial.default_baud))
            self.timeout_entry.insert(0, str(config.serial.timeout))
            self.retry_attempts_entry.insert(0, str(config.serial.retry_attempts))
            self.retry_delay_entry.insert(0, str(config.serial.retry_delay))

            # Load report settings
            self.output_dir_entry.insert(0, str(config.reporting.output_directory))

            # Load logging settings
            self.logging_enabled_var.set(config.logging.enabled)
            self.log_level_combo.set(config.logging.level.value)
            self.log_to_file_var.set(config.logging.log_to_file)
            self.log_to_console_var.set(config.logging.log_to_console)

            if config.logging.log_file_path:
                self.log_file_entry.delete(0, "end")
                self.log_file_entry.insert(0, config.logging.log_file_path)

            # Update control states based on enabled status
            self._update_logging_controls_state()

        except Exception:
            # If config load fails, keep placeholder values
            pass

    def _on_logging_enabled_changed(self):
        """Handle logging enabled checkbox change."""
        self._update_logging_controls_state()

    def _update_logging_controls_state(self):
        """Update enabled/disabled state of logging controls."""
        enabled = self.logging_enabled_var.get()
        state = "normal" if enabled else "disabled"

        self.log_level_combo.configure(state=state)
        self.log_to_file_checkbox.configure(state=state)
        self.log_to_console_checkbox.configure(state=state)
        self.open_log_dir_button.configure(state=state)

        # File path controls depend on both logging enabled and log_to_file
        file_state = "normal" if (enabled and self.log_to_file_var.get()) else "disabled"
        self.log_file_entry.configure(state=file_state)
        self.browse_button.configure(state=file_state)

    def _on_log_to_file_changed(self):
        """Handle log to file checkbox change."""
        self._update_logging_controls_state()

    def _on_browse_log_file(self):
        """Handle Browse button for log file path."""
        filepath = filedialog.asksaveasfilename(
            title="Select Log File Location",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filepath:
            self.log_file_entry.delete(0, "end")
            self.log_file_entry.insert(0, filepath)

    def _on_open_log_dir(self):
        """Handle Open Log Directory button."""
        try:
            log_path = self.log_file_entry.get()
            if not log_path:
                log_path = str(Path.home() / ".modem-inspector" / "logs")

            log_dir = Path(log_path).parent if Path(log_path).is_file() else Path(log_path)

            # Create directory if it doesn't exist
            log_dir.mkdir(parents=True, exist_ok=True)

            # Open in file explorer
            import subprocess
            import platform
            if platform.system() == 'Windows':
                subprocess.run(['explorer', str(log_dir)], check=False)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(log_dir)], check=False)
            else:  # Linux
                subprocess.run(['xdg-open', str(log_dir)], check=False)

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to open log directory: {e}")

    def _on_browse_output_dir(self):
        """Handle Browse button for output directory."""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir_entry.get() or "./reports"
        )

        if directory:
            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, directory)

    def _on_reset(self):
        """Handle Reset to Defaults button."""
        if not messagebox.askyesno("Reset to Defaults",
                                   "Are you sure you want to reset all settings to defaults?\n\nThis will restore factory default values for all configuration options."):
            return

        try:
            from src.config.defaults import get_default_config
            defaults = get_default_config()

            # Clear and reload with defaults
            self.baud_entry.delete(0, "end")
            self.baud_entry.insert(0, str(defaults.serial.default_baud))

            self.timeout_entry.delete(0, "end")
            self.timeout_entry.insert(0, str(defaults.serial.timeout))

            self.retry_attempts_entry.delete(0, "end")
            self.retry_attempts_entry.insert(0, str(defaults.serial.retry_attempts))

            self.retry_delay_entry.delete(0, "end")
            self.retry_delay_entry.insert(0, str(defaults.serial.retry_delay))

            self.output_dir_entry.delete(0, "end")
            self.output_dir_entry.insert(0, str(defaults.reporting.output_directory))

            self.logging_enabled_var.set(defaults.logging.enabled)
            self.log_level_combo.set(defaults.logging.level.value)
            self.log_to_file_var.set(defaults.logging.log_to_file)
            self.log_to_console_var.set(defaults.logging.log_to_console)

            if defaults.logging.log_file_path:
                self.log_file_entry.delete(0, "end")
                self.log_file_entry.insert(0, defaults.logging.log_file_path)

            self._update_logging_controls_state()

            messagebox.showinfo("Reset Complete", "All settings have been reset to defaults.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset settings: {e}")

    def _update_hot_reload_status(self):
        """Update hot reload status indicators."""
        try:
            config_manager = ConfigManager.instance()

            # Update hot reload status
            is_enabled = config_manager.is_hot_reload_enabled()
            if is_enabled:
                self.hot_reload_status_label.configure(
                    text="✓ Enabled",
                    text_color="green"
                )
                self.toggle_hot_reload_button.configure(text="Disable Hot Reload")
            else:
                self.hot_reload_status_label.configure(
                    text="✗ Disabled",
                    text_color="orange"
                )
                self.toggle_hot_reload_button.configure(text="Enable Hot Reload")

            # Update config file path
            if config_manager._config_path:
                self.config_path_label.configure(
                    text=str(config_manager._config_path),
                    text_color="white"
                )
            else:
                self.config_path_label.configure(
                    text="Using defaults only",
                    text_color="gray"
                )

        except RuntimeError:
            # ConfigManager not initialized
            self.hot_reload_status_label.configure(
                text="Not initialized",
                text_color="red"
            )
            self.config_path_label.configure(
                text="N/A",
                text_color="gray"
            )
            self.toggle_hot_reload_button.configure(state="disabled")

    def _on_toggle_hot_reload(self):
        """Handle hot reload toggle button."""
        try:
            config_manager = ConfigManager.instance()

            if config_manager.is_hot_reload_enabled():
                config_manager.disable_hot_reload()
                messagebox.showinfo("Hot Reload Disabled",
                                  "Configuration hot reload has been disabled.\n\nChanges to config.yaml will no longer be automatically detected.")
            else:
                success = config_manager.enable_hot_reload()
                if success:
                    messagebox.showinfo("Hot Reload Enabled",
                                      "Configuration hot reload has been enabled.\n\nChanges to config.yaml will be automatically detected and applied.")
                else:
                    messagebox.showerror("Hot Reload Failed",
                                       "Failed to enable hot reload.\n\nMake sure a config file is loaded.")

            # Update status display
            self._update_hot_reload_status()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle hot reload: {e}")

    def _on_ok(self):
        """Handle OK button - validate and save settings."""
        try:
            # Validate serial settings
            is_valid, error = validate_baud_rate(self.baud_entry.get())
            if not is_valid:
                messagebox.showerror("Invalid Baud Rate", error)
                self.tabview.set("Serial")
                return

            is_valid, error = validate_timeout(self.timeout_entry.get())
            if not is_valid:
                messagebox.showerror("Invalid Timeout", error)
                self.tabview.set("Serial")
                return

            is_valid, error = validate_retry_count(self.retry_attempts_entry.get())
            if not is_valid:
                messagebox.showerror("Invalid Retry Attempts", error)
                self.tabview.set("Serial")
                return

            is_valid, error = validate_retry_delay(self.retry_delay_entry.get())
            if not is_valid:
                messagebox.showerror("Invalid Retry Delay", error)
                self.tabview.set("Serial")
                return

            # Validate report settings
            is_valid, error = validate_directory_path(self.output_dir_entry.get())
            if not is_valid and not error.startswith("Warning"):
                messagebox.showerror("Invalid Output Directory", error)
                self.tabview.set("Reports")
                return

            # Validate log file path if logging to file
            if self.logging_enabled_var.get() and self.log_to_file_var.get():
                log_path = self.log_file_entry.get()
                if log_path:
                    try:
                        test_path = Path(log_path).parent
                        test_path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        messagebox.showerror("Invalid Log Path", f"Log file path is not writable: {e}")
                        self.tabview.set("Logging")
                        return

            # All validation passed - save settings
            # Note: This is a placeholder. In a full implementation, this would:
            # 1. Update ConfigManager with new values
            # 2. Persist to config file
            # 3. Notify application of config changes
            messagebox.showinfo("Settings Saved",
                              "Settings have been validated successfully.\n\nNote: Full save functionality requires integration with ConfigManager.save().")

            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
