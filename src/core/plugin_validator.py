"""Plugin validation and testing module.

Provides comprehensive validation for plugin YAML files including schema validation,
semantic checks, and optional hardware testing capabilities.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import re
from src.core.plugin import Plugin, PluginMetadata, PluginConnection, CommandDefinition, ParserDefinition, ParserType, PluginValidation, PluginTestResult
from src.core.exceptions import PluginValidationError


class PluginValidator:
    """Validates plugin definitions against schema and performs additional checks.

    Provides three levels of validation:
    1. Schema validation: Ensures YAML structure matches JSON schema
    2. Semantic validation: Additional logical checks (command conflicts, parser references)
    3. Hardware testing: Optional validation against real modem hardware

    Example:
        >>> validator = PluginValidator()
        >>> is_valid, errors = validator.validate_schema(plugin_yaml)
        >>> if is_valid:
        ...     warnings = validator.validate_plugin(plugin_obj)
        ...     if hardware_available:
        ...         result = validator.test_plugin(plugin_obj, serial_handler)
    """

    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize validator with JSON schema.

        Args:
            schema_path: Optional path to plugin_schema.json. If None, uses default location.
        """
        if schema_path is None:
            # Default schema location
            schema_path = Path(__file__).parent.parent / "schemas" / "plugin_schema.json"

        self.schema_path = schema_path
        self._schema: Optional[Dict[str, Any]] = None
        self._load_schema()

    def _load_schema(self):
        """Load JSON schema from file.

        Raises:
            PluginValidationError: If schema file cannot be loaded.
        """
        try:
            if not self.schema_path.exists():
                raise PluginValidationError(f"Schema file not found: {self.schema_path}")

            with open(self.schema_path, 'r', encoding='utf-8') as f:
                self._schema = json.load(f)
        except json.JSONDecodeError as e:
            raise PluginValidationError(f"Invalid JSON schema: {e}")
        except Exception as e:
            raise PluginValidationError(f"Failed to load schema: {e}")

    def validate_schema(self, plugin_yaml: str) -> Tuple[bool, List[str]]:
        """Validate plugin YAML against JSON schema.

        Args:
            plugin_yaml: YAML content as string.

        Returns:
            Tuple of (is_valid, error_messages).
            - is_valid: True if validation passed
            - error_messages: List of validation error messages (empty if valid)

        Example:
            >>> validator = PluginValidator()
            >>> is_valid, errors = validator.validate_schema(yaml_content)
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Validation error: {error}")
        """
        errors = []

        # Parse YAML safely
        try:
            plugin_data = yaml.safe_load(plugin_yaml)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML syntax: {e}")
            return False, errors

        # Validate against JSON schema
        try:
            import jsonschema
            jsonschema.validate(instance=plugin_data, schema=self._schema)
        except jsonschema.ValidationError as e:
            # Format error message with field path and description
            field_path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            error_msg = f"Field '{field_path}': {e.message}"
            errors.append(error_msg)
            return False, errors
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")
            return False, errors
        except ImportError:
            errors.append("jsonschema library not installed. Install with: pip install jsonschema")
            return False, errors

        return True, []

    def validate_plugin(self, plugin: Plugin) -> List[str]:
        """Perform additional semantic validation beyond schema.

        Checks for:
        - Command conflicts (duplicate command strings)
        - Undefined parser references (commands referencing non-existent parsers)
        - AT command format issues
        - Category consistency

        Args:
            plugin: Plugin object to validate.

        Returns:
            List of warning messages (non-blocking issues). Empty if no warnings.

        Example:
            >>> validator = PluginValidator()
            >>> warnings = validator.validate_plugin(plugin)
            >>> for warning in warnings:
            ...     print(f"Warning: {warning}")
        """
        warnings = []

        # Check for duplicate commands
        seen_commands = {}
        for cmd_def in plugin.get_all_commands():
            cmd_str = cmd_def.cmd
            if cmd_str in seen_commands:
                warnings.append(
                    f"Duplicate command '{cmd_str}' in categories '{seen_commands[cmd_str]}' and '{cmd_def.category}'"
                )
            else:
                seen_commands[cmd_str] = cmd_def.category

        # Check for undefined parser references
        parser_names = set(plugin.parsers.keys()) if plugin.parsers else set()
        for cmd_def in plugin.get_all_commands():
            if cmd_def.parser and cmd_def.parser not in parser_names:
                warnings.append(
                    f"Command '{cmd_def.cmd}' references undefined parser '{cmd_def.parser}'"
                )

        # Validate AT command format (should start with AT)
        for cmd_def in plugin.get_all_commands():
            if not cmd_def.cmd.startswith("AT"):
                warnings.append(
                    f"Command '{cmd_def.cmd}' does not start with 'AT' (non-standard format)"
                )

        # Check category consistency in commands dict
        for category, cmd_list in plugin.commands.items():
            for cmd_def in cmd_list:
                if cmd_def.category != category:
                    warnings.append(
                        f"Command '{cmd_def.cmd}' has category '{cmd_def.category}' but is in '{category}' group"
                    )

        # Check init_sequence commands
        if plugin.connection.init_sequence:
            for idx, init_cmd in enumerate(plugin.connection.init_sequence):
                cmd = init_cmd.get('cmd', '')
                if not cmd.startswith('AT'):
                    warnings.append(
                        f"Init sequence command #{idx+1} '{cmd}' does not start with 'AT'"
                    )

        # Validate parser patterns (regex parsers only)
        if plugin.parsers:
            for parser_name, parser_def in plugin.parsers.items():
                if parser_def.type == ParserType.REGEX and parser_def.pattern:
                    try:
                        re.compile(parser_def.pattern)
                    except re.error as e:
                        warnings.append(
                            f"Parser '{parser_name}' has invalid regex pattern: {e}"
                        )

        return warnings

    def test_plugin(
        self,
        plugin: Plugin,
        serial_handler: Any,
        at_executor: Optional[Any] = None
    ) -> PluginTestResult:
        """Test plugin against real modem hardware.

        Executes critical commands and validation checks to verify plugin works
        with actual hardware.

        Args:
            plugin: Plugin to test.
            serial_handler: SerialHandler instance (from at-command-engine).
            at_executor: Optional ATExecutor instance. If None, creates one.

        Returns:
            PluginTestResult with test outcomes and details.

        Example:
            >>> from src.core.serial_handler import SerialHandler
            >>> from src.core.at_executor import ATExecutor
            >>>
            >>> serial_handler = SerialHandler(port="/dev/ttyUSB0")
            >>> serial_handler.open()
            >>> at_executor = ATExecutor(serial_handler)
            >>>
            >>> validator = PluginValidator()
            >>> result = validator.test_plugin(plugin, serial_handler, at_executor)
            >>> print(f"Success rate: {result.success_rate():.1%}")
        """
        from src.core.at_executor import ATExecutor

        # Create ATExecutor if not provided
        if at_executor is None:
            at_executor = ATExecutor(serial_handler)

        # Test results tracking
        passed_commands = []
        failed_commands = []
        validation_passed = True
        validation_errors = []

        # Test init sequence if present
        if plugin.connection.init_sequence:
            for init_cmd in plugin.connection.init_sequence:
                cmd = init_cmd['cmd']
                expected = init_cmd.get('expected', 'OK')

                try:
                    response = at_executor.execute_command(cmd, timeout=5)
                    if response.is_successful() and expected in response.raw:
                        passed_commands.append(cmd)
                    else:
                        failed_commands.append(cmd)
                except Exception as e:
                    failed_commands.append(cmd)
                    validation_errors.append(f"Init command '{cmd}' failed: {e}")

        # Test critical commands
        critical_commands = [cmd for cmd in plugin.get_all_commands() if getattr(cmd, 'critical', False)]
        for cmd_def in critical_commands:
            try:
                timeout = cmd_def.timeout if cmd_def.timeout else 30
                response = at_executor.execute_command(cmd_def.cmd, timeout=timeout)

                if response.is_successful():
                    passed_commands.append(cmd_def.cmd)
                else:
                    failed_commands.append(cmd_def.cmd)
            except Exception as e:
                failed_commands.append(cmd_def.cmd)
                validation_errors.append(f"Critical command '{cmd_def.cmd}' failed: {e}")

        # Test validation.required_responses
        if plugin.validation and plugin.validation.required_responses:
            for required_cmd in plugin.validation.required_responses:
                # Skip if already tested
                if required_cmd in passed_commands or required_cmd in failed_commands:
                    continue

                try:
                    response = at_executor.execute_command(required_cmd, timeout=5)
                    if response.is_successful():
                        passed_commands.append(required_cmd)
                    else:
                        failed_commands.append(required_cmd)
                        validation_passed = False
                        validation_errors.append(f"Required command '{required_cmd}' failed")
                except Exception as e:
                    failed_commands.append(required_cmd)
                    validation_passed = False
                    validation_errors.append(f"Required command '{required_cmd}' failed: {e}")

        # Verify manufacturer/model if specified
        if plugin.validation:
            if plugin.validation.expected_manufacturer:
                try:
                    response = at_executor.execute_command("AT+CGMI", timeout=5)
                    if response.is_successful():
                        if plugin.validation.expected_manufacturer not in response.raw:
                            validation_passed = False
                            validation_errors.append(
                                f"Expected manufacturer '{plugin.validation.expected_manufacturer}' not found in response"
                            )
                except Exception as e:
                    validation_errors.append(f"Manufacturer check failed: {e}")

            if plugin.validation.expected_model_pattern:
                try:
                    response = at_executor.execute_command("AT+CGMM", timeout=5)
                    if response.is_successful():
                        pattern = re.compile(plugin.validation.expected_model_pattern)
                        if not pattern.search(response.raw):
                            validation_passed = False
                            validation_errors.append(
                                f"Model does not match pattern '{plugin.validation.expected_model_pattern}'"
                            )
                except Exception as e:
                    validation_errors.append(f"Model check failed: {e}")

        # Create test result
        total_commands = len(passed_commands) + len(failed_commands)
        result = PluginTestResult(
            plugin_name=f"{plugin.metadata.vendor}.{plugin.metadata.model}",
            total_commands=total_commands,
            passed=len(passed_commands),
            failed=len(failed_commands),
            errors=validation_errors
        )

        return result

    def validate_file(self, file_path: Path) -> Tuple[bool, List[str], List[str]]:
        """Validate a plugin YAML file (schema + semantic validation).

        Convenience method that combines schema and semantic validation.

        Args:
            file_path: Path to plugin YAML file.

        Returns:
            Tuple of (is_valid, errors, warnings).
            - is_valid: True if schema validation passed
            - errors: List of schema validation errors
            - warnings: List of semantic validation warnings

        Example:
            >>> validator = PluginValidator()
            >>> is_valid, errors, warnings = validator.validate_file(Path("plugin.yaml"))
            >>> if is_valid:
            ...     print(f"Schema valid, {len(warnings)} warnings")
            ... else:
            ...     print(f"Invalid: {errors}")
        """
        # Read file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()
        except Exception as e:
            return False, [f"Failed to read file: {e}"], []

        # Schema validation
        is_valid, errors = self.validate_schema(yaml_content)
        if not is_valid:
            return False, errors, []

        # Load plugin and perform semantic validation
        try:
            from src.core.plugin_manager import PluginManager
            manager = PluginManager()
            plugin = manager.load_plugin(file_path)
            warnings = self.validate_plugin(plugin)
            return True, [], warnings
        except Exception as e:
            return False, [f"Failed to load plugin for semantic validation: {e}"], []
