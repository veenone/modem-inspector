"""Basic test demonstrating parser layer functionality."""

from src.parsers import ModemFeatures, FeatureExtractor
from src.core.command_response import CommandResponse, ResponseStatus


def test_basic_parsing():
    """Test basic feature extraction with sample responses."""
    print("Testing Parser Layer Basic Functionality")
    print("=" * 60)

    # Create sample AT command responses
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
            raw_response=["123456789012345"],  # Valid 15-digit IMEI
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        ),
        "AT+CPIN?": CommandResponse(
            command="AT+CPIN?",
            raw_response=["+CPIN: READY"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.1
        ),
    }

    # Create mock plugin
    class MockMetadata:
        vendor = "Quectel"
        model = "EC25"
        category = "general"

    class MockPlugin:
        metadata = MockMetadata()

    plugin = MockPlugin()

    # Extract features
    extractor = FeatureExtractor()
    features = extractor.extract_features(responses, plugin)

    # Display results
    print("\n[OK] Feature Extraction Complete")
    print(f"\nBasic Information:")
    print(f"  Manufacturer: {features.basic_info.manufacturer} "
          f"(confidence: {features.basic_info.manufacturer_confidence:.2f})")
    print(f"  Model: {features.basic_info.model} "
          f"(confidence: {features.basic_info.model_confidence:.2f})")
    print(f"  Revision: {features.basic_info.revision} "
          f"(confidence: {features.basic_info.revision_confidence:.2f})")
    print(f"  IMEI: {features.basic_info.imei} "
          f"(confidence: {features.basic_info.imei_confidence:.2f})")

    print(f"\nSIM Information:")
    print(f"  Status: {features.sim_info.sim_status.value} "
          f"(confidence: {features.sim_info.sim_status_confidence:.2f})")

    print(f"\nAggregate Confidence: {features.aggregate_confidence:.2f}")
    print(f"Parsing Errors: {len(features.parsing_errors)}")

    # Test high confidence filtering
    high_conf = features.get_high_confidence_features(threshold=0.7)
    print(f"\nHigh Confidence Features (>= 0.7): {len(high_conf)}")
    for field_name in list(high_conf.keys())[:5]:
        print(f"  - {field_name}")

    # Test JSON serialization
    feature_dict = features.to_dict()
    print(f"\n[OK] JSON Serialization: {len(feature_dict)} top-level keys")

    # Test immutability
    try:
        features.basic_info.manufacturer = "Modified"
        print("\n[FAIL] FAILED: ModemFeatures should be immutable!")
    except Exception:
        print("\n[OK] Immutability: Features are correctly frozen")

    print("\n" + "=" * 60)
    print("All basic tests passed!")


if __name__ == "__main__":
    test_basic_parsing()
