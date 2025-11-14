"""Vendor parser dispatcher for routing to vendor-specific parsers.

This module provides a dispatcher that routes parsing requests to the appropriate
vendor-specific parser based on plugin metadata, with graceful error handling.
"""

import logging
from typing import Dict, Any, Optional
from src.parsers.base_parser import BaseVendorParser
from src.parsers.vendors.quectel_parser import QuectelParser
from src.parsers.vendors.nordic_parser import NordicParser
from src.parsers.vendors.simcom_parser import SIMComParser

logger = logging.getLogger(__name__)


class VendorParser:
    """Dispatcher for vendor-specific parsers with graceful error handling.

    Routes parsing requests to the appropriate vendor parser based on
    plugin.metadata.vendor and aggregates results with conflict detection.
    """

    def __init__(self):
        """Initialize vendor parser registry."""
        self._registry: Dict[str, BaseVendorParser] = {
            "qualcomm": None,  # Placeholder for future implementation
            "quectel": QuectelParser(),
            "nordic": NordicParser(),
            "simcom": SIMComParser(),
        }

    def parse_vendor_features(
        self,
        responses: Dict[str, Any],
        plugin: Any,
        universal_features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Parse vendor-specific features and merge with universal features.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects
            plugin: Plugin instance with metadata.vendor for routing
            universal_features: Optional universal parser results for conflict detection

        Returns:
            Dictionary with vendor-specific enhancements and vendor_specific dict.
            Returns empty dict if vendor parser not found or on error (graceful degradation).
        """
        if universal_features is None:
            universal_features = {}

        # Get vendor name from plugin metadata
        vendor = self._get_vendor_name(plugin)
        if not vendor:
            logger.info("No vendor metadata found in plugin, skipping vendor parsing")
            return {}

        # Get parser for vendor
        parser = self._get_parser_for_vendor(vendor)
        if not parser:
            logger.info(f"No vendor parser registered for '{vendor}', skipping vendor parsing")
            return {}

        # Parse vendor features with error isolation
        try:
            logger.debug(f"Parsing vendor features using {parser.__class__.__name__}")
            vendor_features = parser.parse_vendor_features(responses, plugin)

            # Detect conflicts with universal features
            self._log_conflicts(vendor_features, universal_features)

            return vendor_features

        except Exception as e:
            logger.error(
                f"Error in vendor parser {parser.__class__.__name__}: {e}",
                exc_info=True
            )
            return {}

    def _get_vendor_name(self, plugin: Any) -> Optional[str]:
        """Extract vendor name from plugin metadata.

        Args:
            plugin: Plugin instance

        Returns:
            Vendor name (lowercase) or None if not found
        """
        if not hasattr(plugin, "metadata"):
            return None

        if not hasattr(plugin.metadata, "vendor"):
            return None

        vendor = plugin.metadata.vendor
        if isinstance(vendor, str):
            return vendor.lower().strip()

        return None

    def _get_parser_for_vendor(self, vendor: str) -> Optional[BaseVendorParser]:
        """Look up parser by vendor name (case-insensitive).

        Args:
            vendor: Vendor name (will be normalized to lowercase)

        Returns:
            Parser instance or None if not registered
        """
        vendor_lower = vendor.lower()
        return self._registry.get(vendor_lower)

    def _log_conflicts(
        self,
        vendor_features: Dict[str, Any],
        universal_features: Dict[str, Any]
    ) -> None:
        """Log conflicts when vendor features contradict universal features.

        Args:
            vendor_features: Features from vendor parser
            universal_features: Features from universal parser
        """
        # Check for conflicts in top-level fields (excluding vendor_specific)
        for key, vendor_value in vendor_features.items():
            if key == "vendor_specific":
                continue

            # Check if this is a data field (not a confidence field)
            if key.endswith("_confidence"):
                continue

            # Check if universal parser also extracted this field
            if key in universal_features:
                universal_value = universal_features[key]

                # Compare values (handle different types gracefully)
                if vendor_value != universal_value:
                    logger.warning(
                        f"Conflict detected for '{key}': "
                        f"universal={universal_value}, vendor={vendor_value}. "
                        f"Preferring universal value."
                    )
