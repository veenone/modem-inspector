"""Log viewer frame for real-time communication log display.

Provides real-time log viewing with search, filtering, color coding, and export
functionality for AT command communication logs.
"""

import customtkinter as ctk
from typing import Optional
from datetime import datetime
from pathlib import Path
import subprocess
import platform

from src.logging import CommunicationLogger


class LogViewerFrame(ctk.CTkFrame):
    """Frame for viewing communication logs in real-time.

    Displays log entries from CommunicationLogger with color coding by level,
    search/filter capabilities, and export functionality. Updates asynchronously
    using tkinter's after() method for non-blocking operation.

    Example:
        >>> logger = CommunicationLogger(...)
        >>> frame = LogViewerFrame(parent, logger=logger)
        >>> frame.start_logging()
    """

    # Color scheme for log levels
    LEVEL_COLORS = {
        "DEBUG": "#808080",    # Gray
        "INFO": "#4A90E2",     # Blue
        "WARNING": "#F5A623",  # Orange/Yellow
        "ERROR": "#D0021B"     # Red
    }

    def __init__(
        self,
        master,
        logger: Optional[CommunicationLogger] = None,
        **kwargs
    ):
        """Initialize log viewer frame.

        Args:
            master: Parent widget
            logger: CommunicationLogger instance for log data (optional)
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(master, **kwargs)

        self.logger = logger
        self.is_logging = False
        self._last_entry_count = 0
        self._search_text = ""
        self._filter_level = "All"
        self._max_displayed_entries = 1000

        self._setup_ui()

    def _setup_ui(self):
        """Set up UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Log display row expands

        # Title and controls row
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(1, weight=1)

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Communication Logs",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        # Log level filter
        filter_label = ctk.CTkLabel(header_frame, text="Level:")
        filter_label.grid(row=0, column=1, sticky="e", padx=(10, 5), pady=5)

        self.level_filter = ctk.CTkComboBox(
            header_frame,
            values=["All", "DEBUG", "INFO", "WARNING", "ERROR"],
            command=self._on_filter_changed,
            width=120
        )
        self.level_filter.set("All")
        self.level_filter.grid(row=0, column=2, sticky="e", padx=5, pady=5)

        # Search row
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        search_frame.grid_columnconfigure(1, weight=1)

        search_label = ctk.CTkLabel(search_frame, text="Search:")
        search_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search logs..."
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        # Log display (textbox with monospace font)
        self.log_textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Courier New", size=10),
            wrap="none"
        )
        self.log_textbox.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        # Configure text tags for color coding
        for level, color in self.LEVEL_COLORS.items():
            self.log_textbox._textbox.tag_config(level, foreground=color)

        # Button row
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))

        self.clear_button = ctk.CTkButton(
            button_frame,
            text="Clear Display",
            command=self._on_clear_clicked,
            width=120
        )
        self.clear_button.grid(row=0, column=0, padx=5, pady=5)

        self.save_button = ctk.CTkButton(
            button_frame,
            text="Save Log",
            command=self._on_save_clicked,
            width=120
        )
        self.save_button.grid(row=0, column=1, padx=5, pady=5)

        self.open_file_button = ctk.CTkButton(
            button_frame,
            text="Open Log File",
            command=self._on_open_file_clicked,
            width=120
        )
        self.open_file_button.grid(row=0, column=2, padx=5, pady=5)

        # Entry count label
        self.count_label = ctk.CTkLabel(
            button_frame,
            text="Entries: 0",
            font=ctk.CTkFont(size=10)
        )
        self.count_label.grid(row=0, column=3, sticky="e", padx=(20, 5), pady=5)

    def set_logger(self, logger: CommunicationLogger):
        """Set the logger instance.

        Args:
            logger: CommunicationLogger to display logs from
        """
        self.logger = logger
        self._last_entry_count = 0

    def start_logging(self):
        """Start polling logger for new entries.

        Begins asynchronous polling using tkinter's after() method.
        Updates display every 100ms with new log entries.
        """
        if not self.is_logging and self.logger:
            self.is_logging = True
            self._poll_logs()

    def stop_logging(self):
        """Stop polling logger for new entries.

        Pauses display updates but does not clear existing entries.
        """
        self.is_logging = False

    def _poll_logs(self):
        """Poll logger for new entries (internal method).

        Called asynchronously via after() to check for new log entries
        and update the display. Automatically reschedules itself.
        """
        if not self.is_logging or not self.logger:
            return

        try:
            # Get entries from logger's in-memory buffer
            entries = self.logger.get_entries(limit=self._max_displayed_entries)

            # Check if new entries arrived
            if len(entries) != self._last_entry_count:
                self._last_entry_count = len(entries)
                self._update_display(entries)

        except Exception as e:
            # Silently handle errors to avoid breaking the polling loop
            pass

        # Reschedule polling (100ms interval)
        if self.is_logging:
            self.after(100, self._poll_logs)

    def _update_display(self, entries):
        """Update log display with filtered entries.

        Args:
            entries: List of LogEntry objects to display
        """
        # Apply filters
        filtered_entries = self._apply_filters(entries)

        # Clear textbox
        self.log_textbox.delete("1.0", "end")

        # Add filtered entries with color coding
        for entry in filtered_entries:
            line = entry.to_string() + "\n"

            # Insert with tag for color coding
            start_index = self.log_textbox.index("end-1c")
            self.log_textbox.insert("end", line)
            end_index = self.log_textbox.index("end-1c")

            # Apply color tag based on log level
            if entry.level in self.LEVEL_COLORS:
                self.log_textbox._textbox.tag_add(entry.level, start_index, end_index)

        # Auto-scroll to bottom
        self.log_textbox.see("end")

        # Update entry count
        self.count_label.configure(text=f"Entries: {len(filtered_entries)}/{len(entries)}")

    def _apply_filters(self, entries):
        """Apply search and level filters to entries.

        Args:
            entries: List of LogEntry objects

        Returns:
            Filtered list of LogEntry objects
        """
        filtered = entries

        # Apply level filter
        if self._filter_level != "All":
            filtered = [e for e in filtered if e.level == self._filter_level]

        # Apply search filter
        if self._search_text:
            search_lower = self._search_text.lower()
            filtered = [
                e for e in filtered
                if search_lower in e.message.lower()
                or (e.command and search_lower in e.command.lower())
                or (e.response and search_lower in e.response.lower())
            ]

        # Limit to max displayed entries (keep most recent)
        if len(filtered) > self._max_displayed_entries:
            filtered = filtered[-self._max_displayed_entries:]

        return filtered

    def _on_filter_changed(self, selected_level: str):
        """Handle log level filter change.

        Args:
            selected_level: Selected log level from dropdown
        """
        self._filter_level = selected_level

        # Refresh display with new filter
        if self.logger:
            entries = self.logger.get_entries(limit=self._max_displayed_entries)
            self._update_display(entries)

    def _on_search_changed(self, event=None):
        """Handle search text change.

        Args:
            event: Tkinter event (unused)
        """
        self._search_text = self.search_entry.get()

        # Refresh display with new search
        if self.logger:
            entries = self.logger.get_entries(limit=self._max_displayed_entries)
            self._update_display(entries)

    def _on_clear_clicked(self):
        """Handle Clear Display button click.

        Clears the viewer (not the log file or logger buffer).
        """
        self.log_textbox.delete("1.0", "end")
        self.count_label.configure(text="Entries: 0")

        # Clear logger's in-memory buffer
        if self.logger:
            self.logger.clear_buffer()
            self._last_entry_count = 0

    def _on_save_clicked(self):
        """Handle Save Log button click.

        Exports visible (filtered) log entries to a file.
        """
        if not self.logger:
            return

        try:
            # Get current displayed entries
            entries = self.logger.get_entries(limit=self._max_displayed_entries)
            filtered_entries = self._apply_filters(entries)

            if not filtered_entries:
                return

            # Generate default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"comm_log_export_{timestamp}.txt"

            # File dialog for save location
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=default_filename,
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )

            if filepath:
                # Write entries to file
                with open(filepath, 'w', encoding='utf-8') as f:
                    for entry in filtered_entries:
                        f.write(entry.to_string() + '\n')

        except Exception as e:
            # Show error dialog
            from tkinter import messagebox
            messagebox.showerror("Save Error", f"Failed to save log: {e}")

    def _on_open_file_clicked(self):
        """Handle Open Log File button click.

        Opens the current log file in the system's default text editor.
        """
        if not self.logger or not self.logger.log_file_path:
            from tkinter import messagebox
            messagebox.showinfo("No Log File", "No log file is currently active.")
            return

        try:
            log_path = Path(self.logger.log_file_path)

            if not log_path.exists():
                from tkinter import messagebox
                messagebox.showwarning("File Not Found", f"Log file not found: {log_path}")
                return

            # Open file with system default application
            if platform.system() == 'Windows':
                subprocess.run(['notepad', str(log_path)], check=False)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(log_path)], check=False)
            else:  # Linux
                subprocess.run(['xdg-open', str(log_path)], check=False)

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Open Error", f"Failed to open log file: {e}")
