"""Integration test for parser layer with AT Command Engine.

Tests the complete pipeline from AT command execution to feature extraction.
"""

import pytest
from src.core import CommandResponse, ResponseStatus, ATExecutor
from src.parsers import FeatureExtractor, ModemFeatures, NetworkTechnology, SIMStatus


class TestParserATIntegration:
    """Integration tests for parser layer with AT Command Engine."""

    def test_basic_feature_extraction(self):
        """Test feature extraction from standard AT responses."""
        # Simulate AT command responses
        responses = {
            "AT+CGMI": CommandResponse(
                command="AT+CGMI",
                raw_response=["Quectel"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
            "AT+CGMM": CommandResponse(
                command="AT+CGMM",
                raw_response=["EC25"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
            "AT+CGMR": CommandResponse(
                command="AT+CGMR",
                raw_response=["EC25EFAR06A03M4G"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
            "AT+CGSN": CommandResponse(
                command="AT+CGSN",
                raw_response=["123456789012345"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
        }

        # Mock plugin
        class MockMetadata:
            vendor = "Quectel"
            model = "EC25"
            category = "general"

        class MockPlugin:
            metadata = MockMetadata()

        # Extract features
        extractor = FeatureExtractor()
        features = extractor.extract_features(responses, MockPlugin())

        # Verify basic info
        assert features.basic_info.manufacturer == "Quectel"
        assert features.basic_info.manufacturer_confidence == 1.0
        assert features.basic_info.model == "EC25"
        assert features.basic_info.model_confidence == 1.0
        assert features.basic_info.revision == "EC25EFAR06A03M4G"
        assert features.basic_info.revision_confidence == 1.0
        assert features.basic_info.imei == "123456789012345"
        assert features.basic_info.imei_confidence == 1.0

        # Verify aggregate confidence
        assert features.aggregate_confidence == 1.0

        # Verify no errors
        assert len(features.parsing_errors) == 0

    def test_vendor_specific_parsing_quectel(self):
        """Test Quectel vendor-specific feature extraction."""
        responses = {
            "AT+CGMI": CommandResponse(
                command="AT+CGMI",
                raw_response=["Quectel"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
            'AT+QENG="servingcell"': CommandResponse(
                command='AT+QENG="servingcell"',
                raw_response=[
                    '+QENG: "servingcell","NOCONN","LTE","FDD",310,410,2E42,123,2300,4,5,5,B7D9,-95,-9,-71,16,Cat-4',
                    "OK"
                ],
                status=ResponseStatus.SUCCESS,
                execution_time=0.2
            ),
        }

        class MockMetadata:
            vendor = "Quectel"
            model = "EC25"
            category = "general"

        class MockPlugin:
            metadata = MockMetadata()

        extractor = FeatureExtractor()
        features = extractor.extract_features(responses, MockPlugin())

        # Verify LTE category was extracted from vendor parser
        assert features.network_capabilities.lte_category == "Cat-4"
        assert features.network_capabilities.lte_category_confidence == 1.0

    def test_sim_status_extraction(self):
        """Test SIM status extraction and enum conversion."""
        responses = {
            "AT+CPIN?": CommandResponse(
                command="AT+CPIN?",
                raw_response=["+CPIN: READY", "OK"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
        }

        class MockMetadata:
            vendor = "Unknown"
            model = "Unknown"
            category = "general"

        class MockPlugin:
            metadata = MockMetadata()

        extractor = FeatureExtractor()
        features = extractor.extract_features(responses, MockPlugin())

        # Verify SIM status
        assert features.sim_info.sim_status == SIMStatus.READY
        assert features.sim_info.sim_status_confidence == 1.0

    def test_error_responses_graceful_degradation(self):
        """Test graceful handling of error responses."""
        responses = {
            "AT+CGMI": CommandResponse(
                command="AT+CGMI",
                raw_response=["ERROR"],
                status=ResponseStatus.ERROR,
                execution_time=0.1,
                error_message="Command not supported"
            ),
            "AT+CGMM": CommandResponse(
                command="AT+CGMM",
                raw_response=[],  # Empty response
                status=ResponseStatus.ERROR,
                execution_time=0.1
            ),
        }

        class MockMetadata:
            vendor = "Unknown"
            model = "Unknown"
            category = "general"

        class MockPlugin:
            metadata = MockMetadata()

        extractor = FeatureExtractor()
        features = extractor.extract_features(responses, MockPlugin())

        # Should return "Unknown" with 0.0 confidence for failed commands
        assert features.basic_info.manufacturer == "Unknown"
        assert features.basic_info.manufacturer_confidence == 0.0
        assert features.basic_info.model == "Unknown"
        assert features.basic_info.model_confidence == 0.0

        # Aggregate confidence should be 0 when all extractions fail
        assert features.aggregate_confidence == 0.0

    def test_json_serialization(self):
        """Test JSON serialization of extracted features."""
        import json

        responses = {
            "AT+CGMI": CommandResponse(
                command="AT+CGMI",
                raw_response=["TestManufacturer"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
        }

        class MockMetadata:
            vendor = "Test"
            model = "Test"
            category = "general"

        class MockPlugin:
            metadata = MockMetadata()

        extractor = FeatureExtractor()
        features = extractor.extract_features(responses, MockPlugin())

        # Convert to dict and then JSON
        feature_dict = features.to_dict()
        json_str = json.dumps(feature_dict, default=str)

        # Verify JSON is valid and contains expected data
        parsed = json.loads(json_str)
        assert parsed["basic_info"]["manufacturer"] == "TestManufacturer"
        assert parsed["basic_info"]["manufacturer_confidence"] == 1.0

    def test_high_confidence_filtering(self):
        """Test filtering of high-confidence features."""
        responses = {
            "AT+CGMI": CommandResponse(
                command="AT+CGMI",
                raw_response=["Quectel"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
            "AT+CGMM": CommandResponse(
                command="AT+CGMM",
                raw_response=["EC25"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
        }

        class MockMetadata:
            vendor = "Quectel"
            model = "EC25"
            category = "general"

        class MockPlugin:
            metadata = MockMetadata()

        extractor = FeatureExtractor()
        features = extractor.extract_features(responses, MockPlugin())

        # Get high confidence features
        high_conf = features.get_high_confidence_features(threshold=0.7)

        # Should include manufacturer and model (both confidence 1.0)
        assert "basic_info.manufacturer" in high_conf
        assert "basic_info.model" in high_conf
        assert high_conf["basic_info.manufacturer"] == "Quectel"
        assert high_conf["basic_info.model"] == "EC25"

        # Should not include unknown fields (confidence 0.0)
        assert "basic_info.serial_number" not in high_conf

    def test_immutability(self):
        """Test that ModemFeatures is immutable."""
        responses = {
            "AT+CGMI": CommandResponse(
                command="AT+CGMI",
                raw_response=["Quectel"],
                status=ResponseStatus.SUCCESS,
                execution_time=0.1
            ),
        }

        class MockMetadata:
            vendor = "Quectel"
            model = "EC25"
            category = "general"

        class MockPlugin:
            metadata = MockMetadata()

        extractor = FeatureExtractor()
        features = extractor.extract_features(responses, MockPlugin())

        # Attempt to modify should raise error
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            features.basic_info.manufacturer = "Modified"

    def test_empty_responses(self):
        """Test handling of empty response dictionary."""
        responses = {}

        class MockMetadata:
            vendor = "Unknown"
            model = "Unknown"
            category = "general"

        class MockPlugin:
            metadata = MockMetadata()

        extractor = FeatureExtractor()
        features = extractor.extract_features(responses, MockPlugin())

        # Should return complete structure with all "Unknown" values
        assert features.basic_info.manufacturer == "Unknown"
        assert features.basic_info.model == "Unknown"
        assert features.aggregate_confidence == 0.0
        assert len(features.parsing_errors) == 0  # No errors, just no data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
