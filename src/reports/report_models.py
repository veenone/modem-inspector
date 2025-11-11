"""Report result data models.

This module defines immutable data structures representing report
generation results and metadata.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


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

    def __str__(self) -> str:
        """Human-readable report result."""
        status = "SUCCESS" if self.success else "FAILED"
        validation = "PASS" if self.validation_passed else "FAIL"
        size_kb = self.file_size_bytes / 1024
        return (f"ReportResult[{status}]: {self.format.upper()} report "
                f"at {self.output_path} ({size_kb:.1f} KB, "
                f"{self.generation_time_seconds:.2f}s) "
                f"validation={validation}")
