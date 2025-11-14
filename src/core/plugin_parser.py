"""Plugin-based response parsing module.

Provides flexible parsing of AT command responses using plugin-defined parsers,
supporting regex, JSON, and custom Python function parsers.
"""

import re
import json
import importlib
from typing import Dict, Any, Optional, Union
from src.core.plugin import Plugin, ParserDefinition, ParserType
from src.core.command_response import CommandResponse
from src.core.exceptions import ParserError


class PluginParser:
    """Parses AT command responses using plugin-defined parsers.

    Supports three parser types:
    1. REGEX: Regular expression with named capture groups
    2. JSON: JSON response parsing with optional path extraction
    3. CUSTOM: Custom Python function parser loaded dynamically

    Implements graceful degradation - returns raw response on parser failure.

    Example:
        >>> parser = PluginParser(plugin)
        >>> response = at_executor.execute_command("AT+CSQ")
        >>> parsed = parser.parse_response(response, "signal_parser")
        >>> print(parsed)  # {'rssi': 25, 'ber': 99}
    """

    def __init__(self, plugin: Plugin):
        """Initialize parser with plugin configuration.

        Args:
            plugin: Plugin object containing parser definitions.
        """
        self.plugin = plugin
        self._custom_parser_cache: Dict[str, Any] = {}

    def parse_response(
        self,
        response: CommandResponse,
        parser_name: Optional[str] = None
    ) -> Union[Dict[str, Any], str]:
        """Parse AT command response using specified parser.

        Args:
            response: CommandResponse object from AT executor.
            parser_name: Name of parser to use (from plugin.parsers). If None, returns raw response.

        Returns:
            Parsed data (dict, list, or string) or raw response on failure.

        Example:
            >>> response = at_executor.execute_command("AT+CSQ")
            >>> parsed = parser.parse_response(response, "signal_parser")
            >>> print(parsed['rssi'])  # 25
        """
        # If no parser specified, return raw response
        if not parser_name:
            return response.raw

        # Get parser definition
        parser_def = self.plugin.get_parser(parser_name)
        if not parser_def:
            print(f"Warning: Parser '{parser_name}' not found, returning raw response")
            return response.raw

        # Check if response was successful
        if not response.is_successful():
            return response.raw

        # Dispatch to appropriate parser
        try:
            if parser_def.type == ParserType.REGEX:
                result = self._parse_regex(response.raw, parser_def)
            elif parser_def.type == ParserType.JSON:
                result = self._parse_json(response.raw, parser_def)
            elif parser_def.type == ParserType.CUSTOM:
                result = self._parse_custom(response.raw, parser_def)
            elif parser_def.type == ParserType.NONE:
                result = response.raw
            else:
                print(f"Warning: Unknown parser type '{parser_def.type}', returning raw response")
                result = response.raw

            # Append unit if specified
            if parser_def.unit and isinstance(result, dict):
                # Add unit to all numeric values
                for key, value in result.items():
                    if isinstance(value, (int, float)):
                        result[f"{key}_unit"] = parser_def.unit

            return result

        except Exception as e:
            # Graceful degradation: log error and return raw response
            print(f"Warning: Parser '{parser_name}' failed: {e}")
            return response.raw

    def _parse_regex(self, raw_response: str, parser_def: ParserDefinition) -> Union[Dict[str, Any], str]:
        """Parse response using regular expression.

        Args:
            raw_response: Raw AT command response string.
            parser_def: Parser definition with regex pattern and groups.

        Returns:
            Dictionary of named groups or raw response if no match.

        Example:
            Pattern: "\\+CSQ: (\\d+),(\\d+)"
            Groups: ["rssi", "ber"]
            Result: {"rssi": "25", "ber": "99"}
        """
        if not parser_def.pattern:
            return raw_response

        try:
            # Compile regex pattern
            pattern = re.compile(parser_def.pattern, re.MULTILINE | re.DOTALL)

            # Try to match
            match = pattern.search(raw_response)
            if not match:
                return raw_response

            # Extract named groups or numbered groups
            if parser_def.groups:
                # Map groups to names
                result = {}
                for idx, group_name in enumerate(parser_def.groups, start=1):
                    try:
                        group_value = match.group(idx)
                        # Try to convert to int/float if possible
                        try:
                            if '.' in str(group_value):
                                result[group_name] = float(group_value)
                            else:
                                result[group_name] = int(group_value)
                        except (ValueError, TypeError):
                            result[group_name] = group_value
                    except IndexError:
                        # Group not found, skip
                        pass
                return result
            else:
                # Return all matched groups as dict (using named groups if present)
                if match.groupdict():
                    return match.groupdict()
                else:
                    # Return numbered groups as list
                    return {f"group_{i}": g for i, g in enumerate(match.groups(), start=1)}

        except re.error as e:
            raise ParserError(f"Invalid regex pattern: {e}")

    def _parse_json(self, raw_response: str, parser_def: ParserDefinition) -> Union[Dict[str, Any], Any]:
        """Parse JSON response.

        Args:
            raw_response: Raw AT command response string.
            parser_def: Parser definition with optional json_path.

        Returns:
            Parsed JSON object or raw response if invalid JSON.

        Example:
            Response: '{"signal": {"rssi": -75, "ber": 0}}'
            JSON Path: "signal"
            Result: {"rssi": -75, "ber": 0}
        """
        try:
            # Find JSON in response (may have AT command echo before it)
            json_start = raw_response.find('{')
            if json_start == -1:
                json_start = raw_response.find('[')
            if json_start == -1:
                return raw_response

            # Extract JSON portion
            json_str = raw_response[json_start:]

            # Parse JSON
            parsed = json.loads(json_str)

            # Apply JSON path if specified
            if parser_def.json_path:
                keys = parser_def.json_path.split('.')
                for key in keys:
                    if isinstance(parsed, dict) and key in parsed:
                        parsed = parsed[key]
                    else:
                        return raw_response  # Path not found

            return parsed

        except json.JSONDecodeError:
            return raw_response

    def _parse_custom(self, raw_response: str, parser_def: ParserDefinition) -> Any:
        """Parse using custom Python parser function.

        Args:
            raw_response: Raw AT command response string.
            parser_def: Parser definition with module and function names.

        Returns:
            Result from custom parser function or raw response on error.

        Example:
            Module: "parsers.custom.signal"
            Function: "parse_signal_quality"
            Result: Custom parser return value
        """
        if not parser_def.module or not parser_def.function:
            raise ParserError("Custom parser requires 'module' and 'function' fields")

        # Check cache first
        cache_key = f"{parser_def.module}.{parser_def.function}"
        if cache_key in self._custom_parser_cache:
            parser_func = self._custom_parser_cache[cache_key]
        else:
            # Load module dynamically
            try:
                module = importlib.import_module(parser_def.module)
                parser_func = getattr(module, parser_def.function)
                self._custom_parser_cache[cache_key] = parser_func
            except ImportError as e:
                raise ParserError(f"Failed to import custom parser module '{parser_def.module}': {e}")
            except AttributeError as e:
                raise ParserError(f"Function '{parser_def.function}' not found in module '{parser_def.module}': {e}")

        # Call custom parser function
        try:
            result = parser_func(raw_response)
            return result
        except Exception as e:
            raise ParserError(f"Custom parser '{cache_key}' failed: {e}")

    def _load_custom_parser(self, module_name: str, function_name: str) -> Any:
        """Load custom parser function from module.

        Args:
            module_name: Python module path (e.g., "parsers.custom.signal").
            function_name: Function name within module.

        Returns:
            Callable parser function.

        Raises:
            ParserError: If module or function cannot be loaded.
        """
        cache_key = f"{module_name}.{function_name}"

        # Check cache
        if cache_key in self._custom_parser_cache:
            return self._custom_parser_cache[cache_key]

        # Load module
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ParserError(f"Failed to import custom parser module '{module_name}': {e}")

        # Get function
        try:
            parser_func = getattr(module, function_name)
        except AttributeError:
            raise ParserError(f"Function '{function_name}' not found in module '{module_name}'")

        # Cache and return
        self._custom_parser_cache[cache_key] = parser_func
        return parser_func

    def clear_cache(self):
        """Clear custom parser cache.

        Useful for reloading parsers during development or testing.
        """
        self._custom_parser_cache.clear()

    def get_cached_parsers(self) -> Dict[str, Any]:
        """Get currently cached custom parsers.

        Returns:
            Dictionary of cached parser functions keyed by module.function.
        """
        return self._custom_parser_cache.copy()
