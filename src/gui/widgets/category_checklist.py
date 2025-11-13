"""Category checklist widget for command category selection.

Provides a scrollable list of checkboxes for selecting command categories
with Select All/Deselect All functionality and Quick Scan filter.
"""

import customtkinter as ctk
from typing import Dict, List, Callable, Optional


class CategoryChecklist(ctk.CTkScrollableFrame):
    """Scrollable checklist for command category selection.

    Displays checkboxes for each command category with command counts,
    Select All/Deselect All buttons, and Quick Scan Only filter.

    Example:
        >>> categories = {
        ...     "basic": 5,
        ...     "network": 10,
        ...     "sim": 8
        ... }
        >>> checklist = CategoryChecklist(parent, categories=categories)
        >>> selected = checklist.get_selected_categories()
        >>> print(selected)  # ['basic', 'network']
    """

    def __init__(
        self,
        master,
        categories: Optional[Dict[str, int]] = None,
        on_change: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """Initialize category checklist.

        Args:
            master: Parent widget
            categories: Dict mapping category name to command count
            on_change: Callback when selection changes
            **kwargs: Additional CTkScrollableFrame arguments
        """
        # Set default height if not provided
        if 'height' not in kwargs:
            kwargs['height'] = 200

        super().__init__(master, **kwargs)

        self.on_change_callback = on_change
        self.checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.category_counts: Dict[str, int] = {}

        # Configure grid for the scrollable frame
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Make checkboxes frame expandable

        # Control buttons frame
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Select All button
        self.select_all_button = ctk.CTkButton(
            self.controls_frame,
            text="Select All",
            width=100,
            command=self.select_all
        )
        self.select_all_button.grid(row=0, column=0, padx=(0, 5))

        # Deselect All button
        self.deselect_all_button = ctk.CTkButton(
            self.controls_frame,
            text="Deselect All",
            width=100,
            command=self.deselect_all
        )
        self.deselect_all_button.grid(row=0, column=1)

        # Quick Scan Only checkbox
        self.quick_scan_var = ctk.BooleanVar(value=False)
        self.quick_scan_checkbox = ctk.CTkCheckBox(
            self.controls_frame,
            text="Quick Scan Only",
            variable=self.quick_scan_var,
            command=self._on_quick_scan_toggled
        )
        self.quick_scan_checkbox.grid(row=0, column=2, padx=(20, 0))

        # Separator
        self.separator = ctk.CTkFrame(self, height=2)
        self.separator.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        # Checkboxes container frame
        self.checkboxes_frame = ctk.CTkFrame(self)
        self.checkboxes_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.checkboxes_frame.grid_columnconfigure(0, weight=1)

        # Load initial categories if provided
        if categories:
            self.set_categories(categories)

    def set_categories(self, categories: Dict[str, int], quick_categories: Optional[List[str]] = None):
        """Set available categories with command counts.

        Args:
            categories: Dict mapping category name to total command count
            quick_categories: Optional list of categories marked as "quick"

        Example:
            >>> checklist.set_categories(
            ...     {"basic": 5, "network": 10},
            ...     quick_categories=["basic"]
            ... )
        """
        # Clear existing checkboxes
        for checkbox in self.checkboxes.values():
            checkbox.destroy()
        self.checkboxes.clear()

        self.category_counts = categories.copy()
        self.quick_categories = set(quick_categories or [])

        # Create checkbox for each category
        for idx, (category, count) in enumerate(sorted(categories.items())):
            # Format label with count
            quick_marker = " ⚡" if category in self.quick_categories else ""
            label = f"{category.replace('_', ' ').title()} ({count} commands){quick_marker}"

            var = ctk.BooleanVar(value=True)  # Default: all selected
            checkbox = ctk.CTkCheckBox(
                self.checkboxes_frame,
                text=label,
                variable=var,
                command=self._on_selection_changed
            )
            checkbox.grid(row=idx, column=0, sticky="w", padx=10, pady=5)

            self.checkboxes[category] = checkbox
            checkbox._var = var  # Store variable reference

    def get_selected_categories(self) -> List[str]:
        """Get list of selected category names.

        Returns:
            List of selected category names

        Example:
            >>> selected = checklist.get_selected_categories()
            >>> print(selected)  # ['basic', 'network']
        """
        selected = []
        for category, checkbox in self.checkboxes.items():
            if checkbox._var.get():
                selected.append(category)
        return selected

    def select_all(self):
        """Select all categories."""
        for checkbox in self.checkboxes.values():
            checkbox._var.set(True)
        self._on_selection_changed()

    def deselect_all(self):
        """Deselect all categories."""
        for checkbox in self.checkboxes.values():
            checkbox._var.set(False)
        self._on_selection_changed()

    def is_quick_scan_only(self) -> bool:
        """Check if Quick Scan Only mode is enabled.

        Returns:
            True if quick scan mode is enabled
        """
        return self.quick_scan_var.get()

    def _on_quick_scan_toggled(self):
        """Handle Quick Scan Only checkbox toggle."""
        quick_only = self.quick_scan_var.get()

        if quick_only:
            # Select only quick categories, deselect others
            for category, checkbox in self.checkboxes.items():
                is_quick = category in self.quick_categories
                checkbox._var.set(is_quick)
        else:
            # Re-enable all categories
            self.select_all()

        self._on_selection_changed()

    def _on_selection_changed(self):
        """Handle checkbox selection change."""
        if self.on_change_callback:
            self.on_change_callback()

    def get_selected_count(self) -> int:
        """Get total number of commands in selected categories.

        Returns:
            Total command count for selected categories
        """
        selected = self.get_selected_categories()
        return sum(self.category_counts.get(cat, 0) for cat in selected)

    def set_enabled(self, enabled: bool):
        """Enable or disable all checkboxes.

        Args:
            enabled: True to enable, False to disable
        """
        state = "normal" if enabled else "disabled"
        for checkbox in self.checkboxes.values():
            checkbox.configure(state=state)
        self.select_all_button.configure(state=state)
        self.deselect_all_button.configure(state=state)
        self.quick_scan_checkbox.configure(state=state)
