"""Abstract base reporter interface.

Defines the common interface and shared functionality for all format-specific
report generators.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Any, Dict


class BaseReporter(ABC):
    """Abstract base class for report generators.

    All format-specific reporters (CSV, HTML, JSON, Markdown) must inherit
    from this class and implement the abstract methods.

    This class provides:
    - Abstract interface for report generation and validation
    - Common utility methods for filtering and formatting
    - Consistent error handling patterns
    """

    @abstractmethod
    def generate(
        self,
        features: Any,  # ModemFeatures from parser layer
        output_path: Path,
        confidence_threshold: float = 0.0,
        **kwargs
    ) -> 'ReportResult':
        """Generate a report from modem features.

        Args:
            features: ModemFeatures object from parser layer
            output_path: Path where report should be written
            confidence_threshold: Minimum confidence score (0.0-1.0) for feature inclusion
            **kwargs: Format-specific options (e.g., template path)

        Returns:
            ReportResult with generation status and metadata

        Raises:
            ValueError: If confidence_threshold is not in range [0.0, 1.0]
            IOError: If output_path cannot be written

        Example:
            >>> reporter = CSVReporter()
            >>> result = reporter.generate(features, Path("report.csv"), 0.7)
            >>> print(result.success)
            True
        """
        pass

    @abstractmethod
    def validate_output(self, output_path: Path) -> Tuple[bool, List[str]]:
        """Validate generated report format and content.

        Performs format-specific validation to ensure the generated report
        is well-formed and contains expected data.

        Args:
            output_path: Path to report file to validate

        Returns:
            Tuple of (is_valid, error_messages)
            - is_valid: True if report is valid, False otherwise
            - error_messages: List of validation error descriptions (empty if valid)

        Example:
            >>> reporter = CSVReporter()
            >>> is_valid, errors = reporter.validate_output(Path("report.csv"))
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Validation error: {error}")
        """
        pass

    def _filter_by_confidence(
        self,
        features: Any,
        threshold: float
    ) -> Any:
        """Filter features by confidence threshold.

        Removes features with confidence scores below the specified threshold.
        This is a helper method for subclasses to use during report generation.

        Args:
            features: ModemFeatures object
            threshold: Minimum confidence score (0.0-1.0)

        Returns:
            Filtered ModemFeatures object with only high-confidence features

        Raises:
            ValueError: If threshold is not in range [0.0, 1.0]

        Note:
            Features without confidence scores are included by default.
            Threshold of 0.0 includes all features (no filtering).
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"Confidence threshold must be in range [0.0, 1.0], got {threshold}"
            )

        # If threshold is 0.0, no filtering needed
        if threshold == 0.0:
            return features

        # Implementation note: This is a placeholder that returns features as-is.
        # Actual filtering logic should be implemented in ModemFeatures class
        # with a filter_by_confidence() method, or implemented here if needed.
        # For now, we return the features unchanged.
        # TODO: Implement actual filtering based on confidence scores
        return features

    def _format_timestamp(self, dt: Optional[datetime] = None) -> str:
        """Format timestamp for report metadata.

        Args:
            dt: Datetime to format (defaults to current time)

        Returns:
            ISO 8601 formatted timestamp string

        Example:
            >>> reporter = CSVReporter()
            >>> timestamp = reporter._format_timestamp()
            >>> print(timestamp)
            2024-01-15T14:30:00
        """
        if dt is None:
            dt = datetime.now()

        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    def _get_file_size(self, path: Path) -> int:
        """Get file size in bytes.

        Args:
            path: Path to file

        Returns:
            File size in bytes, or 0 if file doesn't exist

        Example:
            >>> size = reporter._get_file_size(Path("report.csv"))
            >>> print(f"Report size: {size} bytes")
        """
        try:
            return path.stat().st_size
        except (FileNotFoundError, OSError):
            return 0

    def _ensure_directory(self, path: Path) -> None:
        """Ensure parent directory exists for output path.

        Creates parent directories if they don't exist.

        Args:
            path: Output file path

        Raises:
            OSError: If directory cannot be created

        Example:
            >>> reporter._ensure_directory(Path("output/reports/report.csv"))
            # Creates 'output/reports/' if it doesn't exist
        """
        path.parent.mkdir(parents=True, exist_ok=True)

    def _validate_confidence_threshold(self, threshold: float) -> None:
        """Validate confidence threshold is in valid range.

        Args:
            threshold: Confidence threshold to validate

        Raises:
            ValueError: If threshold is not in range [0.0, 1.0]

        Example:
            >>> reporter._validate_confidence_threshold(0.7)  # OK
            >>> reporter._validate_confidence_threshold(1.5)  # Raises ValueError
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"Confidence threshold must be in range [0.0, 1.0], got {threshold}"
            )
