"""Quectel-specific AT command parser.

Extracts Quectel-specific features like LTE category, automotive V2X, and Wi-Fi combo status.
"""

import re
import logging
from typing import Dict, Any
from src.parsers.base_parser import BaseVendorParser
from src.core.command_response import CommandResponse

logger = logging.getLogger(__name__)


class QuectelParser(BaseVendorParser):
    """Parser for Quectel-specific AT commands."""

    def __init__(self):
        """Initialize parser with pre-compiled regex patterns."""
        self.lte_cat_patterns = [
            re.compile(r'Cat[-\s]*([0-9]+)', re.IGNORECASE),
            re.compile(r'Category\s+([0-9]+)', re.IGNORECASE),
            re.compile(r'LTE\s+Cat[.\s]*([0-9]+)', re.IGNORECASE),
        ]

        self.ims_patterns = [
            re.compile(r'\+QCFG:\s*"ims",\s*(\d+)', re.IGNORECASE),
            re.compile(r'IMS.*enabled', re.IGNORECASE),
        ]

        self.firmware_pattern = re.compile(r'([A-Z0-9_]+\.[A-Z0-9_\.]+)', re.IGNORECASE)

    def parse_vendor_features(
        self,
        responses: Dict[str, CommandResponse],
        plugin: Any,
    ) -> Dict[str, Any]:
        """Extract Quectel-specific features.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects
            plugin: Plugin instance with metadata

        Returns:
            Dictionary with standard field enhancements and vendor_specific dict
        """
        result: Dict[str, Any] = {"vendor_specific": {}}

        try:
            # Extract LTE category from AT+QENG="servingcell"
            if 'AT+QENG="servingcell"' in responses:
                lte_cat = self._parse_lte_category(responses['AT+QENG="servingcell"'])
                if lte_cat:
                    result["lte_category"] = lte_cat
                    result["lte_category_confidence"] = 1.0
                    logger.debug(f"Extracted LTE category: {lte_cat}")

            # Extract IMS/VoLTE status from AT+QCFG="ims"
            if 'AT+QCFG="ims"' in responses:
                ims_enabled = self._parse_ims_status(responses['AT+QCFG="ims"'])
                if ims_enabled:
                    result["volte_supported"] = True
                    result["volte_supported_confidence"] = 1.0
                    logger.debug("VoLTE/IMS enabled detected")

            # Extract detailed firmware from AT+QGMR
            if "AT+QGMR" in responses:
                firmware = self._parse_firmware(responses["AT+QGMR"])
                if firmware:
                    result["revision"] = firmware
                    result["revision_confidence"] = 1.0
                    result["vendor_specific"]["detailed_firmware"] = firmware
                    logger.debug(f"Extracted firmware: {firmware}")

            # Extract automotive features
            if hasattr(plugin, "metadata") and hasattr(plugin.metadata, "category"):
                if plugin.metadata.category == "automotive":
                    result["vendor_specific"]["v2x_support"] = self._detect_v2x_support(responses)
                    logger.debug("Automotive category detected, checking V2X support")

            # Extract Wi-Fi combo status for RG650L
            if hasattr(plugin, "metadata") and hasattr(plugin.metadata, "model"):
                model = plugin.metadata.model.lower()
                if "rg650l" in model or "rg65" in model:
                    wifi_status = self._detect_wifi_combo(responses)
                    if wifi_status:
                        result["vendor_specific"]["wifi_combo"] = wifi_status
                        logger.debug(f"Wi-Fi combo detected: {wifi_status}")

        except Exception as e:
            logger.error(f"Error parsing Quectel features: {e}", exc_info=True)

        return result

    def _parse_lte_category(self, response: CommandResponse) -> str:
        """Extract LTE category from AT+QENG response.

        Args:
            response: CommandResponse from AT+QENG

        Returns:
            LTE category (e.g., "Cat-4", "Cat-6") or empty string
        """
        if not response.is_successful():
            return ""

        text = "\n".join(response.raw_response)

        for pattern in self.lte_cat_patterns:
            match = pattern.search(text)
            if match:
                cat_num = match.group(1)
                return f"Cat-{cat_num}"

        return ""

    def _parse_ims_status(self, response: CommandResponse) -> bool:
        """Extract IMS status from AT+QCFG="ims" response.

        Args:
            response: CommandResponse from AT+QCFG

        Returns:
            True if IMS is enabled, False otherwise
        """
        if not response.is_successful():
            return False

        text = "\n".join(response.raw_response)

        for pattern in self.ims_patterns:
            match = pattern.search(text)
            if match:
                if match.lastindex and match.group(1) == "1":
                    return True
                return True

        return False

    def _parse_firmware(self, response: CommandResponse) -> str:
        """Extract detailed firmware version from AT+QGMR.

        Args:
            response: CommandResponse from AT+QGMR

        Returns:
            Firmware version string or empty string
        """
        if not response.is_successful():
            return ""

        text = "\n".join(response.raw_response)
        match = self.firmware_pattern.search(text)

        if match:
            return match.group(1)

        return ""

    def _detect_v2x_support(self, responses: Dict[str, CommandResponse]) -> bool:
        """Detect V2X support for automotive modems.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects

        Returns:
            True if V2X features detected, False otherwise
        """
        # Check for V2X-specific commands
        v2x_commands = ["AT+QCFG=\"v2x\"", "AT+QV2X"]

        for cmd in v2x_commands:
            if cmd in responses and responses[cmd].is_successful():
                text = "\n".join(responses[cmd].raw_response)
                if "v2x" in text.lower() or "c-v2x" in text.lower():
                    return True

        return False

    def _detect_wifi_combo(self, responses: Dict[str, CommandResponse]) -> str:
        """Detect Wi-Fi combo modem capabilities.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects

        Returns:
            Wi-Fi version string (e.g., "Wi-Fi 7") or empty string
        """
        # Check for Wi-Fi status commands
        wifi_commands = ["AT+QCFG=\"wifi\"", "AT+QWIFI"]

        for cmd in wifi_commands:
            if cmd in responses and responses[cmd].is_successful():
                text = "\n".join(responses[cmd].raw_response)
                if "wi-fi 7" in text.lower() or "802.11be" in text.lower():
                    return "Wi-Fi 7"
                elif "wi-fi 6" in text.lower() or "802.11ax" in text.lower():
                    return "Wi-Fi 6"

        return ""
