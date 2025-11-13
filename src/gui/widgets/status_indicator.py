"""Status indicator widget with LED-style visual feedback.

Provides a visual indicator with colored circle and status text for
connection state display.
"""

import customtkinter as ctk
from typing import Literal


StatusState = Literal["disconnected", "connected", "error", "busy"]


class StatusIndicator(ctk.CTkFrame):
    """LED-style status indicator with color and text.

    Displays connection status with colored circle indicator and text label:
    - disconnected: Gray circle, "Disconnected"
    - connected: Green circle, "Connected"
    - error: Red circle, "Error"
    - busy: Yellow circle, "Connecting..."

    Example:
        >>> indicator = StatusIndicator(parent)
        >>> indicator.set_status("connected")
        >>> indicator.set_status("error", "Connection failed")
    """

    # Color scheme for status states
    COLORS = {
        "disconnected": "#808080",  # Gray
        "connected": "#2FA572",     # Green
        "error": "#E74C3C",         # Red
        "busy": "#FFBF00"           # Yellow/Gold
    }

    # Default status text
    STATUS_TEXT = {
        "disconnected": "Disconnected",
        "connected": "Connected",
        "error": "Error",
        "busy": "Connecting..."
    }

    def __init__(self, master, **kwargs):
        """Initialize status indicator.

        Args:
            master: Parent widget
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(master, **kwargs)

        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # LED indicator (canvas)
        self.indicator_canvas = ctk.CTkCanvas(
            self,
            width=20,
            height=20,
            highlightthickness=0
        )
        self.indicator_canvas.grid(row=0, column=0, sticky="w", padx=(0, 8))

        # Draw circle
        self.indicator_id = self.indicator_canvas.create_oval(
            2, 2, 18, 18,
            fill=self.COLORS["disconnected"],
            outline=""
        )

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text=self.STATUS_TEXT["disconnected"],
            anchor="w"
        )
        self.status_label.grid(row=0, column=1, sticky="w")

        self.current_state = "disconnected"

    def set_status(self, state: StatusState, custom_text: str = None):
        """Update status indicator.

        Args:
            state: Status state (disconnected/connected/error/busy)
            custom_text: Optional custom status text (overrides default)

        Example:
            >>> indicator.set_status("connected")
            >>> indicator.set_status("error", "Port not found")
        """
        if state not in self.COLORS:
            raise ValueError(f"Invalid state: {state}. Must be one of {list(self.COLORS.keys())}")

        self.current_state = state

        # Update indicator color
        self.indicator_canvas.itemconfig(
            self.indicator_id,
            fill=self.COLORS[state]
        )

        # Update status text
        text = custom_text if custom_text else self.STATUS_TEXT[state]
        self.status_label.configure(text=text)

    def get_status(self) -> StatusState:
        """Get current status state.

        Returns:
            Current status state
        """
        return self.current_state

    def set_disconnected(self):
        """Convenience method to set disconnected state."""
        self.set_status("disconnected")

    def set_connected(self):
        """Convenience method to set connected state."""
        self.set_status("connected")

    def set_error(self, error_message: str = None):
        """Convenience method to set error state.

        Args:
            error_message: Optional error message to display
        """
        self.set_status("error", error_message)

    def set_busy(self, message: str = None):
        """Convenience method to set busy state.

        Args:
            message: Optional busy message to display
        """
        self.set_status("busy", message)
