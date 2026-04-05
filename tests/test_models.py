"""
Unit tests for CellTower and DeviceLocation models

Tests data model behavior, properties, and serialization.
"""

import pytest
from datetime import datetime
from src.models.tower import CellTower, DeviceLocation


class TestCellTowerModel:
    """Test suite for CellTower data model"""
    
    def test_create_terrestrial_lte_tower(self):
        """
        Verify we can create a basic terrestrial LTE tower.
        
        This is the most common use case - a standard cell tower
        with all required fields populated.
        """
        tower = CellTower(
            cell_id=12345678,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-85,
            registered=True,
            detected_at=datetime.now()
        )
        
        assert tower.cell_id == 12345678
        assert tower.tower_type == "TERRESTRIAL"
        assert tower.network_type == "LTE"
        assert tower.mcc == 310
        assert tower.mnc == 260
        assert tower.signal_strength == -85
        assert tower.registered is True
        assert not tower.is_satellite
    
    def test_create_satellite_5g_ntn_tower(self):
        """
        Verify we can create a non-terrestrial (satellite) 5G NR-NTN tower.
        
        Satellite towers are the key differentiator for this app.
        They use different PLMN codes and have NTN capability.
        """
        tower = CellTower(
            cell_id=987654321,
            tower_type="NON_TERRESTRIAL_SATELLITE",
            network_type="5G_NR_NTN",
            mcc=901,  # Example satellite PLMN
            mnc=88,
            signal_strength=-105,
            registered=False,
            detected_at=datetime.now()
        )
        
        assert tower.tower_type == "NON_TERRESTRIAL_SATELLITE"
        assert tower.network_type == "5G_NR_NTN"
        assert tower.is_satellite is True
    
    def test_operator_code_property(self):
        """
        Verify PLMN operator code formatting.
        
        Operator codes should be formatted as MCC-MNC for display
        and lookup in carrier databases.
        """
        tower = CellTower(
            cell_id=123,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-90,
            registered=True,
            detected_at=datetime.now()
        )
        
        assert tower.operator_code == "310-260"
    
    def test_signal_bars_excellent(self):
        """
        Verify signal strength converts to 5 bars for excellent signal.
        
        Signal >= -85 dBm should show as full bars (5/5).
        """
        tower = CellTower(
            cell_id=123,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-80,  # Excellent
            registered=True,
            detected_at=datetime.now()
        )
        
        assert tower.signal_bars == 5
    
    def test_signal_bars_good(self):
        """Verify -90 dBm shows as 4 bars (good signal)"""
        tower = CellTower(
            cell_id=123,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-90,
            registered=True,
            detected_at=datetime.now()
        )
        
        assert tower.signal_bars == 4
    
    def test_signal_bars_fair(self):
        """Verify -100 dBm shows as 3 bars (fair signal)"""
        tower = CellTower(
            cell_id=123,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-100,
            registered=True,
            detected_at=datetime.now()
        )
        
        assert tower.signal_bars == 3
    
    def test_signal_bars_poor(self):
        """Verify -110 dBm shows as 2 bars (poor signal)"""
        tower = CellTower(
            cell_id=123,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-110,
            registered=True,
            detected_at=datetime.now()
        )
        
        assert tower.signal_bars == 2
    
    def test_signal_bars_very_poor(self):
        """Verify -120 dBm shows as 1 bar (very poor signal)"""
        tower = CellTower(
            cell_id=123,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-120,
            registered=True,
            detected_at=datetime.now()
        )
        
        assert tower.signal_bars == 1
    
    def test_signal_bars_no_signal(self):
        """Verify very weak signal shows as 0 bars"""
        tower = CellTower(
            cell_id=123,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-130,  # Extremely weak
            registered=False,
            detected_at=datetime.now()
        )
        
        assert tower.signal_bars == 0
    
    def test_to_dict_serialization(self):
        """
        Verify tower data can be serialized to dictionary for JSON API.
        
        This is critical for the Flask API endpoints - we need to
        convert tower objects to JSON for transmission to frontend.
        """
        timestamp = datetime(2026, 4, 5, 12, 30, 0)
        tower = CellTower(
            cell_id=12345,
            tower_type="TERRESTRIAL",
            network_type="LTE",
            mcc=310,
            mnc=260,
            signal_strength=-90,
            registered=True,
            detected_at=timestamp,
            lac=456,
            tac=789,
            pci=123,
            latitude=37.7749,
            longitude=-122.4194
        )
        
        data = tower.to_dict()
        
        assert data['cell_id'] == 12345
        assert data['tower_type'] == "TERRESTRIAL"
        assert data['network_type'] == "LTE"
        assert data['mcc'] == 310
        assert data['mnc'] == 260
        assert data['signal_strength'] == -90
        assert data['registered'] is True
        assert data['lac'] == 456
        assert data['tac'] == 789
        assert data['pci'] == 123
        assert data['latitude'] == 37.7749
        assert data['longitude'] == -122.4194
        assert data['detected_at'] == timestamp.isoformat()


class TestDeviceLocationModel:
    """Test suite for DeviceLocation data model"""
    
    def test_create_basic_location(self):
        """
        Verify we can create a basic device location with GPS coordinates.
        
        This is the minimum required data for showing device position
        on the map.
        """
        timestamp = datetime.now()
        location = DeviceLocation(
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=10.0,
            timestamp=timestamp
        )
        
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194
        assert location.accuracy == 10.0
        assert location.timestamp == timestamp
        assert location.altitude is None
        assert location.speed is None
    
    def test_create_location_with_altitude_and_speed(self):
        """
        Verify location can include optional altitude and speed data.
        
        When available from GPS, altitude and speed provide additional
        context for network analysis (e.g., airplane mode, vehicle movement).
        """
        timestamp = datetime.now()
        location = DeviceLocation(
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=5.0,
            timestamp=timestamp,
            altitude=150.5,  # meters above sea level
            speed=15.0       # m/s (about 54 km/h)
        )
        
        assert location.altitude == 150.5
        assert location.speed == 15.0
    
    def test_to_dict_serialization(self):
        """
        Verify location can be serialized for JSON API.
        
        Frontend needs location data to center the map and show
        the device's current position.
        """
        timestamp = datetime(2026, 4, 5, 14, 30, 0)
        location = DeviceLocation(
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=8.0,
            timestamp=timestamp,
            altitude=100.0,
            speed=10.0
        )
        
        data = location.to_dict()
        
        assert data['latitude'] == 37.7749
        assert data['longitude'] == -122.4194
        assert data['accuracy'] == 8.0
        assert data['altitude'] == 100.0
        assert data['speed'] == 10.0
        assert data['timestamp'] == timestamp.isoformat()
