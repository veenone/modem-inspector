"""Connection frame for serial port management.

Provides port selection, connection/disconnection controls, and status display.
"""

import customtkinter as ctk
from typing import Optional, Callable
from src.gui.widgets import PortSelector, StatusIndicator
from src.core.serial_handler import SerialHandler
from src.core.exceptions import SerialPortError


class ConnectionFrame(ctk.CTkFrame):
    """Frame for managing serial port connection.

    Integrates PortSelector and StatusIndicator widgets with connection
    management controls. Handles port discovery, connection state, and
    error reporting.

    Example:
        >>> def on_connect_callback(port: str, handler: SerialHandler):
        ...     print(f"Connected to {port}")
        ...
        >>> frame = ConnectionFrame(
        ...     parent,
        ...     on_connect=on_connect_callback,
        ...     on_disconnect=lambda: print("Disconnected")
        ... )
    """

    def __init__(
        self,
        master,
        on_connect: Optional[Callable[[str, SerialHandler], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """Initialize connection frame.

        Args:
            master: Parent widget
            on_connect: Callback when connection established (receives port, handler)
            on_disconnect: Callback when disconnected
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(master, **kwargs)

        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        self.serial_handler: Optional[SerialHandler] = None
        self.current_port: Optional[str] = None
        self.is_connected = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)  # Label column
        self.grid_columnconfigure(1, weight=1)  # Widget column
        self.grid_columnconfigure(2, weight=0)  # Button column

        # Title label
        title_label = ctk.CTkLabel(
            self,
            text="Serial Port Connection",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 15))

        # Port selection row
        port_label = ctk.CTkLabel(self, text="Port:", width=80, anchor="w")
        port_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.port_selector = PortSelector(
            self,
            on_refresh=self._refresh_ports,
            on_select=self._on_port_selected
        )
        self.port_selector.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        # Connect/Disconnect button
        self.connect_button = ctk.CTkButton(
            self,
            text="Connect",
            width=120,
            command=self._on_connect_clicked
        )
        self.connect_button.grid(row=1, column=2, sticky="e", padx=10, pady=5)

        # Status row
        status_label = ctk.CTkLabel(self, text="Status:", width=80, anchor="w")
        status_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)

        self.status_indicator = StatusIndicator(self)
        self.status_indicator.grid(row=2, column=1, sticky="w", padx=10, pady=5)

    def _refresh_ports(self):
        """Refresh available serial ports.

        Returns:
            List of (device, description) tuples
        """
        try:
            ports = SerialHandler.discover_ports()
            return [(port.device, port.description) for port in ports]
        except Exception as e:
            # Return empty list on error - PortSelector will show "No ports available"
            return []

    def _on_port_selected(self, port: str):
        """Handle port selection from dropdown.

        Args:
            port: Selected port device name
        """
        self.current_port = port

    def _on_connect_clicked(self):
        """Handle Connect/Disconnect button click."""
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        """Attempt to connect to selected port."""
        if not self.current_port:
            self._show_error("No port selected", "Please select a serial port to connect.")
            return

        try:
            # Update UI to busy state
            self.status_indicator.set_busy("Connecting...")
            self.connect_button.configure(state="disabled")
            self.port_selector.set_enabled(False)

            # Create and open serial handler
            self.serial_handler = SerialHandler(self.current_port)
            self.serial_handler.open()

            # Connection successful
            self.is_connected = True
            self.status_indicator.set_connected()
            self.connect_button.configure(text="Disconnect", state="normal")

            # Call success callback
            if self.on_connect_callback:
                self.on_connect_callback(self.current_port, self.serial_handler)

        except SerialPortError as e:
            # Connection failed
            self.is_connected = False
            self.status_indicator.set_error("Connection failed")
            self.connect_button.configure(text="Connect", state="normal")
            self.port_selector.set_enabled(True)
            self.serial_handler = None

            self._show_error("Connection Error", str(e))

        except Exception as e:
            # Unexpected error
            self.is_connected = False
            self.status_indicator.set_error("Unexpected error")
            self.connect_button.configure(text="Connect", state="normal")
            self.port_selector.set_enabled(True)
            self.serial_handler = None

            self._show_error("Unexpected Error", f"An unexpected error occurred: {str(e)}")

    def _disconnect(self):
        """Disconnect from current port."""
        try:
            if self.serial_handler:
                self.serial_handler.close()
                self.serial_handler = None

            self.is_connected = False
            self.status_indicator.set_disconnected()
            self.connect_button.configure(text="Connect")
            self.port_selector.set_enabled(True)

            # Call disconnect callback
            if self.on_disconnect_callback:
                self.on_disconnect_callback()

        except Exception as e:
            self._show_error("Disconnect Error", f"Error disconnecting: {str(e)}")

    def _show_error(self, title: str, message: str):
        """Show error dialog.

        Args:
            title: Error dialog title
            message: Error message
        """
        # For now, use simple CTk dialog
        # Will be replaced with custom ErrorDialog in Task 9
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # Message
        msg_label = ctk.CTkLabel(
            dialog,
            text=message,
            wraplength=350
        )
        msg_label.pack(pady=20, padx=20)

        # OK button
        ok_button = ctk.CTkButton(
            dialog,
            text="OK",
            width=100,
            command=dialog.destroy
        )
        ok_button.pack(pady=10)

    def get_serial_handler(self) -> Optional[SerialHandler]:
        """Get current serial handler if connected.

        Returns:
            SerialHandler instance or None if not connected
        """
        return self.serial_handler if self.is_connected else None

    def get_current_port(self) -> Optional[str]:
        """Get currently connected port.

        Returns:
            Port device name or None if not connected
        """
        return self.current_port if self.is_connected else None

    def is_port_connected(self) -> bool:
        """Check if port is currently connected.

        Returns:
            True if connected, False otherwise
        """
        return self.is_connected
