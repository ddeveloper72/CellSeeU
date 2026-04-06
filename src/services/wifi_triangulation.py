"""
WiFi Triangulation Service

Estimates WiFi Access Point locations using:
- Multiple scans from different device positions
- Signal strength (RSSI) for distance estimation  
- Device compass heading for bearing calculation
- Triangulation from multiple bearings

The algorithm:
1. Collect scans from different GPS positions
2. For each WiFi AP (identified by BSSID):
   - Calculate distance from signal strength (path loss model)
   - Use device heading to estimate bearing to AP
   - Triangulate position from multiple (location, bearing, distance) points
3. Return estimated lat/lon with confidence score
"""

import math
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


def signal_to_distance(rssi: int, frequency_mhz: int = 2437) -> float:
    """
    Estimate distance from WiFi signal strength using Free Space Path Loss model.
    
    Formula: FSPL(dB) = 20*log10(d) + 20*log10(f) + 32.45
    Where d = distance in km, f = frequency in MHz
    
    Rearranged: d = 10^((FSPL - 20*log10(f) - 32.45) / 20)
    
    Args:
        rssi: Signal strength in dBm (e.g., -42)
        frequency_mhz: Frequency in MHz (default 2437 = channel 6)
        
    Returns:
        Estimated distance in meters (rough estimate)
        
    Note:
        This is a rough estimate. Real-world factors:
        - Walls and obstacles (adds 10-30 dB loss)
        - Reflections and multipath
        - Antenna gain variations
        - Environmental noise
    """
    # Typical WiFi AP transmit power
    tx_power = 20  # dBm (100mW, common for home routers)
    
    # Path loss = TX power - RX power
    path_loss = tx_power - rssi
    
    # Calculate distance in km
    freq_factor = 20 * math.log10(frequency_mhz)
    distance_km = 10 ** ((path_loss - freq_factor - 32.45) / 20)
    distance_m = distance_km * 1000
    
    # Clamp to reasonable range (WiFi max ~300m outdoors)
    distance_m = min(max(distance_m, 1), 500)
    
    logger.debug(f"Signal {rssi} dBm @ {frequency_mhz} MHz → {distance_m:.1f}m")
    
    return distance_m


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing from point 1 to point 2.
    
    Args:
        lat1, lon1: Starting point (degrees)
        lat2, lon2: Ending point (degrees)
        
    Returns:
        Bearing in degrees (0-360, where 0=North)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon_rad = math.radians(lon2 - lon1)
    
    y = math.sin(dlon_rad) * math.cos(lat2_rad)
    x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))
    
    bearing_rad = math.atan2(y, x)
    bearing_deg = math.degrees(bearing_rad)
    
    # Normalize to 0-360
    bearing_deg = (bearing_deg + 360) % 360
    
    return bearing_deg


def calculate_destination(lat: float, lon: float, bearing: float, distance_m: float) -> Tuple[float, float]:
    """
    Calculate destination point given start point, bearing, and distance.
    
    Args:
        lat, lon: Starting point (degrees)
        bearing: Direction in degrees (0-360)
        distance_m: Distance in meters
        
    Returns:
        (latitude, longitude) of destination point
    """
    R = 6371000  # Earth radius in meters
    
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)
    
    lat2_rad = math.asin(
        math.sin(lat_rad) * math.cos(distance_m / R) +
        math.cos(lat_rad) * math.sin(distance_m / R) * math.cos(bearing_rad)
    )
    
    lon2_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(distance_m / R) * math.cos(lat_rad),
        math.cos(distance_m / R) - math.sin(lat_rad) * math.sin(lat2_rad)
    )
    
    return math.degrees(lat2_rad), math.degrees(lon2_rad)


def triangulate_ap_position(scans: List[Dict]) -> Optional[Dict]:
    """
    Triangulate WiFi AP position from multiple scans.
    
    Args:
        scans: List of scan observations for a specific BSSID:
            [{
                'location': {'latitude': 53.29, 'longitude': -6.68},
                'orientation': {'heading': 287.5},
                'signal_strength': -42,
                'frequency': 2437
            }, ...]
            
    Returns:
        {
            'latitude': 53.xxx,
            'longitude': -6.xxx,
            'confidence': 0.8,  # 0-1 score
            'scan_count': 3,
            'estimated_accuracy_m': 25
        }
        or None if not enough data
    """
    if len(scans) < 2:
        return None  # Need at least 2 scans for basic triangulation
    
    # Calculate candidate positions from each scan
    candidates = []
    
    for scan in scans:
        loc = scan.get('location', {})
        orientation = scan.get('orientation', {})
        
        if not loc.get('latitude') or not orientation.get('heading'):
            continue
        
        device_lat = loc['latitude']
        device_lon = loc['longitude']
        device_heading = orientation['heading']
        
        signal = scan.get('signal_strength', -70)
        frequency = scan.get('frequency', 2437)
        
        # Estimate distance from signal
        distance = signal_to_distance(signal, frequency)
        
        # Assume AP is roughly in the direction device is facing
        # (This is a simplification - real implementation would use antenna patterns)
        ap_lat, ap_lon = calculate_destination(device_lat, device_lon, device_heading, distance)
        
        candidates.append({
            'lat': ap_lat,
            'lon': ap_lon,
            'distance': distance,
            'signal': signal
        })
        
        logger.debug(f"Scan: device ({device_lat:.6f}, {device_lon:.6f}) " +
                    f"heading {device_heading:.0f}° → AP at ({ap_lat:.6f}, {ap_lon:.6f})")
    
    if len(candidates) < 2:
        return None
    
    # Calculate centroid (simple average for now)
    # TODO: Could implement weighted average based on signal strength
    avg_lat = sum(c['lat'] for c in candidates) / len(candidates)
    avg_lon = sum(c['lon'] for c in candidates) / len(candidates)
    
    # Calculate spread (standard deviation) as confidence indicator
    lat_variance = sum((c['lat'] - avg_lat) ** 2 for c in candidates) / len(candidates)
    lon_variance = sum((c['lon'] - avg_lon) ** 2 for c in candidates) / len(candidates)
    
    # Convert variance to meters (approximate)
    avg_variance_deg = (lat_variance + lon_variance) / 2
    variance_m = avg_variance_deg * 111000  # 1 degree ≈ 111km
    
    # Confidence: higher when points cluster tightly
    # Range: 0-1 (1 = all points within 10m, 0 = spread >100m)
    confidence = max(0, min(1, 1 - (variance_m / 100)))
    
    estimated_accuracy = min(variance_m * 1.5, 200)  # Cap at 200m
    
    logger.info(f"🎯 Triangulated AP from {len(candidates)} scans: " +
               f"({avg_lat:.6f}, {avg_lon:.6f}) ±{estimated_accuracy:.0f}m (confidence: {confidence:.2f})")
    
    return {
        'latitude': round(avg_lat, 6),
        'longitude': round(avg_lon, 6),
        'confidence': round(confidence, 2),
        'scan_count': len(candidates),
        'estimated_accuracy_m': round(estimated_accuracy)
    }


def analyze_wifi_scan_history(scan_history: List[Dict]) -> Dict[str, Dict]:
    """
    Analyze WiFi scan history to estimate AP positions.
    
    Args:
        scan_history: List of scan records from backend:
            [{
                'timestamp': '2026-04-06T12:00:00Z',
                'location': {'latitude': 53.29, 'longitude': -6.68},
                'orientation': {'heading': 287.5, 'pitch': 12, 'roll': -5},
                'networks': [
                    {'ssid': 'MyWiFi', 'bssid': 'aa:bb:cc:dd:ee:ff', 
                     'signal_strength': -42, 'frequency': 2437}
                ]
            }, ...]
            
    Returns:
        {
            'aa:bb:cc:dd:ee:ff': {
                'ssid': 'MyWiFi',
                'estimated_position': {
                    'latitude': 53.xxx,
                    'longitude': -6.xxx,
                    'confidence': 0.8,
                    'scan_count': 5
                },
                'last_seen': '2026-04-06T12:05:00Z'
            },
            ...
        }
    """
    # Group scans by BSSID (MAC address)
    ap_scans = defaultdict(list)
    ap_info = {}
    
    for scan_record in scan_history:
        networks = scan_record.get('networks', [])
        location = scan_record.get('location')
        orientation = scan_record.get('orientation')
        timestamp = scan_record.get('timestamp')
        
        for network in networks:
            bssid = network.get('bssid')
            if not bssid:
                continue
            
            # Store scan observation for this AP
            ap_scans[bssid].append({
                'location': location,
                'orientation': orientation,
                'signal_strength': network.get('signal_strength'),
                'frequency': network.get('frequency'),
                'timestamp': timestamp
            })
            
            # Store AP metadata
            if bssid not in ap_info:
                ap_info[bssid] = {
                    'ssid': network.get('ssid', ''),
                    'security': network.get('security', 'Unknown'),
                    'first_seen': timestamp
                }
            ap_info[bssid]['last_seen'] = timestamp
    
    # Triangulate position for each AP
    results = {}
    
    for bssid, scans in ap_scans.items():
        position = triangulate_ap_position(scans)
        
        if position and position['confidence'] > 0.1:  # Only include if somewhat confident
            results[bssid] = {
                'ssid': ap_info[bssid]['ssid'],
                'security': ap_info[bssid]['security'],
                'estimated_position': position,
                'first_seen': ap_info[bssid]['first_seen'],
                'last_seen': ap_info[bssid]['last_seen']
            }
            
            logger.info(f"✓ {ap_info[bssid]['ssid']} ({bssid}): " +
                       f"{position['scan_count']} scans, confidence {position['confidence']:.0%}")
        else:
            logger.debug(f"✗ {ap_info[bssid]['ssid']} ({bssid}): insufficient data for triangulation")
    
    return results
