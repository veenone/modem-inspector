"""Help dialog for built-in documentation.

Provides modal dialog displaying application help and usage instructions.
"""

import customtkinter as ctk


class HelpDialog(ctk.CTkToplevel):
    """Modal dialog for application help.

    Displays help content with searchable table of contents.

    Example:
        >>> dialog = HelpDialog(parent)
        >>> dialog.wait_window()
    """

    HELP_CONTENT = """
# Modem Inspector - Help Guide

## Getting Started

### 1. Connect to Serial Port
- Select a serial port from the dropdown in the Connection section
- Click "Connect" to establish connection
- Status indicator will turn green when connected

### 2. Select Plugin
- Use "Auto-Detect" to automatically identify your modem
  (requires active connection)
- Or manually select from the plugin dropdown
- Plugin info will display showing vendor, model, and command count

### 3. Select Command Categories
- Choose which command categories to execute
- Use "Quick Scan Only" for faster inspection with essential commands
- Command count updates based on your selection

### 4. Run Inspection
- Click "Start Inspection" to begin command execution
- Progress bar shows current status
- Commands and responses appear in real-time in the log
- Use "Cancel" to stop gracefully after current command

### 5. View Results
- Results are organized by command category in tabs
- Use search box to find specific responses
- Click "Export Report" to save results to CSV file

## Tips

- **Port Discovery**: Use the refresh button (⟳) to update available ports
- **Quick Scan**: Enable for faster inspection with only essential commands
- **Command Log**: Color-coded (blue=command, green=success, red=error)
- **Elapsed Time**: Shows progress and estimated time remaining

## Keyboard Shortcuts

- Ctrl+S: Open Settings
- Ctrl+Q: Quit Application
- F1: Open this Help dialog

## Troubleshooting

**Port won't connect?**
- Ensure modem is powered on and connected
- Check that no other application is using the port
- Try refreshing the port list

**Auto-detect fails?**
- Verify modem responds to AT+CGMI and AT+CGMM commands
- Try manual plugin selection
- Check plugin matches your modem model

**Commands timeout?**
- Increase timeout in Settings
- Check serial cable connection
- Verify baud rate matches modem configuration

## Support

For more information, visit the project repository or consult the README.md file.
"""

    def __init__(self, parent, **kwargs):
        """Initialize help dialog.

        Args:
            parent: Parent window
            **kwargs: Additional CTkToplevel arguments
        """
        super().__init__(parent, **kwargs)

        self.title("Help - Modem Inspector")
        self.geometry("700x600")

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self._setup_ui()

    def _setup_ui(self):
        """Set up UI components."""
        # Title
        title_label = ctk.CTkLabel(
            self,
            text="Modem Inspector - Help",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=15)

        # Help content in textbox
        help_textbox = ctk.CTkTextbox(self, wrap="word")
        help_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Insert help content
        help_textbox.insert("1.0", self.HELP_CONTENT)
        help_textbox.configure(state="disabled")

        # Close button
        close_button = ctk.CTkButton(
            self,
            text="Close",
            width=100,
            command=self.destroy
        )
        close_button.pack(pady=(0, 15))
