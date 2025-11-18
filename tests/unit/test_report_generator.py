"""Unit tests for ReportGenerator class."""

import os
import re
import json
import csv
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.reports.report_generator import ReportGenerator
from src.reports.base_reporter import BaseReporter
from src.reports.report_models import ReportResult, BatchReportResult
from src.parsers.feature_model import ModemFeatures


def create_mock_modem_features(manufacturer="Test", model="Modem"):
    """Create a mock ModemFeatures object for testing."""
    mock_features = MagicMock(spec=ModemFeatures)

    # Create a mock basic_info with configurable manufacturer and model
    mock_basic_info = MagicMock()
    mock_basic_info.manufacturer = manufacturer
    mock_basic_info.model = model

    # Attach the mock basic_info to the mock features
    mock_features.basic_info = mock_basic_info

    return mock_features


@pytest.fixture
def report_generator():
    """Create a default ReportGenerator instance."""
    return ReportGenerator()


@pytest.fixture
def mock_modem_features():
    """Create mock ModemFeatures for testing."""
    return create_mock_modem_features()


@pytest.mark.unit
class TestReportGenerator:
    """Comprehensive unit tests for ReportGenerator."""

    @pytest.mark.parametrize("format, reporter_class",
    [
        ('csv', 'CSVReporter'),
        ('html', 'HTMLReporter'),
        ('json', 'JSONReporter'),
        ('markdown', 'MarkdownReporter')
    ])
    def test_generate_report_single_format(
        self,
        report_generator,
        mock_modem_features,
        tmp_path,
        format,
        reporter_class
    ):
        """Test generating a single report in each supported format."""
        # Setup output path
        output_path = tmp_path / f"test_report.{format}"

        # Use a consistent confidence threshold
        confidence_threshold = 0.75

        # Patch the generate method of the specific reporter to simulate success
        with patch(f"src.reports.{format}_reporter.{reporter_class}.generate") as mock_generate, \
             patch(f"src.reports.{format}_reporter.{reporter_class}") as mock_reporter_class:

            # Create a mock ReportResult
            mock_result = ReportResult(
                output_path=output_path,
                format=format,
                success=True,
                validation_passed=True,
                warnings=[],
                file_size_bytes=1024,
                generation_time_seconds=0.5
            )

            # Create a mock reporter instance
            mock_reporter_instance = MagicMock()
            mock_reporter_class.return_value = mock_reporter_instance

            # Set the generate method return value
            mock_generate.return_value = mock_result

            # Generate the report
            result = report_generator.generate_report(
                features=mock_modem_features,
                output_path=output_path,
                format=format,
                confidence_threshold=confidence_threshold
            )

        # Assertions
        assert result.success is True
        assert result.output_path == output_path
        assert result.format == format
        assert result.validation_passed is True

        # Verify reporter was called with correct arguments
        mock_generate.assert_called_once_with(
            features=mock_modem_features,
            output_path=output_path,
            confidence_threshold=confidence_threshold
        )

    def test_generate_multi_format(
        self,
        report_generator,
        mock_modem_features,
        tmp_path
    ):
        """Test generating reports in multiple formats."""
        # Supported formats
        formats = ['csv', 'html', 'json']

        # Patch the reporters for each format
        mocks = {}
        for fmt in formats:
            reporter_class = f"{fmt.upper()}Reporter"
            patcher_generate = patch(f"src.reports.{fmt}_reporter.{reporter_class}.generate")
            patcher_reporter = patch(f"src.reports.{fmt}_reporter.{reporter_class}")

            mock_generate = patcher_generate.start()
            mock_reporter = patcher_reporter.start()

            # Simulate successful generation
            output_path = tmp_path / f"test_{fmt}_report.{fmt}"
            mock_result = ReportResult(
                output_path=output_path,
                format=fmt,
                success=True,
                validation_passed=True,
                warnings=[],
                file_size_bytes=1024,
                generation_time_seconds=0.5
            )
            mock_generate.return_value = mock_result
            mock_reporter.return_value.generate = mock_generate

            mocks[fmt] = {
                'patcher_generate': patcher_generate,
                'patcher_reporter': patcher_reporter,
                'mock_generate': mock_generate,
                'mock_reporter': mock_reporter
            }

        try:
            # Create multi-format results
            results = report_generator.generate_multi_format(
                features=mock_modem_features,
                output_directory=tmp_path,
                formats=formats,
                confidence_threshold=0.8
            )

            # Assertions
            assert len(results) == len(formats)

            # Verify paths match the expected pattern
            for fmt, result in results.items():
                assert result.success is True
                assert result.format == fmt

                # Check filename pattern
                expected_pattern = re.compile(
                    rf"^test_{fmt}_report\.{fmt}$"
                )
                assert expected_pattern.match(result.output_path.name) is not None

                # Verify generate was called
                mocks[fmt]['mock_generate'].assert_called_once()

        finally:
            # Stop all patchers
            for mock_data in mocks.values():
                mock_data['patcher_generate'].stop()
                mock_data['patcher_reporter'].stop()

    def test_get_reporter(self, report_generator):
        """Test factory method for reporters."""
        # Test each supported format returns correct reporter
        from src.reports.csv_reporter import CSVReporter
        from src.reports.html_reporter import HTMLReporter
        from src.reports.json_reporter import JSONReporter
        from src.reports.markdown_reporter import MarkdownReporter

        reporters = {
            'csv': CSVReporter,
            'html': HTMLReporter,
            'json': JSONReporter,
            'markdown': MarkdownReporter
        }

        for fmt, reporter_cls in reporters.items():
            reporter = report_generator._get_reporter(fmt)
            assert isinstance(reporter, reporter_cls)

    def test_get_reporter_invalid_format(self, report_generator):
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            report_generator._get_reporter('invalid_format')

    def test_generate_output_path(self, report_generator, tmp_path):
        """Test output path generation."""
        # Mock datetime to get consistent timestamp
        with patch('src.reports.report_generator.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 17, 10, 30, 0)

            # Test path generation with different modem IDs
            test_cases = [
                ('Test Modem', 'Test_Modem'),      # With space
                ('TestModem123', 'TestModem123'),  # Alphanumeric
                ('$Invalid#Chars', 'InvalidChars')  # Special characters
            ]

            for modem_id, expected_sanitized_id in test_cases:
                path = report_generator._generate_output_path(
                    output_directory=tmp_path,
                    format='csv',
                    modem_id=modem_id
                )

                # Check filename matches expected pattern
                assert path.parent == tmp_path
                expected_filename = re.compile(
                    rf"^{expected_sanitized_id}_20250117_103000\.csv$"
                )
                assert expected_filename.match(path.name) is not None, \
                    f"Failed for input '{modem_id}', expected pattern not matched"

    def test_batch_generation(self, report_generator, tmp_path):
        """Test batch report generation."""
        # Create mock features for multiple modems
        features_list = [
            ('Modem1', create_mock_modem_features('Test', 'Modem1')),
            ('Modem2', create_mock_modem_features('Test', 'Modem2')),
            ('Modem3', create_mock_modem_features('Test', 'Modem3'))
        ]

        # Patch the reporters for csv and html
        mocks = {}
        formats = ['csv', 'html']

        for fmt in formats:
            reporter_class = f"{fmt.upper()}Reporter"
            patcher_generate = patch(f"src.reports.{fmt}_reporter.{reporter_class}.generate")
            patcher_reporter = patch(f"src.reports.{fmt}_reporter.{reporter_class}")

            mock_generate = patcher_generate.start()
            mock_reporter = patcher_reporter.start()

            mock_generate.side_effect = [
                ReportResult(
                    output_path=tmp_path / f"Modem1_{fmt}_report.{fmt}",
                    format=fmt,
                    success=True,
                    validation_passed=True,
                    warnings=[],
                    file_size_bytes=1024,
                    generation_time_seconds=0.5
                ),
                ReportResult(
                    output_path=tmp_path / f"Modem2_{fmt}_report.{fmt}",
                    format=fmt,
                    success=True,
                    validation_passed=True,
                    warnings=[],
                    file_size_bytes=1024,
                    generation_time_seconds=0.5
                ),
                ReportResult(
                    output_path=tmp_path / f"Modem3_{fmt}_report.{fmt}",
                    format=fmt,
                    success=True,
                    validation_passed=True,
                    warnings=[],
                    file_size_bytes=1024,
                    generation_time_seconds=0.5
                )
            ]

            mock_reporter.return_value.generate = mock_generate

            mocks[fmt] = {
                'patcher_generate': patcher_generate,
                'patcher_reporter': patcher_reporter,
                'mock_generate': mock_generate,
                'mock_reporter': mock_reporter
            }

        try:
            # Generate batch reports
            batch_result = report_generator.generate_batch(
                features_list=features_list,
                output_directory=tmp_path,
                formats=formats,
                parallel=False
            )

            # Assertions
            assert isinstance(batch_result, BatchReportResult)
            assert batch_result.total_count == 3
            assert batch_result.success_count == 3
            assert batch_result.failure_count == 0
            assert len(batch_result.report_results) == 6  # 2 formats * 3 modems

            # Verify batch summary CSV
            assert batch_result.batch_summary_path is not None
            assert batch_result.batch_summary_path.exists()

            # Validate batch summary content
            with open(batch_result.batch_summary_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                assert header == [
                    'Modem ID', 'Formats', 'Total Reports',
                    'Successful', 'Failed', 'Generation Time (s)'
                ]

            # Verify calls
            for fmt_mocks in mocks.values():
                assert fmt_mocks['mock_generate'].call_count == 3

        finally:
            # Stop all patchers
            for mock_data in mocks.values():
                mock_data['patcher_generate'].stop()
                mock_data['patcher_reporter'].stop()

    def test_configuration_initialization(self):
        """Test ReportGenerator configuration."""
        # Test with different config options
        config_options = [
            None,  # Default config
            {
                'default_format': 'html',
                'default_confidence_threshold': 0.8,
                'output_directory': Path('/test/reports'),
                'custom_templates': {
                    'html': '/path/to/custom.j2'
                }
            }
        ]

        for config in config_options:
            generator = ReportGenerator(config)

            # Verify defaults or config values
            assert generator._default_format in ['csv', 'html', 'json', 'markdown']
            assert 0.0 <= generator._default_confidence_threshold <= 1.0
            assert isinstance(generator._default_output_directory, Path)

    def test_error_handling(self, report_generator, mock_modem_features, tmp_path):
        """Test error handling in report generation."""
        # Test invalid confidence threshold
        with pytest.raises(ValueError, match="Invalid default_confidence_threshold"):
            ReportGenerator({
                'default_confidence_threshold': 1.5
            })

        # Test unsupported format
        with pytest.raises(ValueError, match="Unsupported format"):
            report_generator.generate_report(
                features=mock_modem_features,
                output_path=tmp_path / 'error.txt',
                format='unsupported'
            )

    @pytest.mark.parametrize("parallel", [True, False])
    def test_generate_batch_multiprocessing(
        self,
        report_generator,
        tmp_path,
        parallel
    ):
        """Test batch generation with parallel and sequential processing."""
        # Create mock features for multiple modems
        features_list = [
            ('Modem1', create_mock_modem_features('Test', 'Modem1')),
            ('Modem2', create_mock_modem_features('Test', 'Modem2')),
            ('Modem3', create_mock_modem_features('Test', 'Modem3'))
        ]

        # Patch the reporters for csv and html
        mocks = {}
        formats = ['csv', 'html']

        for fmt in formats:
            reporter_class = f"{fmt.upper()}Reporter"
            patcher_generate = patch(f"src.reports.{fmt}_reporter.{reporter_class}.generate")
            patcher_reporter = patch(f"src.reports.{fmt}_reporter.{reporter_class}")

            mock_generate = patcher_generate.start()
            mock_reporter = patcher_reporter.start()

            mock_generate.side_effect = [
                ReportResult(
                    output_path=tmp_path / f"Modem1_{fmt}_report.{fmt}",
                    format=fmt,
                    success=True,
                    validation_passed=True,
                    warnings=[],
                    file_size_bytes=1024,
                    generation_time_seconds=0.5
                ),
                ReportResult(
                    output_path=tmp_path / f"Modem2_{fmt}_report.{fmt}",
                    format=fmt,
                    success=True,
                    validation_passed=True,
                    warnings=[],
                    file_size_bytes=1024,
                    generation_time_seconds=0.5
                ),
                ReportResult(
                    output_path=tmp_path / f"Modem3_{fmt}_report.{fmt}",
                    format=fmt,
                    success=True,
                    validation_passed=True,
                    warnings=[],
                    file_size_bytes=1024,
                    generation_time_seconds=0.5
                )
            ]

            mock_reporter.return_value.generate = mock_generate

            mocks[fmt] = {
                'patcher_generate': patcher_generate,
                'patcher_reporter': patcher_reporter,
                'mock_generate': mock_generate,
                'mock_reporter': mock_reporter
            }

        try:
            # Generate batch reports
            batch_result = report_generator.generate_batch(
                features_list=features_list,
                output_directory=tmp_path,
                formats=formats,
                parallel=parallel
            )

            # Assertions
            assert batch_result.total_count == 3
            assert batch_result.success_count == 3
            assert batch_result.failure_count == 0
            assert len(batch_result.report_results) == 6  # 2 formats * 3 modems

            # Verify batch summary was created
            assert batch_result.batch_summary_path is not None
            assert batch_result.batch_summary_path.exists()

            # Verify calls
            for fmt_mocks in mocks.values():
                assert fmt_mocks['mock_generate'].call_count == 3

        finally:
            # Stop all patchers
            for mock_data in mocks.values():
                mock_data['patcher_generate'].stop()
                mock_data['patcher_reporter'].stop()