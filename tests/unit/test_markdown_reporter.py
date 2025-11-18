"""Unit tests for MarkdownReporter class."""

import json
import re
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.reports.markdown_reporter import MarkdownReporter
from src.parsers.feature_model import (
    ModemFeatures, BasicInfo, NetworkCapabilities,
    VoiceFeatures, GNSSInfo, PowerManagement, SIMInfo,
    NetworkTechnology, SIMStatus
)


@pytest.fixture
def mock_modem_features() -> ModemFeatures:
    """Create a comprehensive mock ModemFeatures object for testing."""
    return ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Quectel",
            model="EC25",
            firmware_version="1.2.3",
            imei="123456789012345",
            imei_confidence=0.9
        ),
        network_capabilities=NetworkCapabilities(
            max_downlink_speed=150,
            max_downlink_speed_confidence=0.8,
            supported_technologies=[
                NetworkTechnology.LTE,
                NetworkTechnology.LTE_CAT4
            ],
            supported_technologies_confidence=0.7,
        ),
        voice_features=VoiceFeatures(
            volte_support=True,
            volte_support_confidence=0.6,
            vowifi_support=False,
            vowifi_support_confidence=0.3
        ),
        gnss_info=GNSSInfo(
            gps_support=True,
            gps_support_confidence=0.9,
            glonass_support=True,
            glonass_support_confidence=0.8
        ),
        power_management=PowerManagement(
            psm_support=True,
            psm_support_confidence=0.7,
            edrx_support=False,
            edrx_support_confidence=0.4
        ),
        sim_info=SIMInfo(
            sim_status=SIMStatus.READY,
            sim_status_confidence=0.9
        ),
        vendor_specific={
            "custom_key": "custom_value",
            "extra_info": {"nested": "data"}
        },
        aggregate_confidence=0.75,
        parsing_errors=[],
        warnings=[]
    )


@pytest.fixture
def markdown_reporter():
    """Create a MarkdownReporter instance."""
    return MarkdownReporter()


def test_markdown_reporter_generate(
    markdown_reporter: MarkdownReporter,
    mock_modem_features: ModemFeatures,
    tmp_path: Path
):
    """Test successful Markdown generation."""
    output_path = tmp_path / "modem_report.md"

    # Generate report
    result = markdown_reporter.generate(
        features=mock_modem_features,
        output_path=output_path,
        confidence_threshold=0.5
    )

    # Assertions
    assert result.success is True
    assert result.output_path == output_path
    assert result.format == 'markdown'
    assert result.validation_passed is True
    assert output_path.exists()

    # Read generated markdown
    content = output_path.read_text(encoding='utf-8')

    # Validate content
    assert "# Modem Inspection Report" in content
    assert "Quectel EC25" in content
    assert "## Basic Information" in content
    assert "| Feature" in content
    assert "| --- |" in content
    assert "150 Mbps" in content  # Downlink speed
    assert "---" in content  # Horizontal rule
    assert json.dumps(mock_modem_features.vendor_specific, indent=2) in content


def test_markdown_reporter_confidence_threshold(
    markdown_reporter: MarkdownReporter,
    mock_modem_features: ModemFeatures,
    tmp_path: Path
):
    """Test confidence threshold filtering."""
    output_path = tmp_path / "filtered_report.md"

    # Generate report with high threshold
    result = markdown_reporter.generate(
        features=mock_modem_features,
        output_path=output_path,
        confidence_threshold=0.8
    )

    # Read generated markdown
    content = output_path.read_text(encoding='utf-8')

    # Verify feature filtering
    assert result.success is True
    assert "Max Downlink Speed" in content  # 0.8 confidence
    assert "VoLTE Support" not in content  # 0.6 confidence (below threshold)
    assert "VoWiFi Support" not in content  # 0.3 confidence (below threshold)

    # Verify total feature count
    assert "Total Features: 3" in content  # High confidence features


def test_markdown_reporter_emoji_indicators(
    markdown_reporter: MarkdownReporter,
    mock_modem_features: ModemFeatures,
    tmp_path: Path
):
    """Test confidence emoji indicators."""
    output_path = tmp_path / "confidence_report.md"

    # Generate report
    markdown_reporter.generate(
        features=mock_modem_features,
        output_path=output_path,
        confidence_threshold=0.0
    )

    # Read generated markdown
    content = output_path.read_text(encoding='utf-8')

    # Check emoji indicators
    # High confidence (≥0.7)
    assert "✅ IMEI" in content  # 0.9
    assert "✅ GPS Support" in content  # 0.9

    # Medium confidence (0.3-0.69)
    assert "⚠️ VoLTE Support" in content  # 0.6

    # Low confidence (<0.3)
    assert "❌ VoWiFi Support" in content  # 0.3


def test_markdown_reporter_template_loading(
    markdown_reporter: MarkdownReporter,
    mock_modem_features: ModemFeatures,
    tmp_path: Path
):
    """Test custom and default template loading."""
    # Create a test custom template
    custom_template_path = tmp_path / "custom_template.j2"
    custom_template_path.write_text("""
# Custom {{ modem_id }} Report
Total Features: {{ total_features }}
    """)

    # Test default template
    output_path_default = tmp_path / "default_report.md"
    result_default = markdown_reporter.generate(
        features=mock_modem_features,
        output_path=output_path_default
    )
    assert result_default.success is True

    # Test custom template
    output_path_custom = tmp_path / "custom_report.md"
    result_custom = markdown_reporter.generate(
        features=mock_modem_features,
        output_path=output_path_custom,
        template=str(custom_template_path)
    )
    assert result_custom.success is True

    # Verify custom template contents
    custom_content = output_path_custom.read_text(encoding='utf-8')
    assert "# Custom Quectel EC25 Report" in custom_content
    assert f"Total Features: 6" in custom_content  # All features at threshold 0.0


def test_markdown_reporter_validation(
    markdown_reporter: MarkdownReporter,
    mock_modem_features: ModemFeatures,
    tmp_path: Path
):
    """Test Markdown file validation."""
    # Prepare test path
    output_path = tmp_path / "validation_report.md"

    # Generate report
    markdown_reporter.generate(
        features=mock_modem_features,
        output_path=output_path
    )

    # Validate output
    validation_passed, warnings = markdown_reporter.validate_output(output_path)

    # Assertions
    assert validation_passed is True
    assert not warnings  # No warnings expected for a valid report

    # Manual validation
    content = output_path.read_text(encoding='utf-8')

    # Validate headers
    assert re.search(r'^#\s+', content)  # Main title
    assert re.search(r'^##\s+', content)  # Section headers

    # Validate tables
    assert '|' in content  # Pipe table present
    assert re.search(r'\|\s*---\s*\|', content)  # Table header separator

    # Validate horizontal rules
    assert '---' in content


def test_markdown_reporter_error_handling(
    markdown_reporter: MarkdownReporter,
    tmp_path: Path
):
    """Test error handling scenarios."""
    # Create an empty features mock
    empty_features = ModemFeatures(
        basic_info=BasicInfo(),
        network_capabilities=NetworkCapabilities(),
        voice_features=VoiceFeatures(),
        gnss_info=GNSSInfo(),
        power_management=PowerManagement(),
        sim_info=SIMInfo()
    )

    # Test with no features
    output_path = tmp_path / "empty_report.md"
    result = markdown_reporter.generate(
        features=empty_features,
        output_path=output_path,
        confidence_threshold=0.5
    )

    # Validate result
    assert result.success is True
    assert result.total_features == 0
    assert "No features met the confidence threshold" in result.warnings

    # Test invalid confidence threshold
    with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
        markdown_reporter.generate(
            features=empty_features,
            output_path=output_path,
            confidence_threshold=1.5
        )


def test_markdown_reporter_value_formatting(markdown_reporter: MarkdownReporter):
    """Test value formatting for different types."""
    # Test None
    assert markdown_reporter._format_value(None) == "N/A"

    # Test bool
    assert markdown_reporter._format_value(True) == "Yes"
    assert markdown_reporter._format_value(False) == "No"

    # Test list
    assert markdown_reporter._format_value([1, 2, 3]) == "1, 2, 3"
    assert markdown_reporter._format_value([]) == "N/A"

    # Test NetworkTechnology
    assert markdown_reporter._format_value(NetworkTechnology.LTE) == "LTE"

    # Test other types
    assert markdown_reporter._format_value(42) == "42"
    assert markdown_reporter._format_value("test") == "test"


def test_markdown_reporter_field_name_formatting(markdown_reporter: MarkdownReporter):
    """Test field name formatting."""
    # Test snake_case to Title Case conversion
    assert markdown_reporter._format_field_name("max_downlink_speed") == "Max Downlink Speed"

    # Test acronyms
    assert markdown_reporter._format_field_name("imei") == "IMEI"
    assert markdown_reporter._format_field_name("max_lte_speed") == "Max LTE Speed"
    assert markdown_reporter._format_field_name("volte_support") == "VoLTE Support"


def test_markdown_reporter_unit_extraction(markdown_reporter: MarkdownReporter):
    """Test unit extraction for different fields."""
    # Test predefined unit mapping
    assert markdown_reporter._extract_unit("battery_voltage", 3800) == "mV"
    assert markdown_reporter._extract_unit("max_downlink_speed", 150) == "Mbps"

    # Test unit extraction from string
    assert markdown_reporter._extract_unit("custom_field", "150 Mbps") == "Mbps"
    assert markdown_reporter._extract_unit("custom_field", "5 GHz") == "GHz"

    # Test no unit
    assert markdown_reporter._extract_unit("unknown_field", "value") == ""