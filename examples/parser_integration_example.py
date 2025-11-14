"""Integration example demonstrating parser layer with AT Command Engine.

This example shows the complete pipeline:
SerialHandler → ATExecutor → FeatureExtractor → ModemFeatures
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import SerialHandler, ATExecutor, CommandResponse, ResponseStatus
from src.parsers import FeatureExtractor, ModemFeatures


def example_with_mock_data():
    """Demonstrate parser integration with mock AT command responses."""
    print("Parser Layer Integration Example")
    print("=" * 70)

    # Simulate AT command responses (in real usage, these come from ATExecutor)
    responses = {
        "AT+CGMI": CommandResponse(
            command="AT+CGMI",
            raw_response=["Quectel"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.15
        ),
        "AT+CGMM": CommandResponse(
            command="AT+CGMM",
            raw_response=["EC25"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.12
        ),
        "AT+CGMR": CommandResponse(
            command="AT+CGMR",
            raw_response=["EC25EFAR06A03M4G"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.13
        ),
        "AT+CGSN": CommandResponse(
            command="AT+CGSN",
            raw_response=["867698040123456"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.11
        ),
        "AT+CPIN?": CommandResponse(
            command="AT+CPIN?",
            raw_response=["+CPIN: READY", "OK"],
            status=ResponseStatus.SUCCESS,
            execution_time=0.10
        ),
        'AT+QENG="servingcell"': CommandResponse(
            command='AT+QENG="servingcell"',
            raw_response=[
                '+QENG: "servingcell","NOCONN","LTE","FDD",310,410,2E42,123,2300,4,5,5,B7D9,-95,-9,-71,16,Cat-6',
                'OK'
            ],
            status=ResponseStatus.SUCCESS,
            execution_time=0.25
        ),
    }

    # Create mock plugin with vendor metadata
    class MockMetadata:
        vendor = "Quectel"
        model = "EC25"
        category = "general"

    class MockPlugin:
        metadata = MockMetadata()

    plugin = MockPlugin()

    # Extract features using parser layer
    print("\nStep 1: Initializing FeatureExtractor")
    extractor = FeatureExtractor()

    print("\nStep 2: Extracting features from AT responses")
    features = extractor.extract_features(
        responses=responses,
        plugin=plugin,
        pre_parsed=None
    )

    # Display comprehensive results
    print("\n" + "=" * 70)
    print("EXTRACTED MODEM FEATURES")
    print("=" * 70)

    print("\n[BASIC INFORMATION]")
    print(f"  Manufacturer: {features.basic_info.manufacturer}")
    print(f"    Confidence: {features.basic_info.manufacturer_confidence:.2f}")
    print(f"  Model:        {features.basic_info.model}")
    print(f"    Confidence: {features.basic_info.model_confidence:.2f}")
    print(f"  Revision:     {features.basic_info.revision}")
    print(f"    Confidence: {features.basic_info.revision_confidence:.2f}")
    print(f"  IMEI:         {features.basic_info.imei}")
    print(f"    Confidence: {features.basic_info.imei_confidence:.2f}")

    print("\n[NETWORK CAPABILITIES]")
    print(f"  LTE Category: {features.network_capabilities.lte_category}")
    print(f"    Confidence: {features.network_capabilities.lte_category_confidence:.2f}")
    if features.network_capabilities.lte_bands:
        print(f"  LTE Bands:    {features.network_capabilities.lte_bands}")
        print(f"    Confidence: {features.network_capabilities.lte_bands_confidence:.2f}")

    print("\n[SIM INFORMATION]")
    print(f"  SIM Status:   {features.sim_info.sim_status.value}")
    print(f"    Confidence: {features.sim_info.sim_status_confidence:.2f}")

    print("\n[VENDOR-SPECIFIC FEATURES]")
    if features.vendor_specific:
        for key, value in features.vendor_specific.items():
            print(f"  {key}: {value}")
    else:
        print("  (none)")

    print("\n[QUALITY METRICS]")
    print(f"  Aggregate Confidence: {features.aggregate_confidence:.2f}")
    print(f"  Parsing Errors:       {len(features.parsing_errors)}")
    if features.parsing_errors:
        for error in features.parsing_errors:
            print(f"    - {error}")

    # Demonstrate filtering methods
    print("\n[HIGH CONFIDENCE FEATURES] (>= 0.7)")
    high_conf = features.get_high_confidence_features(threshold=0.7)
    for field_name, value in list(high_conf.items())[:8]:
        print(f"  {field_name}: {value}")
    if len(high_conf) > 8:
        print(f"  ... and {len(high_conf) - 8} more")

    # Demonstrate JSON export
    print("\n[JSON SERIALIZATION]")
    feature_dict = features.to_dict()
    print(f"  Exported to dictionary with {len(feature_dict)} top-level keys")
    print(f"  Keys: {list(feature_dict.keys())}")

    # Can be converted to JSON
    import json
    json_str = json.dumps(feature_dict, indent=2, default=str)
    print(f"\n  JSON size: {len(json_str)} bytes")
    print(f"  Sample: {json_str[:200]}...")

    print("\n" + "=" * 70)
    print("Integration example complete!")
    print("=" * 70)


def example_integration_workflow():
    """Show how parser integrates with real AT command execution flow."""
    print("\n\nTYPICAL INTEGRATION WORKFLOW")
    print("=" * 70)

    workflow = """
    1. Setup Hardware Connection
       |-> serial_handler = SerialHandler(port="/dev/ttyUSB0")
       |-> serial_handler.open()

    2. Initialize AT Executor
       |-> at_executor = ATExecutor(serial_handler)

    3. Execute AT Commands (from plugin or predefined list)
       |-> responses = {}
       |-> for cmd in ["AT+CGMI", "AT+CGMM", "AT+CGMR", "AT+CGSN", ...]:
           |-> responses[cmd] = at_executor.execute_command(cmd)

    4. Extract Features with Parser Layer
       |-> extractor = FeatureExtractor()
       |-> features = extractor.extract_features(responses, plugin)

    5. Use Extracted Features
       |-> Display in GUI
       |-> Export to CSV/JSON report
       |-> Store in database
       |-> Apply configuration recommendations

    6. Cleanup
       |-> serial_handler.close()
    """

    print(workflow)
    print("=" * 70)


if __name__ == "__main__":
    # Run examples
    example_with_mock_data()
    example_integration_workflow()
