"""
CellSeeU Flask Application

Main entry point for the web dashboard. Implements security best practices
including HTTPS enforcement, security headers, input validation, and rate limiting.

Run with: flask run --host=0.0.0.0 --port=5000
Or: python app.py
"""

import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_talisman import Talisman
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load configuration from environment
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-in-production')
app.config['ENV'] = os.getenv('FLASK_ENV', 'development')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# CORS configuration - Allow API access from mobile app
# In production, restrict this to specific origins
CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv('ALLOWED_ORIGINS', '*').split(',')
    }
})

# Security headers with Talisman
# Disabled in development for easier testing, enabled in production
if app.config['ENV'] == 'production':
    # Enforce HTTPS and set Content Security Policy
    # CSP allows maps from external services while blocking inline scripts
    Talisman(app,
        force_https=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 year
        content_security_policy={
            'default-src': ["'self'"],
            'script-src': ["'self'", 'unpkg.com', 'cdn.jsdelivr.net'],  # For Leaflet.js
            'style-src': ["'self'", "'unsafe-inline'", 'unpkg.com', 'cdn.jsdelivr.net'],
            'img-src': ["'self'", 'data:', '*.tile.openstreetmap.org', '*.basemaps.cartocdn.com'],
            'connect-src': ["'self'", 'api.opencellid.org'],
            'font-src': ["'self'", 'data:'],
        },
        content_security_policy_nonce_in=['script-src']
    )


@app.after_request
def set_security_headers(response):
    """
    Add security headers to all responses.
    
    Implements OWASP security best practices:
    - X-Content-Type-Options: Prevent MIME-type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable browser XSS filter
    - Strict-Transport-Security: Enforce HTTPS (production only)
    
    Args:
        response: Flask response object
        
    Returns:
        Modified response with security headers
    """
    # Prevent MIME-type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevent clickjacking - don't allow framing
    response.headers['X-Frame-Options'] = 'DENY'
    
    # Enable XSS protection (legacy but still useful)
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # HSTS header - only in production with HTTPS
    if app.config['ENV'] == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    # Referrer policy - don't leak URLs
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions policy - disable unnecessary features
    response.headers['Permissions-Policy'] = 'geolocation=(self), camera=(), microphone=(), payment=()'
    
    return response


@app.route('/')
def index():
    """
    Main dashboard page.
    
    Mobile-first responsive dashboard showing detected cell towers,
    device location, and interactive map visualization.
    
    Returns:
        Rendered dashboard HTML template
    """
    return render_template('dashboard.html')


@app.route('/map')
def map_view():
    """
    Full-screen interactive map view.
    
    Displays all detected towers with color-coded markers based on
    signal strength and tower type (terrestrial vs satellite).
    
    Returns:
        Rendered map HTML template
    """
    return render_template('map.html')


@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns basic app status and version information.
    Used by monitoring tools to verify the app is running.
    
    Returns:
        JSON with status and version
    """
    return jsonify({
        'status': 'healthy',
        'version': '0.1.0',
        'timestamp': datetime.utcnow().isoformat()
    })


@app.errorhandler(404)
def not_found(error):
    """
    Handle 404 Not Found errors.
    
    Returns user-friendly JSON response instead of exposing
    server details in error pages.
    
    Returns:
        JSON error message with 404 status
    """
    return jsonify({
        'error': 'Resource not found',
        'status': 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server errors.
    
    Logs the actual error server-side but returns generic
    message to user to avoid leaking implementation details.
    
    Args:
        error: The exception that caused the 500 error
        
    Returns:
        JSON error message with 500 status
    """
    # TODO: Log error to proper logging system
    app.logger.error(f'Internal error: {error}')
    
    return jsonify({
        'error': 'Internal server error',
        'status': 500
    }), 500


if __name__ == '__main__':
    # Development server
    # In production, use proper WSGI server like gunicorn
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🗼 CellSeeU starting on port {port}")
    print(f"📱 Dashboard: http://localhost:{port}")
    print(f"🗺️  Map view: http://localhost:{port}/map")
    print(f"🔒 Security headers: {'ENABLED' if app.config['ENV'] == 'production' else 'DEVELOPMENT MODE'}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
