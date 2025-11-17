"""Execution frame for command execution with real-time progress tracking.

Provides threaded command execution with progress bar, live logging, and
graceful cancellation support.
"""

import customtkinter as ctk
import time
from typing import Optional, Callable, List, Any
from datetime import datetime, timedelta
from src.gui.widgets import ProgressLog
from src.gui.utils.threading_utils import WorkerThread
from src.core.at_executor import ATExecutor
from src.core.plugin import Plugin, CommandDefinition
from src.parsers import FeatureExtractor, ModemFeatures


class ExecutionFrame(ctk.CTkFrame):
    """Frame for command execution control and progress monitoring.

    Executes AT commands in background thread with real-time progress updates,
    elapsed time tracking, and graceful cancellation.

    Example:
        >>> def on_complete(results):
        ...     print(f"Completed: {len(results)} commands")
        ...
        >>> frame = ExecutionFrame(
        ...     parent,
        ...     on_execution_complete=on_complete
        ... )
        >>> frame.start_execution(at_executor, commands)
    """

    def __init__(
        self,
        master,
        on_execution_complete: Optional[Callable[[List], None]] = None,
        **kwargs
    ):
        """Initialize execution frame.

        Args:
            master: Parent widget
            on_execution_complete: Callback when execution completes (receives results list)
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(master, **kwargs)

        self.on_execution_complete_callback = on_execution_complete
        self.execution_worker: Optional[WorkerThread] = None
        self.is_executing = False
        self.cancel_requested = False
        self.start_time: Optional[float] = None
        self.execution_results = []
        self.modem_features: Optional[ModemFeatures] = None
        self.feature_extractor = FeatureExtractor()

        self._setup_ui()

    def _setup_ui(self):
        """Set up UI components."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Title label
        title_label = ctk.CTkLabel(
            self,
            text="Command Execution",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 15))

        # Control buttons frame
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        controls_frame.grid_columnconfigure(1, weight=1)

        self.start_button = ctk.CTkButton(
            controls_frame,
            text="Start Inspection",
            width=150,
            command=self._on_start_clicked,
            state="disabled"
        )
        self.start_button.grid(row=0, column=0, padx=(10, 5), pady=10)

        self.cancel_button = ctk.CTkButton(
            controls_frame,
            text="Cancel",
            width=100,
            command=self._on_cancel_clicked,
            state="disabled",
            fg_color="#E74C3C",
            hover_color="#C0392B"
        )
        self.cancel_button.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        # Progress info frame
        progress_info_frame = ctk.CTkFrame(self)
        progress_info_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        progress_info_frame.grid_columnconfigure(0, weight=1)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(progress_info_frame)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.progress_bar.set(0)

        # Progress labels frame
        labels_frame = ctk.CTkFrame(progress_info_frame)
        labels_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 10))
        labels_frame.grid_columnconfigure(0, weight=1)
        labels_frame.grid_columnconfigure(1, weight=1)
        labels_frame.grid_columnconfigure(2, weight=1)

        self.command_count_label = ctk.CTkLabel(
            labels_frame,
            text="Commands: 0 / 0",
            anchor="w"
        )
        self.command_count_label.grid(row=0, column=0, sticky="w", padx=5)

        self.elapsed_label = ctk.CTkLabel(
            labels_frame,
            text="Elapsed: 00:00",
            anchor="center"
        )
        self.elapsed_label.grid(row=0, column=1, sticky="ew", padx=5)

        self.eta_label = ctk.CTkLabel(
            labels_frame,
            text="Remaining: --:--",
            anchor="e"
        )
        self.eta_label.grid(row=0, column=2, sticky="e", padx=5)

        # Progress log
        log_label = ctk.CTkLabel(
            self,
            text="Execution Log",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        log_label.grid(row=3, column=0, sticky="w", padx=10, pady=(10, 5))

        self.progress_log = ProgressLog(self, height=300)
        self.progress_log.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.grid_rowconfigure(4, weight=1)

    def set_ready(self, at_executor: Optional[ATExecutor], commands: Optional[List[CommandDefinition]]):
        """Set execution readiness.

        Args:
            at_executor: ATExecutor instance or None
            commands: List of commands to execute or None
        """
        self.at_executor = at_executor
        self.commands = commands

        ready = at_executor is not None and commands is not None and len(commands) > 0

        if ready:
            self.start_button.configure(state="normal")
        else:
            self.start_button.configure(state="disabled")

    def _on_start_clicked(self):
        """Handle Start button click."""
        if self.is_executing:
            return

        if not self.at_executor or not self.commands:
            self.progress_log.log("Cannot start: No connection or commands selected", level="error")
            return

        self._start_execution()

    def _start_execution(self):
        """Start command execution in background thread."""
        self.is_executing = True
        self.cancel_requested = False
        self.start_time = time.time()
        self.execution_results = []

        # Update UI
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_log.clear()
        self.progress_log.log(f"Starting inspection with {len(self.commands)} commands...", level="info")

        # Start worker thread
        self.execution_worker = WorkerThread(
            target=self._execution_worker,
            args=(self.at_executor, self.commands),
            name="CommandExecution"
        )
        self.execution_worker.start()

        # Start polling for updates
        self.after(100, self._check_execution_progress)

    def _execution_worker(self, progress_queue, at_executor: ATExecutor, commands: List[CommandDefinition]):
        """Background worker for command execution.

        Args:
            progress_queue: Queue for progress updates
            at_executor: ATExecutor instance
            commands: List of commands to execute
        """
        total = len(commands)

        for idx, cmd_def in enumerate(commands):
            # Check for cancellation
            if self.cancel_requested:
                progress_queue.put(("cancelled", idx, total))
                return

            # Update progress
            progress_queue.put(("command_start", idx, total, cmd_def.cmd))

            try:
                # Execute command
                start_time = time.time()
                response = at_executor.execute_command(cmd_def.cmd)
                elapsed = time.time() - start_time

                # Store result
                result = {
                    "command": cmd_def.cmd,
                    "description": cmd_def.description,
                    "category": cmd_def.category,
                    "response": response,
                    "elapsed": elapsed
                }

                if response.is_success():
                    progress_queue.put(("command_success", idx, total, cmd_def.cmd, response, elapsed))
                else:
                    progress_queue.put(("command_error", idx, total, cmd_def.cmd, response, elapsed))

                progress_queue.put(("result", result))

            except Exception as e:
                progress_queue.put(("command_exception", idx, total, cmd_def.cmd, str(e)))
                result = {
                    "command": cmd_def.cmd,
                    "description": cmd_def.description,
                    "category": cmd_def.category,
                    "error": str(e)
                }
                progress_queue.put(("result", result))

        # Execution complete
        progress_queue.put(("complete", total))

    def _check_execution_progress(self):
        """Check execution progress and update UI."""
        if not self.execution_worker:
            return

        # Process all available messages
        while True:
            msg = self.execution_worker.get_progress(timeout=0)
            if not msg:
                break

            msg_type = msg[0]

            if msg_type == "command_start":
                _, idx, total, command = msg
                self.progress_log.log_command(command)
                self._update_progress(idx, total)

            elif msg_type == "command_success":
                _, idx, total, command, response, elapsed = msg
                data = response.data.strip() if response.data else "OK"
                self.progress_log.log_response(data, is_success=True)
                self._update_progress(idx + 1, total)

            elif msg_type == "command_error":
                _, idx, total, command, response, elapsed = msg
                error_msg = response.error or response.status.value
                self.progress_log.log_response(error_msg, is_success=False)
                self._update_progress(idx + 1, total)

            elif msg_type == "command_exception":
                _, idx, total, command, error = msg
                self.progress_log.log(f"Exception: {error}", level="error")
                self._update_progress(idx + 1, total)

            elif msg_type == "result":
                _, result = msg
                self.execution_results.append(result)

            elif msg_type == "cancelled":
                _, idx, total = msg
                self.progress_log.log(f"Execution cancelled after {idx} commands", level="warning")
                self._finish_execution()
                return

            elif msg_type == "complete":
                _, total = msg
                self.progress_log.log(f"Inspection complete! Executed {total} commands.", level="success")
                self._finish_execution()
                return

        # Continue polling if thread is alive
        if self.execution_worker.is_alive():
            self.after(100, self._check_execution_progress)
        else:
            self._finish_execution()

    def _update_progress(self, current: int, total: int):
        """Update progress indicators.

        Args:
            current: Current command index
            total: Total command count
        """
        # Update progress bar
        if total > 0:
            progress = current / total
            self.progress_bar.set(progress)
        else:
            self.progress_bar.set(0)

        # Update command count
        self.command_count_label.configure(text=f"Commands: {current} / {total}")

        # Update elapsed time
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_str = str(timedelta(seconds=int(elapsed)))[2:]  # Remove "0 days, " prefix
            self.elapsed_label.configure(text=f"Elapsed: {elapsed_str}")

            # Calculate ETA
            if current > 0:
                avg_time_per_cmd = elapsed / current
                remaining_cmds = total - current
                eta_seconds = avg_time_per_cmd * remaining_cmds
                eta_str = str(timedelta(seconds=int(eta_seconds)))[2:]
                self.eta_label.configure(text=f"Remaining: {eta_str}")
            else:
                self.eta_label.configure(text="Remaining: --:--")

    def _finish_execution(self):
        """Finish execution and display summary."""
        self.is_executing = False
        self.cancel_requested = False

        # Update UI
        self.start_button.configure(state="normal" if self.at_executor and self.commands else "disabled")
        self.cancel_button.configure(state="disabled")

        # Parse features from execution results
        if self.execution_results and self.plugin:
            try:
                self.progress_log.log("", level="info")
                self.progress_log.log("Parsing modem features...", level="info")

                # Convert execution results to response dictionary
                responses = {}
                for result in self.execution_results:
                    if "command" in result and "response" in result:
                        cmd = result["command"]
                        responses[cmd] = result["response"]

                # Extract features using parser layer
                self.modem_features = self.feature_extractor.extract_features(
                    responses=responses,
                    plugin=self.plugin
                )

                # Log parsing results
                if self.modem_features:
                    confidence = self.modem_features.aggregate_confidence
                    self.progress_log.log(
                        f"Features parsed successfully (confidence: {confidence:.1%})",
                        level="success"
                    )
                    if self.modem_features.parsing_errors:
                        self.progress_log.log(
                            f"Parsing warnings: {len(self.modem_features.parsing_errors)}",
                            level="warning"
                        )

            except Exception as e:
                self.progress_log.log(f"Feature parsing failed: {e}", level="error")
                self.modem_features = None

        # Display summary
        if self.execution_results:
            success_count = sum(1 for r in self.execution_results if "response" in r and r["response"].is_success())
            error_count = len(self.execution_results) - success_count

            self.progress_log.log("", level="info")
            self.progress_log.log("=== Execution Summary ===", level="info")
            self.progress_log.log(f"Total commands: {len(self.execution_results)}", level="info")
            self.progress_log.log(f"Successful: {success_count}", level="success")
            if error_count > 0:
                self.progress_log.log(f"Failed: {error_count}", level="error")

            # Calculate total time
            if self.start_time:
                total_time = time.time() - self.start_time
                self.progress_log.log(f"Total time: {timedelta(seconds=int(total_time))}", level="info")

        # Call completion callback
        if self.on_execution_complete_callback:
            self.on_execution_complete_callback(self.execution_results)

    def _on_cancel_clicked(self):
        """Handle Cancel button click."""
        if not self.is_executing:
            return

        self.cancel_requested = True
        self.cancel_button.configure(state="disabled")
        self.progress_log.log("Cancelling... (will stop after current command)", level="warning")

    def get_execution_results(self) -> List:
        """Get execution results.

        Returns:
            List of result dictionaries
        """
        return self.execution_results

    def get_modem_features(self) -> Optional[ModemFeatures]:
        """Get parsed modem features from last execution.

        Returns:
            ModemFeatures object if parsing succeeded, None otherwise
        """
        return self.modem_features

    def is_execution_running(self) -> bool:
        """Check if execution is currently running.

        Returns:
            True if executing, False otherwise
        """
        return self.is_executing
