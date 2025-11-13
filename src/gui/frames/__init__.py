"""GUI frame components.

Provides main frame components for the modem inspector interface:
- ConnectionFrame: Port selection and connection management
- PluginFrame: Plugin selection and auto-detection
- ExecutionFrame: Command execution controls
- ResultsFrame: Results display with tabs
- SettingsFrame: Settings dialog
- LogViewerFrame: Communication log viewer with filtering and search
"""

from src.gui.frames.connection_frame import ConnectionFrame
from src.gui.frames.log_viewer_frame import LogViewerFrame

__all__ = [
    'ConnectionFrame',
    'LogViewerFrame',
]
