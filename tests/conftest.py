"""
Pytest configuration and shared fixtures for all tests

Provides common test fixtures, mock data, and helper functions
used across the test suite.
"""

import pytest
from datetime import datetime
from src.models.tower import CellTower, DeviceLocation


@pytest.fixture
def sample_lte_tower():
    """
    Fixture providing a sample terrestrial LTE tower.
    
    Represents a typical T-Mobile USA LTE tower with good signal.
    Use this for tests that need a standard tower example.
    """
    return CellTower(
        cell_id=12345678,
        tower_type="TERRESTRIAL",
        network_type="LTE",
        mcc=310,
        mnc=260,
        signal_strength=-85,
        signal_quality=-10,
        registered=True,
        detected_at=datetime(2026, 4, 5, 12, 0, 0),
        lac=None,
        tac=45678,
        pci=123,
        latitude=37.7749,
        longitude=-122.4194,
        bandwidth_khz=20000,
        earfcn=2100
    )


@pytest.fixture
def sample_satellite_tower():
    """
    Fixture providing a sample satellite 5G NR-NTN tower.
    
    Represents a satellite-based network like Starlink cellular.
    Use this for testing NTN classification and satellite features.
    """
    return CellTower(
        cell_id=987654321,
        tower_type="NON_TERRESTRIAL_SATELLITE",
        network_type="5G_NR_NTN",
        mcc=901,
        mnc=88,
        signal_strength=-105,
        signal_quality=-15,
        registered=False,
        detected_at=datetime(2026, 4, 5, 12, 0, 0),
        lac=None,
        tac=12345,
        pci=456,
        latitude=None,  # Satellite location changes, may not be available
        longitude=None,
        bandwidth_khz=40000
    )


@pytest.fixture
def sample_device_location():
    """
    Fixture providing a sample device location (San Francisco).
    
    Use this for testing geolocation features and distance calculations.
    """
    return DeviceLocation(
        latitude=37.7749,
        longitude=-122.4194,
        accuracy=10.0,
        timestamp=datetime(2026, 4, 5, 12, 0, 0),
        altitude=50.0,
        speed=0.0
    )


@pytest.fixture
def app():
    """
    Fixture providing a Flask app instance for testing.
    
    Creates a fresh app instance in testing mode with a
    separate configuration to avoid affecting real data.
    """
    from app import app as flask_app
    
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    return flask_app


@pytest.fixture
def client(app):
    """
    Fixture providing a Flask test client.
    
    Use this to make HTTP requests to your Flask routes
    in tests without running a real server.
    """
    return app.test_client()


@pytest.fixture
def mock_opencellid_response():
    """
    Fixture providing a mock OpenCellID API response.
    
    Use this to test tower location lookups without making
    real API calls (faster tests, no API key required).
    """
    return {
        'lat': 37.7749,
        'lon': -122.4194,
        'range': 500,  # accuracy in meters
        'samples': 100,
        'changeable': 1,
        'radio': 'LTE',
        'mcc': 310,
        'net': 260,
        'area': 45678,
        'cell': 12345678,
        'unit': 1
    }
