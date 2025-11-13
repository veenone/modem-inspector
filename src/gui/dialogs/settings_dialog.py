"""Settings dialog for configuration management.

Provides modal dialog for viewing and editing application settings.
"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from src.config.config_manager import ConfigManager
from src.config.config_models import LogLevel


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
        self.geometry("500x400")
        self.resizable(False, False)

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
        self.timeout_entry = ctk.CTkEntry(serial_frame, placeholder_text="5")
        self.timeout_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=10)

        serial_frame.grid_columnconfigure(1, weight=1)

        # Reports settings tab
        self.tabview.add("Reports")
        reports_frame = self.tabview.tab("Reports")

        ctk.CTkLabel(reports_frame, text="Output Directory:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.output_dir_entry = ctk.CTkEntry(reports_frame, placeholder_text="./reports")
        self.output_dir_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        reports_frame.grid_columnconfigure(1, weight=1)

        # Logging settings tab
        self.tabview.add("Logging")
        logging_frame = self.tabview.tab("Logging")
        logging_frame.grid_columnconfigure(1, weight=1)

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
        self.open_log_dir_button.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=20)

        # Advanced settings tab
        self.tabview.add("Advanced")
        advanced_frame = self.tabview.tab("Advanced")

        info_label = ctk.CTkLabel(
            advanced_frame,
            text="Advanced settings are configured via config.yaml file.",
            wraplength=400
        )
        info_label.pack(pady=20, padx=20)

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=self.destroy
        )
        cancel_button.pack(side="right", padx=5)

        ok_button = ctk.CTkButton(
            button_frame,
            text="OK",
            width=100,
            command=self._on_ok
        )
        ok_button.pack(side="right", padx=5)

    def _load_settings(self):
        """Load current settings."""
        try:
            config = ConfigManager.get_config()

            # Load serial settings
            self.baud_entry.insert(0, str(config.serial.default_baud))
            self.timeout_entry.insert(0, str(config.serial.timeout))

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

    def _on_ok(self):
        """Handle OK button - save settings and close dialog."""
        try:
            # Note: In a full implementation, this would save to ConfigManager
            # For now, we just validate and close
            # The application layer should handle applying these settings

            # Validate log file path if logging to file
            if self.logging_enabled_var.get() and self.log_to_file_var.get():
                log_path = self.log_file_entry.get()
                if log_path:
                    # Validate path is writable
                    try:
                        test_path = Path(log_path).parent
                        test_path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        from tkinter import messagebox
                        messagebox.showerror("Invalid Path", f"Log file path is not writable: {e}")
                        return

            self.destroy()

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to save settings: {e}")
