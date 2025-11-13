"""Plugin frame for plugin selection and command category management.

Provides plugin auto-detection, manual selection, and command category filtering.
"""

import customtkinter as ctk
from typing import Optional, Callable, List
from src.gui.widgets import CategoryChecklist
from src.gui.utils.threading_utils import WorkerThread
from src.core.plugin_manager import PluginManager
from src.core.at_executor import ATExecutor
from src.core.plugin import Plugin
from src.core.exceptions import PluginNotFoundError


class PluginFrame(ctk.CTkFrame):
    """Frame for plugin selection and configuration.

    Supports both automatic plugin detection via AT commands and manual
    selection from available plugins. Displays plugin information and
    command category selection.

    Example:
        >>> def on_plugin_selected(plugin: Plugin):
        ...     print(f"Selected: {plugin.metadata.vendor} {plugin.metadata.model}")
        ...
        >>> frame = PluginFrame(
        ...     parent,
        ...     plugin_manager=manager,
        ...     on_plugin_selected=on_plugin_selected
        ... )
    """

    def __init__(
        self,
        master,
        plugin_manager: PluginManager,
        category_checklist: "CategoryChecklist",
        on_plugin_selected: Optional[Callable[[Plugin], None]] = None,
        **kwargs
    ):
        """Initialize plugin frame.

        Args:
            master: Parent widget
            plugin_manager: PluginManager instance for plugin operations
            category_checklist: External CategoryChecklist widget to manage
            on_plugin_selected: Callback when plugin selected (receives Plugin)
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(master, **kwargs)

        self.plugin_manager = plugin_manager
        self.category_checklist = category_checklist
        self.on_plugin_selected_callback = on_plugin_selected
        self.current_plugin: Optional[Plugin] = None
        self.at_executor: Optional[ATExecutor] = None
        self.auto_detect_worker: Optional[WorkerThread] = None

        self._setup_ui()
        self._load_plugins()

    def _setup_ui(self):
        """Set up UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=0)  # Label column
        self.grid_columnconfigure(1, weight=1)  # Widget column
        self.grid_columnconfigure(2, weight=0)  # Button column

        # Title label
        title_label = ctk.CTkLabel(
            self,
            text="Plugin Selection",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 15))

        # Auto-detect row
        autodetect_label = ctk.CTkLabel(self, text="Auto-Detect:", width=80, anchor="w")
        autodetect_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

        self.autodetect_status = ctk.CTkLabel(
            self,
            text="Connect to port to enable auto-detection",
            text_color="gray"
        )
        self.autodetect_status.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        self.autodetect_button = ctk.CTkButton(
            self,
            text="Auto-Detect",
            width=120,
            command=self._on_autodetect_clicked,
            state="disabled"
        )
        self.autodetect_button.grid(row=1, column=2, sticky="e", padx=10, pady=5)

        # Manual selection row
        manual_label = ctk.CTkLabel(self, text="Manual:", width=80, anchor="w")
        manual_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)

        self.plugin_dropdown = ctk.CTkComboBox(
            self,
            values=["Loading plugins..."],
            command=self._on_plugin_manually_selected,
            state="readonly"
        )
        self.plugin_dropdown.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

        # Plugin info frame
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        self.info_frame.grid_columnconfigure(1, weight=1)

        self.vendor_label = ctk.CTkLabel(self.info_frame, text="Vendor: -", anchor="w")
        self.vendor_label.grid(row=0, column=0, sticky="w", padx=10, pady=2)

        self.model_label = ctk.CTkLabel(self.info_frame, text="Model: -", anchor="w")
        self.model_label.grid(row=0, column=1, sticky="w", padx=10, pady=2)

        self.version_label = ctk.CTkLabel(self.info_frame, text="Version: -", anchor="w")
        self.version_label.grid(row=1, column=0, sticky="w", padx=10, pady=2)

        self.command_count_label = ctk.CTkLabel(self.info_frame, text="Commands: -", anchor="w")
        self.command_count_label.grid(row=1, column=1, sticky="w", padx=10, pady=2)

    def _load_plugins(self):
        """Load available plugins into dropdown."""
        try:
            plugins = self.plugin_manager.discover_plugins()

            if not plugins:
                self.plugin_dropdown.configure(values=["No plugins available"])
                self.plugin_dropdown.set("No plugins available")
                return

            # Format: "Quectel EC200U (v1.0.0)"
            plugin_displays = []
            self.plugin_map = {}  # Maps display string to (vendor, model)

            for plugin in plugins:
                display = f"{plugin.metadata.vendor.title()} {plugin.metadata.model.upper()} (v{plugin.metadata.version})"
                plugin_displays.append(display)
                self.plugin_map[display] = (plugin.metadata.vendor, plugin.metadata.model)

            self.plugin_dropdown.configure(values=plugin_displays)
            if plugin_displays:
                self.plugin_dropdown.set("Select a plugin...")

        except Exception as e:
            self.plugin_dropdown.configure(values=[f"Error: {str(e)}"])
            self.plugin_dropdown.set(f"Error: {str(e)}")

    def set_at_executor(self, at_executor: Optional[ATExecutor]):
        """Set ATExecutor for auto-detection.

        Args:
            at_executor: ATExecutor instance or None to disable auto-detect
        """
        self.at_executor = at_executor

        if at_executor:
            self.autodetect_button.configure(state="normal")
            self.autodetect_status.configure(
                text="Ready for auto-detection",
                text_color=("gray10", "gray90")
            )
        else:
            self.autodetect_button.configure(state="disabled")
            self.autodetect_status.configure(
                text="Connect to port to enable auto-detection",
                text_color="gray"
            )

    def _on_autodetect_clicked(self):
        """Handle Auto-Detect button click."""
        if not self.at_executor:
            return

        # Disable button during detection
        self.autodetect_button.configure(state="disabled")
        self.autodetect_status.configure(text="Detecting...", text_color="#FFBF00")

        # Run auto-detection in background thread
        self.auto_detect_worker = WorkerThread(
            target=self._autodetect_worker,
            name="PluginAutoDetect"
        )
        self.auto_detect_worker.start()

        # Poll for completion
        self.after(100, self._check_autodetect_progress)

    def _autodetect_worker(self, progress_queue):
        """Background worker for plugin auto-detection.

        Args:
            progress_queue: Queue for progress updates
        """
        try:
            # Execute manufacturer command
            progress_queue.put(("status", "Querying manufacturer..."))
            cgmi_response = self.at_executor.execute_command("AT+CGMI")

            if not cgmi_response.is_success():
                progress_queue.put(("error", "Failed to get manufacturer info"))
                return

            manufacturer = cgmi_response.data.strip() if cgmi_response.data else ""

            # Execute model command
            progress_queue.put(("status", "Querying model..."))
            cgmm_response = self.at_executor.execute_command("AT+CGMM")

            if not cgmm_response.is_success():
                progress_queue.put(("error", "Failed to get model info"))
                return

            model = cgmm_response.data.strip() if cgmm_response.data else ""

            # Try to match plugin
            progress_queue.put(("status", f"Matching plugin for {manufacturer} {model}..."))
            plugin = self.plugin_manager.select_plugin_auto(manufacturer, model)

            if plugin:
                progress_queue.put(("success", plugin))
            else:
                progress_queue.put(("not_found", f"{manufacturer} {model}"))

        except Exception as e:
            progress_queue.put(("error", str(e)))

    def _check_autodetect_progress(self):
        """Check auto-detection progress."""
        if not self.auto_detect_worker:
            return

        msg = self.auto_detect_worker.get_progress(timeout=0)

        if msg:
            msg_type, value = msg

            if msg_type == "status":
                self.autodetect_status.configure(text=value, text_color="#3B8ED0")
                self.after(100, self._check_autodetect_progress)

            elif msg_type == "success":
                plugin = value
                self._select_plugin(plugin)
                self.autodetect_status.configure(
                    text=f"Detected: {plugin.metadata.vendor} {plugin.metadata.model}",
                    text_color="#2FA572"
                )
                self.autodetect_button.configure(state="normal")

            elif msg_type == "not_found":
                device_info = value
                self.autodetect_status.configure(
                    text=f"No plugin found for {device_info}",
                    text_color="#E74C3C"
                )
                self.autodetect_button.configure(state="normal")

            elif msg_type == "error":
                self.autodetect_status.configure(
                    text=f"Error: {value}",
                    text_color="#E74C3C"
                )
                self.autodetect_button.configure(state="normal")

        elif self.auto_detect_worker.is_alive():
            self.after(100, self._check_autodetect_progress)
        else:
            # Thread finished without message
            self.autodetect_button.configure(state="normal")

    def _on_plugin_manually_selected(self, display_value: str):
        """Handle manual plugin selection from dropdown.

        Args:
            display_value: Display string from dropdown
        """
        vendor_model = self.plugin_map.get(display_value)
        if not vendor_model:
            return

        vendor, model = vendor_model

        try:
            plugin = self.plugin_manager.get_plugin(vendor, model)
            self._select_plugin(plugin)
        except PluginNotFoundError as e:
            self.autodetect_status.configure(
                text=f"Error: {str(e)}",
                text_color="#E74C3C"
            )

    def _select_plugin(self, plugin: Plugin):
        """Select and display plugin.

        Args:
            plugin: Selected Plugin instance
        """
        self.current_plugin = plugin

        # Update plugin info
        self.vendor_label.configure(text=f"Vendor: {plugin.metadata.vendor.title()}")
        self.model_label.configure(text=f"Model: {plugin.metadata.model.upper()}")
        self.version_label.configure(text=f"Version: {plugin.metadata.version}")

        # Get command categories with counts
        # plugin.commands is a dict: {category_name: [CommandDefinition, ...]}
        categories = {}
        quick_categories = []

        for category, command_list in plugin.commands.items():
            # Count total commands in this category
            categories[category] = len(command_list)

            # Check if any commands in this category are marked as quick
            for cmd in command_list:
                if cmd.quick and category not in quick_categories:
                    quick_categories.append(category)
                    break

        # Update category checklist
        self.category_checklist.set_categories(categories, quick_categories)

        # Update command count
        self._update_command_count()

        # Call callback
        if self.on_plugin_selected_callback:
            self.on_plugin_selected_callback(plugin)

    def _update_command_count(self):
        """Update displayed command count based on selected categories."""
        if not self.current_plugin:
            return

        selected_count = self.category_checklist.get_selected_count()

        # Calculate total command count from all categories
        total_count = sum(len(cmd_list) for cmd_list in self.current_plugin.commands.values())

        self.command_count_label.configure(
            text=f"Commands: {selected_count} / {total_count} selected"
        )

    def get_selected_plugin(self) -> Optional[Plugin]:
        """Get currently selected plugin.

        Returns:
            Plugin instance or None if no plugin selected
        """
        return self.current_plugin

    def set_enabled(self, enabled: bool):
        """Enable or disable plugin selection controls.

        Args:
            enabled: True to enable, False to disable
        """
        state = "readonly" if enabled else "disabled"
        self.plugin_dropdown.configure(state=state)

        # Auto-detect only enabled if AT executor is set
        if enabled and self.at_executor:
            self.autodetect_button.configure(state="normal")
        else:
            self.autodetect_button.configure(state="disabled")
