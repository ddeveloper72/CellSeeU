"""
Mobile Carrier Lookup Service

Maps MCC-MNC codes to carrier names worldwide.
Uses publicly available operator code databases.
"""

from typing import Optional, Dict, Tuple


# Carrier database: (MCC, MNC) -> Carrier Name
# Source: Public ITU-T E.212 database and OpenCellID
CARRIER_DATABASE: Dict[Tuple[int, int], str] = {
    # United States (MCC 310-316)
    (310, 260): "T-Mobile USA",
    (310, 120): "Sprint (T-Mobile)",
    (310, 410): "AT&T",
    (310, 150): "AT&T",
    (310, 70): "AT&T",
    (311, 480): "Verizon",
    (310, 4): "Verizon",
    (310, 12): "Verizon",
    (310, 590): "Verizon",
    (310, 890): "Verizon",
    (311, 270): "Verizon",
    (312, 530): "Sprint (T-Mobile)",
    (316, 10): "Sprint (T-Mobile)",
    
    # United Kingdom (MCC 234)
    (234, 10): "O2 UK",
    (234, 15): "Vodafone UK",
    (234, 20): "Three UK",
    (234, 30): "EE",
    (234, 33): "EE",
    (234, 50): "Three UK",
    
    # Ireland (MCC 272)
    (272, 1): "Vodafone Ireland",
    (272, 2): "Three Ireland",
    (272, 3): "Eir Mobile",
    (272, 5): "Three Ireland",
    
    # Canada (MCC 302)
    (302, 220): "Telus",
    (302, 610): "Bell Canada",
    (302, 720): "Rogers Wireless",
    
    # Australia (MCC 505)
    (505, 1): "Telstra",
    (505, 2): "Optus",
    (505, 3): "Vodafone Australia",
    (505, 6): "Three Australia",
    
    # Germany (MCC 262)
    (262, 1): "Telekom Deutschland",
    (262, 2): "Vodafone Germany",
    (262, 3): "O2 Germany",
    (262, 7): "O2 Germany",
    
    # France (MCC 208)
    (208, 1): "Orange France",
    (208, 10): "SFR",
    (208, 20): "Bouygues Telecom",
    
    # Spain (MCC 214)
    (214, 1): "Vodafone Spain",
    (214, 3): "Orange Spain",
    (214, 7): "Movistar",
    
    # Italy (MCC 222)
    (222, 1): "TIM Italy",
    (222, 10): "Vodafone Italy",
    (222, 88): "Wind Tre",
    
    # Japan (MCC 440)
    (440, 10): "NTT DoCoMo",
    (440, 20): "SoftBank",
    (440, 50): "KDDI",
    
    # South Korea (MCC 450)
    (450, 5): "SK Telecom",
    (450, 6): "LG U+",
    (450, 8): "KT",
    
    # China (MCC 460)
    (460, 0): "China Mobile",
    (460, 1): "China Unicom",
    (460, 11): "China Telecom",
    
    # India (MCC 404-405)
    (404, 10): "Airtel India",
    (404, 40): "Vodafone Idea",
    (404, 45): "Airtel India",
    (404, 90): "Airtel India",
    (405, 51): "Airtel India",
    (405, 52): "Airtel India",
    
    # Brazil (MCC 724)
    (724, 5): "Claro Brazil",
    (724, 10): "Vivo",
    (724, 11): "Vivo",
    (724, 31): "TIM Brazil",
    
    # Satellite Networks (MCC 901)
    (901, 11): "Inmarsat",
    (901, 12): "Maritime Communications Partner AS",
    (901, 13): "BebbiCell AG (Globalstar)",
    (901, 14): "AeroMobile",
    (901, 15): "OnAir",
    (901, 16): "Cisco",
    (901, 17): "Navitas",
    (901, 18): "Cellular @Sea",
    (901, 19): "Vodafone Malta Maritime",
    (901, 88): "Starlink (SpaceX)",  # Future NTN allocation
    (901, 99): "OneWeb",  # Future NTN allocation
}


def get_carrier_name(mcc: int, mnc: int) -> str:
    """
    Get carrier name from MCC and MNC codes.
    
    Looks up the carrier name in the public ITU-T E.212 database.
    This is publicly available information and not considered private.
    
    Args:
        mcc: Mobile Country Code (e.g., 310 for USA)
        mnc: Mobile Network Code (e.g., 260 for T-Mobile)
    
    Returns:
        Carrier name if found, otherwise formatted MCC-MNC string
        
    Example:
        >>> get_carrier_name(310, 260)
        'T-Mobile USA'
        >>> get_carrier_name(901, 88)
        'Starlink (SpaceX)'
        >>> get_carrier_name(999, 999)
        'Unknown Carrier (999-999)'
    
    Privacy Note:
        MCC-MNC codes are public standards and do not reveal
        personal information. They only identify the network operator.
    """
    carrier = CARRIER_DATABASE.get((mcc, mnc))
    
    if carrier:
        return carrier
    
    # Try to identify country at least
    country = get_country_from_mcc(mcc)
    if country:
        return f"Unknown Carrier in {country} ({mcc}-{mnc:03d})"
    
    return f"Unknown Carrier ({mcc}-{mnc:03d})"


def get_country_from_mcc(mcc: int) -> Optional[str]:
    """
    Get country name from Mobile Country Code.
    
    Args:
        mcc: Mobile Country Code
    
    Returns:
        Country name if known, None otherwise
    """
    # MCC ranges to countries (partial list)
    mcc_countries = {
        range(310, 317): "United States",
        range(302, 304): "Canada",
        range(234, 235): "United Kingdom",
        range(272, 273): "Ireland",
        range(208, 209): "France",
        range(214, 215): "Spain",
        range(222, 223): "Italy",
        range(262, 263): "Germany",
        range(240, 241): "Sweden",
        range(242, 243): "Norway",
        range(244, 245): "Finland",
        range(228, 229): "Switzerland",
        range(232, 233): "Austria",
        range(204, 205): "Netherlands",
        range(206, 207): "Belgium",
        range(238, 239): "Denmark",
        range(505, 507): "Australia",
        range(440, 442): "Japan",
        range(450, 451): "South Korea",
        range(460, 461): "China",
        range(404, 407): "India",
        range(724, 725): "Brazil",
        range(334, 335): "Mexico",
        range(730, 731): "Chile",
        range(732, 733): "Colombia",
        range(716, 717): "Peru",
        range(710, 711): "Nicaragua",
        range(722, 723): "Argentina",
        range(330, 331): "Puerto Rico",
        range(901, 902): "International/Satellite",
    }
    
    for mcc_range, country in mcc_countries.items():
        if mcc in mcc_range:
            return country
    
    return None


def add_carrier_mapping(mcc: int, mnc: int, carrier_name: str) -> None:
    """
    Add a custom carrier mapping to the database.
    
    Useful for adding new carriers or updating existing ones
    without modifying the source code.
    
    Args:
        mcc: Mobile Country Code
        mnc: Mobile Network Code
        carrier_name: Full carrier name
    
    Example:
        >>> add_carrier_mapping(310, 999, "New Carrier USA")
    """
    CARRIER_DATABASE[(mcc, mnc)] = carrier_name


def get_all_carriers_for_country(country_name: str) -> Dict[Tuple[int, int], str]:
    """
    Get all carriers for a specific country.
    
    Args:
        country_name: Country name to search for
    
    Returns:
        Dictionary mapping (MCC, MNC) to carrier names
        
    Example:
        >>> carriers = get_all_carriers_for_country("United States")
        >>> len(carriers) > 0
        True
    """
    # Get all MCCs for this country
    country_carriers = {}
    
    for (mcc, mnc), carrier in CARRIER_DATABASE.items():
        country = get_country_from_mcc(mcc)
        if country and country.lower() == country_name.lower():
            country_carriers[(mcc, mnc)] = carrier
    
    return country_carriers


# Public data source attribution
# Based on ITU-T Recommendation E.212 (publicly available)
# and OpenCellID community database (open source)
__data_source__ = "ITU-T E.212 & OpenCellID"
__data_license__ = "Public Domain / Creative Commons"
