"""Plugin data models for vendor-specific modem support.

This module defines immutable dataclasses representing plugin definitions
loaded from YAML files, enabling declarative modem configuration.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class ParserType(Enum):
    """Parser implementation type.

    - REGEX: Regular expression with named groups
    - JSON: JSON response parsing
    - CUSTOM: Custom Python function parser
    - NONE: No parsing (raw response)
    """
    REGEX = "regex"
    JSON = "json"
    CUSTOM = "custom"
    NONE = "none"


class PluginCategory(Enum):
    """Modem category for feature-based filtering.

    Categories help organize plugins by modem capabilities:
    - 5G_HIGHPERF: High-performance 5G modems
    - LTE_CAT1: LTE Category 1 modems
    - AUTOMOTIVE: Automotive-grade modems
    - IOT: IoT-optimized modems
    - NBIOT: NB-IoT modems
    - OTHER: Other/uncategorized modems
    """
    FIVEG_HIGHPERF = "5g_highperf"
    LTE_CAT1 = "lte_cat1"
    AUTOMOTIVE = "automotive"
    IOT = "iot"
    NBIOT = "nbiot"
    OTHER = "other"


@dataclass(frozen=True)
class PluginMetadata:
    """Plugin identification and versioning information.

    Attributes:
        vendor: Modem vendor (e.g., "quectel", "nordic")
        model: Modem model (e.g., "ec200u", "nrf9160")
        category: Plugin category (e.g., "lte_cat1", "5g_highperf")
        version: Semantic version string (e.g., "1.0.0")
        author: Plugin author name (optional)
        compatible_with: Inspector version compatibility (e.g., "inspector_v2.0+")
        variants: Model variants supported (e.g., ["EC25-E", "EC25-AU"])
    """
    vendor: str
    model: str
    category: str
    version: str
    author: Optional[str] = None
    compatible_with: Optional[str] = None
    variants: Optional[List[str]] = field(default=None)


@dataclass(frozen=True)
class PluginConnection:
    """Serial connection configuration.

    Defines serial port settings specific to this modem.

    Attributes:
        default_baud: Default baud rate (default 115200)
        data_bits: Number of data bits (default 8)
        parity: Parity setting - 'N'one, 'E'ven, 'O'dd (default 'N')
        stop_bits: Number of stop bits (default 1)
        flow_control: Enable hardware flow control (default False)
        init_sequence: Initialization command sequence (optional)
    """
    default_baud: int = 115200
    data_bits: int = 8
    parity: str = 'N'
    stop_bits: int = 1
    flow_control: bool = False
    init_sequence: Optional[List[Dict[str, str]]] = field(default=None)


@dataclass(frozen=True)
class CommandDefinition:
    """Single AT command definition.

    Defines an AT command with metadata for execution and parsing.

    Attributes:
        cmd: AT command string (e.g., "AT+CGMI")
        description: Human-readable description
        category: Command category (e.g., "basic", "network", "power")
        timeout: Override default timeout in seconds (optional)
        parser: Parser name to use for response (optional)
        critical: Abort inspection if this command fails (default False)
        quick: Include in quick-scan mode (default False)
        expected_format: Expected response format documentation (optional)
    """
    cmd: str
    description: str
    category: str
    timeout: Optional[int] = None
    parser: Optional[str] = None
    critical: bool = False
    quick: bool = False
    expected_format: Optional[str] = None


@dataclass(frozen=True)
class ParserDefinition:
    """Parser configuration for response extraction.

    Defines how to parse AT command responses into structured data.

    Attributes:
        name: Parser identifier
        type: Parser type (REGEX, JSON, CUSTOM, NONE)
        pattern: Regex pattern for REGEX parser (optional)
        groups: Named capture group names for REGEX parser (optional)
        json_path: JSON path expression for JSON parser (optional)
        module: Python module path for CUSTOM parser (optional)
        function: Function name in module for CUSTOM parser (optional)
        unit: Measurement unit to append to values (e.g., "mV", "dBm")
        output_format: Expected output format (e.g., "dict", "list", "string")
    """
    name: str
    type: ParserType
    pattern: Optional[str] = None
    groups: Optional[List[str]] = field(default=None)
    json_path: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    unit: Optional[str] = None
    output_format: Optional[str] = None


@dataclass(frozen=True)
class PluginValidation:
    """Validation rules for plugin testing.

    Defines test criteria for validating plugin with real hardware.

    Attributes:
        required_responses: Commands that must receive responses
        expected_manufacturer: Expected manufacturer string from AT+CGMI
        expected_model_pattern: Regex pattern for expected model from AT+CGMM
    """
    required_responses: Optional[List[str]] = field(default=None)
    expected_manufacturer: Optional[str] = None
    expected_model_pattern: Optional[str] = None
    expected_values: Optional[Dict[str, List[str]]] = field(default=None)


@dataclass(frozen=True)
class Plugin:
    """Complete plugin definition from YAML file.

    Represents a fully loaded and validated plugin with all metadata,
    commands, parsers, and validation rules.

    Attributes:
        metadata: Plugin identification and versioning
        connection: Serial connection configuration
        commands: Commands organized by category
        parsers: Parser definitions by name
        validation: Validation rules (optional)
        file_path: Source YAML file path (optional)

    Example:
        >>> plugin = Plugin(
        ...     metadata=PluginMetadata(vendor="quectel", model="ec200u",
        ...                            category="lte_cat1", version="1.0.0"),
        ...     connection=PluginConnection(),
        ...     commands={"basic": [CommandDefinition(cmd="AT", description="Test",
        ...                                           category="basic")]},
        ...     parsers={}
        ... )
        >>> cmds = plugin.get_all_commands()
        >>> assert len(cmds) == 1
    """
    metadata: PluginMetadata
    connection: PluginConnection
    commands: Dict[str, List[CommandDefinition]]
    parsers: Dict[str, ParserDefinition]
    validation: Optional[PluginValidation] = None
    file_path: Optional[str] = None

    def get_all_commands(self) -> List[CommandDefinition]:
        """Flatten all commands across categories.

        Returns:
            List of all CommandDefinition objects from all categories

        Example:
            >>> plugin = Plugin(...)
            >>> all_cmds = plugin.get_all_commands()
            >>> print(f"Plugin has {len(all_cmds)} total commands")
        """
        return [cmd for cmds in self.commands.values() for cmd in cmds]

    def get_commands_by_category(self, category: str) -> List[CommandDefinition]:
        """Get commands for specific category.

        Args:
            category: Category name (e.g., "basic", "network", "power")

        Returns:
            List of CommandDefinition objects in that category

        Example:
            >>> basic_commands = plugin.get_commands_by_category("basic")
            >>> for cmd in basic_commands:
            ...     print(cmd.cmd, cmd.description)
        """
        return self.commands.get(category, [])

    def get_parser(self, name: str) -> Optional[ParserDefinition]:
        """Lookup parser by name.

        Args:
            name: Parser identifier

        Returns:
            ParserDefinition if found, None otherwise

        Example:
            >>> parser = plugin.get_parser("signal_parser")
            >>> if parser:
            ...     print(f"Parser type: {parser.type.value}")
        """
        return self.parsers.get(name)

    def get_init_commands(self) -> List[str]:
        """Extract init sequence command strings.

        Returns:
            List of command strings from init_sequence

        Example:
            >>> init_cmds = plugin.get_init_commands()
            >>> for cmd in init_cmds:
            ...     print(f"Init: {cmd}")
        """
        if self.connection.init_sequence is None:
            return []

        return [item['cmd'] for item in self.connection.init_sequence
                if 'cmd' in item]

    def __str__(self) -> str:
        """Human-readable plugin representation."""
        return (f"Plugin({self.metadata.vendor}.{self.metadata.model} "
                f"v{self.metadata.version}, {len(self.get_all_commands())} commands)")


@dataclass
class PluginTestResult:
    """Results from plugin hardware validation test.

    Attributes:
        plugin_name: Plugin identifier (vendor.model)
        total_commands: Total number of commands tested
        passed: Number of commands that succeeded
        failed: Number of commands that failed
        errors: List of error messages for failed commands
    """
    plugin_name: str
    total_commands: int
    passed: int
    failed: int
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage.

        Returns:
            Success rate between 0.0 and 100.0
        """
        if self.total_commands == 0:
            return 0.0
        return (self.passed / self.total_commands) * 100.0

    def __str__(self) -> str:
        """Human-readable test result."""
        return (f"PluginTestResult({self.plugin_name}: "
                f"{self.passed}/{self.total_commands} passed "
                f"({self.success_rate:.1f}%))")
