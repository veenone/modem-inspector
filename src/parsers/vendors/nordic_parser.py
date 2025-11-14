"""Nordic nRF91-specific AT command parser.

Extracts Nordic-specific IoT features like LTE-M/NB-IoT system mode, band locking,
and battery voltage monitoring.
"""

import re
import logging
from typing import Dict, Any, List
from src.parsers.base_parser import BaseVendorParser
from src.core.command_response import CommandResponse

logger = logging.getLogger(__name__)


class NordicParser(BaseVendorParser):
    """Parser for Nordic nRF91-specific AT% commands."""

    def __init__(self):
        """Initialize parser with pre-compiled regex patterns."""
        self.system_mode_patterns = [
            re.compile(r'%XSYSTEMMODE:\s*(\d+),(\d+),(\d+),(\d+)', re.IGNORECASE),
            re.compile(r'LTE-M:\s*(\d+).*NB-IoT:\s*(\d+)', re.IGNORECASE),
        ]

        self.band_lock_pattern = re.compile(r'%XBANDLOCK:\s*(\d+),"([^"]+)"', re.IGNORECASE)
        self.battery_pattern = re.compile(r'%XVBAT:\s*(\d+)', re.IGNORECASE)
        self.psm_timer_pattern = re.compile(r'%XPTW:\s*(\d+),(\d+)', re.IGNORECASE)

    def parse_vendor_features(
        self,
        responses: Dict[str, CommandResponse],
        plugin: Any,
    ) -> Dict[str, Any]:
        """Extract Nordic nRF91-specific features.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects
            plugin: Plugin instance with metadata

        Returns:
            Dictionary with standard field enhancements and vendor_specific dict
        """
        result: Dict[str, Any] = {"vendor_specific": {}}

        try:
            # Extract system mode (LTE-M/NB-IoT) from AT%XSYSTEMMODE
            if "AT%XSYSTEMMODE?" in responses:
                system_mode = self._parse_system_mode(responses["AT%XSYSTEMMODE?"])
                if system_mode:
                    result["vendor_specific"]["system_mode"] = system_mode
                    # Update supported technologies
                    techs = []
                    if "LTE-M" in system_mode:
                        techs.append("LTE-M")
                    if "NB-IoT" in system_mode:
                        techs.append("NB-IoT")
                    if techs:
                        result["supported_technologies"] = techs
                        result["supported_technologies_confidence"] = 1.0
                    logger.debug(f"Extracted system mode: {system_mode}")

            # Extract band lock configuration from AT%XBANDLOCK
            if "AT%XBANDLOCK?" in responses:
                band_config = self._parse_band_lock(responses["AT%XBANDLOCK?"])
                if band_config:
                    result["vendor_specific"]["band_lock"] = band_config
                    logger.debug(f"Extracted band lock: {band_config}")

            # Extract battery voltage from AT%XVBAT
            if "AT%XVBAT" in responses or "AT%XVBAT?" in responses:
                cmd = "AT%XVBAT" if "AT%XVBAT" in responses else "AT%XVBAT?"
                battery_mv = self._parse_battery_voltage(responses[cmd])
                if battery_mv:
                    result["battery_voltage"] = battery_mv
                    result["battery_voltage_confidence"] = 1.0
                    result["vendor_specific"]["battery_voltage_mv"] = battery_mv
                    logger.debug(f"Extracted battery voltage: {battery_mv} mV")

            # Extract PSM timers from AT%XPTW
            if "AT%XPTW?" in responses:
                psm_timers = self._parse_psm_timers(responses["AT%XPTW?"])
                if psm_timers:
                    result["psm_supported"] = True
                    result["psm_supported_confidence"] = 1.0
                    result["vendor_specific"]["psm_timers"] = psm_timers
                    logger.debug(f"Extracted PSM timers: {psm_timers}")

        except Exception as e:
            logger.error(f"Error parsing Nordic features: {e}", exc_info=True)

        return result

    def _parse_system_mode(self, response: CommandResponse) -> str:
        """Extract system mode from AT%XSYSTEMMODE response.

        Args:
            response: CommandResponse from AT%XSYSTEMMODE

        Returns:
            System mode string (e.g., "LTE-M", "NB-IoT", "LTE-M+NB-IoT") or empty string
        """
        if not response.is_successful():
            return ""

        text = "\n".join(response.raw_response)

        # Try first pattern: %XSYSTEMMODE: ltem_mode,nbiot_mode,gps_mode,lte_mode
        match = self.system_mode_patterns[0].search(text)
        if match:
            ltem_enabled = match.group(1) == "1"
            nbiot_enabled = match.group(2) == "1"

            modes = []
            if ltem_enabled:
                modes.append("LTE-M")
            if nbiot_enabled:
                modes.append("NB-IoT")

            return "+".join(modes) if modes else ""

        # Try second pattern: LTE-M: 1, NB-IoT: 1
        match = self.system_mode_patterns[1].search(text)
        if match:
            ltem_enabled = match.group(1) == "1"
            nbiot_enabled = match.group(2) == "1"

            modes = []
            if ltem_enabled:
                modes.append("LTE-M")
            if nbiot_enabled:
                modes.append("NB-IoT")

            return "+".join(modes) if modes else ""

        return ""

    def _parse_band_lock(self, response: CommandResponse) -> Dict[str, Any]:
        """Extract band lock configuration from AT%XBANDLOCK response.

        Args:
            response: CommandResponse from AT%XBANDLOCK

        Returns:
            Dictionary with band lock configuration or empty dict
        """
        if not response.is_successful():
            return {}

        text = "\n".join(response.raw_response)
        match = self.band_lock_pattern.search(text)

        if match:
            mode = match.group(1)
            bands_str = match.group(2)

            # Parse band string (e.g., "0001000000001000") to band numbers
            bands = []
            for i, bit in enumerate(bands_str):
                if bit == "1":
                    bands.append(i + 1)

            return {
                "mode": "enabled" if mode == "1" else "disabled",
                "bands": bands
            }

        return {}

    def _parse_battery_voltage(self, response: CommandResponse) -> int:
        """Extract battery voltage from AT%XVBAT response.

        Args:
            response: CommandResponse from AT%XVBAT

        Returns:
            Battery voltage in millivolts (mV) or 0 if not found
        """
        if not response.is_successful():
            return 0

        text = "\n".join(response.raw_response)
        match = self.battery_pattern.search(text)

        if match:
            try:
                voltage_mv = int(match.group(1))
                # Validate reasonable battery voltage range (1800-4500 mV)
                if 1800 <= voltage_mv <= 4500:
                    return voltage_mv
            except ValueError:
                pass

        return 0

    def _parse_psm_timers(self, response: CommandResponse) -> Dict[str, int]:
        """Extract PSM timers from AT%XPTW response.

        Args:
            response: CommandResponse from AT%XPTW

        Returns:
            Dictionary with PSM timer values or empty dict
        """
        if not response.is_successful():
            return {}

        text = "\n".join(response.raw_response)
        match = self.psm_timer_pattern.search(text)

        if match:
            try:
                tau_timer = int(match.group(1))
                active_timer = int(match.group(2))

                return {
                    "tau_timer": tau_timer,
                    "active_timer": active_timer
                }
            except ValueError:
                pass

        return {}
