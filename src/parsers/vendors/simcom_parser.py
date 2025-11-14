"""SIMCom-specific AT command parser.

Extracts SIMCom-specific features like network scanning and band preferences.
"""

import re
import logging
from typing import Dict, Any, List
from src.parsers.base_parser import BaseVendorParser
from src.core.command_response import CommandResponse

logger = logging.getLogger(__name__)


class SIMComParser(BaseVendorParser):
    """Parser for SIMCom-specific AT commands."""

    def __init__(self):
        """Initialize parser with pre-compiled regex patterns."""
        self.network_scan_pattern = re.compile(
            r'\+CNETSCAN:\s*(\d+),\s*"([^"]+)",\s*"([^"]+)",\s*(\d+),\s*(\d+)',
            re.IGNORECASE
        )
        self.band_cfg_pattern = re.compile(r'\+CBANDCFG:\s*"([^"]+)",\s*(.+)', re.IGNORECASE)
        self.sim_status_pattern = re.compile(r'\+CPIN:\s*([A-Z\s]+)', re.IGNORECASE)

    def parse_vendor_features(
        self,
        responses: Dict[str, CommandResponse],
        plugin: Any,
    ) -> Dict[str, Any]:
        """Extract SIMCom-specific features.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects
            plugin: Plugin instance with metadata

        Returns:
            Dictionary with standard field enhancements and vendor_specific dict
        """
        result: Dict[str, Any] = {"vendor_specific": {}}

        try:
            # Extract network scan details from AT+CNETSCAN
            if "AT+CNETSCAN" in responses:
                network_scan = self._parse_network_scan(responses["AT+CNETSCAN"])
                if network_scan:
                    result["vendor_specific"]["network_scan"] = network_scan
                    logger.debug(f"Extracted network scan: {len(network_scan)} networks")

            # Extract band preferences from AT+CBANDCFG
            if "AT+CBANDCFG?" in responses:
                band_config = self._parse_band_config(responses["AT+CBANDCFG?"])
                if band_config:
                    result["vendor_specific"]["band_preferences"] = band_config
                    # Update LTE bands if available
                    if "lte_bands" in band_config:
                        result["lte_bands"] = band_config["lte_bands"]
                        result["lte_bands_confidence"] = 1.0
                    logger.debug(f"Extracted band config: {band_config}")

            # Extract detailed SIM status from AT+CPIN?
            if "AT+CPIN?" in responses:
                sim_status = self._parse_sim_status_detailed(responses["AT+CPIN?"])
                if sim_status:
                    result["sim_status"] = sim_status["status"]
                    result["sim_status_confidence"] = 1.0
                    if sim_status.get("details"):
                        result["vendor_specific"]["sim_details"] = sim_status["details"]
                    logger.debug(f"Extracted SIM status: {sim_status}")

        except Exception as e:
            logger.error(f"Error parsing SIMCom features: {e}", exc_info=True)

        return result

    def _parse_network_scan(self, response: CommandResponse) -> List[Dict[str, Any]]:
        """Extract network scan details from AT+CNETSCAN response.

        Args:
            response: CommandResponse from AT+CNETSCAN

        Returns:
            List of network dictionaries with operator, band, signal strength
        """
        if not response.is_successful():
            return []

        text = "\n".join(response.raw_response)
        networks = []

        for match in self.network_scan_pattern.finditer(text):
            try:
                network = {
                    "index": int(match.group(1)),
                    "operator": match.group(2),
                    "technology": match.group(3),
                    "band": int(match.group(4)),
                    "rssi": int(match.group(5))
                }
                networks.append(network)
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse network scan entry: {e}")
                continue

        return networks

    def _parse_band_config(self, response: CommandResponse) -> Dict[str, Any]:
        """Extract band configuration from AT+CBANDCFG response.

        Args:
            response: CommandResponse from AT+CBANDCFG

        Returns:
            Dictionary with band configuration or empty dict
        """
        if not response.is_successful():
            return {}

        text = "\n".join(response.raw_response)
        config = {}

        for match in self.band_cfg_pattern.finditer(text):
            try:
                mode = match.group(1).strip()
                bands_str = match.group(2).strip()

                # Parse band list (e.g., "1,3,5,7,8,20,28")
                bands = []
                for band_str in bands_str.split(","):
                    band_str = band_str.strip().strip('"')
                    if band_str.isdigit():
                        band = int(band_str)
                        # Validate band range
                        if 1 <= band <= 300:
                            bands.append(band)

                if mode.lower() == "cat-m":
                    config["catm_bands"] = bands
                elif mode.lower() == "cat-nb":
                    config["catnb_bands"] = bands
                elif mode.lower() == "lte":
                    config["lte_bands"] = bands

            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse band config entry: {e}")
                continue

        return config

    def _parse_sim_status_detailed(self, response: CommandResponse) -> Dict[str, Any]:
        """Extract detailed SIM status from AT+CPIN? response.

        Args:
            response: CommandResponse from AT+CPIN?

        Returns:
            Dictionary with status and details, or empty dict
        """
        if not response.is_successful():
            return {}

        text = "\n".join(response.raw_response)
        match = self.sim_status_pattern.search(text)

        if match:
            status_str = match.group(1).strip()

            # Map status strings to standard status
            status_map = {
                "READY": "ready",
                "SIM PIN": "pin_required",
                "SIM PUK": "pin_required",
                "SIM PIN2": "pin_required",
                "SIM PUK2": "pin_required",
                "NOT INSERTED": "not_inserted",
                "ERROR": "error"
            }

            status = status_map.get(status_str, "unknown")

            return {
                "status": status,
                "details": status_str
            }

        return {}
