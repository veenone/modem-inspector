"""Progress log widget with color-coded output and auto-scroll.

Provides a read-only text log with timestamp prefixes, color coding for
different message types, and automatic scrolling to latest entries.
"""

import customtkinter as ctk
from datetime import datetime
from typing import Literal


LogLevel = Literal["info", "success", "warning", "error"]


class ProgressLog(ctk.CTkTextbox):
    """Read-only log widget with color-coded entries and auto-scroll.

    Displays timestamped log messages with color coding:
    - info: Blue (default)
    - success: Green
    - warning: Yellow
    - error: Red

    Example:
        >>> log = ProgressLog(parent, height=300)
        >>> log.log("Starting inspection...", level="info")
        >>> log.log("Command executed successfully", level="success")
        >>> log.log("Timeout occurred", level="error")
        >>> log.clear()
    """

    # Color scheme for log levels
    COLORS = {
        "info": "#3B8ED0",      # Blue
        "success": "#2FA572",   # Green
        "warning": "#FFBF00",   # Yellow/Gold
        "error": "#E74C3C"      # Red
    }

    def __init__(self, master, **kwargs):
        """Initialize progress log.

        Args:
            master: Parent widget
            **kwargs: Additional CTkTextbox arguments
        """
        # Set default height if not provided
        if 'height' not in kwargs:
            kwargs['height'] = 300

        super().__init__(master, **kwargs)

        # Configure as read-only
        self.configure(state="disabled", wrap="word")

        # Configure color tags
        for level, color in self.COLORS.items():
            self._textbox.tag_config(level, foreground=color)

    def log(self, message: str, level: LogLevel = "info"):
        """Add log entry with timestamp and color coding.

        Args:
            message: Log message text
            level: Log level (info/success/warning/error)

        Example:
            >>> log.log("Port opened", level="success")
            >>> log.log("Connection failed", level="error")
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        # Enable editing temporarily
        self.configure(state="normal")

        # Insert with color tag
        self._textbox.insert("end", formatted_message, level)

        # Disable editing
        self.configure(state="disabled")

        # Auto-scroll to bottom
        self._textbox.see("end")

    def log_command(self, command: str):
        """Log AT command being executed.

        Args:
            command: AT command string

        Example:
            >>> log.log_command("AT+CGMI")
        """
        self.log(f"→ {command}", level="info")

    def log_response(self, response: str, is_success: bool = True):
        """Log command response.

        Args:
            response: Response text
            is_success: True for successful response, False for error

        Example:
            >>> log.log_response("Quectel", is_success=True)
            >>> log.log_response("ERROR", is_success=False)
        """
        level = "success" if is_success else "error"
        # Format multi-line responses with indentation
        lines = response.strip().split('\n')
        for line in lines:
            self.log(f"  ← {line}", level=level)

    def clear(self):
        """Clear all log entries."""
        self.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self.configure(state="disabled")

    def get_text(self) -> str:
        """Get all log text.

        Returns:
            Full log content as string
        """
        return self._textbox.get("1.0", "end-1c")

    def save_to_file(self, file_path: str):
        """Save log content to file.

        Args:
            file_path: Path to save log file

        Example:
            >>> log.save_to_file("inspection_log.txt")
        """
        content = self.get_text()
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
