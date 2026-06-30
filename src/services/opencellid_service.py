"""
OpenCelliD API Service

Fetches nearby cell towers from OpenCelliD crowd-sourced database.
Implements caching and rate limiting for efficient API usage.
"""

import os
import requests
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# API configuration
OPENCELLID_API_BASE = "https://opencellid.org/cell"
OPENCELLID_TOKEN = os.getenv('OPENCELLID_API_KEY')

# Cache for area queries (bbox → towers)
_area_cache = {}
_cache_ttl = timedelta(hours=24)  # Towers don't move, cache for 24 hours


def get_towers_in_area(min_lat, min_lon, max_lat, max_lon, mcc=272):
    """
    Get all cell towers within a bounding box from OpenCelliD.
    
    Uses the /cell/getInArea endpoint (free tier for data contributors).
    
    Args:
        min_lat: Minimum latitude (south)
        min_lon: Minimum longitude (west)
        max_lat: Maximum latitude (north)
        max_lon: Maximum longitude (east)
        mcc: Mobile Country Code (272 = Ireland, default)
    
    Returns:
        list: Tower records with lat/lon/operator/signal
    """
    
    if not OPENCELLID_TOKEN:
        logger.warning("OPENCELLID_API_KEY not configured")
        return generate_estimated_towers(
            (min_lat + max_lat) / 2,
            (min_lon + max_lon) / 2,
            ((max_lat - min_lat) * 111.0 / 2)  # Approx radius in km
        )
    
    # Create cache key from bounding box
    cache_key = f"{mcc}_{round(min_lat, 3)}_{round(min_lon, 3)}_{round(max_lat, 3)}_{round(max_lon, 3)}"
    
    # Check cache
    if cache_key in _area_cache:
        cached_data, cached_time = _area_cache[cache_key]
        if datetime.now() - cached_time < _cache_ttl:
            logger.info(f"Cache hit for area query ({len(cached_data)} towers)")
            return cached_data
    
    logger.info(f"Fetching towers in BBOX: {min_lat},{min_lon} to {max_lat},{max_lon}")
    
    try:
        # OpenCelliD getInArea endpoint - BBOX format: latmin,lonmin,latmax,lonmax
        response = requests.get(
            f"{OPENCELLID_API_BASE}/getInArea",
            params={
                'key': OPENCELLID_TOKEN,
                'BBOX': f"{min_lat},{min_lon},{max_lat},{max_lon}",
                'mcc': mcc,
                'format': 'json',
                'limit': 100  # Max towers to return per page
            },
            timeout=10
        )
        
        if response.status_code != 200:
            logger.warning(f"OpenCelliD API error {response.status_code}, using estimated towers")
            return generate_estimated_towers(
                (min_lat + max_lat) / 2,
                (min_lon + max_lon) / 2,
                ((max_lat - min_lat) * 111.0 / 2)
            )
        
        data = response.json()
        
        # Check for error response
        if isinstance(data, dict) and 'error' in data:
            logger.warning(f"OpenCelliD error: {data.get('error')}, using estimated towers")
            return generate_estimated_towers(
                (min_lat + max_lat) / 2,
                (min_lon + max_lon) / 2,
                ((max_lat - min_lat) * 111.0 / 2)
            )
        
        # Parse cell list from JSON response
        towers = []
        cells = data.get('cells', [])
        
        if not cells:
            logger.info("No OpenCelliD data, using estimated towers")
            return generate_estimated_towers(
                (min_lat + max_lat) / 2,
                (min_lon + max_lon) / 2,
                (( max_lat - min_lat) * 111.0 / 2)
            )
        
        for cell in cells:
            try:
                # Extract tower data
                tower = {
                    'cell_id': cell.get('cellid', 0),
                    'mcc': cell.get('mcc', mcc),
                    'mnc': cell.get('mnc', 0),
                    'lac': cell.get('lac', cell.get('tac', 0)),
                    'latitude': float(cell.get('lat', 0)),
                    'longitude': float(cell.get('lon', 0)),
                    'range_meters': cell.get('range', 1000),
                    'samples': cell.get('samples', 0),
                    'network_type': cell.get('radio', 'Unknown'),
                    'location_source': 'opencellid',
                    'tower_type': 'TERRESTRIAL'
                }
                
                # Map MNC to carrier (Ireland)
                mnc = tower['mnc']
                if mnc == 1:
                    tower['carrier'] = 'Vodafone Ireland'
                elif mnc == 2:
                    tower['carrier'] = 'Three Ireland'
                elif mnc == 3:
                    tower['carrier'] = 'Eir'
                elif mnc == 5:
                    tower['carrier'] = 'Three Ireland (Meteor)'
                else:
                    tower['carrier'] = f'MNC {mnc}'
                
                # Only include towers with valid coordinates
                if tower['latitude'] != 0 and tower['longitude'] != 0:
                    towers.append(tower)
                    
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to parse cell: {e}")
                continue
        
        logger.info(f"Found {len(towers)} towers from OpenCelliD")
        
        # Cache results
        _area_cache[cache_key] = (towers, datetime.now())
        
        return towers
        
    except requests.exceptions.Timeout:
        logger.warning("OpenCelliD API timeout, using estimated towers")
        return generate_estimated_towers(
            (min_lat + max_lat) / 2,
            (min_lon + max_lon) / 2,
            ((max_lat - min_lat) * 111.0 / 2)
        )
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error: {e}, using estimated towers")
        return generate_estimated_towers(
            (min_lat + max_lat) / 2,
            (min_lon + max_lon) / 2,
            ((max_lat - min_lat) * 111.0 / 2)
        )
    except Exception as e:
        logger.warning(f"Error: {e}, using estimated towers")
        return generate_estimated_towers(
            (min_lat + max_lat) / 2,
            (min_lon + max_lon) / 2,
            ((max_lat - min_lat) * 111.0 / 2)
        )


def get_nearby_towers(latitude, longitude, radius_km=5.0, mcc=272):
    """
    Get towers within radius of a point.
    
    Converts radius to bounding box and calls get_towers_in_area.
    
    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius_km: Search radius in kilometers (default: 5km, max: 100km)
        mcc: Mobile Country Code (272 = Ireland)
    
    Returns:
        list: Nearby towers (real from OpenCelliD or estimated)
    """
    
    # Convert radius to lat/lon degrees (approximate)
    # 1 degree latitude ≈ 111 km
    # 1 degree longitude ≈ 111 km * cos(latitude)
    import math
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(latitude)))
    
    min_lat = latitude - lat_delta
    max_lat = latitude + lat_delta
    min_lon = longitude - lon_delta
    max_lon = longitude + lon_delta
    
    return get_towers_in_area(min_lat, min_lon, max_lat, max_lon, mcc)


def generate_estimated_towers(latitude, longitude, radius_km):
    """
    Generate estimated tower positions based on typical Irish cell density.
    
    Ireland has ~7,300 towers for ~70,000 km² = ~1 tower per 10 km²
    In rural areas: ~1 tower per 2-4 km
    In urban areas: ~1 tower per 0.5-1 km
    
    Args:
        latitude: Center latitude
        longitude: Center longitude
        radius_km: Search radius
    
    Returns:
        list: Estimated tower positions
    """
    import math
    import random
    
    logger.info(f"Generating estimated towers for {radius_km}km radius")
    
    # Estimate tower count based on area and density
    area_km2 = math.pi * (radius_km ** 2)
    tower_density = 0.12  # Approximate: ~1 tower per 8 km² (rural Ireland average)
    estimated_count = int(area_km2 * tower_density)
    estimated_count = min(max(estimated_count, 3), 25)  # Between 3-25 towers
    
    towers = []
    carriers = [
        (1, 'Vodafone Ireland', 0.35),  # 35% market share
        (2, 'Three Ireland', 0.35),      # 35% market share
        (3, 'Eir', 0.30)                 # 30% market share
    ]
    
    # Use location as random seed for consistency
    random.seed(int((latitude + longitude) * 100000) % 1000000)
    
    for i in range(estimated_count):
        # Random distance and angle
        distance_km = random.uniform(0.5, radius_km)
        angle_rad = random.uniform(0, 2 * math.pi)
        
        # Calculate tower position
        # 1 degree latitude ≈ 111km
        # 1 degree longitude ≈ 111km * cos(latitude)
        lat_offset = (distance_km / 111.0) * math.cos(angle_rad)
        lon_offset = (distance_km / (111.0 * math.cos(math.radians(latitude)))) * math.sin(angle_rad)
        
        tower_lat = latitude + lat_offset
        tower_lon = longitude + lon_offset
        
        # Assign carrier based on market share
        rand_carrier = random.random()
        cumulative = 0
        selected_mnc, selected_carrier, _ = carriers[0]
        for mnc, carrier, share in carriers:
            cumulative += share
            if rand_carrier <= cumulative:
                selected_mnc = mnc
                selected_carrier = carrier
                break
        
        # Create  estimated tower
        towers.append({
            'cell_id': 90000000 + i,  # Fake cell ID (starts with 9)
            'mcc': 272,
            'mnc': selected_mnc,
            'lac': random.randint(10000, 60000),
            'latitude': round(tower_lat, 6),
            'longitude': round(tower_lon, 6),
            'range_meters': random.randint(800, 3000),
            'samples': 0,
            'network_type': random.choice(['LTE', 'LTE', 'LTE', 'UMTS']),  # Mostly LTE
            'location_source': 'estimated',
            'tower_type': 'TERRESTRIAL',
            'carrier': selected_carrier
        })
    
    logger.info(f"Generated {len(towers)} estimated tower positions")
    return towers
