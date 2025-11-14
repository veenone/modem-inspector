"""Plugin management frame for GUI.

Provides interface for browsing, validating, testing, and creating plugins.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, List
from pathlib import Path
from src.core.plugin_manager import PluginManager
from src.core.plugin_validator import PluginValidator
from src.core.plugin_generator import PluginGenerator
from src.core.plugin import Plugin


class PluginManagerFrame(ctk.CTkFrame):
    """Frame for managing plugins.

    Provides interface for:
    - Browsing available plugins
    - Validating plugin files
    - Testing plugins against hardware
    - Creating new plugin templates
    """

    def __init__(self, master, plugin_manager: PluginManager, **kwargs):
        """Initialize plugin manager frame.

        Args:
            master: Parent widget
            plugin_manager: PluginManager instance
        """
        super().__init__(master, **kwargs)
        self.plugin_manager = plugin_manager
        self.plugin_validator = PluginValidator()
        self.plugin_generator = PluginGenerator()
        self.selected_plugin: Optional[Plugin] = None

        self._setup_ui()
        self._refresh_plugin_list()

    def _setup_ui(self):
        """Set up UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            self,
            text="Plugin Management",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, pady=(10, 20), padx=10, sticky="w")

        # Left panel - Plugin list
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(0, 10))
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(1, weight=1)

        # Plugin list header with refresh button
        list_header_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        list_header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        list_header_frame.grid_columnconfigure(0, weight=1)

        list_label = ctk.CTkLabel(
            list_header_frame,
            text="Available Plugins",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        list_label.grid(row=0, column=0, sticky="w")

        refresh_btn = ctk.CTkButton(
            list_header_frame,
            text="Refresh",
            width=80,
            command=self._refresh_plugin_list
        )
        refresh_btn.grid(row=0, column=1, padx=(10, 0))

        # Plugin listbox
        self.plugin_listbox = tk.Listbox(
            left_panel,
            selectmode=tk.SINGLE,
            font=("Courier New", 10)
        )
        self.plugin_listbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.plugin_listbox.bind("<<ListboxSelect>>", self._on_plugin_select)

        # Scrollbar for listbox
        scrollbar = ctk.CTkScrollbar(left_panel, command=self.plugin_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        self.plugin_listbox.config(yscrollcommand=scrollbar.set)

        # Right panel - Plugin details and actions
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(0, 10))
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        # Details section
        details_label = ctk.CTkLabel(
            right_panel,
            text="Plugin Details",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        details_label.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        # Details textbox
        self.details_text = ctk.CTkTextbox(right_panel, wrap="word", font=("Courier New", 10))
        self.details_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.details_text.configure(state="disabled")

        # Actions section
        actions_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        actions_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Action buttons
        validate_btn = ctk.CTkButton(
            actions_frame,
            text="Validate Plugin",
            command=self._validate_selected_plugin
        )
        validate_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        validate_file_btn = ctk.CTkButton(
            actions_frame,
            text="Validate File...",
            command=self._validate_file
        )
        validate_file_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        create_template_btn = ctk.CTkButton(
            actions_frame,
            text="Create Template...",
            command=self._create_template
        )
        create_template_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

    def _refresh_plugin_list(self):
        """Refresh the plugin list."""
        self.plugin_listbox.delete(0, tk.END)

        try:
            plugins = self.plugin_manager.get_all_plugins()

            if not plugins:
                self.plugin_listbox.insert(tk.END, "No plugins found")
                self._update_details("No plugins discovered.\n\n"
                                   "Plugins should be placed in src/plugins/")
                return

            # Add plugins to listbox
            for plugin in sorted(plugins, key=lambda p: f"{p.metadata.vendor}.{p.metadata.model}"):
                plugin_id = f"{plugin.metadata.vendor}.{plugin.metadata.model}"
                display_text = f"{plugin_id:30} v{plugin.metadata.version}"
                self.plugin_listbox.insert(tk.END, display_text)

            self._update_details(f"Discovered {len(plugins)} plugins.\n\n"
                               "Select a plugin to view details.")

        except Exception as e:
            self.plugin_listbox.insert(tk.END, f"Error: {str(e)}")
            self._update_details(f"Error discovering plugins:\n{str(e)}")

    def _on_plugin_select(self, event):
        """Handle plugin selection."""
        selection = self.plugin_listbox.curselection()
        if not selection:
            return

        selected_text = self.plugin_listbox.get(selection[0])
        if selected_text.startswith("No plugins") or selected_text.startswith("Error:"):
            return

        # Extract plugin ID from display text
        plugin_id = selected_text.split()[0]
        vendor, model = plugin_id.split('.')

        # Get plugin details
        plugin = self.plugin_manager.get_plugin(vendor, model)
        if plugin:
            self.selected_plugin = plugin
            self._display_plugin_details(plugin)

    def _display_plugin_details(self, plugin: Plugin):
        """Display details for selected plugin."""
        details = []

        # Metadata
        details.append("=== METADATA ===")
        details.append(f"Vendor:   {plugin.metadata.vendor}")
        details.append(f"Model:    {plugin.metadata.model}")
        details.append(f"Category: {plugin.metadata.category}")
        details.append(f"Version:  {plugin.metadata.version}")
        if plugin.metadata.author:
            details.append(f"Author:   {plugin.metadata.author}")
        details.append("")

        # Connection
        details.append("=== CONNECTION ===")
        details.append(f"Baud Rate:     {plugin.connection.default_baud}")
        details.append(f"Data Bits:     {plugin.connection.data_bits}")
        details.append(f"Parity:        {plugin.connection.parity}")
        details.append(f"Stop Bits:     {plugin.connection.stop_bits}")
        details.append(f"Flow Control:  {plugin.connection.flow_control}")
        details.append("")

        # Commands
        details.append("=== COMMANDS ===")
        total_commands = sum(len(cmds) for cmds in plugin.commands.values())
        details.append(f"Total: {total_commands} commands across {len(plugin.commands)} categories")
        details.append("")
        for category, commands in plugin.commands.items():
            details.append(f"{category.upper()} ({len(commands)} commands):")
            for cmd in commands[:3]:  # Show first 3 commands per category
                details.append(f"  - {cmd.cmd}")
            if len(commands) > 3:
                details.append(f"  ... and {len(commands) - 3} more")
            details.append("")

        # Parsers
        if plugin.parsers:
            details.append("=== PARSERS ===")
            details.append(f"Total: {len(plugin.parsers)} parsers")
            for name, parser in plugin.parsers.items():
                details.append(f"  - {name}: {parser.type.value}")
            details.append("")

        # Validation
        if plugin.validation:
            details.append("=== VALIDATION ===")
            if plugin.validation.required_responses:
                details.append(f"Required: {', '.join(plugin.validation.required_responses)}")
            if plugin.validation.expected_manufacturer:
                details.append(f"Expected Manufacturer: {plugin.validation.expected_manufacturer}")
            if plugin.validation.expected_model_pattern:
                details.append(f"Expected Model: {plugin.validation.expected_model_pattern}")

        self._update_details("\n".join(details))

    def _update_details(self, text: str):
        """Update details textbox."""
        self.details_text.configure(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert("1.0", text)
        self.details_text.configure(state="disabled")

    def _validate_selected_plugin(self):
        """Validate the currently selected plugin."""
        if not self.selected_plugin:
            messagebox.showwarning("No Selection", "Please select a plugin to validate.")
            return

        # Validate plugin
        warnings = self.plugin_validator.validate_plugin(self.selected_plugin)

        # Show results
        if not warnings:
            result = f"[OK] Plugin '{self.selected_plugin.metadata.vendor}.{self.selected_plugin.metadata.model}' is valid.\n\n"
            result += "Schema validation: PASSED\n"
            result += "Semantic validation: PASSED\n"
            result += "No warnings found."
            messagebox.showinfo("Validation Successful", result)
        else:
            result = f"Plugin '{self.selected_plugin.metadata.vendor}.{self.selected_plugin.metadata.model}' has warnings:\n\n"
            for i, warning in enumerate(warnings, 1):
                result += f"{i}. {warning}\n"
            messagebox.showwarning("Validation Warnings", result)

    def _validate_file(self):
        """Validate a plugin file."""
        file_path = filedialog.askopenfilename(
            title="Select Plugin File",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            initialdir="src/plugins"
        )

        if not file_path:
            return

        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                plugin_yaml = f.read()

            # Schema validation
            schema_valid, schema_errors = self.plugin_validator.validate_schema(plugin_yaml)

            if not schema_valid:
                result = f"[X] Schema validation FAILED for {Path(file_path).name}\n\n"
                result += "Errors:\n"
                for error in schema_errors:
                    result += f"  - {error}\n"
                messagebox.showerror("Validation Failed", result)
                return

            # Load plugin and do semantic validation
            plugin = self.plugin_manager.load_plugin(Path(file_path))
            warnings = self.plugin_validator.validate_plugin(plugin)

            if not warnings:
                result = f"[OK] Plugin file is valid: {Path(file_path).name}\n\n"
                result += "Schema validation: PASSED\n"
                result += "Semantic validation: PASSED"
                messagebox.showinfo("Validation Successful", result)
            else:
                result = f"Plugin file has warnings: {Path(file_path).name}\n\n"
                for i, warning in enumerate(warnings, 1):
                    result += f"{i}. {warning}\n"
                messagebox.showwarning("Validation Warnings", result)

        except Exception as e:
            messagebox.showerror("Validation Error", f"Error validating file:\n{str(e)}")

    def _create_template(self):
        """Create a new plugin template."""
        dialog = PluginTemplateDialog(self, self.plugin_generator)
        dialog.grab_set()  # Modal dialog


class PluginTemplateDialog(ctk.CTkToplevel):
    """Dialog for creating plugin templates."""

    def __init__(self, parent, plugin_generator: PluginGenerator):
        """Initialize template dialog.

        Args:
            parent: Parent widget
            plugin_generator: PluginGenerator instance
        """
        super().__init__(parent)
        self.plugin_generator = plugin_generator

        # Configure window
        self.title("Create Plugin Template")
        self.geometry("500x400")
        self.resizable(False, False)

        self._setup_ui()

    def _setup_ui(self):
        """Set up UI components."""
        # Configure grid
        self.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            self,
            text="Create New Plugin Template",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=2, pady=20, padx=20, sticky="w")

        # Vendor
        ctk.CTkLabel(self, text="Vendor:").grid(row=1, column=0, padx=20, pady=10, sticky="e")
        self.vendor_entry = ctk.CTkEntry(self, placeholder_text="e.g., quectel")
        self.vendor_entry.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # Model
        ctk.CTkLabel(self, text="Model:").grid(row=2, column=0, padx=20, pady=10, sticky="e")
        self.model_entry = ctk.CTkEntry(self, placeholder_text="e.g., ec200u")
        self.model_entry.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        # Category
        ctk.CTkLabel(self, text="Category:").grid(row=3, column=0, padx=20, pady=10, sticky="e")
        self.category_combo = ctk.CTkComboBox(
            self,
            values=["5g_highperf", "lte_cat1", "automotive", "iot", "nbiot", "other"],
            state="readonly"
        )
        self.category_combo.set("other")
        self.category_combo.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        # Author
        ctk.CTkLabel(self, text="Author (optional):").grid(row=4, column=0, padx=20, pady=10, sticky="e")
        self.author_entry = ctk.CTkEntry(self, placeholder_text="Your name")
        self.author_entry.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

        # Supported vendors info
        supported_vendors = self.plugin_generator.list_supported_vendors()
        info_text = f"Supported vendors with pre-defined commands:\n{', '.join(supported_vendors)}"
        info_label = ctk.CTkLabel(
            self,
            text=info_text,
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        info_label.grid(row=5, column=0, columnspan=2, padx=20, pady=10, sticky="w")

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=6, column=0, columnspan=2, pady=20, padx=20, sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy
        )
        cancel_btn.grid(row=0, column=0, padx=5, sticky="ew")

        create_btn = ctk.CTkButton(
            button_frame,
            text="Create Template",
            command=self._create_template
        )
        create_btn.grid(row=0, column=1, padx=5, sticky="ew")

    def _create_template(self):
        """Create the template."""
        vendor = self.vendor_entry.get().strip().lower()
        model = self.model_entry.get().strip().lower()
        category = self.category_combo.get()
        author = self.author_entry.get().strip() or None

        # Validate inputs
        if not vendor or not model:
            messagebox.showerror("Invalid Input", "Vendor and model are required.")
            return

        # Ask for output location
        output_path = filedialog.asksaveasfilename(
            title="Save Plugin Template",
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            initialdir="src/plugins",
            initialfile=f"{vendor}_{model}.yaml"
        )

        if not output_path:
            return

        try:
            # Generate template
            yaml_content = self.plugin_generator.generate_template(
                vendor=vendor,
                model=model,
                category=category,
                output_path=Path(output_path),
                author=author,
                overwrite=True
            )

            messagebox.showinfo(
                "Template Created",
                f"Plugin template created successfully:\n\n{output_path}\n\n"
                "The template includes:\n"
                "- Universal 3GPP commands\n"
                "- Vendor-specific commands (if available)\n"
                "- Parser examples\n"
                "- Validation rules\n\n"
                "Customize the template and validate before use."
            )
            self.destroy()

        except Exception as e:
            messagebox.showerror("Template Creation Failed", f"Error creating template:\n{str(e)}")
