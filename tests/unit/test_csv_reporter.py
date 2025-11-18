"""Unit tests for CSVReporter module."""

import csv
import pytest
from pathlib import Path
from typing import List

# Ensure absolute imports
import sys
import importlib
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Explicitly import the module for coverage
importlib.import_module('src.reports.csv_reporter')

from src.parsers.feature_model import (
    ModemFeatures,
    BasicInfo,
    NetworkCapabilities,
    VoiceFeatures,
    GNSSInfo,
    PowerManagement,
    SIMInfo,
    NetworkTechnology,
    SIMStatus
)
from src.reports.csv_reporter import CSVReporter
from src.reports.report_models import ReportResult


@pytest.fixture
def mock_modem_features() -> ModemFeatures:
    """Create a mock ModemFeatures object for testing."""
    return ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Quectel",
            model="EC25",
            manufacturer_confidence=0.95,
            model_confidence=0.90
        ),
        network_capabilities=NetworkCapabilities(
            supported_technologies=[NetworkTechnology.LTE, NetworkTechnology.LTE_M],
            supported_technologies_confidence=0.80,
            lte_bands=[700, 850, 1900],
            lte_bands_confidence=0.85
        ),
        voice_features=VoiceFeatures(
            volte_supported=True,
            volte_supported_confidence=0.75,
            vowifi_supported=False,
            vowifi_supported_confidence=0.60
        ),
        gnss_info=GNSSInfo(
            gnss_supported=True,
            gnss_supported_confidence=0.90,
            supported_systems=['GPS'],
            supported_systems_confidence=0.90
        ),
        power_management=PowerManagement(
            psm_supported=True,
            psm_supported_confidence=0.85,
            battery_voltage=3800,
            battery_voltage_confidence=0.95
        ),
        sim_info=SIMInfo(
            sim_status=SIMStatus.READY,
            sim_status_confidence=0.95
        )
    )


@pytest.fixture
def csv_reporter() -> CSVReporter:
    """Create a CSVReporter instance for testing."""
    return CSVReporter()


def test_csv_generation(csv_reporter: CSVReporter, mock_modem_features: ModemFeatures, tmp_path: Path):
    """Test successful CSV generation with mock ModemFeatures."""
    output_path = tmp_path / "test_report.csv"
    result = csv_reporter.generate(mock_modem_features, output_path, confidence_threshold=0.5)

    # Verify ReportResult
    assert result.success is True
    assert result.output_path == output_path
    assert result.validation_passed is True
    assert result.format == 'csv'
    assert result.file_size_bytes > 0
    assert result.generation_time_seconds >= 0  # Small files might have generation time of 0

    # Verify CSV file contents
    assert output_path.exists()
    with open(output_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        assert headers == ['Category', 'Feature', 'Value', 'Confidence', 'Unit']

        # Convert reader to list to check rows
        rows = list(reader)
        assert len(rows) > 0  # Ensure we have rows

        # Some specific checks
        manufacturer_row = next(row for row in rows if row['Feature'] == 'Manufacturer')
        assert manufacturer_row['Value'] == 'Quectel'
        assert float(manufacturer_row['Confidence']) == 0.95


def test_value_formatting(csv_reporter: CSVReporter):
    """Test _format_value() method for different input types."""
    # Test None
    assert csv_reporter._format_value(None) == "N/A"

    # Test Booleans
    assert csv_reporter._format_value(True) == "Yes"
    assert csv_reporter._format_value(False) == "No"

    # Test Empty List
    assert csv_reporter._format_value([]) == "N/A"

    # Test Lists with different types
    assert csv_reporter._format_value([1, 2, 3]) == "1, 2, 3"
    assert csv_reporter._format_value([NetworkTechnology.LTE, NetworkTechnology.LTE_M]) == "LTE, LTE-M"

    # Test Enums
    assert csv_reporter._format_value(NetworkTechnology.LTE) == "LTE"
    assert csv_reporter._format_value(SIMStatus.READY) == "ready"

    # Test Basic string
    assert csv_reporter._format_value("Test") == "Test"


def test_field_name_formatting(csv_reporter: CSVReporter):
    """Test _format_field_name() method for different field names."""
    # Basic snake_case conversion
    assert csv_reporter._format_field_name("retry_count") == "Retry Count"

    # Acronym handling
    assert csv_reporter._format_field_name("imei") == "IMEI"
    assert csv_reporter._format_field_name("max_downlink_speed") == "Max Downlink Speed"
    assert csv_reporter._format_field_name("lte_support") == "LTE Support"
    assert csv_reporter._format_field_name("psm_enabled") == "PSM Enabled"


def test_feature_flattening(csv_reporter: CSVReporter, mock_modem_features: ModemFeatures):
    """Test _flatten_features() method."""
    # Test default flattening
    rows = csv_reporter._flatten_features(mock_modem_features, threshold=0.5)

    # Check categories and number of rows
    categories_found = set(row['Category'] for row in rows)
    expected_categories = {
        'Basic Information', 'Network Capabilities', 'Voice Features',
        'GNSS/GPS Information', 'Power Management', 'SIM Information'
    }
    assert categories_found == expected_categories

    # Confidence threshold filtering
    low_confidence_rows = csv_reporter._flatten_features(mock_modem_features, threshold=0.95)
    assert len(low_confidence_rows) < len(rows)


def test_output_validation(csv_reporter: CSVReporter, tmp_path: Path, mock_modem_features: ModemFeatures):
    """Test validate_output() method with various CSV scenarios."""
    output_path = tmp_path / "validation_test.csv"

    # First generate a valid CSV
    csv_reporter.generate(mock_modem_features, output_path)

    # Test valid CSV validation
    validation_passed, warnings = csv_reporter.validate_output(output_path)
    assert validation_passed is True
    assert len(warnings) >= 0  # May have warnings for few rows

    # Test non-existent file
    non_existent_path = tmp_path / "non_existent.csv"
    validation_passed, warnings = csv_reporter.validate_output(non_existent_path)
    assert validation_passed is False
    assert "Output file does not exist" in warnings


def test_error_handling(csv_reporter: CSVReporter, tmp_path: Path, mock_modem_features: ModemFeatures):
    """Test error handling scenarios."""
    # Invalid confidence threshold
    result = csv_reporter.generate(
        mock_modem_features,
        tmp_path / "invalid_threshold.csv",
        confidence_threshold=1.5
    )

    # Verify result for invalid threshold
    assert result.success is False
    assert any("Confidence threshold must be" in warning for warning in result.warnings)

    # Test no features above threshold
    result = csv_reporter.generate(
        mock_modem_features,
        tmp_path / "high_threshold.csv",
        confidence_threshold=0.99
    )

    # Verify result for no features
    assert result.success is True
    assert "CSV file has no data rows" in result.warnings
    assert "No features met the confidence threshold" in result.warnings

    # Verify file generation even with no features
    assert result.output_path.exists()

    # Validate the file content
    with open(result.output_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 0  # No rows should be present


def test_unit_extraction(csv_reporter: CSVReporter):
    """Test _extract_unit() method for different field names and values."""
    # Test predefined unit mappings
    assert csv_reporter._extract_unit("battery_voltage", 3800) == "mV"
    assert csv_reporter._extract_unit("max_downlink_speed", 150) == "Mbps"
    assert csv_reporter._extract_unit("max_uplink_speed", 50) == "Mbps"

    # Test unit extraction from string values
    assert csv_reporter._extract_unit("speed", "150 Mbps") == "Mbps"
    assert csv_reporter._extract_unit("frequency", "2.4 GHz") == "GHz"

    # Test fields without known units
    assert csv_reporter._extract_unit("manufacturer", "Quectel") == ""
    assert csv_reporter._extract_unit("model", "EC25") == ""