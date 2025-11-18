"""Unit tests for the ComparisonReporter class.

This module provides comprehensive test coverage for the ComparisonReporter
to ensure accurate feature comparison and report generation across
different formats and scenarios.
"""

import os
import csv
import json
import pytest
from pathlib import Path
from unittest.mock import Mock

from src.reports.comparison_reporter import ComparisonReporter
from src.parsers.feature_model import (
    ModemFeatures,
    BasicInfo,
    NetworkCapabilities,
    VoiceFeatures,
    NetworkTechnology,
    SIMStatus
)
from src.reports.report_models import ReportResult


@pytest.fixture
def quectel_ec25_modem1() -> ModemFeatures:
    """Fixture for Quectel EC25 modem with basic features."""
    return ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Quectel",
            model="EC25",
            imei="123456789",
            manufacturer_confidence=0.95,
            model_confidence=0.90
        ),
        network_capabilities=NetworkCapabilities(
            lte_support=True,
            lte_bands=[700, 850, 1900],
            network_technologies=[NetworkTechnology.LTE],
            lte_support_confidence=1.0,
            network_technologies_confidence=0.95
        ),
        voice_features=VoiceFeatures(
            volte_support=True,
            vowifi_support=False,
            volte_support_confidence=0.95
        )
    )


@pytest.fixture
def quectel_ec25_modem2() -> ModemFeatures:
    """Fixture for identical Quectel EC25 modem."""
    return ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Quectel",
            model="EC25",
            imei="987654321",
            manufacturer_confidence=0.95,
            model_confidence=0.90
        ),
        network_capabilities=NetworkCapabilities(
            lte_support=True,
            lte_bands=[700, 850, 1900],
            network_technologies=[NetworkTechnology.LTE],
            lte_support_confidence=1.0,
            network_technologies_confidence=0.95
        ),
        voice_features=VoiceFeatures(
            volte_support=True,
            vowifi_support=False,
            volte_support_confidence=0.95
        )
    )


@pytest.fixture
def simcom_sim7600_modem() -> ModemFeatures:
    """Fixture for SIMCom SIM7600 modem with different features."""
    return ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="SIMCom",
            model="SIM7600",
            imei="456789123",
            manufacturer_confidence=0.90,
            model_confidence=0.85
        ),
        network_capabilities=NetworkCapabilities(
            lte_support=True,
            lte_bands=[700, 1700, 2100],
            network_technologies=[NetworkTechnology.LTE, NetworkTechnology.FIVE_G],
            lte_support_confidence=1.0,
            network_technologies_confidence=0.85
        ),
        voice_features=VoiceFeatures(
            volte_support=False,
            vowifi_support=False,
            volte_support_confidence=0.85
        )
    )


@pytest.fixture
def comparison_reporter():
    """Fixture for ComparisonReporter instance."""
    return ComparisonReporter()


def test_generate_csv_report(
    comparison_reporter,
    quectel_ec25_modem1,
    quectel_ec25_modem2,
    simcom_sim7600_modem,
    tmp_path
):
    """Test CSV comparison report generation with multiple modems."""
    features_list = [
        ("Quectel EC25 #1", quectel_ec25_modem1),
        ("Quectel EC25 #2", quectel_ec25_modem2),
        ("SIMCom SIM7600", simcom_sim7600_modem)
    ]
    output_path = tmp_path / "comparison.csv"

    result = comparison_reporter.generate(
        features_list,
        output_path,
        confidence_threshold=0.5,
        format='csv'
    )

    # Check ReportResult
    assert result.success is True
    assert result.format == 'csv'
    assert result.output_path == output_path
    assert result.validation_passed is True
    assert result.file_size_bytes > 0

    # Validate CSV contents
    with open(output_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader)

        # Check headers
        assert headers[0] == 'Category'
        assert headers[1] == 'Feature'
        assert 'Quectel EC25 #1' in headers
        assert 'Quectel EC25 #2' in headers
        assert 'SIMCom SIM7600' in headers
        assert headers[-1] == 'Status'

        # Read rows
        rows = list(reader)
        assert len(rows) > 0

        # Sample row checks
        manufacturer_row = next(row for row in rows if row[1] == 'Manufacturer')
        assert manufacturer_row[0] == 'Basic Information'
        assert 'Quectel (95%)' in manufacturer_row[2:]
        assert manufacturer_row[-1] == 'Different'

        lte_bands_row = next(row for row in rows if row[1] == 'LTE Bands')
        assert '700, 850, 1900' in lte_bands_row[2:5]
        assert lte_bands_row[-1] == 'Partial'


def test_generate_html_report(
    comparison_reporter,
    quectel_ec25_modem1,
    quectel_ec25_modem2,
    simcom_sim7600_modem,
    tmp_path
):
    """Test HTML comparison report generation."""
    features_list = [
        ("Quectel EC25 #1", quectel_ec25_modem1),
        ("Quectel EC25 #2", quectel_ec25_modem2),
        ("SIMCom SIM7600", simcom_sim7600_modem)
    ]
    output_path = tmp_path / "comparison.html"

    result = comparison_reporter.generate(
        features_list,
        output_path,
        confidence_threshold=0.5,
        format='html'
    )

    # Check ReportResult
    assert result.success is True
    assert result.format == 'html'
    assert result.output_path == output_path
    assert result.validation_passed is True
    assert result.file_size_bytes > 0

    # Validate HTML contents
    with open(output_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

        # Check key HTML sections
        assert 'Modem Comparison Report' in html_content
        assert 'Summary Statistics' in html_content
        assert 'status-same' in html_content  # Green for identical
        assert 'status-different' in html_content  # Yellow for different
        assert 'status-partial' in html_content  # Gray for partial

        # Check modem names are present
        assert 'Quectel EC25 #1' in html_content
        assert 'SIMCom SIM7600' in html_content

        # Check confidence scores
        assert '95%' in html_content


def test_generate_markdown_report(
    comparison_reporter,
    quectel_ec25_modem1,
    quectel_ec25_modem2,
    simcom_sim7600_modem,
    tmp_path
):
    """Test Markdown comparison report generation."""
    features_list = [
        ("Quectel EC25 #1", quectel_ec25_modem1),
        ("Quectel EC25 #2", quectel_ec25_modem2),
        ("SIMCom SIM7600", simcom_sim7600_modem)
    ]
    output_path = tmp_path / "comparison.md"

    result = comparison_reporter.generate(
        features_list,
        output_path,
        confidence_threshold=0.5,
        format='markdown'
    )

    # Check ReportResult
    assert result.success is True
    assert result.format == 'markdown'
    assert result.output_path == output_path
    assert result.validation_passed is True
    assert result.file_size_bytes > 0

    # Validate Markdown contents
    with open(output_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

        # Check key Markdown sections
        assert '# Modem Comparison Report' in md_content
        assert '## Summary Statistics' in md_content
        assert '✅ Same' in md_content
        assert '⚠️ Different' in md_content
        assert '➖ Partial' in md_content

        # Check modem names
        assert 'Quectel EC25 #1' in md_content
        assert 'SIMCom SIM7600' in md_content

        # Check confidence scores
        assert '(95%)' in md_content


def test_generate_with_low_confidence_threshold(
    comparison_reporter,
    quectel_ec25_modem1,
    tmp_path
):
    """Test generating report with a very low confidence threshold."""
    single_modem_list = [("Quectel EC25", quectel_ec25_modem1)]
    output_path = tmp_path / "single_modem.csv"

    with pytest.raises(ValueError):
        comparison_reporter.generate(
            single_modem_list,
            output_path,
            confidence_threshold=0.0,
            format='csv'
        )


def test_generate_with_unsupported_format(
    comparison_reporter,
    quectel_ec25_modem1,
    quectel_ec25_modem2,
    tmp_path
):
    """Test generating report with an unsupported format."""
    features_list = [
        ("Quectel EC25 #1", quectel_ec25_modem1),
        ("Quectel EC25 #2", quectel_ec25_modem2)
    ]
    output_path = tmp_path / "unsupported_format.txt"

    with pytest.raises(ValueError, match="Invalid format"):
        comparison_reporter.generate(
            features_list,
            output_path,
            format='txt'
        )


def test_feature_comparison_logic(comparison_reporter):
    """Test the internal feature comparison logic."""
    identical_modem1 = ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Identical",
            model="Model A",
            manufacturer_confidence=1.0
        )
    )
    identical_modem2 = ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Identical",
            model="Model A",
            manufacturer_confidence=1.0
        )
    )
    different_modem = ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Different",
            model="Model B",
            manufacturer_confidence=1.0
        )
    )
    partial_modem = ModemFeatures(
        basic_info=BasicInfo(
            manufacturer=None,
            manufacturer_confidence=0.0
        )
    )

    # Test entirely identical features
    features_list = [
        ("Modem 1", identical_modem1),
        ("Modem 2", identical_modem2)
    ]
    result = comparison_reporter._compare_features(features_list, 0.5)
    assert result['summary']['identical_features'] > 0

    # Test different features
    features_list = [
        ("Modem 1", identical_modem1),
        ("Modem 2", different_modem)
    ]
    result = comparison_reporter._compare_features(features_list, 0.5)
    assert result['summary']['different_features'] > 0

    # Test partial features
    features_list = [
        ("Modem 1", identical_modem1),
        ("Modem 2", partial_modem)
    ]
    result = comparison_reporter._compare_features(features_list, 0.5)
    assert result['summary']['partial_features'] > 0


def test_value_comparison(comparison_reporter):
    """Test value comparison methods with different types."""
    # Test None and N/A handling
    assert comparison_reporter._format_value(None) == "N/A"
    assert comparison_reporter._format_value("") == "N/A"

    # Test boolean handling
    assert comparison_reporter._format_value(True) == "Yes"
    assert comparison_reporter._format_value(False) == "No"

    # Test list handling
    test_list = [NetworkTechnology.LTE, NetworkTechnology.FIVE_G]
    assert comparison_reporter._format_value(test_list) == "LTE, 5G"

    # Test enum handling
    assert comparison_reporter._format_value(NetworkTechnology.LTE) == "LTE"
    assert comparison_reporter._format_value(SIMStatus.INSERTED) == "Inserted"


def test_format_field_name(comparison_reporter):
    """Test field name formatting."""
    assert comparison_reporter._format_field_name("max_downlink_speed") == "Max Downlink Speed"
    assert comparison_reporter._format_field_name("imei") == "IMEI"
    assert comparison_reporter._format_field_name("lte_support") == "LTE Support"