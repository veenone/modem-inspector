"""Error dialog for consistent error display.

Provides modal dialog for displaying errors with optional details and actions.
"""

import customtkinter as ctk
from typing import Optional


class ErrorDialog(ctk.CTkToplevel):
    """Modal dialog for error display.

    Displays error information with type, message, and optional detailed stack trace.

    Example:
        >>> ErrorDialog.show_error(
        ...     parent,
        ...     title="Connection Error",
        ...     message="Failed to connect to COM3",
        ...     details="SerialException: Port not found"
        ... )
    """

    def __init__(
        self,
        parent,
        title: str = "Error",
        message: str = "",
        details: Optional[str] = None,
        **kwargs
    ):
        """Initialize error dialog.

        Args:
            parent: Parent window
            title: Error dialog title
            message: Main error message
            details: Optional detailed error information (stack trace, etc)
            **kwargs: Additional CTkToplevel arguments
        """
        super().__init__(parent, **kwargs)

        self.error_details = details

        self.title(title)
        self.geometry("450x200" if not details else "450x300")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self._setup_ui(title, message, details)

    def _setup_ui(self, title: str, message: str, details: Optional[str]):
        """Set up UI components.

        Args:
            title: Error title
            message: Error message
            details: Optional detailed error information
        """
        # Error icon and title
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=20)

        error_label = ctk.CTkLabel(
            header_frame,
            text="⚠️  " + title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#E74C3C"
        )
        error_label.pack(anchor="w")

        # Message
        message_frame = ctk.CTkFrame(self)
        message_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        message_label = ctk.CTkLabel(
            message_frame,
            text=message,
            wraplength=400,
            justify="left",
            anchor="w"
        )
        message_label.pack(fill="x", padx=10, pady=10)

        # Details (if provided)
        if details:
            self.details_textbox = ctk.CTkTextbox(message_frame, height=100)
            self.details_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            self.details_textbox.insert("1.0", details)
            self.details_textbox.configure(state="disabled")

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Copy Error button (if details provided)
        if details:
            copy_button = ctk.CTkButton(
                button_frame,
                text="Copy Error",
                width=100,
                command=self._copy_error
            )
            copy_button.pack(side="left", padx=5)

        ok_button = ctk.CTkButton(
            button_frame,
            text="OK",
            width=100,
            command=self.destroy
        )
        ok_button.pack(side="right", padx=5)

    def _copy_error(self):
        """Copy error details to clipboard."""
        if self.error_details:
            self.clipboard_clear()
            self.clipboard_append(self.error_details)

    @staticmethod
    def show_error(
        parent,
        title: str = "Error",
        message: str = "",
        details: Optional[str] = None
    ):
        """Show error dialog (convenience method).

        Args:
            parent: Parent window
            title: Error dialog title
            message: Main error message
            details: Optional detailed error information

        Example:
            >>> ErrorDialog.show_error(
            ...     parent,
            ...     title="Connection Failed",
            ...     message="Unable to connect to serial port",
            ...     details="Port COM3 not found"
            ... )
        """
        dialog = ErrorDialog(parent, title=title, message=message, details=details)
        dialog.wait_window()
