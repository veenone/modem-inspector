"""Report result data models.

This module defines immutable data structures representing report
generation results and metadata.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class ReportResult:
    """Report generation result.

    Contains metadata about a generated report including success status,
    validation results, and file information.

    Attributes:
        output_path: Path to generated report file
        format: Report format (e.g., 'csv', 'html', 'json')
        success: Whether report generation succeeded
        validation_passed: Whether output validation passed
        warnings: List of warning messages
        file_size_bytes: Size of generated file in bytes
        generation_time_seconds: Time taken to generate report
    """
    output_path: Path
    format: str
    success: bool
    validation_passed: bool = True
    warnings: List[str] = field(default_factory=list)
    file_size_bytes: int = 0
    generation_time_seconds: float = 0.0
    error_message: Optional[str] = None

    def __str__(self) -> str:
        """Human-readable report result."""
        status = "SUCCESS" if self.success else "FAILED"
        validation = "PASS" if self.validation_passed else "FAIL"
        size_kb = self.file_size_bytes / 1024
        result = (f"ReportResult[{status}]: {self.format.upper()} report "
                 f"at {self.output_path} ({size_kb:.1f} KB, "
                 f"{self.generation_time_seconds:.2f}s) "
                 f"validation={validation}")
        if self.error_message:
            result += f" error='{self.error_message}'"
        return result


@dataclass(frozen=True)
class BatchReportResult:
    """Batch report generation result.

    Contains results from generating reports for multiple modems,
    including success/failure counts and detailed results.

    Attributes:
        output_directory: Directory containing all generated reports
        total_count: Total number of modems processed
        success_count: Number of successful report generations
        failure_count: Number of failed report generations
        report_results: List of individual ReportResult objects
        failed_modems: List of modem identifiers that failed
        batch_summary_path: Path to batch summary report
    """
    output_directory: Path
    total_count: int
    success_count: int
    failure_count: int
    report_results: List[ReportResult] = field(default_factory=list)
    failed_modems: List[str] = field(default_factory=list)
    batch_summary_path: Optional[Path] = None

    def __str__(self) -> str:
        """Human-readable batch result."""
        success_rate = (self.success_count / self.total_count * 100) if self.total_count > 0 else 0
        return (f"BatchReportResult: {self.success_count}/{self.total_count} successful "
                f"({success_rate:.1f}%) in {self.output_directory}")

    @property
    def all_successful(self) -> bool:
        """Check if all reports generated successfully."""
        return self.failure_count == 0

    @property
    def has_failures(self) -> bool:
        """Check if any reports failed."""
        return self.failure_count > 0
