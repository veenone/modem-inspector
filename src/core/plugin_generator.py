"""Plugin template generation module.

Provides tools to generate plugin YAML templates with all required sections,
universal 3GPP commands, and vendor-specific commands when available.
"""

import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any


class PluginGenerator:
    """Generates plugin YAML templates with structure and comments.

    Creates valid plugin templates that pass schema validation, including
    all required sections, universal AT commands, and instructional comments.

    Example:
        >>> generator = PluginGenerator()
        >>> generator.generate_template(
        ...     vendor="myvendor",
        ...     model="mymodel",
        ...     category="lte_cat1",
        ...     output_path=Path("plugins/myvendor/mymodel.yaml")
        ... )
    """

    # Universal 3GPP AT commands (included in all templates)
    UNIVERSAL_COMMANDS = {
        "basic": [
            {
                "cmd": "AT",
                "description": "Test command - verifies modem responsiveness",
                "category": "basic",
                "timeout": 5,
                "critical": True,
                "quick": True
            },
            {
                "cmd": "AT+CGMI",
                "description": "Request manufacturer identification",
                "category": "basic",
                "timeout": 5,
                "critical": True,
                "quick": True
            },
            {
                "cmd": "AT+CGMM",
                "description": "Request model identification",
                "category": "basic",
                "timeout": 5,
                "quick": True
            },
            {
                "cmd": "AT+CGMR",
                "description": "Request revision identification (firmware version)",
                "category": "basic",
                "timeout": 5,
                "quick": True
            },
            {
                "cmd": "AT+CGSN",
                "description": "Request IMEI (International Mobile Equipment Identity)",
                "category": "basic",
                "timeout": 5,
                "quick": True
            }
        ],
        "network": [
            {
                "cmd": "AT+CSQ",
                "description": "Signal quality report",
                "category": "network",
                "timeout": 5,
                "quick": True
            },
            {
                "cmd": "AT+COPS?",
                "description": "Operator selection (current network)",
                "category": "network",
                "timeout": 10
            },
            {
                "cmd": "AT+CREG?",
                "description": "Network registration status",
                "category": "network",
                "timeout": 5,
                "quick": True
            }
        ]
    }

    # Vendor-specific commands (optional, added if vendor recognized)
    VENDOR_COMMANDS = {
        "quectel": {
            "network": [
                {
                    "cmd": 'AT+QENG="servingcell"',
                    "description": "Query serving cell information (Quectel-specific)",
                    "category": "network",
                    "timeout": 10
                }
            ],
            "power": [
                {
                    "cmd": "AT+QTEMP",
                    "description": "Query temperature (Quectel-specific)",
                    "category": "power",
                    "timeout": 5
                }
            ]
        },
        "nordic": {
            "network": [
                {
                    "cmd": "AT%XSYSTEMMODE?",
                    "description": "Query system mode (Nordic-specific)",
                    "category": "network",
                    "timeout": 5
                }
            ]
        },
        "simcom": {
            "network": [
                {
                    "cmd": "AT+CPSI?",
                    "description": "Inquiring UE system information (SIMCom-specific)",
                    "category": "network",
                    "timeout": 10
                }
            ]
        }
    }

    def generate_template(
        self,
        vendor: str,
        model: str,
        category: str = "other",
        output_path: Optional[Path] = None,
        author: Optional[str] = None,
        overwrite: bool = False
    ) -> str:
        """Generate plugin YAML template.

        Args:
            vendor: Vendor name (lowercase, e.g., "quectel").
            model: Model name (lowercase, e.g., "ec200u").
            category: Plugin category (default: "other").
                Valid: 5g_highperf, lte_cat1, automotive, iot, nbiot, other
            output_path: Optional output file path. If None, returns string.
            author: Optional author name.
            overwrite: If True, overwrite existing file (default: False).

        Returns:
            Generated YAML content as string.

        Raises:
            FileExistsError: If output_path exists and overwrite=False.

        Example:
            >>> generator = PluginGenerator()
            >>> yaml_content = generator.generate_template(
            ...     vendor="myvendor",
            ...     model="mymodel",
            ...     category="lte_cat1"
            ... )
            >>> print(yaml_content)
        """
        # Validate category
        valid_categories = ["5g_highperf", "lte_cat1", "automotive", "iot", "nbiot", "other"]
        if category not in valid_categories:
            raise ValueError(f"Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}")

        # Check if output file exists
        if output_path and output_path.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {output_path}. Use overwrite=True to replace.")

        # Build template structure
        template = self._build_template_dict(vendor, model, category, author)

        # Convert to YAML with comments
        yaml_content = self._dict_to_yaml_with_comments(template, vendor, model)

        # Write to file if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            print(f"Plugin template created: {output_path}")

        return yaml_content

    def _build_template_dict(
        self,
        vendor: str,
        model: str,
        category: str,
        author: Optional[str]
    ) -> Dict[str, Any]:
        """Build template dictionary structure.

        Args:
            vendor: Vendor name.
            model: Model name.
            category: Plugin category.
            author: Optional author name.

        Returns:
            Dictionary representing plugin structure.
        """
        # Start with universal commands
        commands = {}
        for cat, cmds in self.UNIVERSAL_COMMANDS.items():
            commands[cat] = cmds.copy()

        # Add vendor-specific commands if available
        if vendor.lower() in self.VENDOR_COMMANDS:
            vendor_cmds = self.VENDOR_COMMANDS[vendor.lower()]
            for cat, cmds in vendor_cmds.items():
                if cat in commands:
                    commands[cat].extend(cmds)
                else:
                    commands[cat] = cmds.copy()

        # Build template
        template = {
            "metadata": {
                "vendor": vendor.lower(),
                "model": model.lower(),
                "category": category,
                "version": "1.0.0"
            },
            "connection": {
                "default_baud": 115200,
                "data_bits": 8,
                "parity": "N",
                "stop_bits": 1,
                "flow_control": False
            },
            "commands": commands,
            "validation": {
                "required_responses": ["AT"]
            }
        }

        # Add author if provided
        if author:
            template["metadata"]["author"] = author

        return template

    def _dict_to_yaml_with_comments(
        self,
        data: Dict[str, Any],
        vendor: str,
        model: str
    ) -> str:
        """Convert dictionary to YAML with instructional comments.

        Args:
            data: Template dictionary.
            vendor: Vendor name for header.
            model: Model name for header.

        Returns:
            YAML string with comments.
        """
        lines = []

        # Header comment
        lines.append(f"# {vendor.capitalize()} {model.upper()} Plugin Template")
        lines.append("# Generated by Modem Inspector Plugin Generator")
        lines.append("#")
        lines.append("# This template includes all required sections and universal 3GPP commands.")
        lines.append("# Customize the commands, add parsers, and update validation rules as needed.")
        lines.append("")

        # Metadata section
        lines.append("# Plugin identification and versioning")
        lines.append("metadata:")
        lines.append(f"  vendor: \"{data['metadata']['vendor']}\"  # Vendor name (lowercase)")
        lines.append(f"  model: \"{data['metadata']['model']}\"    # Model identifier (lowercase)")
        lines.append(f"  category: \"{data['metadata']['category']}\"  # Category: 5g_highperf, lte_cat1, automotive, iot, nbiot, other")
        lines.append(f"  version: \"{data['metadata']['version']}\"  # Semantic version (X.Y.Z)")
        if "author" in data["metadata"]:
            lines.append(f"  author: \"{data['metadata']['author']}\"")
        lines.append("")

        # Connection section
        lines.append("# Serial connection configuration")
        lines.append("connection:")
        lines.append(f"  default_baud: {data['connection']['default_baud']}  # Baud rate (9600-921600)")
        lines.append(f"  data_bits: {data['connection']['data_bits']}      # Data bits (5-8)")
        lines.append(f"  parity: \"{data['connection']['parity']}\"         # Parity: N=None, E=Even, O=Odd")
        lines.append(f"  stop_bits: {data['connection']['stop_bits']}      # Stop bits (1-2)")
        lines.append(f"  flow_control: {str(data['connection']['flow_control']).lower()}  # Hardware flow control (RTS/CTS)")
        lines.append("  # Optional: Initialization sequence")
        lines.append("  # init_sequence:")
        lines.append("  #   - cmd: \"ATE0\"")
        lines.append("  #     expected: \"OK\"")
        lines.append("")

        # Commands section
        lines.append("# AT command definitions organized by category")
        lines.append("commands:")
        for category, cmds in data["commands"].items():
            lines.append(f"  # {category.capitalize()} commands")
            lines.append(f"  {category}:")
            for cmd in cmds:
                # Use single quotes for cmd to avoid issues with embedded double quotes
                cmd_value = cmd['cmd'].replace("'", "''")  # Escape single quotes by doubling
                lines.append(f"    - cmd: '{cmd_value}'")
                lines.append(f"      description: \"{cmd['description']}\"")
                lines.append(f"      category: \"{cmd['category']}\"")
                if cmd.get('timeout'):
                    lines.append(f"      timeout: {cmd['timeout']}  # Override default timeout (seconds)")
                if cmd.get('critical'):
                    lines.append(f"      critical: {str(cmd['critical']).lower()}  # Critical command (failure is significant)")
                if cmd.get('quick'):
                    lines.append(f"      quick: {str(cmd['quick']).lower()}  # Include in quick scan mode")
                lines.append("")

        # Parsers section (commented examples)
        lines.append("# Response parsers for extracting structured data")
        lines.append("# Uncomment and customize the examples below, or add your own parsers")
        lines.append("#")
        lines.append("# parsers:")
        lines.append("#   # Example regex parser:")
        lines.append("#   signal_parser:")
        lines.append("#     name: \"signal_parser\"")
        lines.append("#     type: \"regex\"")
        lines.append("#     pattern: \"\\\\+CSQ: (\\\\d+),(\\\\d+)\"  # Escape backslashes in YAML")
        lines.append("#     groups: [\"rssi\", \"ber\"]")
        lines.append("#     output_format: \"dict\"")
        lines.append("#")
        lines.append("#   # Example JSON parser:")
        lines.append("#   json_parser:")
        lines.append("#     name: \"json_parser\"")
        lines.append("#     type: \"json\"")
        lines.append("#     json_path: \"data.value\"  # Optional path to extract")
        lines.append("#")
        lines.append("#   # Example custom parser:")
        lines.append("#   custom_parser:")
        lines.append("#     name: \"custom_parser\"")
        lines.append("#     type: \"custom\"")
        lines.append("#     module: \"parsers.custom.my_parser\"  # Python module path")
        lines.append("#     function: \"parse_response\"          # Function name in module")
        lines.append("")

        # Validation section
        lines.append("# Validation rules for plugin testing")
        lines.append("validation:")
        lines.append("  required_responses:")
        for cmd in data["validation"]["required_responses"]:
            lines.append(f"    - \"{cmd}\"  # Command that must succeed")
        lines.append("  # Optional: Expected manufacturer string from AT+CGMI")
        lines.append(f"  # expected_manufacturer: \"{vendor.capitalize()}\"")
        lines.append("  # Optional: Regex pattern for expected model from AT+CGMM")
        lines.append(f"  # expected_model_pattern: \"{model.upper()}.*\"")
        lines.append("")

        return "\n".join(lines)

    def list_vendor_commands(self, vendor: str) -> Optional[Dict[str, List[Dict]]]:
        """Get vendor-specific commands if available.

        Args:
            vendor: Vendor name (case-insensitive).

        Returns:
            Dictionary of vendor commands or None if not found.
        """
        return self.VENDOR_COMMANDS.get(vendor.lower())

    def list_supported_vendors(self) -> List[str]:
        """Get list of vendors with pre-defined commands.

        Returns:
            List of vendor names.
        """
        return list(self.VENDOR_COMMANDS.keys())
