"""JSON Schema validation for Modem Inspector configuration.

Provides schema definition and validation logic with clear error messages for
configuration validation.
"""

import re
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import jsonschema
from jsonschema import Draft7Validator


class ConfigSchema:
    """Configuration schema validator using JSON Schema Draft 7.

    Validates configuration dictionaries against JSON schema with custom
    validators for domain-specific validation (baud rates, URLs, paths).

    Example:
        >>> schema = ConfigSchema.get_schema()
        >>> is_valid, errors = ConfigSchema.validate_config(config_dict)
        >>> if not is_valid:
        >>>     for error in errors:
        >>>         print(error)
    """

    # Valid baud rates for serial communication
    VALID_BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """Get JSON Schema Draft 7 for configuration validation.

        Returns:
            JSON Schema dictionary defining all configuration sections,
            required fields, types, and value constraints.

        Example:
            >>> schema = ConfigSchema.get_schema()
            >>> assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Modem Inspector Configuration",
            "description": "Configuration schema for Modem Inspector application",
            "type": "object",
            "properties": {
                "serial": {
                    "type": "object",
                    "description": "Serial port communication settings",
                    "properties": {
                        "default_baud": {
                            "type": "integer",
                            "description": "Default baud rate for serial communication",
                            "enum": ConfigSchema.VALID_BAUD_RATES
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Command timeout in seconds",
                            "minimum": 1,
                            "maximum": 300
                        },
                        "retry_attempts": {
                            "type": "integer",
                            "description": "Number of retry attempts for failed commands",
                            "minimum": 0,
                            "maximum": 10
                        },
                        "retry_delay": {
                            "type": "integer",
                            "description": "Delay between retries in milliseconds",
                            "minimum": 100,
                            "maximum": 10000
                        }
                    },
                    "additionalProperties": False
                },
                "plugins": {
                    "type": "object",
                    "description": "Plugin discovery and validation settings",
                    "properties": {
                        "directories": {
                            "type": "array",
                            "description": "List of directories to search for plugins",
                            "items": {
                                "type": "string",
                                "minLength": 1
                            },
                            "minItems": 1
                        },
                        "auto_discover": {
                            "type": "boolean",
                            "description": "Automatically discover modem type on connection"
                        },
                        "validation_level": {
                            "type": "string",
                            "description": "Plugin validation strictness level",
                            "enum": ["strict", "warning", "off"]
                        }
                    },
                    "additionalProperties": False
                },
                "repository": {
                    "type": "object",
                    "description": "Plugin repository synchronization settings",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": "Enable plugin repository synchronization"
                        },
                        "api_url": {
                            "type": ["string", "null"],
                            "description": "Repository API URL (HTTP or HTTPS only)",
                            "pattern": "^https?://.*"
                        },
                        "api_token": {
                            "type": ["string", "null"],
                            "description": "Repository API authentication token"
                        },
                        "sync_mode": {
                            "type": "string",
                            "description": "Repository synchronization mode",
                            "enum": ["auto", "manual", "off"]
                        }
                    },
                    "additionalProperties": False
                },
                "reporting": {
                    "type": "object",
                    "description": "Report generation settings",
                    "properties": {
                        "default_format": {
                            "type": "string",
                            "description": "Default report output format",
                            "enum": ["csv", "html", "json", "markdown"]
                        },
                        "output_directory": {
                            "type": "string",
                            "description": "Directory for report output files",
                            "minLength": 1
                        },
                        "timestamp_format": {
                            "type": "string",
                            "description": "Timestamp format for report filenames",
                            "minLength": 1
                        }
                    },
                    "additionalProperties": False
                },
                "logging": {
                    "type": "object",
                    "description": "Communication logging settings",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": "Enable communication logging"
                        },
                        "level": {
                            "type": "string",
                            "description": "Logging level",
                            "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]
                        },
                        "log_to_file": {
                            "type": "boolean",
                            "description": "Enable logging to file"
                        },
                        "log_to_console": {
                            "type": "boolean",
                            "description": "Enable logging to console"
                        },
                        "log_file_path": {
                            "type": ["string", "null"],
                            "description": "Path to log file"
                        },
                        "max_file_size_mb": {
                            "type": "integer",
                            "description": "Maximum log file size in megabytes",
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "backup_count": {
                            "type": "integer",
                            "description": "Number of backup log files to keep",
                            "minimum": 0,
                            "maximum": 100
                        }
                    },
                    "additionalProperties": False
                },
                "parallel": {
                    "type": "object",
                    "description": "Parallel execution settings",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": "Enable parallel command execution"
                        },
                        "max_workers": {
                            "type": "integer",
                            "description": "Maximum number of parallel workers",
                            "minimum": 1,
                            "maximum": 20
                        },
                        "worker_timeout": {
                            "type": "integer",
                            "description": "Worker timeout in seconds",
                            "minimum": 30,
                            "maximum": 3600
                        }
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        }

    @staticmethod
    def validate_config(config: Dict[str, Any], strict: bool = True) -> Tuple[bool, List[str]]:
        """Validate configuration dictionary against schema.

        Args:
            config: Configuration dictionary to validate.
            strict: If True, reject unknown fields. If False, accept with warning.

        Returns:
            Tuple of (is_valid, error_messages).
            - is_valid: True if configuration is valid, False otherwise.
            - error_messages: List of validation error messages (empty if valid).

        Example:
            >>> config = {"serial": {"default_baud": 9600}}
            >>> is_valid, errors = ConfigSchema.validate_config(config)
            >>> assert is_valid

            >>> bad_config = {"serial": {"default_baud": 12345}}
            >>> is_valid, errors = ConfigSchema.validate_config(bad_config)
            >>> assert not is_valid
            >>> assert len(errors) > 0
        """
        schema = ConfigSchema.get_schema()

        # Modify schema for permissive mode
        if not strict:
            schema = ConfigSchema._make_permissive(schema)

        errors: List[str] = []
        validator = Draft7Validator(schema)

        # Collect validation errors
        for error in validator.iter_errors(config):
            error_msg = ConfigSchema._format_error(error, config)
            errors.append(error_msg)

        # Additional custom validation
        custom_errors = ConfigSchema._custom_validation(config)
        errors.extend(custom_errors)

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def _make_permissive(schema: Dict[str, Any]) -> Dict[str, Any]:
        """Make schema permissive by allowing additional properties.

        Args:
            schema: Original schema dictionary.

        Returns:
            Modified schema allowing additional properties.
        """
        import copy
        permissive_schema = copy.deepcopy(schema)

        # Remove additionalProperties: false from all objects
        def remove_additional_properties(obj):
            if isinstance(obj, dict):
                if "additionalProperties" in obj:
                    del obj["additionalProperties"]
                for value in obj.values():
                    remove_additional_properties(value)

        remove_additional_properties(permissive_schema)
        return permissive_schema

    @staticmethod
    def _format_error(error: jsonschema.exceptions.ValidationError,
                      config: Dict[str, Any]) -> str:
        """Format validation error with clear message including field, section, and example.

        Args:
            error: ValidationError from jsonschema.
            config: Configuration dictionary being validated.

        Returns:
            Formatted error message with field name, section, expected value, and example.

        Example:
            "Section 'serial', field 'default_baud': Expected one of [9600, 19200, 38400,
             57600, 115200, 230400, 460800, 921600], got 12345. Example: default_baud: 115200"
        """
        # Determine field path
        path_parts = list(error.path)
        if len(path_parts) == 0:
            section = "root"
            field = "configuration"
        elif len(path_parts) == 1:
            section = path_parts[0]
            field = "section"
        else:
            section = path_parts[0]
            field = ".".join(str(p) for p in path_parts[1:])

        # Build error message based on validation type
        if error.validator == "type":
            expected_type = error.validator_value
            actual_value = error.instance
            actual_type = type(actual_value).__name__
            return (f"Section '{section}', field '{field}': Expected type {expected_type}, "
                   f"got {actual_type} (value: {actual_value}). "
                   f"Example: {field}: <{expected_type} value>")

        elif error.validator == "enum":
            expected_values = error.validator_value
            actual_value = error.instance
            example_value = expected_values[0] if expected_values else "N/A"
            return (f"Section '{section}', field '{field}': Expected one of {expected_values}, "
                   f"got {actual_value}. Example: {field}: {example_value}")

        elif error.validator == "minimum":
            minimum = error.validator_value
            actual_value = error.instance
            return (f"Section '{section}', field '{field}': Value must be >= {minimum}, "
                   f"got {actual_value}. Example: {field}: {minimum}")

        elif error.validator == "maximum":
            maximum = error.validator_value
            actual_value = error.instance
            return (f"Section '{section}', field '{field}': Value must be <= {maximum}, "
                   f"got {actual_value}. Example: {field}: {maximum}")

        elif error.validator == "minLength":
            min_length = error.validator_value
            actual_value = error.instance
            return (f"Section '{section}', field '{field}': String must be at least "
                   f"{min_length} characters, got {len(actual_value)}. "
                   f"Example: {field}: 'valid_value'")

        elif error.validator == "pattern":
            pattern = error.validator_value
            actual_value = error.instance
            return (f"Section '{section}', field '{field}': Value '{actual_value}' does not "
                   f"match pattern {pattern}. Example: {field}: 'https://example.com'")

        elif error.validator == "minItems":
            min_items = error.validator_value
            actual_count = len(error.instance)
            return (f"Section '{section}', field '{field}': Array must have at least "
                   f"{min_items} items, got {actual_count}. "
                   f"Example: {field}: ['./plugins']")

        elif error.validator == "additionalProperties":
            extra_props = set(error.instance.keys()) - set(error.schema.get('properties', {}).keys())
            return (f"Section '{section}': Unknown fields {list(extra_props)} not allowed. "
                   f"Remove unknown fields or use permissive validation mode.")

        else:
            # Generic error message
            return f"Section '{section}', field '{field}': {error.message}"

    @staticmethod
    def _custom_validation(config: Dict[str, Any]) -> List[str]:
        """Perform custom validation beyond JSON schema.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            List of validation error messages.
        """
        errors = []

        # Validate baud rate if present
        if "serial" in config and isinstance(config["serial"], dict):
            if "default_baud" in config["serial"]:
                baud = config["serial"]["default_baud"]
                if not ConfigSchema.validate_baud_rate(baud):
                    errors.append(
                        f"Section 'serial', field 'default_baud': Baud rate {baud} is not "
                        f"a standard rate. Valid rates: {ConfigSchema.VALID_BAUD_RATES}. "
                        f"Example: default_baud: 115200"
                    )

        # Validate repository URL if present
        if "repository" in config and isinstance(config["repository"], dict):
            if "api_url" in config["repository"]:
                url = config["repository"]["api_url"]
                if url is not None and not ConfigSchema.validate_url(url):
                    errors.append(
                        f"Section 'repository', field 'api_url': URL '{url}' must use "
                        f"HTTP or HTTPS protocol. Example: api_url: 'https://api.example.com'"
                    )

        # Validate paths if present
        if "reporting" in config and isinstance(config["reporting"], dict):
            if "output_directory" in config["reporting"]:
                path = config["reporting"]["output_directory"]
                if not ConfigSchema.validate_path(path):
                    errors.append(
                        f"Section 'reporting', field 'output_directory': Path '{path}' "
                        f"contains invalid characters. Example: output_directory: './reports'"
                    )

        if "logging" in config and isinstance(config["logging"], dict):
            if "log_file_path" in config["logging"]:
                path = config["logging"]["log_file_path"]
                if path is not None and not ConfigSchema.validate_path(path):
                    errors.append(
                        f"Section 'logging', field 'log_file_path': Path '{path}' "
                        f"contains invalid characters. Example: log_file_path: './logs/comm.log'"
                    )

        return errors

    @staticmethod
    def validate_baud_rate(baud: int) -> bool:
        """Validate baud rate is a standard serial communication rate.

        Args:
            baud: Baud rate to validate.

        Returns:
            True if baud rate is valid (9600, 19200, 38400, 57600, 115200,
            230400, 460800, 921600), False otherwise.

        Example:
            >>> ConfigSchema.validate_baud_rate(115200)
            True
            >>> ConfigSchema.validate_baud_rate(12345)
            False
        """
        return baud in ConfigSchema.VALID_BAUD_RATES

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL uses HTTP or HTTPS protocol.

        Args:
            url: URL to validate.

        Returns:
            True if URL starts with http:// or https://, False otherwise.

        Example:
            >>> ConfigSchema.validate_url("https://api.example.com")
            True
            >>> ConfigSchema.validate_url("ftp://example.com")
            False
        """
        if not url:
            return False

        # Check for HTTP/HTTPS protocol
        url_pattern = re.compile(r'^https?://.+', re.IGNORECASE)
        return bool(url_pattern.match(url))

    @staticmethod
    def validate_path(path: str) -> bool:
        """Validate path format (basic validation for invalid characters).

        Args:
            path: File system path to validate.

        Returns:
            True if path format is valid, False otherwise.

        Example:
            >>> ConfigSchema.validate_path("./reports")
            True
            >>> ConfigSchema.validate_path("/var/log/modem.log")
            True
            >>> ConfigSchema.validate_path("")
            False
        """
        if not path:
            return False

        # Check for obviously invalid characters (null bytes, etc.)
        # More permissive validation - just check for null bytes and other control chars
        invalid_chars = ['\0', '\r', '\n']
        if any(char in path for char in invalid_chars):
            return False

        # Path should not be just whitespace
        if path.strip() == "":
            return False

        return True
