"""Data models for modem features with confidence scoring.

This module defines immutable dataclasses representing modem capabilities,
where each feature field has an associated confidence score (0.0-1.0).
"""

from dataclasses import dataclass, field, fields, asdict
from enum import Enum
from typing import List, Dict, Optional, Any


class NetworkTechnology(Enum):
    """Network technology types."""
    LTE = "LTE"
    LTE_M = "LTE-M"
    NB_IOT = "NB-IoT"
    FIVEG_NSA = "5G NSA"
    FIVEG_SA = "5G SA"
    UNKNOWN = "Unknown"


class SIMStatus(Enum):
    """SIM card status."""
    READY = "ready"
    NOT_INSERTED = "not_inserted"
    PIN_REQUIRED = "pin_required"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BasicInfo:
    """Basic modem information.

    Each field has a corresponding _confidence field indicating
    the reliability of the extracted value (0.0-1.0).
    """
    manufacturer: str = "Unknown"
    manufacturer_confidence: float = 0.0

    model: str = "Unknown"
    model_confidence: float = 0.0

    revision: str = "Unknown"
    revision_confidence: float = 0.0

    imei: str = "Unknown"
    imei_confidence: float = 0.0

    serial_number: str = "Unknown"
    serial_number_confidence: float = 0.0


@dataclass(frozen=True)
class NetworkCapabilities:
    """Network capabilities and band support.

    Each field has a corresponding _confidence field indicating
    the reliability of the extracted value (0.0-1.0).
    """
    supported_technologies: List[NetworkTechnology] = field(default_factory=list)
    supported_technologies_confidence: float = 0.0

    lte_bands: List[int] = field(default_factory=list)
    lte_bands_confidence: float = 0.0

    fiveg_bands: List[str] = field(default_factory=list)
    fiveg_bands_confidence: float = 0.0

    max_downlink_speed: str = "Unknown"
    max_downlink_speed_confidence: float = 0.0

    max_uplink_speed: str = "Unknown"
    max_uplink_speed_confidence: float = 0.0

    carrier_aggregation: bool = False
    carrier_aggregation_confidence: float = 0.0

    lte_category: str = "Unknown"
    lte_category_confidence: float = 0.0


@dataclass(frozen=True)
class VoiceFeatures:
    """Voice capabilities.

    Each field has a corresponding _confidence field indicating
    the reliability of the extracted value (0.0-1.0).
    """
    volte_supported: bool = False
    volte_supported_confidence: float = 0.0

    vowifi_supported: bool = False
    vowifi_supported_confidence: float = 0.0

    circuit_switched_voice: bool = False
    circuit_switched_voice_confidence: float = 0.0


@dataclass(frozen=True)
class GNSSInfo:
    """GNSS/GPS capabilities.

    Each field has a corresponding _confidence field indicating
    the reliability of the extracted value (0.0-1.0).
    """
    gnss_supported: bool = False
    gnss_supported_confidence: float = 0.0

    supported_systems: List[str] = field(default_factory=list)
    supported_systems_confidence: float = 0.0

    last_location: Optional[str] = None
    last_location_confidence: float = 0.0


@dataclass(frozen=True)
class PowerManagement:
    """Power management features.

    Each field has a corresponding _confidence field indicating
    the reliability of the extracted value (0.0-1.0).
    """
    psm_supported: bool = False
    psm_supported_confidence: float = 0.0

    edrx_supported: bool = False
    edrx_supported_confidence: float = 0.0

    power_class: str = "Unknown"
    power_class_confidence: float = 0.0

    battery_voltage: Optional[int] = None
    battery_voltage_confidence: float = 0.0


@dataclass(frozen=True)
class SIMInfo:
    """SIM card information.

    Each field has a corresponding _confidence field indicating
    the reliability of the extracted value (0.0-1.0).
    """
    sim_status: SIMStatus = SIMStatus.UNKNOWN
    sim_status_confidence: float = 0.0

    iccid: str = "Unknown"
    iccid_confidence: float = 0.0

    imsi: str = "Unknown"
    imsi_confidence: float = 0.0

    operator: str = "Unknown"
    operator_confidence: float = 0.0


@dataclass(frozen=True)
class ModemFeatures:
    """Complete modem feature set with confidence scoring.

    This is the top-level data structure containing all parsed modem
    capabilities organized by category. Each nested dataclass contains
    features with associated confidence scores.
    """
    basic_info: BasicInfo = field(default_factory=BasicInfo)
    network_capabilities: NetworkCapabilities = field(default_factory=NetworkCapabilities)
    voice_features: VoiceFeatures = field(default_factory=VoiceFeatures)
    gnss_info: GNSSInfo = field(default_factory=GNSSInfo)
    power_management: PowerManagement = field(default_factory=PowerManagement)
    sim_info: SIMInfo = field(default_factory=SIMInfo)

    vendor_specific: Dict[str, Any] = field(default_factory=dict)
    parsing_errors: List[str] = field(default_factory=list)
    aggregate_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary.

        Returns:
            Dictionary with all features, recursively converting nested
            dataclasses and enums to their primitive values.
        """
        def convert_value(obj: Any) -> Any:
            """Recursively convert dataclasses and enums."""
            if isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, "__dataclass_fields__"):
                return {k: convert_value(v) for k, v in asdict(obj).items()}
            elif isinstance(obj, list):
                return [convert_value(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_value(v) for k, v in obj.items()}
            return obj

        return convert_value(asdict(self))

    def get_high_confidence_features(self, threshold: float = 0.7) -> Dict[str, Any]:
        """Get features with confidence >= threshold.

        Args:
            threshold: Minimum confidence score (0.0-1.0)

        Returns:
            Dictionary of field names and values meeting confidence threshold
        """
        result = {}

        def extract_high_confidence(obj: Any, prefix: str = "") -> None:
            """Recursively extract high-confidence fields."""
            if not hasattr(obj, "__dataclass_fields__"):
                return

            obj_fields = fields(obj)
            for f in obj_fields:
                field_name = f.name
                field_value = getattr(obj, field_name)

                # Check if this is a confidence field
                if field_name.endswith("_confidence"):
                    continue

                # Check for corresponding confidence field
                confidence_field = f"{field_name}_confidence"
                if hasattr(obj, confidence_field):
                    confidence = getattr(obj, confidence_field)
                    if confidence >= threshold:
                        full_name = f"{prefix}.{field_name}" if prefix else field_name
                        result[full_name] = field_value

                # Recurse into nested dataclasses
                elif hasattr(field_value, "__dataclass_fields__"):
                    new_prefix = f"{prefix}.{field_name}" if prefix else field_name
                    extract_high_confidence(field_value, new_prefix)

        extract_high_confidence(self)
        return result

    def get_low_confidence_features(self, threshold: float = 0.3) -> Dict[str, Any]:
        """Get features with confidence < threshold.

        Args:
            threshold: Maximum confidence score (0.0-1.0)

        Returns:
            Dictionary of field names and values below confidence threshold
        """
        result = {}

        def extract_low_confidence(obj: Any, prefix: str = "") -> None:
            """Recursively extract low-confidence fields."""
            if not hasattr(obj, "__dataclass_fields__"):
                return

            obj_fields = fields(obj)
            for f in obj_fields:
                field_name = f.name
                field_value = getattr(obj, field_name)

                # Check if this is a confidence field
                if field_name.endswith("_confidence"):
                    continue

                # Check for corresponding confidence field
                confidence_field = f"{field_name}_confidence"
                if hasattr(obj, confidence_field):
                    confidence = getattr(obj, confidence_field)
                    if confidence < threshold:
                        full_name = f"{prefix}.{field_name}" if prefix else field_name
                        result[full_name] = field_value

                # Recurse into nested dataclasses
                elif hasattr(field_value, "__dataclass_fields__"):
                    new_prefix = f"{prefix}.{field_name}" if prefix else field_name
                    extract_low_confidence(field_value, new_prefix)

        extract_low_confidence(self)
        return result
