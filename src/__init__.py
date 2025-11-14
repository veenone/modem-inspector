"""Modem Inspector - AT Command Testing and Feature Extraction Tool.

This package provides comprehensive modem inspection capabilities including:
- AT command execution with retry logic
- Feature extraction with confidence scoring
- Vendor-specific parser extensions
- Multi-modem support
"""

# Core AT Command Engine
from src.core import (
    CommandResponse,
    ResponseStatus,
    SerialHandler,
    PortInfo,
    ATExecutor,
    MultiModemExecutor,
    ModemConnection,
    ModemInspectorError,
    SerialPortError,
    ATCommandError,
)

# Parser Layer
from src.parsers import (
    ModemFeatures,
    BasicInfo,
    NetworkCapabilities,
    VoiceFeatures,
    GNSSInfo,
    PowerManagement,
    SIMInfo,
    NetworkTechnology,
    SIMStatus,
    FeatureExtractor,
    BaseVendorParser,
)

__version__ = "0.1.0"

__all__ = [
    # Core
    "CommandResponse",
    "ResponseStatus",
    "SerialHandler",
    "PortInfo",
    "ATExecutor",
    "MultiModemExecutor",
    "ModemConnection",
    # Parsers
    "ModemFeatures",
    "BasicInfo",
    "NetworkCapabilities",
    "VoiceFeatures",
    "GNSSInfo",
    "PowerManagement",
    "SIMInfo",
    "NetworkTechnology",
    "SIMStatus",
    "FeatureExtractor",
    "BaseVendorParser",
    # Exceptions
    "ModemInspectorError",
    "SerialPortError",
    "ATCommandError",
]
