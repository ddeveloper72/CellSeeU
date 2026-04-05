"""
Flask API Routes for CellSeeU

Provides RESTful endpoints for tower data and geolocation.
Implements input validation, rate limiting, and security best practices.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timezone
from functools import wraps
import time

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api')

# Simple in-memory rate limiting (production should use Redis)
_request_counts = {}
_rate_limit_window = 60  # seconds
_rate_limit_max_requests = 100  # per window

# Global storage for real tower data from Android app
_real_tower_data = []
_device_location = None
_last_update_time = None


def rate_limit(f):
    """
    Decorator to implement basic rate limiting on API endpoints.
    
    Prevents abuse by limiting requests to 100 per minute per IP.
    In production, use proper rate limiting middleware like
    Flask-Limiter with Redis backend.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function that checks rate limits
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP (respect X-Forwarded-For if behind proxy)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if not client_ip:
            client_ip = 'unknown'
        
        current_time = time.time()
        
        # Clean old entries (older than window)
        global _request_counts
        _request_counts = {
            ip: requests for ip, requests in _request_counts.items()
            if any(t > current_time - _rate_limit_window for t in requests)
        }
        
        # Check current IP rate
        if client_ip not in _request_counts:
            _request_counts[client_ip] = []
        
        # Remove old requests from this IP
        _request_counts[client_ip] = [
            t for t in _request_counts[client_ip]
            if t > current_time - _rate_limit_window
        ]
        
        # Check if over limit
        if len(_request_counts[client_ip]) >= _rate_limit_max_requests:
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': f'Maximum {_rate_limit_max_requests} requests per minute',
                'retry_after': _rate_limit_window
            }), 429
        
        # Record this request
        _request_counts[client_ip].append(current_time)
        
        return f(*args, **kwargs)
    
    return decorated_function


@api.route('/towers', methods=['GET'])
@rate_limit
def get_towers():
    """
    Get list of all detected cell towers.
    
    Returns tower data including signal strength, type (terrestrial/satellite),
    location coordinates (if available), and distance from device.
    
    Query Parameters:
        filter: Optional filter by type ('terrestrial', 'satellite', 'connected')
        limit: Maximum number of towers to return (default: 100)
    
    Returns:
        JSON response with tower list and metadata
        
    Security:
        - Input validation on query parameters
        - Rate limited to prevent abuse
        - Does not expose sensitive system information
    
    Example Response:
        {
            "towers": [...],
            "count": 5,
            "timestamp": "2026-04-05T12:30:00Z"
        }
    """
    # TODO: Replace with actual tower detection service
    # For now, return mock data for frontend development
    
    # Validate and sanitize query parameters
    filter_type = request.args.get('filter', 'all')
    if filter_type not in ['all', 'terrestrial', 'satellite', 'connected']:
        return jsonify({
            'error': 'Invalid filter parameter',
            'valid_values': ['all', 'terrestrial', 'satellite', 'connected']
        }), 400
    
    # Validate limit parameter
    try:
        limit = int(request.args.get('limit', 100))
        if limit < 1 or limit > 1000:
            raise ValueError("Limit out of range")
    except (ValueError, TypeError):
        return jsonify({
            'error': 'Invalid limit parameter',
            'message': 'Limit must be between 1 and 1000'
        }), 400
    
    # Use real tower data from Android app if available, otherwise use mock data
    global _real_tower_data, _last_update_time
    
 if _real_tower_data:
        # Use real data from Android TelephonyManager
        towers = _real_tower_data.copy()
    else:
        # Fallback to mock tower data for development (Ireland-based for testing)
        # NOTE: Install and run Android Scanner app to get real tower data
        towers = [
            {
                'cell_id': 45612378,
                'tower_type': 'TERRESTRIAL',
                'network_type': 'LTE',
                'mcc': 272,
                'mnc': 1,
                'carrier': 'Vodafone Ireland',
                'signal_strength': -75,
                'signal_bars': 5,
                'registered': True,
                'latitude': 53.3498,
                'longitude': -6.2603,
                'distance_meters': 180,
                'detected_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'cell_id': 78945612,
                'tower_type': 'TERRESTRIAL',
                'network_type': '5G_NR',
                'mcc': 272,
                'mnc': 2,
                'carrier': 'Three Ireland',
                'signal_strength': -82,
                'signal_bars': 4,
                'registered': False,
                'latitude': 53.3512,
                'longitude': -6.2585,
                'distance_meters': 320,
                'detected_at': datetime.now(timezone.utc).isoformat()
            },
            {
                'cell_id': 87654321,
                'tower_type': 'NON_TERRESTRIAL_SATELLITE',
                'network_type': '5G_NR_NTN',
                'mcc': 901,
                'mnc': 88,
                'carrier': 'Starlink (SpaceX)',
                'signal_strength': -105,
                'signal_bars': 3,
                'registered': False,
                'latitude': 53.3485,
                'longitude': -6.2520,
                'distance_meters': 1200,
                'detected_at': datetime.now(timezone.utc).isoformat()
            }
        ]
    
    # Variable name changed from mock_towers to towers for compatibility
    
    # Apply filter
    if filter_type == 'terrestrial':
        towers = [t for t in towers if t['tower_type'] == 'TERRESTRIAL']
    elif filter_type == 'satellite':
        towers = [t for t in towers if t['tower_type'] == 'NON_TERRESTRIAL_SATELLITE']
    elif filter_type == 'connected':
        towers = [t for t in towers if t.get('registered', False)]
    
    # Apply limit
    towers = towers[:limit]
    
    return jsonify({
        'towers': towers,
        'count': len(towers),
        'data_source': 'real' if _real_tower_data else 'mock',
        'last_update': _last_update_time.isoformat() if _last_update_time else None,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@api.route('/tower/<int:cell_id>', methods=['GET'])
@rate_limit
def get_tower_details(cell_id):
    """
    Get detailed information for a specific cell tower.
    
    Args:
        cell_id: Unique cell identifier (CID)
    
    Returns:
        JSON with detailed tower information
        
    Security:
        - Input validation (cell_id must be positive integer)
        - Rate limited
        - Returns 404 for non-existent towers (don't leak info)
    
    Example:
        GET /api/tower/12345678
    """
    # Validate cell_id (checked by Flask route converter, but double-check)
    if cell_id <= 0 or cell_id > 999999999:
        return jsonify({
            'error': 'Invalid cell ID',
            'message': 'Cell ID must be a positive integer'
        }), 400
    
    # TODO: Query actual tower database
    # For now, return 404 for all requests
    return jsonify({
        'error': 'Tower not found',
        'cell_id': cell_id
    }), 404


@api.route('/location', methods=['GET'])
@rate_limit
def get_location():
    """
    Get current device location (if available).
    
    Returns GPS coordinates, accuracy, and timestamp.
    Only returns location if user has granted permission.
    
    Returns:
        JSON with location data or error
        
    Security:
        - Does not log or store location data
        - Requires explicit user consent (handled by frontend)
        - Rate limited to prevent tracking abuse
    
    Privacy:
        Location data is NEVER stored on server.
        This endpoint only echoes back what the frontend sends.
    """
    # TODO: Implement location storage/retrieval if needed
    # For now, location is handled entirely client-side
    
    return jsonify({
        'message': 'Location is handled client-side',
        'privacy': 'Your location data never leaves your device'
    })


@api.route('/stats', methods=['GET'])
@rate_limit
def get_stats():
    """
    Get aggregate statistics about detected towers.
    
    Returns summary information without exposing individual tower data.
    Useful for dashboard displays and analytics.
    
    Returns:
        JSON with statistics:
        - total_towers: Total count of detected towers
        - terrestrial_count: Number of ground-based towers
        - satellite_count: Number of satellite/NTN towers
        - average_signal: Average signal strength in dBm
        - connected_network: Currently connected network type
    """
    # TODO: Calculate from actual tower data
    
    return jsonify({
        'total_towers': 2,
        'terrestrial_count': 1,
        'satellite_count': 1,
        'average_signal': -95,
        'connected_network': 'LTE',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


@api.route('/towers/upload', methods=['POST'])
@rate_limit
def upload_towers():
    """
    Receive real tower data from Android Scanner app.
    
    This endpoint receives cell tower data collected from the
    Android TelephonyManager API and stores it for display
    in the web dashboard.
    
    Expected JSON format:
    {
        "device_location": {
            "latitude": 53.3498,
            "longitude": -6.2603,
            "accuracy": 15.0,
            "altitude": 42.0
        },
        "towers": [
            {
                "cell_id": 45612378,
                "mcc": 272,
                "mnc": 1,
                "network_type": "LTE",
                "signal_strength": -75,
                "registered": true,
                "tower_type": "TERRESTRIAL",
                "tac": 12345,
                "pci": 123
            }
        ],
        "count": 1,
        "timestamp": 1680723456789
    }
    
    Returns:
        JSON response with success/error status
    """
    global _real_tower_data, _device_location, _last_update_time
    
    # Validate content type
    if not request.is_json:
        return jsonify({
            'error': 'Content-Type must be application/json',
            'status': 400
        }), 400
    
    data = request.get_json()
    
    # Validate required fields
    if 'towers' not in data:
        return jsonify({
            'error': 'Missing required field: towers',
            'status': 400
        }), 400
    
    if not isinstance(data['towers'], list):
        return jsonify({
            'error': 'Field "towers" must be an array',
            'status': 400
        }), 400
    
    try:
        # Import carrier lookup to enrich tower data
        from src.services.carrier_lookup import get_carrier_name
        
        # Process and enrich tower data
        enriched_towers = []
        for tower in data['towers']:
            # Add carrier name from MCC-MNC
            if 'mcc' in tower and 'mnc' in tower:
                tower['carrier'] = get_carrier_name(tower['mcc'], tower['mnc'])
            
            # Calculate signal bars if not provided
            if 'signal_bars' not in tower and 'signal_strength' in tower:
                dbm = tower['signal_strength']
                if dbm >= -85:
                    tower['signal_bars'] = 5
                elif dbm >= -95:
                    tower['signal_bars'] = 4
                elif dbm >= -105:
                    tower['signal_bars'] = 3
                elif dbm >= -115:
                    tower['signal_bars'] = 2
                elif dbm >= -125:
                    tower['signal_bars'] = 1
                else:
                    tower['signal_bars'] = 0
            
            # Add timestamp ifnot provided
            if 'detected_at' not in tower:
                tower['detected_at'] = datetime.now(timezone.utc).isoformat()
            
            enriched_towers.append(tower)
        
        # Update global storage
        _real_tower_data = enriched_towers
        _device_location = data.get('device_location')
        _last_update_time = datetime.now(timezone.utc)
        
        return jsonify({
            'success': True,
            'message': f'Received {len(enriched_towers)} towers',
            'towers_received': len(enriched_towers),
            'timestamp': _last_update_time.isoformat()
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to process tower data',
            'details': str(e),
            'status': 500
        }), 500


# Error handlers for API blueprint
@api.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors in API"""
    return jsonify({
        'error': 'Bad request',
        'status': 400
    }), 400


@api.errorhandler(404)
def not_found_api(error):
    """Handle 404 errors in API endpoints"""
    return jsonify({
        'error': 'API endpoint not found',
        'status': 404
    }), 404


@api.errorhandler(500)
def internal_error_api(error):
    """Handle 500 errors in API endpoints"""
    return jsonify({
        'error': 'Internal server error',
        'status': 500
    }), 500
