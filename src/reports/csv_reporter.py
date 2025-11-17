"""CSV report generator for Excel-compatible spreadsheet output."""

import csv
import time
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import fields

from src.reports.base_reporter import BaseReporter
from src.reports.report_models import ReportResult
from src.parsers.feature_model import ModemFeatures, NetworkTechnology, SIMStatus


class CSVReporter(BaseReporter):
    """Generate CSV reports suitable for Excel/Sheets analysis.

    Creates tabular reports with:
    - Headers: Category, Feature, Value, Confidence, Unit
    - UTF-8-sig encoding with BOM for Excel compatibility
    - List values as comma-separated strings
    - Optional fields as N/A
    - Confidence-based filtering

    The reporter flattens ModemFeatures dataclasses into rows, where each
    feature field becomes a separate row with its category, value, and
    confidence score.

    Example:
        >>> reporter = CSVReporter()
        >>> result = reporter.generate(features, Path("./output.csv"), 0.5)
        >>> if result.success:
        ...     print(f"CSV report saved to {result.output_path}")
    """

    # Category names for feature groups
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
        **kwargs
    ) -> ReportResult:
        """Generate CSV report from modem features.

        Args:
            features: ModemFeatures object from parser layer
            output_path: Path to output CSV file
            confidence_threshold: Minimum confidence score (0.0-1.0) for inclusion
            **kwargs: Additional options (unused for CSV)

        Returns:
            ReportResult with generation metadata

        Example:
            >>> reporter = CSVReporter()
            >>> result = reporter.generate(features, Path('./output.csv'), 0.7)
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

            # Flatten features into CSV rows
            rows = self._flatten_features(features, confidence_threshold)

            # Write CSV with UTF-8-sig encoding (BOM for Excel)
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['Category', 'Feature', 'Value', 'Confidence', 'Unit']
                )

                # Write header
                writer.writeheader()

                # Write data rows
                writer.writerows(rows)

            # Get file size
            file_size = self._get_file_size(output_path)
            generation_time = time.time() - start_time

            # Validate output
            validation_passed, validation_warnings = self.validate_output(output_path)
            warnings.extend(validation_warnings)

            # Add informational warnings
            if len(rows) == 0:
                warnings.append("No features met the confidence threshold")

            return ReportResult(
                output_path=output_path,
                format='csv',
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
                format='csv',
                success=False,
                validation_passed=False,
                warnings=[f"Error generating report: {e}"],
                file_size_bytes=0,
                generation_time_seconds=generation_time
            )

    def validate_output(self, output_path: Path) -> tuple:
        """Validate generated CSV file has correct structure.

        Checks that:
        - File exists and is not empty
        - CSV has correct headers
        - CSV is readable

        Args:
            output_path: Path to CSV file to validate

        Returns:
            Tuple of (validation_passed: bool, warnings: List[str])

        Example:
            >>> reporter = CSVReporter()
            >>> passed, warnings = reporter.validate_output(Path('./report.csv'))
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

        # Try to read CSV and validate headers
        try:
            with open(output_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader, None)

                if not header:
                    return False, ["CSV file has no header"]

                # Validate expected headers
                expected_headers = ['Category', 'Feature', 'Value', 'Confidence', 'Unit']
                if header != expected_headers:
                    return False, [
                        f"CSV headers incorrect. Expected {expected_headers}, "
                        f"got {header}"
                    ]

                # Count rows
                row_count = sum(1 for _ in reader)
                if row_count == 0:
                    warnings.append("CSV file has no data rows")

        except Exception as e:
            return False, [f"Error reading CSV file: {e}"]

        return True, warnings

    def _flatten_features(
        self,
        features: ModemFeatures,
        threshold: float
    ) -> List[Dict[str, str]]:
        """Flatten ModemFeatures into CSV row dictionaries.

        Iterates through all feature categories (basic_info, network_capabilities,
        etc.) and extracts fields with their confidence scores. Filters out fields
        below the confidence threshold.

        Args:
            features: ModemFeatures object to flatten
            threshold: Minimum confidence score for inclusion

        Returns:
            List of dictionaries with keys: Category, Feature, Value, Confidence, Unit

        Example:
            >>> rows = reporter._flatten_features(features, 0.7)
            >>> print(rows[0])
            {'Category': 'Basic Information', 'Feature': 'Manufacturer',
             'Value': 'Quectel', 'Confidence': '0.95', 'Unit': ''}
        """
        rows = []

        # Feature categories to process
        categories = [
            'basic_info',
            'network_capabilities',
            'voice_features',
            'gnss_info',
            'power_management',
            'sim_info'
        ]

        for category_key in categories:
            category_obj = getattr(features, category_key)
            category_name = self.CATEGORY_NAMES.get(category_key, category_key)

            # Extract fields from the category dataclass
            for field_obj in fields(category_obj):
                field_name = field_obj.name

                # Skip confidence fields (these are metadata, not features)
                if field_name.endswith('_confidence'):
                    continue

                # Get field value
                field_value = getattr(category_obj, field_name)

                # Get confidence score (default 1.0 if not present)
                confidence_field = f"{field_name}_confidence"
                confidence = getattr(category_obj, confidence_field, 1.0)

                # Filter by confidence threshold
                if confidence < threshold:
                    continue

                # Format the value
                formatted_value = self._format_value(field_value)

                # Format the field name for display
                display_name = self._format_field_name(field_name)

                # Extract unit if applicable
                unit = self._extract_unit(field_name, field_value)

                # Create row dictionary
                row = {
                    'Category': category_name,
                    'Feature': display_name,
                    'Value': formatted_value,
                    'Confidence': f"{confidence:.2f}",
                    'Unit': unit
                }

                rows.append(row)

        return rows

    def _format_value(self, value: Any) -> str:
        """Format a field value for CSV output.

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

        Converts snake_case to Title Case for better readability.

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
        return "CSVReporter(format=csv)"
