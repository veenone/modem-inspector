"""Unit tests for report data models."""

import pytest
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import List

from src.reports.report_models import ReportResult, BatchReportResult


class TestReportResult:
    def test_immutability(self):
        """Test that ReportResult is immutable."""
        report = ReportResult(
            output_path=Path("/test/report.csv"),
            format="csv",
            success=True
        )

        with pytest.raises(FrozenInstanceError):
            report.success = False

    def test_creation_all_fields(self):
        """Test creating a ReportResult with all fields populated."""
        report = ReportResult(
            output_path=Path("/test/full_report.html"),
            format="html",
            success=True,
            validation_passed=True,
            warnings=["Minor formatting issue"],
            file_size_bytes=1024,
            generation_time_seconds=1.5,
            error_message=None
        )

        assert report.output_path == Path("/test/full_report.html")
        assert report.format == "html"
        assert report.success is True
        assert report.validation_passed is True
        assert report.warnings == ["Minor formatting issue"]
        assert report.file_size_bytes == 1024
        assert report.generation_time_seconds == 1.5
        assert report.error_message is None

    def test_creation_minimal_fields(self):
        """Test creating a ReportResult with minimal required fields."""
        report = ReportResult(
            output_path=Path("/test/minimal_report.json"),
            format="json",
            success=False
        )

        assert report.output_path == Path("/test/minimal_report.json")
        assert report.format == "json"
        assert report.success is False
        assert report.validation_passed is True
        assert report.warnings == []
        assert report.file_size_bytes == 0
        assert report.generation_time_seconds == 0.0
        assert report.error_message is None

    def test_str_output_successful(self):
        """Test __str__() method for a successful report."""
        report = ReportResult(
            output_path=Path("/test/success_report.csv"),
            format="csv",
            success=True,
            validation_passed=True,
            file_size_bytes=2048,
            generation_time_seconds=0.75
        )

        # Check key components instead of exact string due to path separators
        output_str = str(report)
        assert "ReportResult[SUCCESS]" in output_str
        assert "CSV report" in output_str
        assert "success_report.csv" in output_str
        assert "2.0 KB" in output_str
        assert "0.75s" in output_str
        assert "validation=PASS" in output_str

    def test_str_output_failed(self):
        """Test __str__() method for a failed report."""
        report = ReportResult(
            output_path=Path("/test/failed_report.html"),
            format="html",
            success=False,
            validation_passed=False,
            error_message="Generation failed",
            file_size_bytes=0,
            generation_time_seconds=0.1
        )

        # Check key components instead of exact string due to path separators
        output_str = str(report)
        assert "ReportResult[FAILED]" in output_str
        assert "HTML report" in output_str
        assert "failed_report.html" in output_str
        assert "0.0 KB" in output_str
        assert "0.10s" in output_str
        assert "validation=FAIL" in output_str
        assert "error='Generation failed'" in output_str

    def test_failed_report_with_validation_warnings(self):
        """Test a report with validation warnings."""
        report = ReportResult(
            output_path=Path("/test/warning_report.json"),
            format="json",
            success=True,
            validation_passed=False,
            warnings=["Header mismatch", "Extra whitespace detected"],
            file_size_bytes=512,
            generation_time_seconds=0.5
        )

        assert report.success is True
        assert report.validation_passed is False
        assert report.warnings == ["Header mismatch", "Extra whitespace detected"]


class TestBatchReportResult:
    @pytest.fixture
    def sample_report_results(self) -> List[ReportResult]:
        """Fixture to generate a list of sample ReportResults."""
        return [
            ReportResult(
                output_path=Path(f"/test/report_{i}.csv"),
                format="csv",
                success=i % 2 == 0,  # Alternate success/failure
                validation_passed=i % 2 == 0,
                file_size_bytes=1024 * i,
                generation_time_seconds=0.1 * i
            ) for i in range(5)
        ]

    def test_immutability(self, sample_report_results):
        """Test that BatchReportResult is immutable."""
        batch_result = BatchReportResult(
            output_directory=Path("/test/reports"),
            total_count=5,
            success_count=3,
            failure_count=2,
            report_results=sample_report_results,
            failed_modems=["modem1", "modem2"]
        )

        with pytest.raises(FrozenInstanceError):
            batch_result.success_count = 0

    def test_creation_with_report_results(self, sample_report_results):
        """Test creating a BatchReportResult with a list of reports."""
        batch_result = BatchReportResult(
            output_directory=Path("/test/reports"),
            total_count=5,
            success_count=3,
            failure_count=2,
            report_results=sample_report_results,
            failed_modems=["modem1", "modem2"]
        )

        assert batch_result.output_directory == Path("/test/reports")
        assert batch_result.total_count == 5
        assert batch_result.success_count == 3
        assert batch_result.failure_count == 2
        assert batch_result.report_results == sample_report_results
        assert batch_result.failed_modems == ["modem1", "modem2"]

    def test_all_successful_property(self, sample_report_results):
        """Test all_successful property."""
        # Batch with some failures
        mixed_batch = BatchReportResult(
            output_directory=Path("/test/mixed_reports"),
            total_count=5,
            success_count=3,
            failure_count=2,
            report_results=sample_report_results
        )
        assert mixed_batch.all_successful is False

        # Batch with all successful reports
        all_successful = BatchReportResult(
            output_directory=Path("/test/success_reports"),
            total_count=5,
            success_count=5,
            failure_count=0,
            report_results=[
                ReportResult(
                    output_path=Path(f"/test/report_{i}.csv"),
                    format="csv",
                    success=True
                ) for i in range(5)
            ]
        )
        assert all_successful.all_successful is True

    def test_has_failures_property(self, sample_report_results):
        """Test has_failures property."""
        # Batch with some failures
        mixed_batch = BatchReportResult(
            output_directory=Path("/test/mixed_reports"),
            total_count=5,
            success_count=3,
            failure_count=2,
            report_results=sample_report_results
        )
        assert mixed_batch.has_failures is True

        # Batch with no failures
        no_failures_batch = BatchReportResult(
            output_directory=Path("/test/success_reports"),
            total_count=5,
            success_count=5,
            failure_count=0,
            report_results=[
                ReportResult(
                    output_path=Path(f"/test/report_{i}.csv"),
                    format="csv",
                    success=True
                ) for i in range(5)
            ]
        )
        assert no_failures_batch.has_failures is False

    def test_str_output(self, sample_report_results):
        """Test __str__() method for BatchReportResult."""
        batch_result = BatchReportResult(
            output_directory=Path("/test/reports"),
            total_count=5,
            success_count=3,
            failure_count=2,
            report_results=sample_report_results
        )

        # Check key components instead of exact string due to path separators
        output_str = str(batch_result)
        assert "BatchReportResult" in output_str
        assert "3/5 successful" in output_str
        assert "60.0%" in output_str
        assert "reports" in output_str

    def test_empty_report_results(self):
        """Test BatchReportResult with empty report_results list."""
        batch_result = BatchReportResult(
            output_directory=Path("/test/empty_reports"),
            total_count=0,
            success_count=0,
            failure_count=0
        )

        # Use str() comparison to handle path separators
        assert str(batch_result.output_directory) == str(Path("/test/empty_reports"))
        assert batch_result.total_count == 0
        assert batch_result.success_count == 0
        assert batch_result.failure_count == 0
        assert batch_result.report_results == []
        assert batch_result.failed_modems == []
        assert batch_result.all_successful is True
        assert batch_result.has_failures is False

        # Check key components instead of exact string due to path separators
        output_str = str(batch_result)
        assert "0/0 successful" in output_str
        assert "0.0%" in output_str
        assert "empty_reports" in output_str