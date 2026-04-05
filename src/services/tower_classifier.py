"""
Cell Tower Classification Service

Distinguishes between terrestrial cell towers and non-terrestrial (satellite)
networks using multiple detection methods:

1. Android 13+ NTN capability flag (most reliable)
2. Known satellite operator PLMN codes (fallback)
3. Network type indicators (5G NR-NTN)

This is a core feature of CellSeeU - helping users identify which towers
are traditional ground-based vs satellite-based networks.
"""

from typing import Dict, Any, Literal

# Type alias for clarity
TowerType = Literal["TERRESTRIAL", "NON_TERRESTRIAL_SATELLITE"]
NetworkType = Literal["GSM", "UMTS", "LTE", "5G_NR", "5G_NR_NTN", "UNKNOWN"]


# Known satellite operator PLMN codes (MCC, MNC)
# This list will grow as more satellite networks launch
# Source: ITU-T E.212, 3GPP specifications, industry announcements
SATELLITE_PLMN_CODES = {
    (901, 14),   # Example: International mobile satellite system
    (901, 88),   # Example: Satellite test network
    (901, 18),   # Example: Maritime satellite
    # Add more as satellite cellular networks are deployed
    # Starlink, AST SpaceMobile, Lynk Global will get assigned PLMNs
}


def classify_tower_type(cell_data: Dict[str, Any]) -> TowerType:
    """
    Classify a cell tower as terrestrial or non-terrestrial (satellite).
    
    Uses a hierarchical detection approach:
    1. Check for explicit NTN capability flag (Android 13+)
    2. Check if PLMN matches known satellite operator
    3. Check radio type for NTN indicators
    4. Default to TERRESTRIAL if no satellite indicators found
    
    Args:
        cell_data: Dictionary containing cell tower information:
            - radio: Network technology (LTE, 5G_NR, etc.)
            - mcc: Mobile Country Code
            - mnc: Mobile Network Code
            - has_ntn_capability: Optional boolean flag for NTN
    
    Returns:
        "TERRESTRIAL" for ground-based towers
        "NON_TERRESTRIAL_SATELLITE" for satellite networks
    
    Raises:
        TypeError: If cell_data is None (defensive programming)
    
    Example:
        >>> cell_data = {'radio': '5G_NR', 'mcc': 310, 'mnc': 260, 'has_ntn_capability': False}
        >>> classify_tower_type(cell_data)
        'TERRESTRIAL'
    """
    if cell_data is None:
        raise TypeError("cell_data cannot be None")
    
    # Method 1: Direct NTN capability flag (most reliable, Android 13+)
    if is_5g_ntn_capable(cell_data):
        return "NON_TERRESTRIAL_SATELLITE"
    
    # Method 2: Check for known satellite PLMN codes
    mcc = cell_data.get('mcc')
    mnc = cell_data.get('mnc')
    
    if mcc is not None and mnc is not None:
        if is_satellite_plmn(mcc, mnc):
            return "NON_TERRESTRIAL_SATELLITE"
    
    # Method 3: Check radio type for explicit NTN designation
    radio = cell_data.get('radio', '')
    if radio and 'NTN' in radio.upper():
        return "NON_TERRESTRIAL_SATELLITE"
    
    # Default to terrestrial if no satellite indicators found
    return "TERRESTRIAL"


def is_satellite_plmn(mcc: int, mnc: int) -> bool:
    """
    Check if MCC/MNC combination belongs to a known satellite operator.
    
    Satellite networks use specific PLMN codes allocated by ITU.
    This function maintains a database of known satellite PLMNs
    for identification purposes.
    
    Args:
        mcc: Mobile Country Code (3 digits, e.g., 310 for USA)
        mnc: Mobile Network Code (2-3 digits, e.g., 260 for T-Mobile)
    
    Returns:
        True if the PLMN belongs to a satellite operator, False otherwise
    
    Note:
        This list will need updates as new satellite networks launch.
        Consider moving to external configuration file for easy updates.
    
    Example:
        >>> is_satellite_plmn(310, 260)  # T-Mobile USA
        False
        >>> is_satellite_plmn(901, 88)   # Satellite test network
        True
    """
    # Input validation: reasonable ranges for MCC/MNC
    # MCC: 200-799 (assigned codes), 900-999 (international)
    # MNC: 0-999
    if not (200 <= mcc <= 999) or not (0 <= mnc <= 999):
        return False
    
    return (mcc, mnc) in SATELLITE_PLMN_CODES


def is_5g_ntn_capable(cell_data: Dict[str, Any]) -> bool:
    """
    Check if cell tower has 5G NR Non-Terrestrial Network capability.
    
    Android 13 (API 33+) provides isNonTerrestrialNetwork() method
    that directly indicates if a cell is satellite-based.
    
    This is the most reliable detection method when available,
    but only works on newer Android versions.
    
    Args:
        cell_data: Dictionary containing cell info, may have 'has_ntn_capability' key
    
    Returns:
        True if NTN capability flag is present and True, False otherwise
    
    Example:
        >>> cell_data = {'has_ntn_capability': True}
        >>> is_5g_ntn_capable(cell_data)
        True
    """
    return cell_data.get('has_ntn_capability', False) is True


def get_network_type_from_radio(radio: str) -> NetworkType:
    """
    Convert radio technology string to standardized network type.
    
    Different Android versions and manufacturers may report radio
    types with slight variations. This normalizes them to consistent
    values used throughout the app.
    
    Args:
        radio: Radio technology string from Android API
            (e.g., "LTE", "NR", "5G_NR_NTN", "WCDMA", etc.)
    
    Returns:
        Normalized network type: GSM, UMTS, LTE, 5G_NR, 5G_NR_NTN, or UNKNOWN
    
    Example:
        >>> get_network_type_from_radio("NR")
        '5G_NR'
        >>> get_network_type_from_radio("WCDMA")
        'UMTS'
    """
    if radio is None:
        return "UNKNOWN"
    
    # Normalize to uppercase for comparison
    radio_upper = radio.upper()
    
    # Direct mappings
    if radio_upper == "GSM":
        return "GSM"
    elif radio_upper in ("UMTS", "WCDMA"):
        return "UMTS"
    elif radio_upper == "LTE":
        return "LTE"
    elif radio_upper in ("5G_NR", "NR"):
        return "5G_NR"
    elif radio_upper == "5G_NR_NTN":
        return "5G_NR_NTN"
    else:
        # Unknown radio type - return as-is for debugging
        # Future radio types will fall here until we add them
        return "UNKNOWN"


def add_satellite_plmn(mcc: int, mnc: int) -> None:
    """
    Add a new satellite PLMN code to the database.
    
    As new satellite cellular networks launch, they'll get assigned
    PLMN codes. This function allows updating the database at runtime.
    
    Args:
        mcc: Mobile Country Code
        mnc: Mobile Network Code
    
    Note:
        In production, consider persisting this to a database or
        configuration file rather than in-memory set.
    
    Example:
        >>> add_satellite_plmn(999, 99)  # New satellite network
    """
    SATELLITE_PLMN_CODES.add((mcc, mnc))


def get_satellite_plmn_list() -> list:
    """
    Get list of all known satellite PLMN codes.
    
    Useful for debugging, documentation, or displaying in UI.
    
    Returns:
        List of (MCC, MNC) tuples for known satellite operators
    
    Example:
        >>> plmns = get_satellite_plmn_list()
        >>> print(f"Known satellite networks: {len(plmns)}")
    """
    return sorted(list(SATELLITE_PLMN_CODES))
