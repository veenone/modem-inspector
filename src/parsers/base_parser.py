"""Abstract base class for vendor-specific parsers.

This module defines the interface that all vendor-specific parsers must implement,
enabling extensible parsing where new vendor parsers can be added without modifying
core code.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.command_response import CommandResponse


class BaseVendorParser(ABC):
    """Abstract interface for vendor-specific AT command parsers.

    Vendor-specific parsers extract features from proprietary AT commands
    that are unique to a particular modem manufacturer (e.g., Quectel, Nordic, SIMCom).

    Contract
    --------
    Subclasses must implement parse_vendor_features() which receives:
    - responses: Dict mapping AT commands to CommandResponse objects
    - plugin: Plugin instance with metadata (vendor, model, category)

    The method should return a dictionary with two sections:

    1. **Standard field enhancements** (top-level keys matching ModemFeatures fields):
       These augment or override universal parser results. For example:
       {
           "lte_category": "Cat-6",
           "lte_category_confidence": 1.0,
           "battery_voltage": 3800,
           "battery_voltage_confidence": 1.0
       }

    2. **vendor_specific dict** (nested under "vendor_specific" key):
       Vendor-unique features not in the standard schema:
       {
           "vendor_specific": {
               "v2x_support": True,
               "wifi_combo": "Wi-Fi 7"
           }
       }

    Error Handling
    --------------
    - Return empty dict {} if vendor commands not found (graceful degradation)
    - Return partial results if some commands fail
    - Never raise exceptions (catch internally and log)
    - Set confidence to 0.0 for failed extractions

    Example Implementation
    ----------------------
    >>> class QuectelParser(BaseVendorParser):
    ...     def parse_vendor_features(self, responses, plugin):
    ...         result = {"vendor_specific": {}}
    ...
    ...         # Extract LTE category from AT+QENG
    ...         if "AT+QENG" in responses:
    ...             qeng_resp = responses["AT+QENG"]
    ...             if qeng_resp.is_successful():
    ...                 category = extract_lte_category(qeng_resp.raw_response)
    ...                 result["lte_category"] = category
    ...                 result["lte_category_confidence"] = 1.0
    ...
    ...         # Extract V2X for automotive modems
    ...         if plugin.metadata.category == "automotive":
    ...             result["vendor_specific"]["v2x_support"] = True
    ...
    ...         return result
    """

    @abstractmethod
    def parse_vendor_features(
        self,
        responses: Dict[str, "CommandResponse"],
        plugin: Any,
    ) -> Dict[str, Any]:
        """Extract vendor-specific features from AT command responses.

        Args:
            responses: Dictionary mapping AT command strings to CommandResponse objects.
                      Example: {"AT+QENG": <CommandResponse>, "AT+QCFG": <CommandResponse>}
            plugin: Plugin instance containing metadata (vendor, model, category) used
                   to determine which features to extract and how to interpret responses.

        Returns:
            Dictionary with two sections:
            - Top-level keys for standard field enhancements (e.g., "lte_category")
            - "vendor_specific" dict for vendor-unique features

            Example return:
            {
                "lte_category": "Cat-6",
                "lte_category_confidence": 1.0,
                "vendor_specific": {
                    "v2x_support": True,
                    "wifi_combo": "Wi-Fi 7"
                }
            }

            Return empty dict {} if no vendor features extracted (graceful degradation).

        Note:
            This method should never raise exceptions. All errors should be caught,
            logged, and result in partial results or empty dict.
        """
        pass
