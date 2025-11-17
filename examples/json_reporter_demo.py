"""Demonstration of JSONReporter functionality.

This script shows how to use the JSONReporter to generate JSON reports
from modem features with various configuration options.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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


def create_sample_features():
    """Create sample ModemFeatures for demonstration."""
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
        vendor_specific={
            "custom_field": "custom_value",
            "advanced_features": {
                "feature1": True,
                "feature2": "enabled"
            }
        },
        parsing_errors=[],
        aggregate_confidence=0.85
    )


def example_basic_report():
    """Generate a basic JSON report with all features."""
    print("=" * 70)
    print("Example 1: Basic JSON Report Generation")
    print("=" * 70)

    # Create reporter and sample features
    reporter = JSONReporter()
    features = create_sample_features()

    # Generate report
    output_path = Path("output/basic_report.json")
    result = reporter.generate(
        features=features,
        output_path=output_path
    )

    # Display results
    print(f"\nReport Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Output Path: {result.output_path}")
    print(f"File Size: {result.file_size_bytes:,} bytes")
    print(f"Generation Time: {result.generation_time_seconds:.3f}s")
    print(f"Validation: {'PASSED' if result.validation_passed else 'FAILED'}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Display sample of generated JSON
    if output_path.exists():
        with open(output_path, 'r') as f:
            data = json.load(f)
        print("\nMetadata Section:")
        print(json.dumps(data["metadata"], indent=2))
        print("\nBasic Info Section:")
        print(json.dumps(data["features"]["basic_info"], indent=2))

    print()


def example_filtered_report():
    """Generate a report with confidence threshold filtering."""
    print("=" * 70)
    print("Example 2: Filtered Report (Confidence Threshold = 0.8)")
    print("=" * 70)

    # Create reporter and sample features
    reporter = JSONReporter()
    features = create_sample_features()

    # Generate report with confidence threshold
    output_path = Path("output/filtered_report.json")
    result = reporter.generate(
        features=features,
        output_path=output_path,
        confidence_threshold=0.8
    )

    print(f"\nReport Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Confidence Threshold: 0.8")

    # Show filtered results
    if output_path.exists():
        with open(output_path, 'r') as f:
            data = json.load(f)

        print("\nVoice Features (showing filtering):")
        voice = data["features"]["voice_features"]
        print(json.dumps(voice, indent=2))

        # Explain filtering
        print("\nFiltering Effect:")
        print("  - volte_supported: Included (confidence 0.90 >= 0.8)")
        print("  - vowifi_supported: Filtered to null (confidence 0.60 < 0.8)")
        print("  - circuit_switched_voice: Included (confidence 0.85 >= 0.8)")

    print()


def example_validation():
    """Demonstrate report validation."""
    print("=" * 70)
    print("Example 3: Report Validation")
    print("=" * 70)

    # Create and generate a report
    reporter = JSONReporter()
    features = create_sample_features()
    output_path = Path("output/validated_report.json")

    result = reporter.generate(
        features=features,
        output_path=output_path
    )

    # Validate the output
    is_valid, warnings = reporter.validate_output(output_path)

    print(f"\nValidation Result: {'VALID' if is_valid else 'INVALID'}")
    print(f"Warnings: {len(warnings)}")

    if warnings:
        print("\nValidation Warnings:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    else:
        print("\nNo validation issues found!")

    # Show structure verification
    if output_path.exists():
        with open(output_path, 'r') as f:
            data = json.load(f)

        print("\nStructure Verification:")
        print(f"  - Top-level keys: {list(data.keys())}")
        print(f"  - Metadata keys: {list(data['metadata'].keys())}")
        print(f"  - Feature sections: {list(data['features'].keys())}")

    print()


def example_low_confidence_features():
    """Generate a report with low-confidence features to show warnings."""
    print("=" * 70)
    print("Example 4: Low-Confidence Report with Warnings")
    print("=" * 70)

    # Create features with low aggregate confidence
    low_confidence_features = ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="Unknown",
            manufacturer_confidence=0.45,
            model="Unknown",
            model_confidence=0.40
        ),
        parsing_errors=[
            "Failed to parse AT+CGMM response",
            "Timeout on AT+CGSN command"
        ],
        aggregate_confidence=0.42  # Low overall confidence
    )

    reporter = JSONReporter()
    output_path = Path("output/low_confidence_report.json")

    result = reporter.generate(
        features=low_confidence_features,
        output_path=output_path
    )

    print(f"\nReport Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Aggregate Confidence: {low_confidence_features.aggregate_confidence:.2f}")

    # Show warnings
    if output_path.exists():
        with open(output_path, 'r') as f:
            data = json.load(f)

        if "warnings" in data:
            print(f"\nWarnings ({len(data['warnings'])}):")
            for i, warning in enumerate(data['warnings'], 1):
                print(f"  {i}. {warning}")

        if "parsing_errors" in data:
            print(f"\nParsing Errors ({len(data['parsing_errors'])}):")
            for i, error in enumerate(data['parsing_errors'], 1):
                print(f"  {i}. {error}")

    print()


def example_unicode_support():
    """Demonstrate Unicode character support in JSON reports."""
    print("=" * 70)
    print("Example 5: Unicode Support")
    print("=" * 70)

    # Create features with Unicode characters
    unicode_features = ModemFeatures(
        basic_info=BasicInfo(
            manufacturer="中国移动",  # China Mobile in Chinese
            manufacturer_confidence=0.95,
            model="Модель-5G",  # Model-5G in Cyrillic
            model_confidence=0.90
        ),
        sim_info=SIMInfo(
            operator="Société française",  # French operator
            operator_confidence=0.85
        ),
        aggregate_confidence=0.90
    )

    reporter = JSONReporter()
    output_path = Path("output/unicode_report.json")

    result = reporter.generate(
        features=unicode_features,
        output_path=output_path
    )

    print(f"\nReport Status: {'SUCCESS' if result.success else 'FAILED'}")

    # Show Unicode preservation
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print("\nUnicode Characters Preserved:")
        # Use ASCII representation for console output
        manufacturer = data['features']['basic_info']['manufacturer']
        model = data['features']['basic_info']['model']
        operator = data['features']['sim_info']['operator']

        print(f"  - Manufacturer: {manufacturer.encode('unicode-escape').decode('ascii')}")
        print(f"  - Model: {model.encode('unicode-escape').decode('ascii')}")
        print(f"  - Operator: {operator.encode('unicode-escape').decode('ascii')}")
        print("\n  Note: Unicode characters shown in escaped form for console compatibility.")
        print("        They are preserved correctly in the JSON file.")

    print()


def main():
    """Run all examples."""
    # Ensure output directory exists
    Path("output").mkdir(exist_ok=True)

    print("\n" + "=" * 70)
    print("JSONReporter Demonstration")
    print("=" * 70 + "\n")

    # Run examples
    example_basic_report()
    example_filtered_report()
    example_validation()
    example_low_confidence_features()
    example_unicode_support()

    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print("\nGenerated files:")
    for file in Path("output").glob("*.json"):
        size_kb = file.stat().st_size / 1024
        print(f"  - {file.name} ({size_kb:.1f} KB)")
    print()


if __name__ == "__main__":
    main()
