"""JSON report generator for modem features.

This module provides JSON format report generation with proper serialization
of ModemFeatures data, including confidence scores and metadata.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.parsers.feature_model import ModemFeatures
from src.reports.base_reporter import BaseReporter
from src.reports.report_models import ReportResult


class JSONReporter(BaseReporter):
    """Generate JSON format reports from modem features.

    Serializes ModemFeatures to JSON with proper handling of enums,
    confidence scores, and metadata. Includes validation of output
    and comprehensive error handling.

    The JSON structure includes:
    - metadata: Report generation information and statistics
    - features: Complete modem feature set with confidence scores
    - vendor_specific: Vendor-specific data (if present)
    - parsing_errors: Any errors encountered during parsing
    - warnings: Warnings for low-confidence or problematic data

    Example:
        >>> reporter = JSONReporter()
        >>> result = reporter.generate(
        ...     features=modem_features,
        ...     output_path=Path("report.json"),
        ...     confidence_threshold=0.7
        ... )
        >>> print(result.success)
        True
    """

    def generate(
        self,
        features: ModemFeatures,
        output_path: Path,
        confidence_threshold: float = 0.0,
        **kwargs
    ) -> ReportResult:
        """Generate a JSON report from modem features.

        Args:
            features: ModemFeatures object from parser layer
            output_path: Path where JSON report should be written
            confidence_threshold: Minimum confidence score (0.0-1.0) for filtering
            **kwargs: Additional options (currently unused for JSON format)

        Returns:
            ReportResult with generation status and metadata

        Raises:
            ValueError: If confidence_threshold is not in range [0.0, 1.0]
            IOError: If output_path cannot be written

        Example:
            >>> reporter = JSONReporter()
            >>> result = reporter.generate(features, Path("output.json"))
            >>> if result.success:
            ...     print(f"Generated report: {result.output_path}")
        """
        start_time = datetime.now()

        # Validate inputs
        self._validate_confidence_threshold(confidence_threshold)
        self._ensure_directory(output_path)

        try:
            # Serialize features with metadata
            report_data = self._build_report_structure(
                features=features,
                confidence_threshold=confidence_threshold
            )

            # Write JSON to file with pretty printing
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(
                    report_data,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=False
                )

            # Calculate generation time
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()

            # Validate output
            validation_passed, validation_errors = self.validate_output(output_path)

            # Build result
            return ReportResult(
                output_path=output_path,
                format="json",
                success=True,
                validation_passed=validation_passed,
                warnings=validation_errors,
                file_size_bytes=self._get_file_size(output_path),
                generation_time_seconds=generation_time
            )

        except (IOError, OSError) as e:
            return ReportResult(
                output_path=output_path,
                format="json",
                success=False,
                validation_passed=False,
                error_message=f"Failed to write JSON file: {str(e)}",
                file_size_bytes=0
            )
        except (TypeError, ValueError) as e:
            return ReportResult(
                output_path=output_path,
                format="json",
                success=False,
                validation_passed=False,
                error_message=f"JSON serialization error: {str(e)}",
                file_size_bytes=0
            )

    def validate_output(self, output_path: Path) -> Tuple[bool, List[str]]:
        """Validate generated JSON report format and content.

        Checks:
        - File exists and is not empty
        - Valid JSON syntax (can be parsed)
        - Required top-level keys present (metadata, features)
        - Structure integrity

        Args:
            output_path: Path to JSON report file to validate

        Returns:
            Tuple of (is_valid, warnings)
            - is_valid: True if report is valid, False otherwise
            - warnings: List of warning/error messages (empty if fully valid)

        Example:
            >>> reporter = JSONReporter()
            >>> is_valid, warnings = reporter.validate_output(Path("report.json"))
            >>> if not is_valid:
            ...     for warning in warnings:
            ...         print(f"Validation issue: {warning}")
        """
        warnings = []

        # Check file exists
        if not output_path.exists():
            return False, ["Output file does not exist"]

        # Check file is not empty
        file_size = self._get_file_size(output_path)
        if file_size == 0:
            return False, ["Output file is empty"]

        # Validate JSON syntax
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON syntax: {str(e)}"]
        except (IOError, OSError) as e:
            return False, [f"Failed to read file: {str(e)}"]

        # Validate structure - check required top-level keys
        required_keys = ["metadata", "features"]
        for key in required_keys:
            if key not in data:
                warnings.append(f"Missing required top-level key: '{key}'")

        # Validate metadata structure
        if "metadata" in data:
            metadata = data["metadata"]
            expected_metadata_keys = [
                "report_format",
                "generated_at",
                "version",
                "aggregate_confidence",
                "confidence_threshold",
                "total_features"
            ]
            for key in expected_metadata_keys:
                if key not in metadata:
                    warnings.append(f"Missing metadata key: '{key}'")

        # Check for low confidence warning
        if "metadata" in data:
            aggregate_confidence = data["metadata"].get("aggregate_confidence", 0.0)
            if aggregate_confidence < 0.7:
                warnings.append(
                    f"Low aggregate confidence: {aggregate_confidence:.2f} < 0.70"
                )

        # Check for parsing errors
        if "parsing_errors" in data and data["parsing_errors"]:
            error_count = len(data["parsing_errors"])
            warnings.append(
                f"Report contains {error_count} parsing error(s)"
            )

        # Return validation result
        # If we have critical structural issues, mark as invalid
        critical_issues = [
            w for w in warnings
            if "Missing required" in w or "Invalid JSON" in w
        ]
        is_valid = len(critical_issues) == 0

        return is_valid, warnings

    def _serialize_features(
        self,
        features: ModemFeatures,
        confidence_threshold: float
    ) -> Dict[str, Any]:
        """Serialize ModemFeatures to dictionary with confidence filtering.

        Converts ModemFeatures to a JSON-serializable dictionary with:
        - Proper enum serialization (values, not names)
        - Lists as JSON arrays
        - Optional fields as null (not omitted)
        - Confidence score filtering

        Args:
            features: ModemFeatures object to serialize
            confidence_threshold: Minimum confidence for feature inclusion

        Returns:
            Dictionary ready for JSON serialization

        Note:
            This method calls features.to_dict() which handles enum
            conversion and nested dataclass serialization automatically.
        """
        # Use ModemFeatures.to_dict() for base serialization
        # This handles enums, nested dataclasses, and lists properly
        features_dict = features.to_dict()

        # If threshold is 0.0, no filtering needed - return all features
        if confidence_threshold == 0.0:
            return features_dict

        # Filter features by confidence threshold
        # For threshold > 0.0, we need to selectively include features
        filtered_dict = {}

        for section_name, section_data in features_dict.items():
            # Handle special fields that don't need filtering
            if section_name in [
                "vendor_specific",
                "parsing_errors",
                "aggregate_confidence"
            ]:
                filtered_dict[section_name] = section_data
                continue

            # Handle feature sections with confidence scores
            if isinstance(section_data, dict):
                filtered_section = {}

                for field_name, field_value in section_data.items():
                    # Skip confidence fields themselves
                    if field_name.endswith("_confidence"):
                        continue

                    # Check if this field has a confidence score
                    confidence_field = f"{field_name}_confidence"
                    if confidence_field in section_data:
                        confidence = section_data[confidence_field]

                        # Include field if confidence meets threshold
                        if confidence >= confidence_threshold:
                            filtered_section[field_name] = field_value
                            filtered_section[confidence_field] = confidence
                        # Otherwise, set to null but keep confidence score
                        else:
                            filtered_section[field_name] = None
                            filtered_section[confidence_field] = confidence
                    else:
                        # No confidence score - include as-is
                        filtered_section[field_name] = field_value

                filtered_dict[section_name] = filtered_section
            else:
                # Not a dict - include as-is
                filtered_dict[section_name] = section_data

        return filtered_dict

    def _build_report_structure(
        self,
        features: ModemFeatures,
        confidence_threshold: float
    ) -> Dict[str, Any]:
        """Build complete JSON report structure with metadata.

        Creates the full report structure including:
        - metadata section with generation info and statistics
        - features section with serialized modem data
        - vendor_specific section (if present)
        - parsing_errors section (if present)
        - warnings section (if applicable)

        Args:
            features: ModemFeatures object to serialize
            confidence_threshold: Confidence threshold for filtering

        Returns:
            Complete report dictionary ready for JSON serialization
        """
        # Serialize features
        serialized_features = self._serialize_features(features, confidence_threshold)

        # Count total features (excluding metadata fields)
        total_features = self._count_features(serialized_features)

        # Build metadata section
        metadata = {
            "report_format": "json",
            "generated_at": self._format_timestamp(),
            "version": "1.0.0",
            "aggregate_confidence": features.aggregate_confidence,
            "confidence_threshold": confidence_threshold,
            "total_features": total_features
        }

        # Build report structure
        report = {
            "metadata": metadata,
            "features": {
                "basic_info": serialized_features.get("basic_info", {}),
                "network_capabilities": serialized_features.get(
                    "network_capabilities", {}
                ),
                "voice_features": serialized_features.get("voice_features", {}),
                "gnss_info": serialized_features.get("gnss_info", {}),
                "power_management": serialized_features.get("power_management", {}),
                "sim_info": serialized_features.get("sim_info", {})
            }
        }

        # Add vendor_specific if present
        if serialized_features.get("vendor_specific"):
            report["vendor_specific"] = serialized_features["vendor_specific"]

        # Add parsing_errors if present
        if serialized_features.get("parsing_errors"):
            report["parsing_errors"] = serialized_features["parsing_errors"]

        # Add warnings if applicable
        warnings = self._generate_warnings(features, confidence_threshold)
        if warnings:
            report["warnings"] = warnings

        return report

    def _count_features(self, features_dict: Dict[str, Any]) -> int:
        """Count total number of features in serialized dictionary.

        Args:
            features_dict: Serialized features dictionary

        Returns:
            Total count of feature fields (excluding confidence fields)
        """
        count = 0
        for section_name, section_data in features_dict.items():
            # Skip metadata fields
            if section_name in [
                "vendor_specific",
                "parsing_errors",
                "aggregate_confidence"
            ]:
                continue

            # Count fields in this section
            if isinstance(section_data, dict):
                for field_name in section_data.keys():
                    if not field_name.endswith("_confidence"):
                        count += 1

        return count

    def _generate_warnings(
        self,
        features: ModemFeatures,
        confidence_threshold: float
    ) -> List[str]:
        """Generate warnings for low confidence or parsing errors.

        Args:
            features: ModemFeatures object
            confidence_threshold: Confidence threshold used

        Returns:
            List of warning messages (empty if no warnings)
        """
        warnings = []

        # Warn if aggregate confidence is low
        if features.aggregate_confidence < 0.7:
            warnings.append(
                f"Low aggregate confidence: {features.aggregate_confidence:.2f} < 0.70. "
                "Some features may be unreliable."
            )

        # Warn if there are parsing errors
        if features.parsing_errors:
            warnings.append(
                f"Parsing errors encountered: {len(features.parsing_errors)} error(s). "
                "Check parsing_errors field for details."
            )

        return warnings
