"""Report generation dialog.

Provides modal dialog for selecting report format and output location.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import subprocess
import platform
from src.reports.report_generator import ReportGenerator
from src.gui.utils.threading_utils import WorkerThread


class ReportDialog(ctk.CTkToplevel):
    """Modal dialog for report generation.

    Allows user to select format, output location, and generate reports.

    Example:
        >>> dialog = ReportDialog(parent, execution_results=results)
        >>> dialog.wait_window()
    """

    def __init__(self, parent, execution_results: List[Dict], modem_features: Any = None, **kwargs):
        """Initialize report dialog.

        Args:
            parent: Parent window
            execution_results: List of execution result dictionaries (for backward compatibility)
            modem_features: Optional ModemFeatures object from parser (preferred)
            **kwargs: Additional CTkToplevel arguments
        """
        super().__init__(parent, **kwargs)

        self.execution_results = execution_results
        self.modem_features = modem_features
        self.output_path: Optional[Path] = None
        self.generated_file: Optional[Path] = None
        self.report_generator = ReportGenerator()

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

        self.format_var = ctk.StringVar(value="csv")
        format_dropdown = ctk.CTkComboBox(
            content_frame,
            values=["csv", "html", "json", "markdown"],
            variable=self.format_var,
            state="readonly",
            command=self._on_format_changed
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

        # Confidence threshold
        confidence_frame = ctk.CTkFrame(options_inner_frame)
        confidence_frame.pack(anchor="w", padx=5, pady=5, fill="x")

        ctk.CTkLabel(confidence_frame, text="Confidence threshold:").pack(side="left", padx=(0, 5))
        self.confidence_var = ctk.StringVar(value="0.0")
        confidence_entry = ctk.CTkEntry(confidence_frame, textvariable=self.confidence_var, width=60)
        confidence_entry.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(confidence_frame, text="(0.0-1.0)", text_color="gray").pack(side="left")

        # Output path
        path_label = ctk.CTkLabel(content_frame, text="Output Path:")
        path_label.grid(row=2, column=0, sticky="w", padx=10, pady=10)

        self.path_entry = ctk.CTkEntry(content_frame, placeholder_text="Select output path...")
        self.path_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=10)

        # Suggest default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = self._get_extension()
        default_filename = f"inspection_report_{timestamp}{ext}"
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

    def _get_extension(self) -> str:
        """Get file extension for selected format."""
        format_map = {
            'csv': '.csv',
            'html': '.html',
            'json': '.json',
            'markdown': '.md'
        }
        return format_map.get(self.format_var.get(), '.csv')

    def _get_filetypes(self):
        """Get filetypes list for file dialog based on selected format."""
        format_type = self.format_var.get()
        filetypes_map = {
            'csv': [("CSV Files", "*.csv"), ("All Files", "*.*")],
            'html': [("HTML Files", "*.html"), ("All Files", "*.*")],
            'json': [("JSON Files", "*.json"), ("All Files", "*.*")],
            'markdown': [("Markdown Files", "*.md"), ("All Files", "*.*")]
        }
        return filetypes_map.get(format_type, [("All Files", "*.*")])

    def _on_format_changed(self, *args):
        """Handle format selection change."""
        # Update file extension in path entry
        current_path = self.path_entry.get()
        if current_path:
            path = Path(current_path)
            new_ext = self._get_extension()
            new_path = path.with_suffix(new_ext)
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, str(new_path))

    def _browse_output(self):
        """Open file browser for output path selection."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = self._get_extension()
        default_filename = f"inspection_report_{timestamp}{ext}"

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Report As",
            defaultextension=ext,
            filetypes=self._get_filetypes(),
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

        # Validate confidence threshold
        try:
            confidence_threshold = float(self.confidence_var.get())
            if not 0.0 <= confidence_threshold <= 1.0:
                raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        except ValueError as e:
            self.info_label.configure(
                text=f"Invalid confidence threshold: {e}",
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

        # Get selected format
        report_format = self.format_var.get()

        # Generate in background thread
        def generate_task():
            """Background task for report generation."""
            try:
                # If ModemFeatures available, use new report generation
                if self.modem_features:
                    report_result = self.report_generator.generate_report(
                        features=self.modem_features,
                        output_path=self.output_path,
                        format=report_format,
                        confidence_threshold=confidence_threshold
                    )
                    return report_result

                # Fallback: Use old CSVReporter for backward compatibility
                else:
                    from src.core.command_response import CommandResponse
                    from src.reports.csv_reporter import CSVReporter

                    responses = []
                    for result in self.execution_results:
                        if "response" in result:
                            responses.append(result["response"])

                    # Only CSV supported in fallback mode
                    if report_format != 'csv':
                        raise ValueError(f"Format '{report_format}' requires ModemFeatures. Only CSV is available in fallback mode.")

                    reporter = CSVReporter()
                    report_result = reporter.generate(responses, self.output_path)
                    return report_result

            except Exception as e:
                # Return error result
                from src.reports.report_models import ReportResult
                return ReportResult(
                    output_path=self.output_path,
                    format=report_format,
                    success=False,
                    error_message=str(e)
                )

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

                    validation_msg = ""
                    if not result.validation_passed:
                        validation_msg = " (validation warnings)"

                    self.info_label.configure(
                        text=f"✓ Report saved successfully! ({size_str}){validation_msg}",
                        text_color="#2FA572"
                    )
                    self.generated_file = self.output_path
                    self.open_report_button.configure(state="normal")
                else:
                    error_msg = result.error_message if hasattr(result, 'error_message') else "Unknown error"
                    self.info_label.configure(
                        text=f"Error: {error_msg}",
                        text_color="#E74C3C"
                    )

        # Start checking
        self.after(100, check_completion)
