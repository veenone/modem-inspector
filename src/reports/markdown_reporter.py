"""Markdown report generator with Jinja2 template rendering.

This module provides Markdown report generation with customizable templates,
comprehensive validation, and GitHub-flavored markdown support.
"""

import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

try:
    from importlib.resources import files, as_file
except ImportError:
    # Fallback for Python < 3.9
    from importlib.resources import read_text

import jinja2
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound, TemplateSyntaxError

from src.reports.base_reporter import BaseReporter
from src.reports.report_models import ReportResult
from src.parsers.feature_model import ModemFeatures, NetworkTechnology, SIMStatus
from dataclasses import fields


class MarkdownReporter(BaseReporter):
    """Generate Markdown reports with Jinja2 template rendering.

    Creates professional Markdown reports with:
    - Jinja2 template rendering (no autoescaping for Markdown)
    - Embedded default template with GitHub-flavored markdown
    - Support for custom template loading from file path
    - Automatic Markdown validation (headers, tables)
    - Confidence-based filtering with visual indicators
    - GitHub-compatible table formatting

    The reporter uses the same value formatting and category structure as
    CSVReporter and HTMLReporter for consistency across report formats.

    Example:
        >>> reporter = MarkdownReporter()
        >>> result = reporter.generate(
        ...     features,
        ...     Path("./output.md"),
        ...     confidence_threshold=0.5,
        ...     template="custom_template.j2"
        ... )
        >>> if result.success:
        ...     print(f"Markdown report saved to {result.output_path}")
    """

    # Category names for feature groups (same as CSVReporter and HTMLReporter)
    CATEGORY_NAMES = {
        "basic_info": "Basic Information",
        "network_capabilities": "Network Capabilities",
        "voice_features": "Voice Features",
        "gnss_info": "GNSS/GPS Information",
        "power_management": "Power Management",
        "sim_info": "SIM Information",
    }

    def generate(
        self,
        features: ModemFeatures,
        output_path: Path,
        confidence_threshold: float = 0.0,
        template: Optional[str] = None,
        **kwargs
    ) -> ReportResult:
        """Generate Markdown report from modem features.

        Args:
            features: ModemFeatures object from parser layer
            output_path: Path to output Markdown file
            confidence_threshold: Minimum confidence score (0.0-1.0) for inclusion
            template: Optional custom template file path
            **kwargs: Additional template context variables

        Returns:
            ReportResult with generation metadata

        Example:
            >>> reporter = MarkdownReporter()
            >>> result = reporter.generate(
            ...     features,
            ...     Path('./output.md'),
            ...     confidence_threshold=0.7,
            ...     template="my_template.j2"
            ... )
            >>> if result.success:
            ...     print(f"Report saved to {result.output_path}")
        """
        start_time = time.time()
        warnings = []

        try:
            # Validate confidence threshold
            self._validate_confidence_threshold(confidence_threshold)

            # Ensure output directory exists
            self._ensure_directory(output_path)

            # Load template (custom or default)
            try:
                jinja_template = self._load_template(template)
            except Exception as e:
                warnings.append(f"Template loading warning: {e}, using default template")
                jinja_template = self._load_template(None)

            # Prepare template context
            context = self._prepare_context(features, confidence_threshold)

            # Add any additional kwargs to context
            context.update(kwargs)

            # Render template
            try:
                markdown_content = jinja_template.render(**context)
            except Exception as e:
                return ReportResult(
                    output_path=output_path,
                    format='markdown',
                    success=False,
                    validation_passed=False,
                    warnings=[f"Template rendering error: {e}"],
                    file_size_bytes=0,
                    generation_time_seconds=time.time() - start_time
                )

            # Write Markdown to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            # Get file size
            file_size = self._get_file_size(output_path)
            generation_time = time.time() - start_time

            # Validate output
            validation_passed, validation_warnings = self.validate_output(output_path)
            warnings.extend(validation_warnings)

            # Add informational warnings
            if context['total_features'] == 0:
                warnings.append("No features met the confidence threshold")

            return ReportResult(
                output_path=output_path,
                format='markdown',
                success=True,
                validation_passed=validation_passed,
                warnings=warnings,
                file_size_bytes=file_size,
                generation_time_seconds=generation_time
            )

        except Exception as e:
            generation_time = time.time() - start_time
            return ReportResult(
                output_path=output_path,
                format='markdown',
                success=False,
                validation_passed=False,
                warnings=[f"Error generating report: {e}"],
                file_size_bytes=0,
                generation_time_seconds=generation_time
            )

    def validate_output(self, output_path: Path) -> Tuple[bool, List[str]]:
        """Validate generated Markdown file has correct structure.

        Performs basic Markdown validation by checking for:
        - File exists and is not empty
        - Markdown headers (# syntax)
        - Pipe tables (| syntax) if features present
        - Basic structure elements

        Args:
            output_path: Path to Markdown file to validate

        Returns:
            Tuple of (validation_passed: bool, warnings: List[str])

        Example:
            >>> reporter = MarkdownReporter()
            >>> passed, warnings = reporter.validate_output(Path('./report.md'))
            >>> if not passed:
            ...     print(f"Validation failed: {warnings}")
        """
        warnings = []

        # Check file exists
        if not output_path.exists():
            return False, ["Output file does not exist"]

        # Check file is not empty
        if output_path.stat().st_size == 0:
            return False, ["Output file is empty"]

        # Read and validate Markdown structure
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for basic content
            if len(content.strip()) < 50:
                warnings.append("Markdown file seems unusually small")

            # Check for Markdown headers
            header_pattern = re.compile(r'^#{1,6}\s+.+', re.MULTILINE)
            headers = header_pattern.findall(content)

            if not headers:
                warnings.append("No Markdown headers found (# syntax)")

            # Check for pipe tables (if there's feature data)
            if '|' in content:
                # Validate table structure (basic check)
                table_lines = [line for line in content.split('\n') if '|' in line]
                if table_lines:
                    # Check for table header separator (e.g., |---|---|)
                    separator_pattern = re.compile(r'\|[\s-]+\|')
                    has_separator = any(separator_pattern.search(line) for line in table_lines)
                    if not has_separator:
                        warnings.append("Pipe tables detected but no header separator found")
            else:
                # If no pipe symbols, might not have any features
                if 'No features' not in content and 'total_features' not in content:
                    warnings.append("No pipe tables found - report may be missing feature data")

            # Check for basic Markdown structure elements
            if '---' not in content:
                warnings.append("No horizontal rules (---) found - may be missing section separators")

            # Check for title (should have at least one # header at the start)
            first_header_match = re.search(r'^#\s+.+', content, re.MULTILINE)
            if not first_header_match:
                warnings.append("No main title (# header) found at document start")

        except Exception as e:
            return False, [f"Error reading Markdown file: {e}"]

        # Return True if no critical errors, even if there are warnings
        return True, warnings

    def _load_template(self, template_path: Optional[str] = None) -> Template:
        """Load Jinja2 template from file or use embedded default.

        Loads custom template from file path if provided, otherwise loads
        the embedded default template. Falls back to default on any errors.

        Args:
            template_path: Optional path to custom template file

        Returns:
            Jinja2 Template object without autoescaping (Markdown doesn't need it)

        Raises:
            Exception: If both custom and default template loading fail

        Example:
            >>> reporter = MarkdownReporter()
            >>> template = reporter._load_template("custom.j2")
            >>> markdown = template.render(modem_id="Test", ...)
        """
        # Create Jinja2 environment without autoescape (Markdown doesn't need it)
        env = Environment(autoescape=False)

        # If custom template path provided, try to load it
        if template_path:
            try:
                template_file = Path(template_path)

                if not template_file.exists():
                    raise FileNotFoundError(f"Template file not found: {template_path}")

                # Create environment with file system loader
                env = Environment(
                    loader=FileSystemLoader(str(template_file.parent)),
                    autoescape=False
                )

                return env.get_template(template_file.name)

            except (TemplateNotFound, TemplateSyntaxError, FileNotFoundError) as e:
                # Fall back to default template
                raise Exception(f"Custom template error: {e}") from e

        # Load embedded default template
        try:
            # Try modern importlib.resources approach (Python 3.9+)
            try:
                template_files = files('src.reports.templates')
                with as_file(template_files.joinpath('default_markdown.j2')) as template_file:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_content = f.read()
            except (NameError, AttributeError):
                # Fallback for Python < 3.9
                template_content = read_text('src.reports.templates', 'default_markdown.j2')

            return env.from_string(template_content)

        except Exception as e:
            # Last resort: try to read from relative path
            try:
                default_template_path = Path(__file__).parent / 'templates' / 'default_markdown.j2'
                with open(default_template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                return env.from_string(template_content)
            except Exception as fallback_error:
                raise Exception(
                    f"Failed to load default template. "
                    f"Primary error: {e}, Fallback error: {fallback_error}"
                ) from fallback_error

    def _prepare_context(
        self,
        features: ModemFeatures,
        confidence_threshold: float
    ) -> Dict[str, Any]:
        """Prepare template context from ModemFeatures.

        Extracts and formats all feature data into a dictionary suitable
        for template rendering. Includes metadata, statistics, categorized
        features, error/warning information, and JSON-formatted vendor data.

        Args:
            features: ModemFeatures object to extract data from
            confidence_threshold: Minimum confidence for feature inclusion

        Returns:
            Dictionary with template context variables

        Example:
            >>> reporter = MarkdownReporter()
            >>> context = reporter._prepare_context(features, 0.7)
            >>> print(context['modem_id'])
            'Quectel EC25'
            >>> print(context['total_features'])
            42
        """
        # Extract modem ID from basic info
        manufacturer = features.basic_info.manufacturer or "Unknown"
        model = features.basic_info.model or "Unknown"
        modem_id = f"{manufacturer} {model}".strip()

        # Generate timestamp
        generation_time = self._format_timestamp()

        # Calculate statistics
        total_features = 0
        high_confidence_count = 0

        # Build categories list
        categories = []

        category_keys = [
            'basic_info',
            'network_capabilities',
            'voice_features',
            'gnss_info',
            'power_management',
            'sim_info'
        ]

        for category_key in category_keys:
            category_obj = getattr(features, category_key)
            category_name = self.CATEGORY_NAMES.get(category_key, category_key)

            category_features = []

            # Extract fields from the category dataclass
            for field_obj in fields(category_obj):
                field_name = field_obj.name

                # Skip confidence fields
                if field_name.endswith('_confidence'):
                    continue

                # Get field value
                field_value = getattr(category_obj, field_name)

                # Get confidence score
                confidence_field = f"{field_name}_confidence"
                confidence = getattr(category_obj, confidence_field, 1.0)

                # Filter by confidence threshold
                if confidence < confidence_threshold:
                    continue

                total_features += 1

                if confidence >= 0.7:
                    high_confidence_count += 1

                # Format the value
                formatted_value = self._format_value(field_value)

                # Format the field name
                display_name = self._format_field_name(field_name)

                # Extract unit
                unit = self._extract_unit(field_name, field_value)

                # Add feature to category
                category_features.append({
                    'name': display_name,
                    'value': formatted_value,
                    'confidence': confidence,
                    'unit': unit
                })

            # Add category to list
            categories.append({
                'name': category_name,
                'features': category_features
            })

        # Prepare vendor_specific_json for code block rendering
        vendor_specific_json = json.dumps(features.vendor_specific, indent=2) if features.vendor_specific else ""

        # Build context dictionary
        context = {
            'modem_id': modem_id,
            'generation_time': generation_time,
            'confidence_threshold': confidence_threshold,
            'total_features': total_features,
            'aggregate_confidence': features.aggregate_confidence,
            'high_confidence_count': high_confidence_count,
            'categories': categories,
            'parsing_errors': features.parsing_errors,
            'warnings': [],  # Additional warnings can be added by caller
            'vendor_specific': features.vendor_specific,
            'vendor_specific_json': vendor_specific_json,
        }

        return context

    def _format_value(self, value: Any) -> str:
        """Format a field value for Markdown output.

        Handles different value types:
        - Lists: Comma-separated string
        - None: "N/A"
        - Booleans: "Yes"/"No"
        - Enums: String value
        - Others: String representation

        Args:
            value: Field value to format

        Returns:
            Formatted string value

        Example:
            >>> reporter._format_value([1, 3, 7, 20])
            '1, 3, 7, 20'
            >>> reporter._format_value(True)
            'Yes'
            >>> reporter._format_value(None)
            'N/A'
        """
        if value is None:
            return "N/A"

        if isinstance(value, bool):
            return "Yes" if value else "No"

        if isinstance(value, list):
            if not value:
                return "N/A"
            # Format list items, handling enums
            formatted_items = []
            for item in value:
                if isinstance(item, (NetworkTechnology, SIMStatus)):
                    formatted_items.append(item.value)
                else:
                    formatted_items.append(str(item))
            return ", ".join(formatted_items)

        if isinstance(value, (NetworkTechnology, SIMStatus)):
            return value.value

        return str(value)

    def _format_field_name(self, field_name: str) -> str:
        """Format field name for display.

        Converts snake_case to Title Case for better readability,
        handling common acronyms appropriately.

        Args:
            field_name: Field name in snake_case

        Returns:
            Formatted field name in Title Case

        Example:
            >>> reporter._format_field_name("max_downlink_speed")
            'Max Downlink Speed'
            >>> reporter._format_field_name("imei")
            'IMEI'
        """
        # Handle common acronyms
        acronyms = {
            'imei': 'IMEI',
            'imsi': 'IMSI',
            'iccid': 'ICCID',
            'gnss': 'GNSS',
            'gps': 'GPS',
            'lte': 'LTE',
            'volte': 'VoLTE',
            'vowifi': 'VoWiFi',
            'psm': 'PSM',
            'edrx': 'eDRX',
            'sim': 'SIM',
            'fiveg': '5G',
        }

        # Split on underscores and capitalize
        parts = field_name.split('_')
        formatted_parts = []

        for part in parts:
            # Check if part is an acronym
            if part.lower() in acronyms:
                formatted_parts.append(acronyms[part.lower()])
            else:
                formatted_parts.append(part.capitalize())

        return ' '.join(formatted_parts)

    def _extract_unit(self, field_name: str, value: Any) -> str:
        """Extract unit of measurement from field name or value.

        Args:
            field_name: Name of the field
            value: Field value (may contain unit information)

        Returns:
            Unit string, or empty string if no unit applicable

        Example:
            >>> reporter._extract_unit("battery_voltage", 3800)
            'mV'
            >>> reporter._extract_unit("max_downlink_speed", "150 Mbps")
            'Mbps'
        """
        # Common unit mappings based on field names
        unit_mappings = {
            'battery_voltage': 'mV',
            'max_downlink_speed': 'Mbps',
            'max_uplink_speed': 'Mbps',
        }

        # Check if field has a known unit
        if field_name in unit_mappings:
            return unit_mappings[field_name]

        # Try to extract unit from value string
        if isinstance(value, str):
            # Common units to look for
            units = ['Mbps', 'Gbps', 'kbps', 'MHz', 'GHz', 'dBm', 'mV', 'V', 'mA', 'A']
            for unit in units:
                if unit in value:
                    return unit

        return ''

    def __repr__(self) -> str:
        """String representation of reporter."""
        return "MarkdownReporter(format=markdown)"
