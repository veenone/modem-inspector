"""Report generation dialog.

Provides modal dialog for selecting report format and output location.
"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from typing import Optional, List, Dict
from src.reports.csv_reporter import CSVReporter


class ReportDialog(ctk.CTkToplevel):
    """Modal dialog for report generation.

    Allows user to select format, output location, and generate reports.

    Example:
        >>> dialog = ReportDialog(parent, execution_results=results)
        >>> dialog.wait_window()
    """

    def __init__(self, parent, execution_results: List[Dict], **kwargs):
        """Initialize report dialog.

        Args:
            parent: Parent window
            execution_results: List of execution result dictionaries
            **kwargs: Additional CTkToplevel arguments
        """
        super().__init__(parent, **kwargs)

        self.execution_results = execution_results
        self.output_path: Optional[Path] = None

        self.title("Generate Report")
        self.geometry("450x300")
        self.resizable(False, False)

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
            text="Generate Inspection Report",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=20)

        # Content frame
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Format selection
        format_label = ctk.CTkLabel(content_frame, text="Report Format:")
        format_label.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.format_var = ctk.StringVar(value="CSV")
        format_dropdown = ctk.CTkComboBox(
            content_frame,
            values=["CSV", "HTML (Not implemented)", "JSON (Not implemented)"],
            variable=self.format_var,
            state="readonly"
        )
        format_dropdown.grid(row=0, column=1, sticky="ew", padx=10, pady=10)

        # Output path
        path_label = ctk.CTkLabel(content_frame, text="Output Path:")
        path_label.grid(row=1, column=0, sticky="w", padx=10, pady=10)

        self.path_entry = ctk.CTkEntry(content_frame, placeholder_text="Select output path...")
        self.path_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=10)

        browse_button = ctk.CTkButton(
            content_frame,
            text="Browse...",
            width=80,
            command=self._browse_output
        )
        browse_button.grid(row=1, column=2, sticky="e", padx=10, pady=10)

        # Info label
        self.info_label = ctk.CTkLabel(
            content_frame,
            text=f"Report will include {len(self.execution_results)} command results",
            text_color="gray"
        )
        self.info_label.grid(row=2, column=0, columnspan=3, pady=10)

        content_frame.grid_columnconfigure(1, weight=1)

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=20)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            command=self.destroy
        )
        cancel_button.pack(side="right", padx=5)

        self.generate_button = ctk.CTkButton(
            button_frame,
            text="Generate",
            width=100,
            command=self._generate_report
        )
        self.generate_button.pack(side="right", padx=5)

    def _browse_output(self):
        """Open file browser for output path selection."""
        default_filename = f"inspection_report.csv"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Report As",
            defaultextension=".csv",
            filetypes=[
                ("CSV Files", "*.csv"),
                ("All Files", "*.*")
            ],
            initialfile=default_filename
        )

        if file_path:
            self.output_path = Path(file_path)
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, str(self.output_path))

    def _generate_report(self):
        """Generate report and close dialog."""
        if not self.output_path:
            self.info_label.configure(
                text="Please select an output path",
                text_color="#E74C3C"
            )
            return

        try:
            # Convert execution results to CommandResponse objects (simplified)
            # In a full implementation, this would properly reconstruct CommandResponse objects
            from src.core.command_response import CommandResponse, CommandStatus

            responses = []
            for result in self.execution_results:
                if "response" in result:
                    responses.append(result["response"])

            # Generate CSV report
            reporter = CSVReporter()
            report_result = reporter.generate(responses, self.output_path)

            if report_result.success:
                self.info_label.configure(
                    text=f"Report saved successfully!",
                    text_color="#2FA572"
                )
                # Close dialog after short delay
                self.after(1000, self.destroy)
            else:
                self.info_label.configure(
                    text=f"Error: {report_result.error}",
                    text_color="#E74C3C"
                )

        except Exception as e:
            self.info_label.configure(
                text=f"Error generating report: {str(e)}",
                text_color="#E74C3C"
            )
