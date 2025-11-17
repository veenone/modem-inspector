"""Unit tests for JSONReporter class.

Tests JSON report generation, serialization, validation, and error handling.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

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
from src.reports.json_reporter import JSONReporter
from src.reports.report_models import ReportResult


class TestJSONReporterGenerate:
    """Test JSONReporter.generate() method."""

    @pytest.fixture
    def reporter(self):
        """Create JSONReporter instance."""
        return JSONReporter()

    @pytest.fixture
    def sample_features(self):
        """Create sample ModemFeatures for testing."""
        return ModemFeatures(
            basic_info=BasicInfo(
                manufacturer="Quectel",
                manufacturer_confidence=0.95,
                model="EC25",
                model_confidence=0.95,
                revision="EC25EFAR06A03M4G",
                revision_confidence=0.90,
                imei="123456789012345",
                imei_confidence=0.95,
                serial_number="SN123456",
                serial_number_confidence=0.85
            ),
            network_capabilities=NetworkCapabilities(
                supported_technologies=[
                    NetworkTechnology.LTE,
                    NetworkTechnology.LTE_M
                ],
                supported_technologies_confidence=0.90,
                lte_bands=[1, 3, 7, 20, 28],
                lte_bands_confidence=0.85,
                fiveg_bands=[],
                fiveg_bands_confidence=0.0,
                max_downlink_speed="150 Mbps",
                max_downlink_speed_confidence=0.80,
                max_uplink_speed="50 Mbps",
                max_uplink_speed_confidence=0.80,
                carrier_aggregation=True,
                carrier_aggregation_confidence=0.75,
                lte_category="Cat 4",
                lte_category_confidence=0.85
            ),
            voice_features=VoiceFeatures(
                volte_supported=True,
                volte_supported_confidence=0.90,
                vowifi_supported=False,
                vowifi_supported_confidence=0.60,
                circuit_switched_voice=True,
                circuit_switched_voice_confidence=0.85
            ),
            gnss_info=GNSSInfo(
                gnss_supported=True,
                gnss_supported_confidence=0.95,
                supported_systems=["GPS", "GLONASS", "BeiDou"],
                supported_systems_confidence=0.90,
                last_location=None,
                last_location_confidence=0.0
            ),
            power_management=PowerManagement(
                psm_supported=True,
                psm_supported_confidence=0.85,
                edrx_supported=True,
                edrx_supported_confidence=0.80,
                power_class="Class 3",
                power_class_confidence=0.75,
                battery_voltage=3800,
                battery_voltage_confidence=0.90
            ),
            sim_info=SIMInfo(
                sim_status=SIMStatus.READY,
                sim_status_confidence=0.95,
                iccid="89012345678901234567",
                iccid_confidence=0.90,
                imsi="123456789012345",
                imsi_confidence=0.90,
                operator="Example Operator",
                operator_confidence=0.85
            ),
            vendor_specific={"custom_field": "custom_value"},
            parsing_errors=[],
            aggregate_confidence=0.85
        )

    def test_generate_basic_report(self, reporter, sample_features, tmp_path):
        """Test basic JSON report generation."""
        output_path = tmp_path / "report.json"

        result = reporter.generate(
            features=sample_features,
            output_path=output_path
        )

        assert result.success
        assert result.format == "json"
        assert result.output_path == output_path
        assert output_path.exists()
        assert result.file_size_bytes > 0

    def test_generate_with_confidence_threshold(self, reporter, sample_features, tmp_path):
        """Test report generation with confidence threshold filtering."""
        output_path = tmp_path / "filtered_report.json"

        result = reporter.generate(
            features=sample_features,
            output_path=output_path,
            confidence_threshold=0.8
        )

        assert result.success

        # Load and verify filtered content
        with open(output_path, 'r') as f:
            data = json.load(f)

        # Check metadata includes threshold
        assert data["metadata"]["confidence_threshold"] == 0.8

        # Verify low-confidence fields are filtered (set to null)
        assert data["features"]["voice_features"]["vowifi_supported"] is None
        assert data["features"]["voice_features"]["vowifi_supported_confidence"] == 0.60

    def test_generate_creates_directories(self, reporter, sample_features, tmp_path):
        """Test that generate creates parent directories if needed."""
        output_path = tmp_path / "subdir" / "nested" / "report.json"

        result = reporter.generate(
            features=sample_features,
            output_path=output_path
        )

        assert result.success
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_generate_invalid_confidence_threshold(self, reporter, sample_features, tmp_path):
        """Test that invalid confidence threshold raises ValueError."""
        output_path = tmp_path / "report.json"

        with pytest.raises(ValueError, match="Confidence threshold must be in range"):
            reporter.generate(
                features=sample_features,
                output_path=output_path,
                confidence_threshold=1.5
            )

        with pytest.raises(ValueError, match="Confidence threshold must be in range"):
            reporter.generate(
                features=sample_features,
                output_path=output_path,
                confidence_threshold=-0.1
            )

    def test_generate_io_error(self, reporter, sample_features, tmp_path):
        """Test handling of IO errors during file writing."""
        # Use a read-only directory to force IO error
        import os
        import stat

        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        output_path = readonly_dir / "report.json"

        # Make directory read-only on Unix-like systems
        # On Windows, this test may not work as expected due to permission model
        try:
            readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
            result = reporter.generate(
                features=sample_features,
                output_path=output_path
            )

            # On some systems (Windows), chmod may not work as expected
            # So we accept either failure or success
            if not result.success:
                assert result.error_message is not None
                assert "Failed to write JSON file" in result.error_message
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(stat.S_IRWXU)


class TestJSONReporterValidation:
    """Test JSONReporter.validate_output() method."""

    @pytest.fixture
    def reporter(self):
        """Create JSONReporter instance."""
        return JSONReporter()

    def test_validate_valid_report(self, reporter, tmp_path):
        """Test validation of valid JSON report."""
        report_path = tmp_path / "valid_report.json"

        # Create valid report structure
        report_data = {
            "metadata": {
                "report_format": "json",
                "generated_at": "2025-01-17T10:30:00",
                "version": "1.0.0",
                "aggregate_confidence": 0.85,
                "confidence_threshold": 0.0,
                "total_features": 20
            },
            "features": {
                "basic_info": {"manufacturer": "Quectel"},
                "network_capabilities": {},
                "voice_features": {},
                "gnss_info": {},
                "power_management": {},
                "sim_info": {}
            }
        }

        with open(report_path, 'w') as f:
            json.dump(report_data, f)

        is_valid, warnings = reporter.validate_output(report_path)

        assert is_valid
        assert len(warnings) == 0

    def test_validate_missing_file(self, reporter, tmp_path):
        """Test validation of non-existent file."""
        missing_path = tmp_path / "missing.json"

        is_valid, warnings = reporter.validate_output(missing_path)

        assert not is_valid
        assert "does not exist" in warnings[0]

    def test_validate_empty_file(self, reporter, tmp_path):
        """Test validation of empty file."""
        empty_path = tmp_path / "empty.json"
        empty_path.touch()

        is_valid, warnings = reporter.validate_output(empty_path)

        assert not is_valid
        assert "empty" in warnings[0]

    def test_validate_invalid_json_syntax(self, reporter, tmp_path):
        """Test validation of file with invalid JSON syntax."""
        invalid_path = tmp_path / "invalid.json"

        with open(invalid_path, 'w') as f:
            f.write("{ invalid json syntax ]")

        is_valid, warnings = reporter.validate_output(invalid_path)

        assert not is_valid
        assert "Invalid JSON syntax" in warnings[0]

    def test_validate_missing_required_keys(self, reporter, tmp_path):
        """Test validation detects missing required keys."""
        incomplete_path = tmp_path / "incomplete.json"

        # Missing 'features' key
        incomplete_data = {
            "metadata": {
                "report_format": "json",
                "generated_at": "2025-01-17T10:30:00"
            }
        }

        with open(incomplete_path, 'w') as f:
            json.dump(incomplete_data, f)

        is_valid, warnings = reporter.validate_output(incomplete_path)

        assert not is_valid
        assert any("Missing required top-level key: 'features'" in w for w in warnings)

    def test_validate_missing_metadata_keys(self, reporter, tmp_path):
        """Test validation detects missing metadata keys."""
        incomplete_path = tmp_path / "incomplete_metadata.json"

        # Missing some metadata keys
        incomplete_data = {
            "metadata": {
                "report_format": "json"
                # Missing other required keys
            },
            "features": {}
        }

        with open(incomplete_path, 'w') as f:
            json.dump(incomplete_data, f)

        is_valid, warnings = reporter.validate_output(incomplete_path)

        # Should still be valid structurally, but have warnings
        assert any("Missing metadata key" in w for w in warnings)

    def test_validate_low_confidence_warning(self, reporter, tmp_path):
        """Test validation warns about low aggregate confidence."""
        low_confidence_path = tmp_path / "low_confidence.json"

        report_data = {
            "metadata": {
                "report_format": "json",
                "generated_at": "2025-01-17T10:30:00",
                "version": "1.0.0",
                "aggregate_confidence": 0.5,  # Low confidence
                "confidence_threshold": 0.0,
                "total_features": 10
            },
            "features": {}
        }

        with open(low_confidence_path, 'w') as f:
            json.dump(report_data, f)

        is_valid, warnings = reporter.validate_output(low_confidence_path)

        assert is_valid
        assert any("Low aggregate confidence" in w for w in warnings)

    def test_validate_parsing_errors_warning(self, reporter, tmp_path):
        """Test validation warns about parsing errors."""
        errors_path = tmp_path / "with_errors.json"

        report_data = {
            "metadata": {
                "report_format": "json",
                "generated_at": "2025-01-17T10:30:00",
                "version": "1.0.0",
                "aggregate_confidence": 0.85,
                "confidence_threshold": 0.0,
                "total_features": 10
            },
            "features": {},
            "parsing_errors": ["Error 1", "Error 2"]
        }

        with open(errors_path, 'w') as f:
            json.dump(report_data, f)

        is_valid, warnings = reporter.validate_output(errors_path)

        assert is_valid
        assert any("parsing error" in w for w in warnings)


class TestJSONReporterSerialization:
    """Test JSONReporter._serialize_features() method."""

    @pytest.fixture
    def reporter(self):
        """Create JSONReporter instance."""
        return JSONReporter()

    def test_serialize_enum_values(self, reporter):
        """Test that enums are serialized as values, not names."""
        features = ModemFeatures(
            network_capabilities=NetworkCapabilities(
                supported_technologies=[NetworkTechnology.LTE, NetworkTechnology.FIVEG_SA],
                supported_technologies_confidence=0.9
            ),
            sim_info=SIMInfo(
                sim_status=SIMStatus.READY,
                sim_status_confidence=0.95
            )
        )

        serialized = reporter._serialize_features(features, 0.0)

        # Enums should be string values, not enum names
        assert serialized["network_capabilities"]["supported_technologies"] == ["LTE", "5G SA"]
        assert serialized["sim_info"]["sim_status"] == "ready"

    def test_serialize_with_threshold_filtering(self, reporter):
        """Test feature filtering by confidence threshold."""
        features = ModemFeatures(
            basic_info=BasicInfo(
                manufacturer="Quectel",
                manufacturer_confidence=0.95,
                model="EC25",
                model_confidence=0.60  # Below threshold
            )
        )

        serialized = reporter._serialize_features(features, 0.8)

        # High-confidence field included
        assert serialized["basic_info"]["manufacturer"] == "Quectel"
        assert serialized["basic_info"]["manufacturer_confidence"] == 0.95

        # Low-confidence field set to null
        assert serialized["basic_info"]["model"] is None
        assert serialized["basic_info"]["model_confidence"] == 0.60

    def test_serialize_lists_and_optional_fields(self, reporter):
        """Test serialization of lists and optional fields."""
        features = ModemFeatures(
            network_capabilities=NetworkCapabilities(
                lte_bands=[1, 3, 7, 20],
                lte_bands_confidence=0.85,
                fiveg_bands=[],  # Empty list
                fiveg_bands_confidence=0.0
            ),
            gnss_info=GNSSInfo(
                last_location=None,  # Optional field
                last_location_confidence=0.0
            )
        )

        serialized = reporter._serialize_features(features, 0.0)

        # Lists should be JSON arrays
        assert serialized["network_capabilities"]["lte_bands"] == [1, 3, 7, 20]
        assert serialized["network_capabilities"]["fiveg_bands"] == []

        # Optional fields should be null
        assert serialized["gnss_info"]["last_location"] is None


class TestJSONReporterStructure:
    """Test JSON report structure and metadata."""

    @pytest.fixture
    def reporter(self):
        """Create JSONReporter instance."""
        return JSONReporter()

    @pytest.fixture
    def sample_features(self):
        """Create sample ModemFeatures."""
        return ModemFeatures(
            basic_info=BasicInfo(
                manufacturer="Quectel",
                manufacturer_confidence=0.95
            ),
            parsing_errors=["Test error"],
            aggregate_confidence=0.65  # Low confidence
        )

    def test_report_structure_complete(self, reporter, sample_features, tmp_path):
        """Test complete JSON report structure."""
        output_path = tmp_path / "structure_test.json"

        reporter.generate(
            features=sample_features,
            output_path=output_path,
            confidence_threshold=0.7
        )

        with open(output_path, 'r') as f:
            data = json.load(f)

        # Check top-level structure
        assert "metadata" in data
        assert "features" in data
        assert "parsing_errors" in data
        assert "warnings" in data  # Should have warnings due to low confidence

        # Check metadata structure
        metadata = data["metadata"]
        assert metadata["report_format"] == "json"
        assert "generated_at" in metadata
        assert metadata["version"] == "1.0.0"
        assert metadata["aggregate_confidence"] == 0.65
        assert metadata["confidence_threshold"] == 0.7
        assert "total_features" in metadata

        # Check features structure
        features = data["features"]
        assert "basic_info" in features
        assert "network_capabilities" in features
        assert "voice_features" in features
        assert "gnss_info" in features
        assert "power_management" in features
        assert "sim_info" in features

    def test_iso8601_timestamp_format(self, reporter, sample_features, tmp_path):
        """Test that timestamp is in ISO 8601 format."""
        output_path = tmp_path / "timestamp_test.json"

        reporter.generate(
            features=sample_features,
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = json.load(f)

        timestamp = data["metadata"]["generated_at"]

        # Verify ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
        assert len(timestamp) == 19
        assert timestamp[4] == "-"
        assert timestamp[7] == "-"
        assert timestamp[10] == "T"
        assert timestamp[13] == ":"
        assert timestamp[16] == ":"

        # Verify can be parsed
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")

    def test_warnings_generation(self, reporter, sample_features, tmp_path):
        """Test warning generation for low confidence and errors."""
        output_path = tmp_path / "warnings_test.json"

        reporter.generate(
            features=sample_features,
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = json.load(f)

        warnings = data.get("warnings", [])

        # Should have warning for low confidence
        assert any("Low aggregate confidence" in w for w in warnings)

        # Should have warning for parsing errors
        assert any("Parsing errors encountered" in w for w in warnings)

    def test_pretty_printing(self, reporter, sample_features, tmp_path):
        """Test that JSON is pretty-printed with proper indentation."""
        output_path = tmp_path / "pretty_test.json"

        reporter.generate(
            features=sample_features,
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            content = f.read()

        # Check for indentation (2 spaces)
        assert '  "metadata"' in content
        assert '    "report_format"' in content

        # Verify it's still valid JSON
        json.loads(content)

    def test_unicode_support(self, reporter, tmp_path):
        """Test that unicode characters are preserved (ensure_ascii=False)."""
        features = ModemFeatures(
            basic_info=BasicInfo(
                manufacturer="中国移动",  # Chinese characters
                manufacturer_confidence=0.95,
                model="Модель",  # Cyrillic characters
                model_confidence=0.90
            )
        )

        output_path = tmp_path / "unicode_test.json"

        reporter.generate(
            features=features,
            output_path=output_path
        )

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Unicode should be preserved
        assert data["features"]["basic_info"]["manufacturer"] == "中国移动"
        assert data["features"]["basic_info"]["model"] == "Модель"


class TestJSONReporterEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def reporter(self):
        """Create JSONReporter instance."""
        return JSONReporter()

    def test_empty_features(self, reporter, tmp_path):
        """Test report generation with empty/default features."""
        empty_features = ModemFeatures()
        output_path = tmp_path / "empty_features.json"

        result = reporter.generate(
            features=empty_features,
            output_path=output_path
        )

        assert result.success

        with open(output_path, 'r') as f:
            data = json.load(f)

        assert data["metadata"]["aggregate_confidence"] == 0.0
        assert "features" in data

    def test_vendor_specific_data(self, reporter, tmp_path):
        """Test serialization of vendor-specific data."""
        features = ModemFeatures(
            vendor_specific={
                "custom_field": "value",
                "nested": {"key": "value"},
                "list_field": [1, 2, 3]
            }
        )

        output_path = tmp_path / "vendor_test.json"

        reporter.generate(
            features=features,
            output_path=output_path
        )

        with open(output_path, 'r') as f:
            data = json.load(f)

        assert "vendor_specific" in data
        assert data["vendor_specific"]["custom_field"] == "value"
        assert data["vendor_specific"]["nested"]["key"] == "value"
        assert data["vendor_specific"]["list_field"] == [1, 2, 3]

    def test_count_features_accuracy(self, reporter):
        """Test feature counting logic."""
        features = ModemFeatures(
            basic_info=BasicInfo(
                manufacturer="Quectel",
                manufacturer_confidence=0.95,
                model="EC25",
                model_confidence=0.90,
                revision="R01",
                revision_confidence=0.85
            )
        )

        serialized = reporter._serialize_features(features, 0.0)
        count = reporter._count_features(serialized)

        # Count all features across all sections:
        # basic_info: manufacturer, model, revision, imei, serial_number = 5
        # network_capabilities: 7 features (supported_technologies, lte_bands, fiveg_bands,
        #                                    max_downlink_speed, max_uplink_speed, carrier_aggregation, lte_category)
        # voice_features: 3 features (volte_supported, vowifi_supported, circuit_switched_voice)
        # gnss_info: 3 features (gnss_supported, supported_systems, last_location)
        # power_management: 4 features (psm_supported, edrx_supported, power_class, battery_voltage)
        # sim_info: 4 features (sim_status, iccid, imsi, operator)
        # Total: 5 + 7 + 3 + 3 + 4 + 4 = 26
        assert count == 26

    def test_result_metadata_accuracy(self, reporter, tmp_path):
        """Test that ReportResult contains accurate metadata."""
        features = ModemFeatures(
            basic_info=BasicInfo(
                manufacturer="Quectel",
                manufacturer_confidence=0.95
            )
        )

        output_path = tmp_path / "metadata_test.json"

        result = reporter.generate(
            features=features,
            output_path=output_path
        )

        assert result.success
        assert result.format == "json"
        assert result.output_path == output_path
        assert result.file_size_bytes > 0
        assert result.generation_time_seconds >= 0
        assert result.validation_passed
