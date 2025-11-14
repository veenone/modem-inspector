"""Report generation dialog.

Provides modal dialog for selecting report format and output location.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import os
import subprocess
import platform
from src.reports.csv_reporter import CSVReporter
from src.gui.utils.threading_utils import WorkerThread


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
        self.generated_file: Optional[Path] = None

        self.title("Generate Report")
        self.geometry("500x450")
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
            values=["CSV", "HTML (Not implemented)", "JSON (Not implemented)", "Markdown (Not implemented)"],
            variable=self.format_var,
            state="readonly"
        )
        format_dropdown.grid(row=0, column=1, columnspan=2, sticky="ew", padx=10, pady=10)

        # Format options
        options_label = ctk.CTkLabel(content_frame, text="Options:")
        options_label.grid(row=1, column=0, sticky="nw", padx=10, pady=10)

        options_inner_frame = ctk.CTkFrame(content_frame)
        options_inner_frame.grid(row=1, column=1, columnspan=2, sticky="ew", padx=10, pady=10)

        self.include_raw_var = ctk.BooleanVar(value=True)
        include_raw_checkbox = ctk.CTkCheckBox(
            options_inner_frame,
            text="Include raw responses",
            variable=self.include_raw_var
        )
        include_raw_checkbox.pack(anchor="w", padx=5, pady=5)

        self.include_timestamps_var = ctk.BooleanVar(value=True)
        include_timestamps_checkbox = ctk.CTkCheckBox(
            options_inner_frame,
            text="Include timestamps",
            variable=self.include_timestamps_var
        )
        include_timestamps_checkbox.pack(anchor="w", padx=5, pady=5)

        # Output path
        path_label = ctk.CTkLabel(content_frame, text="Output Path:")
        path_label.grid(row=2, column=0, sticky="w", padx=10, pady=10)

        self.path_entry = ctk.CTkEntry(content_frame, placeholder_text="Select output path...")
        self.path_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=10)

        # Suggest default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"inspection_report_{timestamp}.csv"
        self.path_entry.insert(0, str(Path("./reports") / default_filename))

        browse_button = ctk.CTkButton(
            content_frame,
            text="Browse",
            width=80,
            command=self._browse_output
        )
        browse_button.grid(row=2, column=2, sticky="e", padx=10, pady=10)

        # Progress bar (initially hidden)
        self.progress_bar = ctk.CTkProgressBar(content_frame)
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()  # Hide initially

        # Info label
        self.info_label = ctk.CTkLabel(
            content_frame,
            text=f"Report will include {len(self.execution_results)} command results",
            text_color="gray"
        )
        self.info_label.grid(row=4, column=0, columnspan=3, pady=10)

        content_frame.grid_columnconfigure(1, weight=1)

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=20)

        self.open_report_button = ctk.CTkButton(
            button_frame,
            text="Open Report",
            width=120,
            command=self._open_report,
            state="disabled"
        )
        self.open_report_button.pack(side="left", padx=5)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Close",
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"inspection_report_{timestamp}.csv"

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

    def _open_report(self):
        """Open the generated report file in default application."""
        if not self.generated_file or not self.generated_file.exists():
            messagebox.showerror("Error", "Report file not found.")
            return

        try:
            # Open in default application based on platform
            if platform.system() == 'Windows':
                os.startfile(self.generated_file)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(self.generated_file)], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', str(self.generated_file)], check=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open report: {e}")

    def _generate_report(self):
        """Generate report in background thread."""
        output_path_str = self.path_entry.get().strip()
        if not output_path_str:
            self.info_label.configure(
                text="Please select an output path",
                text_color="#E74C3C"
            )
            return

        self.output_path = Path(output_path_str)

        # Check for file overwrite
        if self.output_path.exists():
            if not messagebox.askyesno("Overwrite File",
                                       f"File '{self.output_path.name}' already exists.\n\nDo you want to overwrite it?"):
                return

        # Disable generate button during generation
        self.generate_button.configure(state="disabled", text="Generating...")
        self.progress_bar.grid()  # Show progress bar
        self.progress_bar.set(0.3)  # Indeterminate progress

        # Generate in background thread
        def generate_task():
            """Background task for report generation."""
            try:
                # Convert execution results to CommandResponse objects
                from src.core.command_response import CommandResponse

                responses = []
                for result in self.execution_results:
                    if "response" in result:
                        responses.append(result["response"])

                # Generate CSV report
                reporter = CSVReporter()
                report_result = reporter.generate(responses, self.output_path)

                return report_result

            except Exception as e:
                # Return error result
                from dataclasses import dataclass
                @dataclass
                class ErrorResult:
                    success: bool = False
                    error: str = str(e)
                return ErrorResult()

        # Create worker thread
        worker = WorkerThread(target=generate_task)
        worker.start()

        # Poll for completion
        def check_completion():
            if worker.is_alive():
                # Still working, check again
                self.progress_bar.set((self.progress_bar.get() + 0.1) % 1.0)  # Animate
                self.after(100, check_completion)
            else:
                # Completed
                result = worker.result
                self.progress_bar.grid_remove()  # Hide progress bar
                self.generate_button.configure(state="normal", text="Generate")

                if result and result.success:
                    # Get file size
                    file_size = self.output_path.stat().st_size
                    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB"

                    self.info_label.configure(
                        text=f"✓ Report saved successfully! ({size_str})",
                        text_color="#2FA572"
                    )
                    self.generated_file = self.output_path
                    self.open_report_button.configure(state="normal")
                else:
                    error_msg = result.error if result else "Unknown error"
                    self.info_label.configure(
                        text=f"Error: {error_msg}",
                        text_color="#E74C3C"
                    )

        # Start checking
        self.after(100, check_completion)
