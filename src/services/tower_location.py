"""
Tower Location Lookup Service

Fetches real tower coordinates from OpenCelliD database.
Falls back to signal-based estimation if lookup fails.
"""

import requests
import logging
from typing import Optional, Dict, Tuple
import time
import os

logger = logging.getLogger(__name__)

# OpenCelliD API (free tier)
# Register at: https://opencellid.org/
OPENCELLID_API_URL = "https://opencellid.org/cell/get"
OPENCELLID_TOKEN = os.getenv('OPENCELLID_API_KEY')  # Load from .env file

# Cache to avoid repeated API calls for same tower
_tower_cache = {}
_cache_ttl = 3600  # 1 hour

class TowerLocationService:
    """Service for looking up cell tower GPS coordinates"""
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize tower location service.
        
        Args:
            api_token: OpenCelliD API token (optional, for real lookups)
        """
        self.api_token = api_token or OPENCELLID_TOKEN
        
    def lookup_tower_location(self, mcc: int, mnc: int, lac: int, cell_id: int) -> Optional[Tuple[float, float, int]]:
        """
        Look up tower location from OpenCelliD database.
        
        Args:
            mcc: Mobile Country Code (272 for Ireland)
            mnc: Mobile Network Code (1=Vodafone, 2=Three, 3=Eir)
            lac: Location Area Code (TAC for LTE)
            cell_id: Cell ID (unique tower identifier)
        
        Returns:
            Tuple of (latitude, longitude, range_meters) or None if not found
        """
        # Check cache first
        cache_key = f"{mcc}-{mnc}-{lac}-{cell_id}"
        if cache_key in _tower_cache:
            cached_time, cached_data = _tower_cache[cache_key]
            if time.time() - cached_time < _cache_ttl:
                logger.debug(f"Tower {cache_key} found in cache")
                return cached_data
        
        # If no API token, return None to use fallback estimation
        if not self.api_token:
            logger.warning("No OpenCelliD API token configured - using signal-based estimation")
            return None
        
        try:
            params = {
                'token': self.api_token,
                'mcc': mcc,
                'mnc': mnc,
                'lac': lac,
                'cellid': cell_id,
                'format': 'json'
            }
            
            logger.info(f"Looking up tower: MCC={mcc}, MNC={mnc}, LAC={lac}, CID={cell_id}")
            response = requests.get(OPENCELLID_API_URL, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'lat' in data and 'lon' in data:
                    lat = float(data['lat'])
                    lon = float(data['lon'])
                    range_m = int(data.get('range', 1000))  # Default 1km range
                    
                    logger.info("Found tower location: %.6f, %.6f (range=%sm)", lat, lon, range_m)
                    
                    # Cache the result
                    result = (lat, lon, range_m)
                    _tower_cache[cache_key] = (time.time(), result)
                    
                    return result
                else:
                    logger.warning(f"Tower not found in OpenCelliD database")
                    return None
            else:
                logger.error(f"OpenCelliD API error: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("OpenCelliD API timeout")
            return None
        except Exception as e:
            logger.error(f"Error looking up tower location: {e}")
            return None
    
    def estimate_tower_location_from_signal(
        self, 
        device_lat: float, 
        device_lon: float, 
        signal_dbm: int, 
        cell_id: int
    ) -> Tuple[float, float, int]:
        """
        Estimate tower location based on signal strength (fallback method).
        
        Args:
            device_lat: Device latitude
            device_lon: Device longitude
            signal_dbm: Signal strength in dBm
            cell_id: Cell ID (used as seed for consistent positioning)
        
        Returns:
            Tuple of (latitude, longitude, distance_meters)
        """
        import math
        import random
        
        # Estimate distance based on signal strength
        if signal_dbm >= -70:
            distance_km = random.uniform(0.1, 0.3)  # 100-300m
        elif signal_dbm >= -85:
            distance_km = random.uniform(0.3, 0.8)  # 300-800m
        elif signal_dbm >= -95:
            distance_km = random.uniform(0.8, 2.0)  # 0.8-2km
        elif signal_dbm >= -105:
            distance_km = random.uniform(2.0, 5.0)  # 2-5km
        else:
            distance_km = random.uniform(5.0, 10.0)  # 5-10km
        
        # Use cell_id as seed for consistent bearing
        random.seed(cell_id)
        bearing = random.uniform(0, 360)
        
        # Calculate offset in degrees
        # 1 degree latitude ≈ 111 km
        # 1 degree longitude ≈ 111 km * cos(latitude)
        lat_offset = (distance_km / 111.0) * math.cos(math.radians(bearing))
        lon_offset = (distance_km / (111.0 * math.cos(math.radians(device_lat)))) * math.sin(math.radians(bearing))
        
        tower_lat = device_lat + lat_offset
        tower_lon = device_lon + lon_offset
        distance_m = int(distance_km * 1000)
        
        logger.info(f"Estimated tower location: {tower_lat:.6f}, {tower_lon:.6f} (~{distance_m}m from device)")
        
        return (tower_lat, tower_lon, distance_m)


def get_tower_location(
    mcc: int, 
    mnc: int, 
    lac: int, 
    cell_id: int, 
    device_lat: Optional[float] = None,
    device_lon: Optional[float] = None,
    signal_dbm: Optional[int] = None
) -> Dict[str, any]:
    """
    Get tower location using multiple data sources with priority:
    1. ComReg (official Irish regulator) - for MCC=272 (Ireland)
    2. OpenCelliD (global crowdsourced database)
    3. Signal-based estimation (fallback)
    
    Args:
        mcc: Mobile Country Code (272 for Ireland)
        mnc: Mobile Network Code
        lac: Location Area Code
        cell_id: Cell ID
        device_lat: Device latitude (for fallback estimation)
        device_lon: Device longitude (for fallback estimation)
        signal_dbm: Signal strength (for fallback estimation)
    
    Returns:
        Dict with latitude, longitude, distance_meters, and source
    """
    # Try ComReg first for Irish towers (MCC=272)
    if mcc == 272 and device_lat and device_lon:
        try:
            from src.services.comreg_lookup import lookup_comreg_tower
            
            logger.info(f"Trying ComReg lookup for Irish tower (MCC=272, CID={cell_id})")
            comreg_result = lookup_comreg_tower(cell_id, mcc, mnc, device_lat, device_lon)
            
            if comreg_result and comreg_result.get('latitude'):
                logger.info("Found tower in ComReg database")
                # Calculate distance to device
                import math
                lat_diff = comreg_result['latitude'] - device_lat
                lon_diff = comreg_result['longitude'] - device_lon
                distance_m = int(math.sqrt(lat_diff**2 + lon_diff**2) * 111000)
                
                return {
                    'latitude': comreg_result['latitude'],
                    'longitude': comreg_result['longitude'],
                    'distance_meters': distance_m,
                    'source': 'comreg',
                    'site_id': comreg_result.get('site_id'),
                    'operator': comreg_result.get('operator')
                }
        except Exception as e:
            logger.warning(f"ComReg lookup failed: {e}, trying OpenCelliD...")
    
    # Try OpenCelliD lookup
    service = TowerLocationService()
    result = service.lookup_tower_location(mcc, mnc, lac, cell_id)
    
    if result:
        lat, lon, range_m = result
        return {
            'latitude': lat,
            'longitude': lon,
            'distance_meters': range_m,
            'source': 'opencellid'
        }
    
    # Fallback to signal-based estimation
    if device_lat and device_lon and signal_dbm:
        lat, lon, dist_m = service.estimate_tower_location_from_signal(
            device_lat, device_lon, signal_dbm, cell_id
        )
        return {
            'latitude': lat,
            'longitude': lon,
            'distance_meters': dist_m,
            'source': 'estimated'
        }
    
    # No location available
    logger.error("Cannot determine tower location - no data from any source")
    return {
        'latitude': None,
        'longitude': None,
        'distance_meters': None,
        'source': 'unknown'
    }
