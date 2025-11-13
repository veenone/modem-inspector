"""Threading utilities for GUI background operations.

Provides WorkerThread class for executing long-running operations in background
threads with queue-based progress reporting to keep GUI responsive.
"""

import threading
import queue
from typing import Callable, Any, Optional
import functools


class WorkerThread(threading.Thread):
    """Background worker thread with queue-based progress reporting.

    Executes a target function in a background thread and reports progress
    updates via a queue, allowing the GUI thread to remain responsive.

    Example:
        >>> def long_operation(progress_queue):
        ...     for i in range(10):
        ...         progress_queue.put(("progress", i/10))
        ...         time.sleep(0.1)
        ...     progress_queue.put(("complete", "Done"))
        >>>
        >>> worker = WorkerThread(target=long_operation)
        >>> worker.start()
        >>> while worker.is_alive():
        ...     try:
        ...         msg_type, value = worker.progress_queue.get_nowait()
        ...         print(f"{msg_type}: {value}")
        ...     except queue.Empty:
        ...         pass
    """

    def __init__(self,
                 target: Callable,
                 args: tuple = (),
                 kwargs: Optional[dict] = None,
                 name: Optional[str] = None):
        """Initialize worker thread.

        Args:
            target: Function to execute in background thread
            args: Positional arguments for target function
            kwargs: Keyword arguments for target function
            name: Thread name for debugging
        """
        super().__init__(name=name, daemon=True)
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.progress_queue = queue.Queue()
        self.exception: Optional[Exception] = None

    def run(self):
        """Execute target function and handle exceptions.

        Automatically injects progress_queue as first argument to target.
        Captures any exceptions and stores them for retrieval.
        """
        try:
            # Inject progress queue as first argument
            self.target(self.progress_queue, *self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
            self.progress_queue.put(("error", str(e)))

    def get_progress(self, timeout: float = 0.0) -> Optional[tuple]:
        """Get next progress update from queue.

        Args:
            timeout: Maximum time to wait for update (0 = non-blocking)

        Returns:
            Tuple of (message_type, value) or None if queue empty

        Example:
            >>> msg = worker.get_progress(timeout=0.1)
            >>> if msg:
            ...     msg_type, value = msg
            ...     print(f"Progress: {msg_type} = {value}")
        """
        try:
            return self.progress_queue.get(timeout=timeout)
        except queue.Empty:
            return None


def safe_callback(func: Callable) -> Callable:
    """Decorator to ensure callback executes in GUI thread.

    Prevents cross-thread GUI updates by ensuring decorated functions
    are always called from the main GUI thread. Use this decorator on
    any callback that modifies GUI elements.

    Note: This is a marker decorator for documentation. Actual thread
    safety is ensured by using tkinter's after() method in the GUI code.

    Args:
        func: Function that modifies GUI elements

    Returns:
        Decorated function

    Example:
        >>> @safe_callback
        ... def update_progress_bar(value):
        ...     progress_bar.set(value)
        >>>
        >>> # Call from worker thread - decorator documents intent
        >>> update_progress_bar(0.5)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # In practice, GUI code should call this via tkinter.after()
        # This decorator serves as documentation and can add logging
        return func(*args, **kwargs)
    return wrapper


class CancellableWorker(WorkerThread):
    """WorkerThread with cancellation support.

    Extends WorkerThread with ability to request cancellation.
    Target function should check self.cancel_requested periodically.

    Example:
        >>> def cancelable_task(progress_queue, worker):
        ...     for i in range(100):
        ...         if worker.cancel_requested:
        ...             progress_queue.put(("cancelled", None))
        ...             return
        ...         # Do work...
        ...         progress_queue.put(("progress", i/100))
        >>>
        >>> worker = CancellableWorker(target=cancelable_task)
        >>> worker.start()
        >>> # Later...
        >>> worker.request_cancel()
    """

    def __init__(self, *args, **kwargs):
        """Initialize cancellable worker thread."""
        super().__init__(*args, **kwargs)
        self.cancel_requested = False
        self._cancel_lock = threading.Lock()

    def request_cancel(self):
        """Request cancellation of worker thread.

        Sets flag that worker should check. Does not forcefully terminate.
        """
        with self._cancel_lock:
            self.cancel_requested = True
            self.progress_queue.put(("cancel_requested", None))

    def run(self):
        """Execute target function with self reference for cancel checking."""
        try:
            # Inject both progress_queue and self for cancel checking
            self.target(self.progress_queue, self, *self.args, **self.kwargs)
        except Exception as e:
            self.exception = e
            self.progress_queue.put(("error", str(e)))
