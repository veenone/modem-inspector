"""Results frame for displaying inspection results in tabbed interface.

Provides tabbed results display organized by command categories with search,
pagination, and export functionality.
"""

import customtkinter as ctk
import tkinter as tk
from typing import List, Dict, Optional, Callable
from src.core.command_response import CommandResponse


class ResultsFrame(ctk.CTkFrame):
    """Frame for displaying inspection results.

    Displays execution results organized by command category in tabs with
    search functionality, copy-to-clipboard, and export options.

    Example:
        >>> def on_export():
        ...     print("Export clicked")
        ...
        >>> frame = ResultsFrame(parent, on_export=on_export)
        >>> frame.display_results(execution_results)
    """

    def __init__(
        self,
        master,
        on_export: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """Initialize results frame.

        Args:
            master: Parent widget
            on_export: Callback when Export button clicked
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(master, **kwargs)

        self.on_export_callback = on_export
        self.results_data: List[Dict] = []
        self.current_search = ""
        self.results_by_category: Dict[str, List[Dict]] = {}

        self._setup_ui()

    def _setup_ui(self):
        """Set up UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Title and controls frame
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(1, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="Inspection Results",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.export_button = ctk.CTkButton(
            header_frame,
            text="Export Report",
            width=120,
            command=self._on_export_clicked,
            state="disabled"
        )
        self.export_button.grid(row=0, column=1, sticky="e", padx=10, pady=10)

        # Search frame
        search_frame = ctk.CTkFrame(self)
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        search_frame.grid_columnconfigure(1, weight=1)

        search_label = ctk.CTkLabel(search_frame, text="Search:", width=60)
        search_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search in results...")
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        self.clear_search_button = ctk.CTkButton(
            search_frame,
            text="Clear",
            width=60,
            command=self._clear_search
        )
        self.clear_search_button.grid(row=0, column=2, sticky="e", padx=10, pady=5)

        # Tab view for categories
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))

        # Initial empty state
        self._show_empty_state()

    def _show_empty_state(self):
        """Show empty state message."""
        # Add "No Results" tab
        if "No Results" not in self.tabview._tab_dict:
            self.tabview.add("No Results")
            empty_label = ctk.CTkLabel(
                self.tabview.tab("No Results"),
                text="No results to display.\nRun an inspection to see results here.",
                font=ctk.CTkFont(size=13),
                text_color="gray"
            )
            empty_label.pack(expand=True)

    def display_results(self, results: List[Dict]):
        """Display inspection results.

        Args:
            results: List of result dictionaries from execution

        Example:
            >>> results = [
            ...     {"command": "AT", "response": response_obj, "category": "basic"},
            ...     {"command": "AT+CGMI", "response": response_obj, "category": "basic"}
            ... ]
            >>> frame.display_results(results)
        """
        self.results_data = results

        if not results:
            self._show_empty_state()
            self.export_button.configure(state="disabled")
            return

        # Enable export
        self.export_button.configure(state="normal")

        # Organize by category
        self.results_by_category = {}
        for result in results:
            category = result.get("category", "unknown")
            if category not in self.results_by_category:
                self.results_by_category[category] = []
            self.results_by_category[category].append(result)

        # Clear existing tabs
        for tab_name in list(self.tabview._tab_dict.keys()):
            self.tabview.delete(tab_name)

        # Create tab for each category
        for category, cat_results in self.results_by_category.items():
            tab_name = f"{category.title()} ({len(cat_results)})"
            self.tabview.add(tab_name)
            self._create_category_tab(category, cat_results)

        # Show first tab
        if self.results_by_category:
            first_category = list(self.results_by_category.keys())[0]
            first_tab = f"{first_category.title()} ({len(self.results_by_category[first_category])})"
            self.tabview.set(first_tab)

    def _create_category_tab(self, category: str, results: List[Dict]):
        """Create results tab for a category.

        Args:
            category: Category name
            results: Results for this category
        """
        tab_name = f"{category.title()} ({len(results)})"
        tab_frame = self.tabview.tab(tab_name)

        # Create scrollable text widget for results
        results_text = ctk.CTkTextbox(tab_frame, wrap="word")
        results_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure tags for highlighting
        results_text._textbox.tag_config("command", foreground="#3B8ED0", font=("Courier", 11, "bold"))
        results_text._textbox.tag_config("success", foreground="#2FA572")
        results_text._textbox.tag_config("error", foreground="#E74C3C")
        results_text._textbox.tag_config("highlight", background="#FFFF00", foreground="#000000")
        results_text._textbox.tag_config("response", font=("Courier", 10))

        # Display results
        results_text.configure(state="normal")

        for idx, result in enumerate(results):
            command = result.get("command", "Unknown")
            description = result.get("description", "")

            # Command header
            header = f"\n{'='*60}\n" if idx > 0 else ""
            results_text.insert("end", header)
            results_text.insert("end", f"Command: {command}\n", "command")

            if description:
                results_text.insert("end", f"Description: {description}\n")

            # Status and timing
            if "response" in result:
                response = result["response"]
                elapsed = result.get("elapsed", 0)

                status_tag = "success" if response.is_success() else "error"
                status_text = "✓ SUCCESS" if response.is_success() else "✗ FAILED"
                results_text.insert("end", f"Status: {status_text}\n", status_tag)
                results_text.insert("end", f"Time: {elapsed:.3f}s\n")

                # Response data
                if response.data:
                    results_text.insert("end", "\nResponse:\n")
                    results_text.insert("end", f"{response.data}\n", "response")
                elif response.error:
                    results_text.insert("end", "\nError:\n", "error")
                    results_text.insert("end", f"{response.error}\n", "response")

            elif "error" in result:
                results_text.insert("end", f"Status: ✗ EXCEPTION\n", "error")
                results_text.insert("end", f"Error: {result['error']}\n", "error")

        results_text.configure(state="disabled")

        # Store reference for search
        results_text._category = category

    def _on_search_changed(self, event=None):
        """Handle search entry change."""
        search_term = self.search_entry.get().lower()

        if not search_term:
            self._clear_highlights()
            return

        self.current_search = search_term
        self._highlight_search()

    def _highlight_search(self):
        """Highlight search term in all tabs."""
        if not self.current_search:
            return

        # Get current tab
        current_tab = self.tabview.get()
        if not current_tab or current_tab == "No Results":
            return

        # Find the textbox in current tab
        tab_frame = self.tabview.tab(current_tab)
        for widget in tab_frame.winfo_children():
            if isinstance(widget, ctk.CTkTextbox):
                text_widget = widget._textbox

                # Remove previous highlights
                text_widget.tag_remove("highlight", "1.0", "end")

                # Search and highlight
                start_pos = "1.0"
                while True:
                    start_pos = text_widget.search(
                        self.current_search,
                        start_pos,
                        stopindex="end",
                        nocase=True
                    )

                    if not start_pos:
                        break

                    end_pos = f"{start_pos}+{len(self.current_search)}c"
                    text_widget.tag_add("highlight", start_pos, end_pos)
                    start_pos = end_pos

    def _clear_highlights(self):
        """Clear search highlights from all tabs."""
        self.current_search = ""

        for tab_name in self.tabview._tab_dict.keys():
            if tab_name == "No Results":
                continue

            tab_frame = self.tabview.tab(tab_name)
            for widget in tab_frame.winfo_children():
                if isinstance(widget, ctk.CTkTextbox):
                    widget._textbox.tag_remove("highlight", "1.0", "end")

    def _clear_search(self):
        """Clear search entry and highlights."""
        self.search_entry.delete(0, "end")
        self._clear_highlights()

    def _on_export_clicked(self):
        """Handle Export button click."""
        if self.on_export_callback:
            self.on_export_callback()

    def get_results(self) -> List[Dict]:
        """Get current results data.

        Returns:
            List of result dictionaries
        """
        return self.results_data

    def clear_results(self):
        """Clear all results."""
        self.results_data = []
        self.results_by_category = {}

        # Clear tabs
        for tab_name in list(self.tabview._tab_dict.keys()):
            self.tabview.delete(tab_name)

        self._show_empty_state()
        self.export_button.configure(state="disabled")
