"""Universal parser for standard 3GPP AT commands.

This module extracts modem features from standard AT commands using regex patterns
with confidence scoring and graceful error handling.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from src.core.command_response import CommandResponse

logger = logging.getLogger(__name__)


class UniversalParser:
    """Parser for standard 3GPP AT commands with confidence scoring.

    Confidence Levels:
    - 1.0: Exact match with high certainty
    - 0.7: Inferred from context or partial match
    - 0.3: Guessed or low certainty
    - 0.0: Unknown or parsing failed
    """

    def __init__(self):
        """Initialize parser with pre-compiled regex patterns."""
        # Basic Info patterns
        self.manufacturer_patterns = [
            re.compile(r'^([A-Za-z0-9]+)\s*$', re.MULTILINE),  # Simple manufacturer name
            re.compile(r'Manufacturer:\s*([A-Za-z0-9]+)', re.IGNORECASE),
        ]

        self.model_patterns = [
            re.compile(r'^([A-Za-z0-9_\-]+)\s*$', re.MULTILINE),  # Simple model
            re.compile(r'Model:\s*([A-Za-z0-9_\-]+)', re.IGNORECASE),
        ]

        self.revision_patterns = [
            re.compile(r'^([\w\.\-]+)\s*$', re.MULTILINE),  # Version string
            re.compile(r'Revision:\s*([\w\.\-]+)', re.IGNORECASE),
        ]

        self.imei_patterns = [
            re.compile(r'\b(\d{15})\b'),  # Exactly 15 digits
            re.compile(r'IMEI:\s*(\d{14,16})'),  # IMEI with label
        ]

        # Network patterns
        self.band_patterns = [
            re.compile(r'Band\s+(\d+)', re.IGNORECASE),
            re.compile(r'\bB(\d+)\b'),
            re.compile(r'(\d{3,4})\s*MHz'),  # Frequency to band
        ]

        self.lte_cat_patterns = [
            re.compile(r'Cat[-\s]*(\d+)', re.IGNORECASE),
            re.compile(r'Category\s+(\d+)', re.IGNORECASE),
        ]

        # Voice patterns
        self.volte_patterns = [
            re.compile(r'VoLTE.*enabled', re.IGNORECASE),
            re.compile(r'IMS.*registered', re.IGNORECASE),
        ]

        # GNSS patterns
        self.gnss_patterns = [
            re.compile(r'GPS.*supported', re.IGNORECASE),
            re.compile(r'GNSS.*enabled', re.IGNORECASE),
        ]

        # Power patterns
        self.psm_patterns = [
            re.compile(r'PSM.*enabled', re.IGNORECASE),
            re.compile(r'\+CPSMS:\s*1', re.IGNORECASE),
        ]

        # SIM patterns
        self.sim_ready_patterns = [
            re.compile(r'\+CPIN:\s*READY', re.IGNORECASE),
            re.compile(r'SIM.*ready', re.IGNORECASE),
        ]

        self.iccid_patterns = [
            re.compile(r'\+CCID:\s*(\d{19,20})'),
            re.compile(r'ICCID:\s*(\d{19,20})'),
        ]

    def parse_basic_info(self, responses: Dict[str, CommandResponse]) -> Dict[str, Any]:
        """Extract basic modem information.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects

        Returns:
            Dictionary with basic info fields and confidence scores
        """
        result = {}

        # Parse manufacturer (AT+CGMI)
        if "AT+CGMI" in responses:
            manufacturer, confidence = self._parse_manufacturer(responses["AT+CGMI"])
            result["manufacturer"] = manufacturer
            result["manufacturer_confidence"] = confidence

        # Parse model (AT+CGMM)
        if "AT+CGMM" in responses:
            model, confidence = self._parse_model(responses["AT+CGMM"])
            result["model"] = model
            result["model_confidence"] = confidence

        # Parse revision (AT+CGMR)
        if "AT+CGMR" in responses:
            revision, confidence = self._parse_revision(responses["AT+CGMR"])
            result["revision"] = revision
            result["revision_confidence"] = confidence

        # Parse IMEI (AT+CGSN)
        if "AT+CGSN" in responses:
            imei, confidence = self._parse_imei(responses["AT+CGSN"])
            result["imei"] = imei
            result["imei_confidence"] = confidence

        return result

    def parse_network_capabilities(self, responses: Dict[str, CommandResponse]) -> Dict[str, Any]:
        """Extract network capabilities.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects

        Returns:
            Dictionary with network capability fields and confidence scores
        """
        result = {}

        # Parse supported bands
        bands = []
        bands_confidence = 0.0

        # Check AT+QNWINFO, AT+CPAS, or other band query commands
        for cmd in ["AT+QNWINFO", "AT+COPS?", "AT+CGDCONT?"]:
            if cmd in responses and responses[cmd].is_successful():
                extracted_bands = self._extract_bands_from_text(
                    "\n".join(responses[cmd].raw_response)
                )
                if extracted_bands:
                    bands.extend(extracted_bands)
                    bands_confidence = 0.7

        if bands:
            result["lte_bands"] = sorted(set(bands))
            result["lte_bands_confidence"] = bands_confidence

        return result

    def parse_voice_features(self, responses: Dict[str, CommandResponse]) -> Dict[str, Any]:
        """Extract voice capabilities.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects

        Returns:
            Dictionary with voice feature fields and confidence scores
        """
        result = {}

        # Check for VoLTE support
        for cmd in ["AT+CIREG?", "AT+COPS?"]:
            if cmd in responses and responses[cmd].is_successful():
                text = "\n".join(responses[cmd].raw_response)
                for pattern in self.volte_patterns:
                    if pattern.search(text):
                        result["volte_supported"] = True
                        result["volte_supported_confidence"] = 0.7
                        break

        return result

    def parse_gnss_info(self, responses: Dict[str, CommandResponse]) -> Dict[str, Any]:
        """Extract GNSS capabilities.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects

        Returns:
            Dictionary with GNSS info fields and confidence scores
        """
        result = {}

        # Check for GNSS support
        for cmd in ["AT+CGNSPWR?", "AT+CGPS?"]:
            if cmd in responses and responses[cmd].is_successful():
                text = "\n".join(responses[cmd].raw_response)
                for pattern in self.gnss_patterns:
                    if pattern.search(text):
                        result["gnss_supported"] = True
                        result["gnss_supported_confidence"] = 0.7
                        break

        return result

    def parse_power_management(self, responses: Dict[str, CommandResponse]) -> Dict[str, Any]:
        """Extract power management features.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects

        Returns:
            Dictionary with power management fields and confidence scores
        """
        result = {}

        # Check for PSM support
        if "AT+CPSMS?" in responses and responses["AT+CPSMS?"].is_successful():
            text = "\n".join(responses["AT+CPSMS?"].raw_response)
            for pattern in self.psm_patterns:
                if pattern.search(text):
                    result["psm_supported"] = True
                    result["psm_supported_confidence"] = 0.7
                    break

        return result

    def parse_sim_info(self, responses: Dict[str, CommandResponse]) -> Dict[str, Any]:
        """Extract SIM information.

        Args:
            responses: Dictionary of AT commands to CommandResponse objects

        Returns:
            Dictionary with SIM info fields and confidence scores
        """
        result = {}

        # Check SIM status (AT+CPIN?)
        if "AT+CPIN?" in responses:
            sim_status, confidence = self._parse_sim_status(responses["AT+CPIN?"])
            result["sim_status"] = sim_status
            result["sim_status_confidence"] = confidence

        # Parse ICCID (AT+CCID or AT+QCCID)
        for cmd in ["AT+CCID", "AT+QCCID"]:
            if cmd in responses and responses[cmd].is_successful():
                iccid, confidence = self._parse_iccid(responses[cmd])
                if confidence > 0:
                    result["iccid"] = iccid
                    result["iccid_confidence"] = confidence
                    break

        return result

    def _parse_manufacturer(self, response: CommandResponse) -> Tuple[str, float]:
        """Parse manufacturer from AT+CGMI response.

        Args:
            response: CommandResponse from AT+CGMI

        Returns:
            Tuple of (manufacturer, confidence)
        """
        if not response.is_successful():
            return "Unknown", 0.0

        text = "\n".join(response.raw_response)

        for pattern in self.manufacturer_patterns:
            match = pattern.search(text)
            if match:
                manufacturer = match.group(1).strip()
                if manufacturer:
                    return manufacturer, 1.0

        logger.warning("Could not parse manufacturer from AT+CGMI response")
        return "Unknown", 0.0

    def _parse_model(self, response: CommandResponse) -> Tuple[str, float]:
        """Parse model from AT+CGMM response.

        Args:
            response: CommandResponse from AT+CGMM

        Returns:
            Tuple of (model, confidence)
        """
        if not response.is_successful():
            return "Unknown", 0.0

        text = "\n".join(response.raw_response)

        for pattern in self.model_patterns:
            match = pattern.search(text)
            if match:
                model = match.group(1).strip()
                if model:
                    return model, 1.0

        logger.warning("Could not parse model from AT+CGMM response")
        return "Unknown", 0.0

    def _parse_revision(self, response: CommandResponse) -> Tuple[str, float]:
        """Parse revision from AT+CGMR response.

        Args:
            response: CommandResponse from AT+CGMR

        Returns:
            Tuple of (revision, confidence)
        """
        if not response.is_successful():
            return "Unknown", 0.0

        text = "\n".join(response.raw_response)

        for pattern in self.revision_patterns:
            match = pattern.search(text)
            if match:
                revision = match.group(1).strip()
                if revision:
                    return revision, 1.0

        logger.warning("Could not parse revision from AT+CGMR response")
        return "Unknown", 0.0

    def _parse_imei(self, response: CommandResponse) -> Tuple[str, float]:
        """Parse and validate IMEI from AT+CGSN response.

        Args:
            response: CommandResponse from AT+CGSN

        Returns:
            Tuple of (imei, confidence)
        """
        if not response.is_successful():
            return "Unknown", 0.0

        text = "\n".join(response.raw_response)

        for pattern in self.imei_patterns:
            match = pattern.search(text)
            if match:
                imei = match.group(1).strip()
                # Validate IMEI is exactly 15 digits
                if len(imei) == 15 and imei.isdigit():
                    return imei, 1.0
                else:
                    logger.warning(f"Invalid IMEI format: {imei}")
                    return imei, 0.5

        logger.warning("Could not parse IMEI from AT+CGSN response")
        return "Unknown", 0.0

    def _parse_sim_status(self, response: CommandResponse) -> Tuple[str, float]:
        """Parse SIM status from AT+CPIN? response.

        Args:
            response: CommandResponse from AT+CPIN?

        Returns:
            Tuple of (sim_status, confidence)
        """
        if not response.is_successful():
            return "unknown", 0.0

        text = "\n".join(response.raw_response)

        for pattern in self.sim_ready_patterns:
            if pattern.search(text):
                return "ready", 1.0

        # Check for PIN required
        if "SIM PIN" in text or "CPIN: SIM PIN" in text:
            return "pin_required", 1.0

        # Check for not inserted
        if "not inserted" in text.lower():
            return "not_inserted", 1.0

        logger.warning("Could not determine SIM status from AT+CPIN? response")
        return "unknown", 0.0

    def _parse_iccid(self, response: CommandResponse) -> Tuple[str, float]:
        """Parse ICCID from response.

        Args:
            response: CommandResponse from ICCID query

        Returns:
            Tuple of (iccid, confidence)
        """
        if not response.is_successful():
            return "Unknown", 0.0

        text = "\n".join(response.raw_response)

        for pattern in self.iccid_patterns:
            match = pattern.search(text)
            if match:
                iccid = match.group(1).strip()
                # Validate ICCID length (19-20 digits)
                if 19 <= len(iccid) <= 20 and iccid.isdigit():
                    return iccid, 1.0

        logger.warning("Could not parse ICCID from response")
        return "Unknown", 0.0

    def _extract_bands_from_text(self, text: str) -> List[int]:
        """Extract LTE band numbers from text.

        Supports various formats:
        - "Band 3"
        - "B3"
        - "1800 MHz"

        Args:
            text: Text to search for band information

        Returns:
            List of band numbers (1-300)
        """
        bands = []

        for pattern in self.band_patterns:
            matches = pattern.findall(text)
            for match in matches:
                try:
                    band = int(match)
                    # Validate band number range
                    if 1 <= band <= 300:
                        bands.append(band)
                except ValueError:
                    continue

        return bands
