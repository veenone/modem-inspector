"""Unit tests for HTML report generator.

Tests the HTMLReporter class including template loading, context preparation,
validation, and error handling.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch

from src.reports.html_reporter import HTMLReporter
from src.reports.report_models import ReportResult
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


@pytest.fixture
def temp_dir():
    """Create temporary directory for test output."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_features():
    """Create sample ModemFeatures for testing."""
    return ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Quectel",
            manufacturer_confidence=0.95,
            model="EC25",
            model_confidence=0.95,
            revision="EC25AFAR06A07M4G",
            revision_confidence=0.90,
            imei="123456789012345",
            imei_confidence=0.98,
            serial_number="SN123456",
            serial_number_confidence=0.85
        ),
        network_capabilities=NetworkCapabilities(
            supported_technologies=[NetworkTechnology.LTE, NetworkTechnology.LTE_M],
            supported_technologies_confidence=0.90,
            lte_bands=[1, 3, 7, 8, 20, 28],
            lte_bands_confidence=0.92,
            fiveg_bands=[],
            fiveg_bands_confidence=0.0,
            max_downlink_speed="150 Mbps",
            max_downlink_speed_confidence=0.88,
            max_uplink_speed="50 Mbps",
            max_uplink_speed_confidence=0.88,
            carrier_aggregation=True,
            carrier_aggregation_confidence=0.85,
            lte_category="Cat 4",
            lte_category_confidence=0.90
        ),
        voice_features=VoiceFeatures(
            volte_supported=True,
            volte_supported_confidence=0.80,
            vowifi_supported=False,
            vowifi_supported_confidence=0.75,
            circuit_switched_voice=True,
            circuit_switched_voice_confidence=0.90
        ),
        gnss_info=GNSSInfo(
            gnss_supported=True,
            gnss_supported_confidence=0.95,
            supported_systems=["GPS", "GLONASS", "Galileo"],
            supported_systems_confidence=0.90,
            last_location="37.7749,-122.4194",
            last_location_confidence=0.70
        ),
        power_management=PowerManagement(
            psm_supported=True,
            psm_supported_confidence=0.85,
            edrx_supported=True,
            edrx_supported_confidence=0.82,
            power_class="Class 3",
            power_class_confidence=0.75,
            battery_voltage=3800,
            battery_voltage_confidence=0.88
        ),
        sim_info=SIMInfo(
            sim_status=SIMStatus.READY,
            sim_status_confidence=0.95,
            iccid="89012345678901234567",
            iccid_confidence=0.92,
            imsi="310260123456789",
            imsi_confidence=0.93,
            operator="T-Mobile",
            operator_confidence=0.90
        ),
        vendor_specific={
            "custom_feature_1": "value1",
            "custom_feature_2": "value2"
        },
        parsing_errors=["Error parsing AT+QCFG response"],
        aggregate_confidence=0.87
    )


@pytest.fixture
def reporter():
    """Create HTMLReporter instance."""
    return HTMLReporter()


class TestHTMLReporterGeneration:
    """Test HTML report generation."""

    def test_generate_success_default_template(self, reporter, sample_features, temp_dir):
        """Test successful report generation with default template."""
        output_path = temp_dir / "report.html"

        result = reporter.generate(sample_features, output_path, confidence_threshold=0.0)

        assert result.success is True
        assert result.output_path == output_path
        assert result.format == 'html'
        assert result.validation_passed is True
        assert output_path.exists()
        assert result.file_size_bytes > 0
        assert result.generation_time_seconds > 0

    def test_generate_with_confidence_threshold(self, reporter, sample_features, temp_dir):
        """Test report generation with confidence threshold."""
        output_path = temp_dir / "report_filtered.html"

        result = reporter.generate(sample_features, output_path, confidence_threshold=0.85)

        assert result.success is True
        assert output_path.exists()
        # High threshold should produce smaller file
        assert result.file_size_bytes > 0

    def test_generate_creates_parent_directory(self, reporter, sample_features, temp_dir):
        """Test that parent directories are created if they don't exist."""
        output_path = temp_dir / "subdir" / "nested" / "report.html"

        result = reporter.generate(sample_features, output_path, confidence_threshold=0.0)

        assert result.success is True
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_generate_invalid_confidence_threshold(self, reporter, sample_features, temp_dir):
        """Test that invalid confidence threshold returns error in ReportResult."""
        output_path = temp_dir / "report.html"

        # Test threshold > 1.0
        result = reporter.generate(sample_features, output_path, confidence_threshold=1.5)
        assert result.success is False
        assert any("Confidence threshold must be in range" in str(w) for w in result.warnings)

        # Test threshold < 0.0
        result = reporter.generate(sample_features, output_path, confidence_threshold=-0.1)
        assert result.success is False
        assert any("Confidence threshold must be in range" in str(w) for w in result.warnings)

    def test_generate_with_empty_features(self, reporter, temp_dir):
        """Test report generation with minimal/empty features."""
        empty_features = ModemFeatures()
        output_path = temp_dir / "empty_report.html"

        # Use high threshold so no features pass
        result = reporter.generate(empty_features, output_path, confidence_threshold=0.99)

        assert result.success is True
        assert output_path.exists()
        # Should have warning about no features with high threshold
        assert any("No features met the confidence threshold" in w for w in result.warnings)


class TestHTMLReporterValidation:
    """Test HTML output validation."""

    def test_validate_valid_html(self, reporter, sample_features, temp_dir):
        """Test validation of valid HTML output."""
        output_path = temp_dir / "report.html"
        reporter.generate(sample_features, output_path, confidence_threshold=0.0)

        is_valid, warnings = reporter.validate_output(output_path)

        assert is_valid is True
        assert isinstance(warnings, list)

    def test_validate_missing_file(self, reporter, temp_dir):
        """Test validation fails for non-existent file."""
        output_path = temp_dir / "nonexistent.html"

        is_valid, errors = reporter.validate_output(output_path)

        assert is_valid is False
        assert len(errors) > 0
        assert "does not exist" in errors[0]

    def test_validate_empty_file(self, reporter, temp_dir):
        """Test validation fails for empty file."""
        output_path = temp_dir / "empty.html"
        output_path.touch()  # Create empty file

        is_valid, errors = reporter.validate_output(output_path)

        assert is_valid is False
        assert "empty" in errors[0].lower()

    def test_validate_invalid_html(self, reporter, temp_dir):
        """Test validation of malformed HTML."""
        output_path = temp_dir / "invalid.html"

        # Write invalid HTML (missing required tags)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("<html><body>Missing head tag</body></html>")

        is_valid, errors = reporter.validate_output(output_path)

        assert is_valid is False
        assert len(errors) > 0


class TestHTMLReporterTemplateLoading:
    """Test template loading functionality."""

    def test_load_default_template(self, reporter):
        """Test loading embedded default template."""
        template = reporter._load_template(None)

        assert template is not None
        # Template should render without errors
        context = {
            'modem_id': 'Test',
            'generation_time': '2024-01-01T00:00:00',
            'confidence_threshold': 0.5,
            'total_features': 10,
            'aggregate_confidence': 0.8,
            'high_confidence_count': 8,
            'categories': [],
            'parsing_errors': [],
            'warnings': [],
            'vendor_specific': {}
        }
        html = template.render(**context)
        assert '<!DOCTYPE html>' in html
        assert '<html' in html

    def test_load_custom_template(self, reporter, temp_dir):
        """Test loading custom template from file."""
        # Create custom template
        template_path = temp_dir / "custom.j2"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head><title>{{ modem_id }}</title></head>
<body><h1>Custom Template</h1></body>
</html>
            """)

        template = reporter._load_template(str(template_path))

        assert template is not None
        html = template.render(modem_id="Test Modem")
        assert "Custom Template" in html
        assert "Test Modem" in html

    def test_load_nonexistent_template_fallback(self, reporter):
        """Test that nonexistent custom template falls back to default."""
        with pytest.raises(Exception, match="Custom template error"):
            reporter._load_template("/nonexistent/template.j2")


class TestHTMLReporterContextPreparation:
    """Test template context preparation."""

    def test_prepare_context_basic(self, reporter, sample_features):
        """Test basic context preparation."""
        context = reporter._prepare_context(sample_features, 0.0)

        assert 'modem_id' in context
        assert context['modem_id'] == "Quectel EC25"
        assert 'generation_time' in context
        assert 'confidence_threshold' in context
        assert context['confidence_threshold'] == 0.0
        assert 'total_features' in context
        assert context['total_features'] > 0
        assert 'aggregate_confidence' in context
        assert context['aggregate_confidence'] == 0.87
        assert 'categories' in context
        assert len(context['categories']) == 6  # All category types

    def test_prepare_context_with_threshold(self, reporter, sample_features):
        """Test context preparation with confidence threshold."""
        context_low = reporter._prepare_context(sample_features, 0.0)
        context_high = reporter._prepare_context(sample_features, 0.95)

        # Higher threshold should result in fewer features
        assert context_high['total_features'] < context_low['total_features']
        assert context_high['high_confidence_count'] <= context_low['high_confidence_count']

    def test_prepare_context_includes_errors_and_warnings(self, reporter, sample_features):
        """Test that context includes parsing errors and vendor specific data."""
        context = reporter._prepare_context(sample_features, 0.0)

        assert 'parsing_errors' in context
        assert len(context['parsing_errors']) > 0
        assert 'vendor_specific' in context
        assert len(context['vendor_specific']) > 0


class TestHTMLReporterValueFormatting:
    """Test value formatting methods."""

    def test_format_value_none(self, reporter):
        """Test formatting None values."""
        assert reporter._format_value(None) == "N/A"

    def test_format_value_boolean(self, reporter):
        """Test formatting boolean values."""
        assert reporter._format_value(True) == "Yes"
        assert reporter._format_value(False) == "No"

    def test_format_value_list(self, reporter):
        """Test formatting list values."""
        assert reporter._format_value([1, 2, 3]) == "1, 2, 3"
        assert reporter._format_value([]) == "N/A"

        # Test with enums
        tech_list = [NetworkTechnology.LTE, NetworkTechnology.LTE_M]
        formatted = reporter._format_value(tech_list)
        assert "LTE" in formatted
        assert "LTE-M" in formatted

    def test_format_value_enum(self, reporter):
        """Test formatting enum values."""
        assert reporter._format_value(NetworkTechnology.LTE) == "LTE"
        assert reporter._format_value(SIMStatus.READY) == "ready"

    def test_format_value_string(self, reporter):
        """Test formatting string values."""
        assert reporter._format_value("test") == "test"

    def test_format_field_name(self, reporter):
        """Test field name formatting."""
        assert reporter._format_field_name("manufacturer") == "Manufacturer"
        assert reporter._format_field_name("max_downlink_speed") == "Max Downlink Speed"

        # Test acronyms
        assert reporter._format_field_name("imei") == "IMEI"
        assert reporter._format_field_name("gnss_supported") == "GNSS Supported"
        assert reporter._format_field_name("volte_supported") == "VoLTE Supported"

    def test_extract_unit(self, reporter):
        """Test unit extraction."""
        assert reporter._extract_unit("battery_voltage", 3800) == "mV"
        assert reporter._extract_unit("max_downlink_speed", "150 Mbps") == "Mbps"
        assert reporter._extract_unit("unknown_field", "value") == ""

        # Test unit extraction from value string
        assert reporter._extract_unit("field", "10 MHz") == "MHz"
        assert reporter._extract_unit("field", "-95 dBm") == "dBm"


class TestHTMLReporterRepr:
    """Test string representation."""

    def test_repr(self, reporter):
        """Test __repr__ method."""
        repr_str = repr(reporter)
        assert "HTMLReporter" in repr_str
        assert "html" in repr_str.lower()


class TestHTMLReporterIntegration:
    """Integration tests for complete HTML generation workflow."""

    def test_full_workflow_default_template(self, reporter, sample_features, temp_dir):
        """Test complete workflow with default template."""
        output_path = temp_dir / "full_workflow.html"

        # Generate report
        result = reporter.generate(sample_features, output_path, confidence_threshold=0.5)

        assert result.success is True
        assert output_path.exists()

        # Validate output
        is_valid, errors = reporter.validate_output(output_path)
        assert is_valid is True

        # Check content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "Quectel EC25" in content
        assert "Basic Information" in content
        assert "Network Capabilities" in content
        assert "<!DOCTYPE html>" in content
        assert "Error parsing AT+QCFG response" in content  # Parsing error

    def test_full_workflow_custom_template(self, reporter, sample_features, temp_dir):
        """Test complete workflow with custom template."""
        # Create minimal custom template
        template_path = temp_dir / "minimal.j2"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write("""
<!DOCTYPE html>
<html lang="en">
<head><title>{{ modem_id }}</title></head>
<body>
    <h1>{{ modem_id }}</h1>
    <p>Total Features: {{ total_features }}</p>
</body>
</html>
            """)

        output_path = temp_dir / "custom_workflow.html"

        # Generate with custom template
        result = reporter.generate(
            sample_features,
            output_path,
            confidence_threshold=0.5,
            template=str(template_path)
        )

        assert result.success is True
        assert output_path.exists()

        # Check custom content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "Quectel EC25" in content
        assert "Total Features:" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
