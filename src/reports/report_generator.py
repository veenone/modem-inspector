"""Report generator orchestrator with factory pattern.

This module provides the main ReportGenerator class that orchestrates
report generation across multiple formats using a factory pattern.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from src.parsers.feature_model import ModemFeatures
from src.reports.base_reporter import BaseReporter
from src.reports.csv_reporter import CSVReporter
from src.reports.html_reporter import HTMLReporter
from src.reports.json_reporter import JSONReporter
from src.reports.markdown_reporter import MarkdownReporter
from src.reports.report_models import ReportResult


# Factory pattern mapping: format -> reporter class
REPORTER_CLASSES = {
    'csv': CSVReporter,
    'html': HTMLReporter,
    'json': JSONReporter,
    'markdown': MarkdownReporter,
}


class ReportGenerator:
    """Main orchestrator for report generation using factory pattern.

    Provides a unified interface for generating reports in multiple formats
    (CSV, HTML, JSON, Markdown) with support for:
    - Format-specific reporter selection via factory pattern
    - Configuration-based defaults
    - Single and multi-format report generation
    - Custom template support
    - Automatic output path generation with timestamps

    The factory pattern allows easy extension with new report formats
    by adding new reporter classes to REPORTER_CLASSES.

    Example:
        >>> config = {
        ...     'default_format': 'csv',
        ...     'default_confidence_threshold': 0.7,
        ...     'output_directory': Path('./reports')
        ... }
        >>> generator = ReportGenerator(config)
        >>> result = generator.generate_report(
        ...     features=modem_features,
        ...     output_path=Path('./output.csv')
        ... )
        >>> if result.success:
        ...     print(f"Report generated: {result.output_path}")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional configuration.

        Args:
            config: Optional configuration dictionary with:
                - default_format: Default report format ('csv', 'html', 'json', 'markdown')
                - default_confidence_threshold: Default confidence threshold (0.0-1.0)
                - output_directory: Default output directory path
                - custom_templates: Dict of custom template paths by format

        Example:
            >>> config = {
            ...     'default_format': 'html',
            ...     'default_confidence_threshold': 0.8,
            ...     'output_directory': Path('./reports'),
            ...     'custom_templates': {
            ...         'html': 'templates/custom.j2',
            ...         'markdown': 'templates/custom_md.j2'
            ...     }
            ... }
            >>> generator = ReportGenerator(config)
        """
        self.config = config or {}

        # Extract and validate configuration
        self._default_format = self.config.get('default_format', 'csv')
        self._default_confidence_threshold = self.config.get(
            'default_confidence_threshold', 0.0
        )
        self._default_output_directory = self.config.get(
            'output_directory', Path.cwd()
        )
        self._custom_templates = self.config.get('custom_templates', {})

        # Validate default format
        if self._default_format not in self.supported_formats:
            raise ValueError(
                f"Invalid default_format '{self._default_format}'. "
                f"Must be one of {self.supported_formats}"
            )

        # Validate default confidence threshold
        if not 0.0 <= self._default_confidence_threshold <= 1.0:
            raise ValueError(
                f"Invalid default_confidence_threshold "
                f"'{self._default_confidence_threshold}'. "
                f"Must be in range [0.0, 1.0]"
            )

        # Ensure default output directory is a Path
        if not isinstance(self._default_output_directory, Path):
            self._default_output_directory = Path(self._default_output_directory)

    def generate_report(
        self,
        features: ModemFeatures,
        output_path: Path,
        format: str = 'csv',
        confidence_threshold: float = 0.0,
        template: Optional[str] = None,
        **kwargs
    ) -> ReportResult:
        """Generate a single report.

        Args:
            features: ModemFeatures from parser
            output_path: Path to output file
            format: Report format ('csv', 'html', 'json', 'markdown')
            confidence_threshold: Minimum confidence (0.0-1.0)
            template: Custom template path (for html/markdown)
            **kwargs: Additional reporter-specific options

        Returns:
            ReportResult with generation metadata

        Raises:
            ValueError: If format is unsupported

        Example:
            >>> generator = ReportGenerator()
            >>> result = generator.generate_report(
            ...     features=features,
            ...     output_path=Path('./report.csv'),
            ...     format='csv',
            ...     confidence_threshold=0.7
            ... )
            >>> if result.success:
            ...     print(f"Generated: {result.output_path}")
        """
        # Validate format
        if format not in self.supported_formats:
            raise ValueError(
                f"Unsupported format '{format}'. "
                f"Supported formats: {self.supported_formats}"
            )

        # Use config defaults if not provided
        if confidence_threshold == 0.0 and self._default_confidence_threshold > 0.0:
            confidence_threshold = self._default_confidence_threshold

        # Get custom template from config if not provided
        if template is None and format in self._custom_templates:
            template = self._custom_templates[format]

        try:
            # Get appropriate reporter using factory pattern
            reporter = self._get_reporter(format)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate report with reporter-specific handling
            if format in ['html', 'markdown'] and template:
                # Pass template to templated reporters
                result = reporter.generate(
                    features=features,
                    output_path=output_path,
                    confidence_threshold=confidence_threshold,
                    template=template,
                    **kwargs
                )
            else:
                # Generate without template
                result = reporter.generate(
                    features=features,
                    output_path=output_path,
                    confidence_threshold=confidence_threshold,
                    **kwargs
                )

            return result

        except Exception as e:
            # Return failed ReportResult on any error
            return ReportResult(
                output_path=output_path,
                format=format,
                success=False,
                validation_passed=False,
                warnings=[f"Report generation failed: {str(e)}"],
                file_size_bytes=0,
                generation_time_seconds=0.0,
                error_message=str(e)
            )

    def generate_multi_format(
        self,
        features: ModemFeatures,
        output_directory: Path,
        formats: List[str],
        confidence_threshold: float = 0.0,
        **kwargs
    ) -> Dict[str, ReportResult]:
        """Generate reports in multiple formats.

        Args:
            features: ModemFeatures from parser
            output_directory: Directory for all reports
            formats: List of formats to generate
            confidence_threshold: Minimum confidence
            **kwargs: Additional options

        Returns:
            Dict mapping format to ReportResult

        Example:
            >>> generator = ReportGenerator()
            >>> results = generator.generate_multi_format(
            ...     features=features,
            ...     output_directory=Path('./reports'),
            ...     formats=['csv', 'html', 'json'],
            ...     confidence_threshold=0.7
            ... )
            >>> for fmt, result in results.items():
            ...     if result.success:
            ...         print(f"{fmt}: {result.output_path}")
        """
        # Validate all formats before generating
        unsupported = [fmt for fmt in formats if fmt not in self.supported_formats]
        if unsupported:
            raise ValueError(
                f"Unsupported formats: {unsupported}. "
                f"Supported formats: {self.supported_formats}"
            )

        # Ensure output directory exists
        output_directory.mkdir(parents=True, exist_ok=True)

        # Use config defaults if not provided
        if confidence_threshold == 0.0 and self._default_confidence_threshold > 0.0:
            confidence_threshold = self._default_confidence_threshold

        # Extract modem ID for filename generation
        manufacturer = features.basic_info.manufacturer or "Unknown"
        model = features.basic_info.model or "Unknown"
        modem_id = f"{manufacturer}_{model}".strip()

        # Generate report in each format
        results = {}

        for fmt in formats:
            try:
                # Generate output path for this format
                output_path = self._generate_output_path(
                    output_directory=output_directory,
                    format=fmt,
                    modem_id=modem_id
                )

                # Get custom template if available
                template = self._custom_templates.get(fmt)

                # Generate report
                result = self.generate_report(
                    features=features,
                    output_path=output_path,
                    format=fmt,
                    confidence_threshold=confidence_threshold,
                    template=template,
                    **kwargs
                )

                results[fmt] = result

            except Exception as e:
                # Store failed result for this format
                results[fmt] = ReportResult(
                    output_path=output_directory / f"error.{fmt}",
                    format=fmt,
                    success=False,
                    validation_passed=False,
                    warnings=[f"Multi-format generation failed: {str(e)}"],
                    file_size_bytes=0,
                    generation_time_seconds=0.0,
                    error_message=str(e)
                )

        return results

    def _get_reporter(self, format: str) -> BaseReporter:
        """Factory method to get appropriate reporter.

        Uses the REPORTER_CLASSES mapping to instantiate the correct
        reporter class for the specified format.

        Args:
            format: Report format

        Returns:
            BaseReporter instance

        Raises:
            ValueError: If format is unsupported

        Example:
            >>> generator = ReportGenerator()
            >>> csv_reporter = generator._get_reporter('csv')
            >>> isinstance(csv_reporter, CSVReporter)
            True
        """
        if format not in REPORTER_CLASSES:
            raise ValueError(
                f"Unsupported format '{format}'. "
                f"Supported formats: {list(REPORTER_CLASSES.keys())}"
            )

        # Instantiate and return reporter class
        reporter_class = REPORTER_CLASSES[format]
        return reporter_class()

    def _generate_output_path(
        self,
        output_directory: Path,
        format: str,
        modem_id: Optional[str] = None
    ) -> Path:
        """Generate output path with timestamp and format extension.

        Creates a filename with format:
        {modem_id}_{timestamp}.{extension}

        Where:
        - modem_id: Sanitized modem identifier (spaces -> underscores)
        - timestamp: YYYYMMDD_HHMMSS
        - extension: Format-specific (.csv, .html, .json, .md)

        Args:
            output_directory: Output directory
            format: Report format
            modem_id: Optional modem identifier

        Returns:
            Path to output file

        Example:
            >>> generator = ReportGenerator()
            >>> path = generator._generate_output_path(
            ...     output_directory=Path('./reports'),
            ...     format='csv',
            ...     modem_id='Quectel EC25'
            ... )
            >>> print(path.name)
            Quectel_EC25_20250117_103000.csv
        """
        # Format extension mapping
        extensions = {
            'csv': '.csv',
            'html': '.html',
            'json': '.json',
            'markdown': '.md',
        }

        # Get extension for format
        extension = extensions.get(format, f'.{format}')

        # Generate timestamp: YYYYMMDD_HHMMSS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sanitize modem_id for filesystem
        if modem_id:
            # Replace spaces with underscores
            modem_id = modem_id.replace(' ', '_')
            # Remove any characters that aren't alphanumeric, underscore, or hyphen
            modem_id = re.sub(r'[^\w\-]', '', modem_id)
            # Ensure it's not empty after sanitization
            if not modem_id:
                modem_id = 'modem'
        else:
            modem_id = 'modem_report'

        # Build filename: {modem_id}_{timestamp}.{extension}
        filename = f"{modem_id}_{timestamp}{extension}"

        # Return complete path
        return output_directory / filename

    @property
    def supported_formats(self) -> List[str]:
        """Get list of supported formats.

        Returns:
            List of supported format strings

        Example:
            >>> generator = ReportGenerator()
            >>> print(generator.supported_formats)
            ['csv', 'html', 'json', 'markdown']
        """
        return list(REPORTER_CLASSES.keys())

    def __repr__(self) -> str:
        """String representation of ReportGenerator."""
        return (
            f"ReportGenerator(default_format='{self._default_format}', "
            f"supported_formats={self.supported_formats})"
        )
