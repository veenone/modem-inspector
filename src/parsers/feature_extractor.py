"""Feature extractor orchestrator coordinating parsers to produce ModemFeatures.

This module orchestrates the full feature extraction pipeline:
universal parsing → vendor enhancement → confidence scoring → ModemFeatures assembly
"""

import logging
from typing import Dict, Any, Optional, List
from src.parsers.feature_model import (
    ModemFeatures,
    BasicInfo,
    NetworkCapabilities,
    VoiceFeatures,
    GNSSInfo,
    PowerManagement,
    SIMInfo,
    NetworkTechnology,
    SIMStatus,
)
from src.parsers.universal import UniversalParser
from src.parsers.vendor_specific import VendorParser

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Orchestrates universal and vendor parsers to produce complete ModemFeatures.

    This class coordinates the full feature extraction pipeline with graceful
    error handling, conflict resolution, and confidence scoring.
    """

    def __init__(
        self,
        universal_parser: Optional[UniversalParser] = None,
        vendor_parser: Optional[VendorParser] = None,
    ):
        """Initialize feature extractor with optional parser injection.

        Args:
            universal_parser: Optional UniversalParser instance (for testing)
            vendor_parser: Optional VendorParser instance (for testing)
        """
        self._universal_parser = universal_parser or UniversalParser()
        self._vendor_parser = vendor_parser or VendorParser()

    def extract_features(
        self,
        responses: Dict[str, Any],
        plugin: Any,
        pre_parsed: Optional[Dict[str, Any]] = None,
    ) -> ModemFeatures:
        """Extract complete modem features from AT command responses.

        Orchestrates full pipeline:
        1. Universal parsing (standard 3GPP commands)
        2. Vendor-specific parsing (proprietary commands)
        3. Merge pre-parsed data from PluginParser if provided
        4. Resolve conflicts (prefer universal > vendor > pre_parsed)
        5. Calculate aggregate confidence
        6. Assemble complete ModemFeatures

        Args:
            responses: Dictionary of AT commands to CommandResponse objects
            plugin: Plugin instance with metadata for vendor routing
            pre_parsed: Optional pre-parsed data from PluginParser

        Returns:
            Complete ModemFeatures with all sections populated (even if "Unknown").
            Never returns None or partial results - always returns complete structure.
        """
        parsing_errors: List[str] = []

        # Step 1: Universal parsing
        universal_features = self._parse_universal(responses, parsing_errors)

        # Step 2: Vendor-specific parsing
        vendor_features = self._parse_vendor(responses, plugin, universal_features, parsing_errors)

        # Step 3: Merge results with conflict resolution
        merged_features = self._merge_results(
            universal_features,
            vendor_features,
            pre_parsed or {},
            parsing_errors
        )

        # Step 4: Assemble ModemFeatures from merged data
        modem_features = self._assemble_modem_features(merged_features, parsing_errors)

        # Step 5: Calculate aggregate confidence
        aggregate_confidence = self._calculate_aggregate_confidence(modem_features)

        # Create final ModemFeatures with aggregate confidence
        # (dataclasses are immutable, so we need to create a new instance)
        final_features = ModemFeatures(
            basic_info=modem_features.basic_info,
            network_capabilities=modem_features.network_capabilities,
            voice_features=modem_features.voice_features,
            gnss_info=modem_features.gnss_info,
            power_management=modem_features.power_management,
            sim_info=modem_features.sim_info,
            vendor_specific=modem_features.vendor_specific,
            parsing_errors=parsing_errors,
            aggregate_confidence=aggregate_confidence,
        )

        logger.info(
            f"Feature extraction complete: aggregate_confidence={aggregate_confidence:.2f}, "
            f"errors={len(parsing_errors)}"
        )

        return final_features

    def _parse_universal(
        self,
        responses: Dict[str, Any],
        parsing_errors: List[str]
    ) -> Dict[str, Any]:
        """Parse universal features with error handling.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects
            parsing_errors: List to collect parsing errors

        Returns:
            Dictionary of parsed universal features
        """
        universal_features = {}

        try:
            logger.debug("Parsing universal features")

            # Parse each section with individual error handling
            try:
                basic_info = self._universal_parser.parse_basic_info(responses)
                universal_features.update(basic_info)
            except Exception as e:
                error_msg = f"Error parsing basic info: {e}"
                logger.error(error_msg, exc_info=True)
                parsing_errors.append(error_msg)

            try:
                network_caps = self._universal_parser.parse_network_capabilities(responses)
                universal_features.update(network_caps)
            except Exception as e:
                error_msg = f"Error parsing network capabilities: {e}"
                logger.error(error_msg, exc_info=True)
                parsing_errors.append(error_msg)

            try:
                voice_features = self._universal_parser.parse_voice_features(responses)
                universal_features.update(voice_features)
            except Exception as e:
                error_msg = f"Error parsing voice features: {e}"
                logger.error(error_msg, exc_info=True)
                parsing_errors.append(error_msg)

            try:
                gnss_info = self._universal_parser.parse_gnss_info(responses)
                universal_features.update(gnss_info)
            except Exception as e:
                error_msg = f"Error parsing GNSS info: {e}"
                logger.error(error_msg, exc_info=True)
                parsing_errors.append(error_msg)

            try:
                power_mgmt = self._universal_parser.parse_power_management(responses)
                universal_features.update(power_mgmt)
            except Exception as e:
                error_msg = f"Error parsing power management: {e}"
                logger.error(error_msg, exc_info=True)
                parsing_errors.append(error_msg)

            try:
                sim_info = self._universal_parser.parse_sim_info(responses)
                universal_features.update(sim_info)
            except Exception as e:
                error_msg = f"Error parsing SIM info: {e}"
                logger.error(error_msg, exc_info=True)
                parsing_errors.append(error_msg)

        except Exception as e:
            error_msg = f"Critical error in universal parsing: {e}"
            logger.error(error_msg, exc_info=True)
            parsing_errors.append(error_msg)

        return universal_features

    def _parse_vendor(
        self,
        responses: Dict[str, Any],
        plugin: Any,
        universal_features: Dict[str, Any],
        parsing_errors: List[str]
    ) -> Dict[str, Any]:
        """Parse vendor-specific features with error handling.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects
            plugin: Plugin instance for vendor routing
            universal_features: Universal features for conflict detection
            parsing_errors: List to collect parsing errors

        Returns:
            Dictionary of parsed vendor features
        """
        try:
            logger.debug("Parsing vendor-specific features")
            return self._vendor_parser.parse_vendor_features(
                responses, plugin, universal_features
            )
        except Exception as e:
            error_msg = f"Error in vendor parsing: {e}"
            logger.error(error_msg, exc_info=True)
            parsing_errors.append(error_msg)
            return {}

    def _merge_results(
        self,
        universal: Dict[str, Any],
        vendor: Dict[str, Any],
        pre_parsed: Dict[str, Any],
        parsing_errors: List[str]
    ) -> Dict[str, Any]:
        """Merge parsing results with conflict resolution.

        Priority: universal > vendor > pre_parsed

        Args:
            universal: Universal parser results
            vendor: Vendor parser results
            pre_parsed: Pre-parsed data from PluginParser
            parsing_errors: List to collect conflict warnings

        Returns:
            Merged features dictionary
        """
        merged = {}

        # Start with pre_parsed (lowest priority)
        merged.update(pre_parsed)

        # Merge vendor features (medium priority)
        for key, value in vendor.items():
            if key == "vendor_specific":
                # Always merge vendor_specific dict
                if "vendor_specific" not in merged:
                    merged["vendor_specific"] = {}
                merged["vendor_specific"].update(value)
            elif key not in merged:
                merged[key] = value
            elif merged[key] != value and not key.endswith("_confidence"):
                # Conflict detected - vendor overrides pre_parsed
                logger.debug(
                    f"Vendor overriding pre_parsed for '{key}': "
                    f"{merged[key]} → {value}"
                )
                merged[key] = value

        # Merge universal features (highest priority)
        for key, value in universal.items():
            if key not in merged:
                merged[key] = value
            elif merged[key] != value and not key.endswith("_confidence"):
                # Conflict detected - universal overrides vendor/pre_parsed
                logger.warning(
                    f"Universal overriding for '{key}': "
                    f"{merged[key]} → {value}"
                )
                merged[key] = value

        return merged

    def _assemble_modem_features(
        self,
        merged: Dict[str, Any],
        parsing_errors: List[str]
    ) -> ModemFeatures:
        """Assemble ModemFeatures from merged data.

        Args:
            merged: Merged features dictionary
            parsing_errors: List of parsing errors

        Returns:
            Complete ModemFeatures instance with all sections
        """
        # Assemble BasicInfo
        basic_info = BasicInfo(
            manufacturer=merged.get("manufacturer", "Unknown"),
            manufacturer_confidence=merged.get("manufacturer_confidence", 0.0),
            model=merged.get("model", "Unknown"),
            model_confidence=merged.get("model_confidence", 0.0),
            revision=merged.get("revision", "Unknown"),
            revision_confidence=merged.get("revision_confidence", 0.0),
            imei=merged.get("imei", "Unknown"),
            imei_confidence=merged.get("imei_confidence", 0.0),
            serial_number=merged.get("serial_number", "Unknown"),
            serial_number_confidence=merged.get("serial_number_confidence", 0.0),
        )

        # Assemble NetworkCapabilities
        # Convert string technology names to NetworkTechnology enum
        tech_list = merged.get("supported_technologies", [])
        network_techs = []
        for tech in tech_list:
            if isinstance(tech, str):
                try:
                    network_techs.append(NetworkTechnology(tech))
                except ValueError:
                    logger.warning(f"Unknown network technology: {tech}")
            elif isinstance(tech, NetworkTechnology):
                network_techs.append(tech)

        network_capabilities = NetworkCapabilities(
            supported_technologies=network_techs,
            supported_technologies_confidence=merged.get("supported_technologies_confidence", 0.0),
            lte_bands=merged.get("lte_bands", []),
            lte_bands_confidence=merged.get("lte_bands_confidence", 0.0),
            fiveg_bands=merged.get("fiveg_bands", []),
            fiveg_bands_confidence=merged.get("fiveg_bands_confidence", 0.0),
            max_downlink_speed=merged.get("max_downlink_speed", "Unknown"),
            max_downlink_speed_confidence=merged.get("max_downlink_speed_confidence", 0.0),
            max_uplink_speed=merged.get("max_uplink_speed", "Unknown"),
            max_uplink_speed_confidence=merged.get("max_uplink_speed_confidence", 0.0),
            carrier_aggregation=merged.get("carrier_aggregation", False),
            carrier_aggregation_confidence=merged.get("carrier_aggregation_confidence", 0.0),
            lte_category=merged.get("lte_category", "Unknown"),
            lte_category_confidence=merged.get("lte_category_confidence", 0.0),
        )

        # Assemble VoiceFeatures
        voice_features = VoiceFeatures(
            volte_supported=merged.get("volte_supported", False),
            volte_supported_confidence=merged.get("volte_supported_confidence", 0.0),
            vowifi_supported=merged.get("vowifi_supported", False),
            vowifi_supported_confidence=merged.get("vowifi_supported_confidence", 0.0),
            circuit_switched_voice=merged.get("circuit_switched_voice", False),
            circuit_switched_voice_confidence=merged.get("circuit_switched_voice_confidence", 0.0),
        )

        # Assemble GNSSInfo
        gnss_info = GNSSInfo(
            gnss_supported=merged.get("gnss_supported", False),
            gnss_supported_confidence=merged.get("gnss_supported_confidence", 0.0),
            supported_systems=merged.get("supported_systems", []),
            supported_systems_confidence=merged.get("supported_systems_confidence", 0.0),
            last_location=merged.get("last_location"),
            last_location_confidence=merged.get("last_location_confidence", 0.0),
        )

        # Assemble PowerManagement
        power_management = PowerManagement(
            psm_supported=merged.get("psm_supported", False),
            psm_supported_confidence=merged.get("psm_supported_confidence", 0.0),
            edrx_supported=merged.get("edrx_supported", False),
            edrx_supported_confidence=merged.get("edrx_supported_confidence", 0.0),
            power_class=merged.get("power_class", "Unknown"),
            power_class_confidence=merged.get("power_class_confidence", 0.0),
            battery_voltage=merged.get("battery_voltage"),
            battery_voltage_confidence=merged.get("battery_voltage_confidence", 0.0),
        )

        # Assemble SIMInfo
        # Convert string SIM status to SIMStatus enum
        sim_status_str = merged.get("sim_status", "unknown")
        try:
            sim_status = SIMStatus(sim_status_str)
        except ValueError:
            logger.warning(f"Unknown SIM status: {sim_status_str}, using UNKNOWN")
            sim_status = SIMStatus.UNKNOWN

        sim_info = SIMInfo(
            sim_status=sim_status,
            sim_status_confidence=merged.get("sim_status_confidence", 0.0),
            iccid=merged.get("iccid", "Unknown"),
            iccid_confidence=merged.get("iccid_confidence", 0.0),
            imsi=merged.get("imsi", "Unknown"),
            imsi_confidence=merged.get("imsi_confidence", 0.0),
            operator=merged.get("operator", "Unknown"),
            operator_confidence=merged.get("operator_confidence", 0.0),
        )

        # Extract vendor_specific dict
        vendor_specific = merged.get("vendor_specific", {})

        return ModemFeatures(
            basic_info=basic_info,
            network_capabilities=network_capabilities,
            voice_features=voice_features,
            gnss_info=gnss_info,
            power_management=power_management,
            sim_info=sim_info,
            vendor_specific=vendor_specific,
            parsing_errors=parsing_errors,
            aggregate_confidence=0.0,  # Will be calculated separately
        )

    def _calculate_aggregate_confidence(self, features: ModemFeatures) -> float:
        """Calculate aggregate confidence as average of all field confidences.

        Args:
            features: ModemFeatures instance

        Returns:
            Average confidence score (0.0-1.0), excluding 0.0 values
        """
        confidences = []

        # Collect all confidence scores from all sections
        for section in [
            features.basic_info,
            features.network_capabilities,
            features.voice_features,
            features.gnss_info,
            features.power_management,
            features.sim_info,
        ]:
            for field_name in dir(section):
                if field_name.endswith("_confidence"):
                    confidence = getattr(section, field_name)
                    # Only include non-zero confidences in average
                    if confidence > 0.0:
                        confidences.append(confidence)

        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)
