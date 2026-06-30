"""
ComReg (Irish Telecom Regulator) Tower Location Lookup

ComReg maintains the official registry of all mobile phone masts in Ireland.
This service queries their Site Viewer API for accurate tower coordinates.

NOTE: The API endpoints below are placeholders and need to be discovered.

To find the real ComReg API endpoints:
1. Open https://siteviewer.comreg.ie/#/mobile-masts in Chrome
2. Press F12 to open DevTools → Network tab
3. Zoom/pan the map or search for a location
4. Look for XHR/Fetch requests like:
   - /api/sites
   - /api/search
   - /geoserver/wfs
5. Click on the request → Preview tab to see response format
6. Update COMREG_API_BASE and endpoint URLs below

Alternative: ComReg may provide the data as a downloadable CSV/JSON file
at https://data.gov.ie or https://www.comreg.ie/industry/licensing/
"""

import requests
import logging
from typing import Optional, Tuple, Dict, List
import json

logger = logging.getLogger(__name__)

# ComReg Site Viewer API endpoints
# TODO: Discover actual endpoints from network inspector
COMREG_API_BASE = "https://siteviewer.comreg.ie/api"
COMREG_SEARCH_ENDPOINT = f"{COMREG_API_BASE}/sites/search"
COMREG_SITE_ENDPOINT = f"{COMREG_API_BASE}/sites"

class ComRegLookupService:
    """Service for looking up Irish cell tower locations from ComReg database"""
    
    def __init__(self):
        """Initialize ComReg lookup service"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CellSeeU Educational Tool',
            'Accept': 'application/json'
        })
    
    def search_towers_by_location(self, lat: float, lon: float, radius_km: float = 5) -> List[Dict]:
        """
        Search for towers near a GPS location.
        
        Args:
            lat: Latitude
            lon: Longitude  
            radius_km: Search radius in kilometers (default 5km)
        
        Returns:
            List of tower dictionaries with coordinates and details
        """
        try:
            # ComReg API typically uses bounding box queries
            # Calculate rough bounding box (1 degree ≈ 111km)
            lat_offset = radius_km / 111.0
            lon_offset = radius_km / (111.0 * 0.7)  # Approximate for Ireland latitude
            
            params = {
                'bounds': f"{lat-lat_offset},{lon-lon_offset},{lat+lat_offset},{lon+lon_offset}",
                'technology': 'all'  # Include all mobile technologies
            }
            
            logger.info(f"Searching ComReg towers near {lat:.6f}, {lon:.6f} (radius={radius_km}km)")
            
            response = self.session.get(COMREG_SEARCH_ENDPOINT, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                towers = data.get('sites', [])
                logger.info("Found %d towers in ComReg database", len(towers))
                return towers
            else:
                logger.error(f"ComReg API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error querying ComReg API: {e}")
            return []
    
    def find_tower_by_cell_id(
        self, 
        cell_id: int, 
        mcc: int = 272,  # Ireland
        mnc: int = None,
        device_lat: Optional[float] = None,
        device_lon: Optional[float] = None
    ) -> Optional[Tuple[float, float, Dict]]:
        """
        Find a specific tower by cell ID.
        
        Note: ComReg doesn't index by cell ID directly, so we search nearby
        and try to match based on operator and area.
        
        Args:
            cell_id: Cell ID from TelephonyManager
            mcc: Mobile Country Code (272 for Ireland)
            mnc: Mobile Network Code (1=Vodafone, 2=Three, 3=Eir)
            device_lat: Device latitude (for nearby search)
            device_lon: Device longitude (for nearby search)
        
        Returns:
            Tuple of (latitude, longitude, site_details) or None
        """
        if not device_lat or not device_lon:
            logger.warning("Cannot search ComReg without device location")
            return None
        
        # Map MNC to operator name
        operator_map = {
            1: 'Vodafone',
            2: 'Three',
            3: 'Eir',
            5: 'Vodafone',  # Alternative MNC
            7: 'Eir',  # Alternative MNC
        }
        
        operator = operator_map.get(mnc, 'Unknown')
        
        # Search nearby towers
        towers = self.search_towers_by_location(device_lat, device_lon, radius_km=10)
        
        if not towers:
            return None
        
        # Try to find matching tower
        # Strategy: Find closest tower from same operator
        matching_towers = [
            t for t in towers 
            if operator.lower() in t.get('operator', '').lower()
        ]
        
        if not matching_towers:
            # No operator match, use closest tower
            matching_towers = towers
        
        # Find closest tower to device
        import math
        
        def distance(lat1, lon1, lat2, lon2):
            """Calculate distance in km using Haversine formula"""
            R = 6371  # Earth radius in km
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat/2)**2 + 
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
                 math.sin(dlon/2)**2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            return R * c
        
        closest_tower = min(
            matching_towers,
            key=lambda t: distance(device_lat, device_lon, t.get('latitude', 0), t.get('longitude', 0))
        )
        
        tower_lat = closest_tower.get('latitude')
        tower_lon = closest_tower.get('longitude')
        
        if tower_lat and tower_lon:
            logger.info(
                f"Matched tower: {closest_tower.get('site_id')} "
                f"({operator}) at {tower_lat:.6f}, {tower_lon:.6f}"
            )
            return (tower_lat, tower_lon, closest_tower)
        
        return None


def lookup_comreg_tower(
    cell_id: int,
    mcc: int,
    mnc: int,
    device_lat: Optional[float] = None,
    device_lon: Optional[float] = None
) -> Optional[Dict]:
    """
    Look up tower location from ComReg database.
    
    Args:
        cell_id: Cell ID
        mcc: Mobile Country Code (should be 272 for Ireland)
        mnc: Mobile Network Code
        device_lat: Device latitude (required for search)
        device_lon: Device longitude (required for search)
    
    Returns:
        Dict with latitude, longitude, and site details or None
    """
    # Only works for Ireland
    if mcc != 272:
        logger.info(f"ComReg only covers Ireland (MCC=272), got MCC={mcc}")
        return None
    
    if not device_lat or not device_lon:
        logger.warning("ComReg lookup requires device location")
        return None
    
    try:
        service = ComRegLookupService()
        result = service.find_tower_by_cell_id(
            cell_id, mcc, mnc, device_lat, device_lon
        )
        
        if result:
            lat, lon, details = result
            return {
                'latitude': lat,
                'longitude': lon,
                'site_id': details.get('site_id'),
                'operator': details.get('operator'),
                'technologies': details.get('technologies', []),
                'source': 'comreg'
            }
        
        return None
        
    except Exception as e:
        logger.error(f"ComReg lookup failed: {e}")
        return None
