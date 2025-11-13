"""Port selector widget with integrated refresh functionality.

Provides a dropdown for serial port selection with built-in refresh button
and formatted port information display.
"""

import customtkinter as ctk
from typing import List, Callable, Optional, Tuple


class PortSelector(ctk.CTkFrame):
    """Serial port selector with refresh button.

    Combines a dropdown (ComboBox) for port selection with a refresh button.
    Displays ports in format: "COM3 - Intel SOL (PCI\VEN...)"

    Example:
        >>> def on_refresh():
        ...     ports = SerialHandler.discover_ports()
        ...     return [(p.device, p.description) for p in ports]
        ...
        >>> selector = PortSelector(parent, on_refresh=on_refresh)
        >>> selected_port = selector.get_selected_port()
    """

    def __init__(
        self,
        master,
        on_refresh: Optional[Callable[[], List[Tuple[str, str]]]] = None,
        on_select: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """Initialize port selector.

        Args:
            master: Parent widget
            on_refresh: Callback that returns list of (device, description) tuples
            on_select: Callback called when port selected (receives device name)
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(master, **kwargs)

        self.on_refresh_callback = on_refresh
        self.on_select_callback = on_select
        self.port_map = {}  # Maps display string to device name

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        # Port dropdown
        self.port_combo = ctk.CTkComboBox(
            self,
            values=["No ports available"],
            command=self._on_port_selected,
            state="readonly"
        )
        self.port_combo.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # Refresh button
        self.refresh_button = ctk.CTkButton(
            self,
            text="⟳",
            width=40,
            command=self.refresh_ports
        )
        self.refresh_button.grid(row=0, column=1, sticky="e")

        # Initial refresh if callback provided
        if on_refresh:
            self.refresh_ports()

    def refresh_ports(self):
        """Refresh available ports using callback.

        Calls on_refresh callback and updates the dropdown with discovered ports.
        """
        if not self.on_refresh_callback:
            return

        try:
            # Get ports from callback
            ports = self.on_refresh_callback()

            if not ports:
                self.port_combo.configure(values=["No ports available"])
                self.port_combo.set("No ports available")
                self.port_map = {}
                return

            # Format ports: "COM3 - Intel SOL"
            display_values = []
            self.port_map = {}

            for device, description in ports:
                # Truncate long descriptions
                desc_short = description[:50] + "..." if len(description) > 50 else description
                display = f"{device} - {desc_short}"
                display_values.append(display)
                self.port_map[display] = device

            # Update dropdown
            self.port_combo.configure(values=display_values)
            if display_values:
                self.port_combo.set(display_values[0])

        except Exception as e:
            self.port_combo.configure(values=[f"Error: {str(e)}"])
            self.port_combo.set(f"Error: {str(e)}")
            self.port_map = {}

    def _on_port_selected(self, display_value: str):
        """Handle port selection from dropdown.

        Args:
            display_value: Display string from dropdown
        """
        device = self.port_map.get(display_value)
        if device and self.on_select_callback:
            self.on_select_callback(device)

    def get_selected_port(self) -> Optional[str]:
        """Get currently selected port device name.

        Returns:
            Port device name (e.g., "COM3", "/dev/ttyUSB0") or None if no valid port selected
        """
        display_value = self.port_combo.get()
        return self.port_map.get(display_value)

    def set_enabled(self, enabled: bool):
        """Enable or disable the port selector.

        Args:
            enabled: True to enable, False to disable
        """
        state = "readonly" if enabled else "disabled"
        self.port_combo.configure(state=state)
        self.refresh_button.configure(state="normal" if enabled else "disabled")
