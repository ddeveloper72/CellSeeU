"""
Data model for cell tower information

Represents a cell tower with all relevant information including
location, signal strength, and network type classification.
"""

from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime


# Type aliases for clarity
TowerType = Literal["TERRESTRIAL", "NON_TERRESTRIAL_SATELLITE"]
NetworkType = Literal["GSM", "UMTS", "LTE", "5G_NR", "5G_NR_NTN"]


@dataclass
class CellTower:
    """
    Represents a detected cell tower with its characteristics.
    
    This model captures all relevant information about a cell tower
    including its identity, location, signal strength, and whether
    it's a terrestrial or satellite-based network.
    
    Attributes:
        cell_id: Unique cell identifier (CID)
        tower_type: Either TERRESTRIAL or NON_TERRESTRIAL_SATELLITE
        network_type: Technology type (GSM, LTE, 5G_NR, etc.)
        mcc: Mobile Country Code
        mnc: Mobile Network Code
        lac: Location Area Code (for GSM/UMTS)
        tac: Tracking Area Code (for LTE/5G)
        pci: Physical Cell ID (for LTE)
        signal_strength: Signal strength in dBm
        signal_quality: Signal quality in dB (RSRQ for LTE, RSSI for others)
        registered: Whether device is currently connected to this tower
        latitude: Tower latitude (if known from OpenCellID)
        longitude: Tower longitude (if known from OpenCellID)
        distance_meters: Distance from device to tower
        bandwidth_khz: Channel bandwidth in kHz
        earfcn: E-UTRA Absolute Radio Frequency Channel Number (LTE)
        detected_at: Timestamp when tower was detected
    """
    
    cell_id: int
    tower_type: TowerType
    network_type: NetworkType
    mcc: int
    mnc: int
    signal_strength: int  # dBm
    registered: bool
    detected_at: datetime
    
    # Optional fields
    lac: Optional[int] = None
    tac: Optional[int] = None
    pci: Optional[int] = None
    signal_quality: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_meters: Optional[float] = None
    bandwidth_khz: Optional[int] = None
    earfcn: Optional[int] = None
    
    def to_dict(self) -> dict:
        """
        Convert tower data to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation with all non-None fields
        """
        return {
            'cell_id': self.cell_id,
            'tower_type': self.tower_type,
            'network_type': self.network_type,
            'mcc': self.mcc,
            'mnc': self.mnc,
            'signal_strength': self.signal_strength,
            'signal_quality': self.signal_quality,
            'registered': self.registered,
            'lac': self.lac,
            'tac': self.tac,
            'pci': self.pci,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'distance_meters': self.distance_meters,
            'bandwidth_khz': self.bandwidth_khz,
            'earfcn': self.earfcn,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None
        }
    
    @property
    def operator_code(self) -> str:
        """
        Get the PLMN (Public Land Mobile Network) code.
        
        Format: MCC-MNC (e.g., "310-260" for T-Mobile USA)
        
        Returns:
            Formatted PLMN code string
        """
        return f"{self.mcc}-{self.mnc}"
    
    @property
    def signal_bars(self) -> int:
        """
        Convert signal strength to familiar 0-5 bar representation.
        
        Uses standard signal strength thresholds for LTE:
        - 5 bars: >= -85 dBm (Excellent)
        - 4 bars: -85 to -95 dBm (Good)
        - 3 bars: -95 to -105 dBm (Fair)
        - 2 bars: -105 to -115 dBm (Poor)
        - 1 bar: < -115 dBm (Very Poor)
        - 0 bars: No signal
        
        Returns:
            Integer from 0-5 representing signal strength
        """
        if self.signal_strength >= -85:
            return 5
        elif self.signal_strength >= -95:
            return 4
        elif self.signal_strength >= -105:
            return 3
        elif self.signal_strength >= -115:
            return 2
        elif self.signal_strength >= -125:
            return 1
        else:
            return 0
    
    @property
    def is_satellite(self) -> bool:
        """
        Check if this tower is a satellite/non-terrestrial network.
        
        Returns:
            True if NON_TERRESTRIAL_SATELLITE, False otherwise
        """
        return self.tower_type == "NON_TERRESTRIAL_SATELLITE"


@dataclass
class DeviceLocation:
    """
    Represents the device's current geographic location.
    
    Attributes:
        latitude: Device latitude in decimal degrees
        longitude: Device longitude in decimal degrees
        accuracy: Location accuracy in meters
        altitude: Altitude above sea level in meters (optional)
        speed: Movement speed in m/s (optional)
        timestamp: When location was obtained
    """
    
    latitude: float
    longitude: float
    accuracy: float
    timestamp: datetime
    altitude: Optional[float] = None
    speed: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'altitude': self.altitude,
            'speed': self.speed,
            'timestamp': self.timestamp.isoformat()
        }
