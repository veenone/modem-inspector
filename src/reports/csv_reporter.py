"""CSV report generator for AT command execution results.

This module provides CSV format report generation from AT command
execution history.
"""

import csv
import time
from pathlib import Path
from typing import List

from src.core.command_response import CommandResponse
from src.reports.report_models import ReportResult


class CSVReporter:
    """CSV format reporter for AT command execution results.

    Generates CSV reports from CommandResponse objects with columns
    for command, status, response, timing, and retry information.

    Example:
        >>> reporter = CSVReporter()
        >>> responses = [...]  # List of CommandResponse objects
        >>> result = reporter.generate(responses, Path('./report.csv'))
        >>> print(result)
    """

    def generate(self,
                responses: List[CommandResponse],
                output_path: Path,
                include_responses: bool = True) -> ReportResult:
        """Generate CSV report from command responses.

        Args:
            responses: List of CommandResponse objects to report
            output_path: Path to output CSV file
            include_responses: Include full response text (default True)

        Returns:
            ReportResult with generation metadata

        Example:
            >>> reporter = CSVReporter()
            >>> responses = executor.get_history()
            >>> result = reporter.generate(responses, Path('./output.csv'))
            >>> if result.success:
            ...     print(f"Report saved to {result.output_path}")
        """
        start_time = time.time()
        warnings = []

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                header = [
                    'Command',
                    'Status',
                    'Execution Time (s)',
                    'Retry Count',
                    'Timestamp',
                    'Error Code',
                    'Error Message'
                ]
                if include_responses:
                    header.append('Response')

                writer.writerow(header)

                # Write data rows
                for response in responses:
                    row = [
                        response.command,
                        response.status.value,
                        f"{response.execution_time:.3f}",
                        response.retry_count,
                        time.strftime('%Y-%m-%d %H:%M:%S',
                                     time.localtime(response.timestamp)),
                        response.error_code or '',
                        response.error_message or ''
                    ]

                    if include_responses:
                        # Join response lines with semicolon separator
                        response_text = '; '.join(response.raw_response)
                        row.append(response_text)

                    writer.writerow(row)

            # Get file size
            file_size = output_path.stat().st_size
            generation_time = time.time() - start_time

            # Validate
            validation_passed, validation_warnings = self.validate_output(output_path)
            warnings.extend(validation_warnings)

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
        """Validate generated CSV file.

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

        # Try to read CSV
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)

                if not header:
                    return False, ["CSV file has no header"]

                # Count rows
                row_count = sum(1 for _ in reader)
                if row_count == 0:
                    warnings.append("CSV file has no data rows")

        except Exception as e:
            return False, [f"Error reading CSV file: {e}"]

        return True, warnings

    def __repr__(self) -> str:
        """String representation of reporter."""
        return "CSVReporter(format=csv)"
