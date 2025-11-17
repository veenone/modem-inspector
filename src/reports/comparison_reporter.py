"""Comparison report generator for comparing features across multiple modems.

This module provides comparison report generation with support for CSV, HTML,
and Markdown output formats. It compares features across multiple ModemFeatures
instances and highlights differences and commonalities.
"""

import csv
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import fields

from src.reports.base_reporter import BaseReporter
from src.reports.report_models import ReportResult
from src.parsers.feature_model import ModemFeatures, NetworkTechnology, SIMStatus


class ComparisonReporter(BaseReporter):
    """Generate comparison reports across multiple modems.

    Creates comparison reports with:
    - Support for CSV, HTML, and Markdown output formats
    - Side-by-side feature comparison across modems
    - Status indicators (same, different, partial)
    - Confidence score reporting
    - Summary statistics

    The reporter compares features across multiple ModemFeatures instances
    and highlights differences, commonalities, and partial matches.

    Example:
        >>> reporter = ComparisonReporter()
        >>> features_list = [
        ...     ("Modem1", features1),
        ...     ("Modem2", features2),
        ...     ("Modem3", features3)
        ... ]
        >>> result = reporter.generate(
        ...     features_list,
        ...     Path("./comparison.csv"),
        ...     confidence_threshold=0.5,
        ...     format='csv'
        ... )
        >>> if result.success:
        ...     print(f"Comparison report saved to {result.output_path}")
    """

    # Category names for feature groups (consistent with other reporters)
    CATEGORY_NAMES = {
        "basic_info": "Basic Information",
        "network_capabilities": "Network Capabilities",
        "voice_features": "Voice Features",
        "gnss_info": "GNSS/GPS Information",
        "power_management": "Power Management",
        "sim_info": "SIM Information",
    }

    def __init__(self):
        """Initialize comparison reporter."""
        pass

    def generate(
        self,
        features_list: List[Tuple[str, ModemFeatures]],
        output_path: Path,
        confidence_threshold: float = 0.0,
        format: str = 'csv',
        **kwargs
    ) -> ReportResult:
        """Generate comparison report.

        Args:
            features_list: List of (modem_id, ModemFeatures) tuples
            output_path: Path to output file
            confidence_threshold: Minimum confidence score (0.0-1.0)
            format: Output format ('csv', 'html', 'markdown')
            **kwargs: Additional format-specific options

        Returns:
            ReportResult with generation metadata

        Raises:
            ValueError: If less than 2 modems provided or invalid format

        Example:
            >>> reporter = ComparisonReporter()
            >>> features_list = [("M1", f1), ("M2", f2)]
            >>> result = reporter.generate(
            ...     features_list,
            ...     Path('./comparison.csv'),
            ...     format='csv'
            ... )
        """
        start_time = time.time()
        warnings = []

        try:
            # Validate inputs
            self._validate_confidence_threshold(confidence_threshold)

            if len(features_list) < 2:
                raise ValueError("Comparison requires at least 2 modems")

            if format not in ['csv', 'html', 'markdown']:
                raise ValueError(f"Invalid format: {format}. Must be 'csv', 'html', or 'markdown'")

            # Ensure output directory exists
            self._ensure_directory(output_path)

            # Compare features across all modems
            comparison_data = self._compare_features(features_list, confidence_threshold)

            # Generate report based on format
            if format == 'csv':
                result = self._generate_csv_comparison(comparison_data, output_path)
            elif format == 'html':
                result = self._generate_html_comparison(comparison_data, output_path)
            elif format == 'markdown':
                result = self._generate_markdown_comparison(comparison_data, output_path)
            else:
                raise ValueError(f"Unsupported format: {format}")

            return result

        except Exception as e:
            generation_time = time.time() - start_time
            return ReportResult(
                output_path=output_path,
                format=format,
                success=False,
                validation_passed=False,
                warnings=[],
                file_size_bytes=0,
                generation_time_seconds=generation_time,
                error_message=str(e)
            )

    def validate_output(self, output_path: Path) -> Tuple[bool, List[str]]:
        """Validate comparison report output.

        Checks format-specific validation based on file extension.

        Args:
            output_path: Path to report file to validate

        Returns:
            Tuple of (is_valid, error_messages)

        Example:
            >>> reporter = ComparisonReporter()
            >>> is_valid, errors = reporter.validate_output(Path("comparison.csv"))
        """
        warnings = []

        # Check file exists
        if not output_path.exists():
            return False, ["Output file does not exist"]

        # Check file is not empty
        if output_path.stat().st_size == 0:
            return False, ["Output file is empty"]

        # Format-specific validation based on extension
        ext = output_path.suffix.lower()

        if ext == '.csv':
            return self._validate_csv_output(output_path)
        elif ext in ['.html', '.htm']:
            return self._validate_html_output(output_path)
        elif ext in ['.md', '.markdown']:
            return self._validate_markdown_output(output_path)
        else:
            warnings.append(f"Unknown file extension: {ext}")
            return True, warnings

    def _compare_features(
        self,
        features_list: List[Tuple[str, ModemFeatures]],
        threshold: float
    ) -> Dict[str, Any]:
        """Compare features across all modems.

        Args:
            features_list: List of (modem_id, ModemFeatures) tuples
            threshold: Minimum confidence threshold

        Returns:
            Comparison data structure with modem IDs, categories, and summary

        Example structure:
            {
                'modem_ids': ['Modem1', 'Modem2', ...],
                'categories': {
                    'Basic Information': [
                        {
                            'feature': 'Manufacturer',
                            'values': ['Quectel', 'Sierra', ...],
                            'confidences': [0.95, 0.90, ...],
                            'all_same': False,
                            'status': 'different'
                        }
                    ]
                },
                'summary': {
                    'total_modems': 3,
                    'total_features': 45,
                    'identical_features': 12,
                    'different_features': 20,
                    'partial_features': 13
                }
            }
        """
        modem_ids = [modem_id for modem_id, _ in features_list]
        comparison_data = {
            'modem_ids': modem_ids,
            'categories': {},
            'summary': {
                'total_modems': len(features_list),
                'total_features': 0,
                'identical_features': 0,
                'different_features': 0,
                'partial_features': 0
            }
        }

        # Feature categories to process
        categories = [
            'basic_info',
            'network_capabilities',
            'voice_features',
            'gnss_info',
            'power_management',
            'sim_info'
        ]

        # Process each category
        for category_key in categories:
            category_name = self.CATEGORY_NAMES.get(category_key, category_key)
            category_features = []

            # Get the first modem's category object to extract field names
            first_features = features_list[0][1]
            first_category_obj = getattr(first_features, category_key)

            # Iterate through all fields in this category
            for field_obj in fields(first_category_obj):
                field_name = field_obj.name

                # Skip confidence fields
                if field_name.endswith('_confidence'):
                    continue

                # Collect values and confidences from all modems
                values = []
                confidences = []
                present_count = 0

                for modem_id, features in features_list:
                    category_obj = getattr(features, category_key)
                    field_value = getattr(category_obj, field_name)

                    # Get confidence score
                    confidence_field = f"{field_name}_confidence"
                    confidence = getattr(category_obj, confidence_field, 1.0)

                    # Check if value meets threshold and is present
                    if confidence >= threshold:
                        formatted_value = self._format_value(field_value)
                        if formatted_value not in ["N/A", "Unknown", ""]:
                            present_count += 1
                    else:
                        formatted_value = "N/A"
                        confidence = 0.0

                    values.append(formatted_value)
                    confidences.append(confidence)

                # Determine status
                if present_count == 0:
                    # Skip features with no values across any modem
                    continue

                comparison_data['summary']['total_features'] += 1

                if present_count == len(features_list):
                    # All modems have values
                    unique_values = set(v for v in values if v not in ["N/A", "Unknown", ""])
                    if len(unique_values) == 1:
                        status = 'same'
                        comparison_data['summary']['identical_features'] += 1
                    else:
                        status = 'different'
                        comparison_data['summary']['different_features'] += 1
                else:
                    # Some modems have values, some don't
                    status = 'partial'
                    comparison_data['summary']['partial_features'] += 1

                # Format field name for display
                display_name = self._format_field_name(field_name)

                # Add feature comparison
                feature_comparison = {
                    'feature': display_name,
                    'values': values,
                    'confidences': confidences,
                    'all_same': status == 'same',
                    'status': status
                }

                category_features.append(feature_comparison)

            # Add category if it has features
            if category_features:
                comparison_data['categories'][category_name] = category_features

        return comparison_data

    def _generate_csv_comparison(
        self,
        comparison_data: Dict[str, Any],
        output_path: Path
    ) -> ReportResult:
        """Generate CSV comparison report.

        Args:
            comparison_data: Comparison data structure
            output_path: Path to output CSV file

        Returns:
            ReportResult with generation metadata
        """
        start_time = time.time()
        warnings = []

        try:
            modem_ids = comparison_data['modem_ids']

            # Build CSV headers: Category, Feature, Modem1, Modem2, ..., Status
            headers = ['Category', 'Feature'] + modem_ids + ['Status']

            # Build rows
            rows = []
            for category_name, features in comparison_data['categories'].items():
                for feature in features:
                    row = {
                        'Category': category_name,
                        'Feature': feature['feature'],
                        'Status': feature['status'].capitalize()
                    }

                    # Add modem values with confidence in parentheses
                    for i, modem_id in enumerate(modem_ids):
                        value = feature['values'][i]
                        confidence = feature['confidences'][i]
                        if confidence > 0.0 and value not in ["N/A", "Unknown"]:
                            row[modem_id] = f"{value} ({confidence:.0%})"
                        else:
                            row[modem_id] = value

                    rows.append(row)

            # Write CSV with UTF-8-sig encoding (BOM for Excel)
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)

            # Get file size
            file_size = self._get_file_size(output_path)
            generation_time = time.time() - start_time

            # Validate output
            validation_passed, validation_warnings = self.validate_output(output_path)
            warnings.extend(validation_warnings)

            # Add summary warning if no features
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
                warnings=[],
                file_size_bytes=0,
                generation_time_seconds=generation_time,
                error_message=f"Error generating CSV comparison: {e}"
            )

    def _generate_html_comparison(
        self,
        comparison_data: Dict[str, Any],
        output_path: Path
    ) -> ReportResult:
        """Generate HTML comparison report with color coding.

        Args:
            comparison_data: Comparison data structure
            output_path: Path to output HTML file

        Returns:
            ReportResult with generation metadata
        """
        start_time = time.time()
        warnings = []

        try:
            modem_ids = comparison_data['modem_ids']
            summary = comparison_data['summary']

            # Build HTML content
            html_parts = []

            # HTML header with embedded CSS
            html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Modem Comparison Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #bdc3c7;
            padding-bottom: 8px;
        }
        .summary {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }
        .summary-item {
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }
        .summary-label {
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        .summary-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            margin-bottom: 30px;
        }
        th {
            background-color: #34495e;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .status-same {
            background-color: #d4edda;
            color: #155724;
        }
        .status-different {
            background-color: #fff3cd;
            color: #856404;
        }
        .status-partial {
            background-color: #e2e3e5;
            color: #383d41;
        }
        .confidence {
            font-size: 0.85em;
            color: #6c757d;
        }
        .category-name {
            font-weight: 600;
            color: #2c3e50;
        }
        .timestamp {
            text-align: right;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Modem Comparison Report</h1>
""")

            # Summary section
            html_parts.append(f"""
        <div class="summary">
            <h2>Summary Statistics</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-label">Total Modems</div>
                    <div class="summary-value">{summary['total_modems']}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Total Features</div>
                    <div class="summary-value">{summary['total_features']}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Identical Features</div>
                    <div class="summary-value" style="color: #27ae60;">{summary['identical_features']}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Different Features</div>
                    <div class="summary-value" style="color: #f39c12;">{summary['different_features']}</div>
                </div>
                <div class="summary-item">
                    <div class="summary-label">Partial Features</div>
                    <div class="summary-value" style="color: #95a5a6;">{summary['partial_features']}</div>
                </div>
            </div>
        </div>
""")

            # Comparison table for each category
            for category_name, features in comparison_data['categories'].items():
                html_parts.append(f"""
        <h2>{category_name}</h2>
        <table>
            <thead>
                <tr>
                    <th>Feature</th>
""")
                # Add modem columns
                for modem_id in modem_ids:
                    html_parts.append(f"                    <th>{self._escape_html(modem_id)}</th>\n")

                html_parts.append("""                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
""")

                # Add feature rows
                for feature in features:
                    status_class = f"status-{feature['status']}"
                    html_parts.append(f"""                <tr>
                    <td class="category-name">{self._escape_html(feature['feature'])}</td>
""")
                    # Add modem values
                    for i, modem_id in enumerate(modem_ids):
                        value = self._escape_html(feature['values'][i])
                        confidence = feature['confidences'][i]
                        if confidence > 0.0 and value not in ["N/A", "Unknown"]:
                            html_parts.append(f'                    <td>{value} <span class="confidence">({confidence:.0%})</span></td>\n')
                        else:
                            html_parts.append(f'                    <td>{value}</td>\n')

                    html_parts.append(f'                    <td class="{status_class}">{feature["status"].capitalize()}</td>\n')
                    html_parts.append("                </tr>\n")

                html_parts.append("""            </tbody>
        </table>
""")

            # Footer with timestamp
            timestamp = self._format_timestamp()
            html_parts.append(f"""
        <div class="timestamp">
            Generated: {timestamp}
        </div>
    </div>
</body>
</html>
""")

            # Write HTML file
            html_content = ''.join(html_parts)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Get file size
            file_size = self._get_file_size(output_path)
            generation_time = time.time() - start_time

            # Validate output
            validation_passed, validation_warnings = self.validate_output(output_path)
            warnings.extend(validation_warnings)

            return ReportResult(
                output_path=output_path,
                format='html',
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
                format='html',
                success=False,
                validation_passed=False,
                warnings=[],
                file_size_bytes=0,
                generation_time_seconds=generation_time,
                error_message=f"Error generating HTML comparison: {e}"
            )

    def _generate_markdown_comparison(
        self,
        comparison_data: Dict[str, Any],
        output_path: Path
    ) -> ReportResult:
        """Generate Markdown comparison report with emoji indicators.

        Args:
            comparison_data: Comparison data structure
            output_path: Path to output Markdown file

        Returns:
            ReportResult with generation metadata
        """
        start_time = time.time()
        warnings = []

        try:
            modem_ids = comparison_data['modem_ids']
            summary = comparison_data['summary']

            # Build Markdown content
            md_parts = []

            # Title
            md_parts.append("# Modem Comparison Report\n\n")

            # Summary section
            md_parts.append("## Summary Statistics\n\n")
            md_parts.append(f"- **Total Modems:** {summary['total_modems']}\n")
            md_parts.append(f"- **Total Features:** {summary['total_features']}\n")
            md_parts.append(f"- **Identical Features:** {summary['identical_features']} ✅\n")
            md_parts.append(f"- **Different Features:** {summary['different_features']} ⚠️\n")
            md_parts.append(f"- **Partial Features:** {summary['partial_features']} ➖\n\n")

            # Status legend
            md_parts.append("### Status Legend\n\n")
            md_parts.append("- ✅ **Same:** All modems have identical values\n")
            md_parts.append("- ⚠️ **Different:** All modems have values but they differ\n")
            md_parts.append("- ➖ **Partial:** Some modems have values, some don't\n\n")

            # Comparison tables for each category
            for category_name, features in comparison_data['categories'].items():
                md_parts.append(f"## {category_name}\n\n")

                # Build table header
                header_parts = ["Feature"] + modem_ids + ["Status"]
                md_parts.append("| " + " | ".join(header_parts) + " |\n")

                # Build separator row
                separators = ["---"] * len(header_parts)
                md_parts.append("| " + " | ".join(separators) + " |\n")

                # Build feature rows
                for feature in features:
                    row_parts = [feature['feature']]

                    # Add modem values with confidence
                    for i, modem_id in enumerate(modem_ids):
                        value = feature['values'][i]
                        confidence = feature['confidences'][i]
                        if confidence > 0.0 and value not in ["N/A", "Unknown"]:
                            cell_value = f"{value} ({confidence:.0%})"
                        else:
                            cell_value = value
                        row_parts.append(cell_value)

                    # Add status with emoji
                    status_emoji = {
                        'same': '✅ Same',
                        'different': '⚠️ Different',
                        'partial': '➖ Partial'
                    }
                    row_parts.append(status_emoji.get(feature['status'], feature['status']))

                    md_parts.append("| " + " | ".join(row_parts) + " |\n")

                md_parts.append("\n")

            # Footer with timestamp
            timestamp = self._format_timestamp()
            md_parts.append(f"\n---\n\n*Generated: {timestamp}*\n")

            # Write Markdown file
            md_content = ''.join(md_parts)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)

            # Get file size
            file_size = self._get_file_size(output_path)
            generation_time = time.time() - start_time

            # Validate output
            validation_passed, validation_warnings = self.validate_output(output_path)
            warnings.extend(validation_warnings)

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
                warnings=[],
                file_size_bytes=0,
                generation_time_seconds=generation_time,
                error_message=f"Error generating Markdown comparison: {e}"
            )

    def _validate_csv_output(self, output_path: Path) -> Tuple[bool, List[str]]:
        """Validate CSV comparison output.

        Args:
            output_path: Path to CSV file

        Returns:
            Tuple of (is_valid, error_messages)
        """
        warnings = []

        try:
            with open(output_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader, None)

                if not header:
                    return False, ["CSV file has no header"]

                # Validate minimum headers (Category, Feature, at least 2 modems, Status)
                if len(header) < 5:
                    return False, ["CSV must have at least Category, Feature, 2 modems, and Status"]

                if header[0] != 'Category' or header[1] != 'Feature':
                    return False, ["CSV must start with 'Category' and 'Feature' columns"]

                if header[-1] != 'Status':
                    return False, ["CSV must end with 'Status' column"]

                # Count rows
                row_count = sum(1 for _ in reader)
                if row_count == 0:
                    warnings.append("CSV file has no data rows")

        except Exception as e:
            return False, [f"Error reading CSV file: {e}"]

        return True, warnings

    def _validate_html_output(self, output_path: Path) -> Tuple[bool, List[str]]:
        """Validate HTML comparison output.

        Args:
            output_path: Path to HTML file

        Returns:
            Tuple of (is_valid, error_messages)
        """
        warnings = []

        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Basic HTML structure validation
                if '<!DOCTYPE html>' not in content:
                    warnings.append("HTML file missing DOCTYPE declaration")

                if '<html' not in content:
                    return False, ["HTML file missing <html> tag"]

                if '<head>' not in content:
                    return False, ["HTML file missing <head> section"]

                if '<body>' not in content:
                    return False, ["HTML file missing <body> section"]

                if 'Modem Comparison Report' not in content:
                    warnings.append("HTML file missing expected title")

                # Check for summary section
                if 'Summary Statistics' not in content:
                    warnings.append("HTML file missing summary section")

        except Exception as e:
            return False, [f"Error reading HTML file: {e}"]

        return True, warnings

    def _validate_markdown_output(self, output_path: Path) -> Tuple[bool, List[str]]:
        """Validate Markdown comparison output.

        Args:
            output_path: Path to Markdown file

        Returns:
            Tuple of (is_valid, error_messages)
        """
        warnings = []

        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Basic Markdown structure validation
                if '# Modem Comparison Report' not in content:
                    warnings.append("Markdown file missing main title")

                if '## Summary Statistics' not in content:
                    warnings.append("Markdown file missing summary section")

                # Check for table structure
                if '|' not in content:
                    return False, ["Markdown file missing table structure"]

                # Check for status legend
                if 'Status Legend' not in content:
                    warnings.append("Markdown file missing status legend")

        except Exception as e:
            return False, [f"Error reading Markdown file: {e}"]

        return True, warnings

    def _format_value(self, value: Any) -> str:
        """Format a field value for comparison output.

        Handles different value types consistently across all formats.

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

        value_str = str(value)
        if value_str in ["Unknown", ""]:
            return "N/A"

        return value_str

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

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            HTML-safe text
        """
        if not isinstance(text, str):
            text = str(text)

        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;'
        }

        for char, escaped in replacements.items():
            text = text.replace(char, escaped)

        return text

    def __repr__(self) -> str:
        """String representation of reporter."""
        return "ComparisonReporter(formats=['csv', 'html', 'markdown'])"
