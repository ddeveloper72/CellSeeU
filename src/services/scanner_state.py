"""
In-memory scanner state for CellSeeU.

The Android scanner uploads cell, WiFi, location, and orientation data as one
snapshot. This service keeps that latest scanner state in one place so Flask
routes, dashboard views, and 3D views do not each maintain their own globals.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def calculate_signal_bars(dbm: Optional[int]) -> int:
    """Convert signal strength in dBm into a 0-5 bar display value."""
    if dbm is None:
        return 0
    if dbm >= -85:
        return 5
    if dbm >= -95:
        return 4
    if dbm >= -105:
        return 3
    if dbm >= -115:
        return 2
    if dbm >= -125:
        return 1
    return 0


def development_towers() -> List[Dict[str, Any]]:
    """Return sample Ireland tower data used before scanner uploads arrive."""
    now = datetime.now(timezone.utc).isoformat()
    return [
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
            'detected_at': now
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
            'detected_at': now
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
            'detected_at': now
        }
    ]


@dataclass
class ScannerState:
    """Stores the latest Android scanner snapshot in memory."""

    max_scan_history: int = 100
    towers: List[Dict[str, Any]] = field(default_factory=list)
    device_location: Optional[Dict[str, Any]] = None
    last_update_time: Optional[datetime] = None
    wifi_networks: List[Dict[str, Any]] = field(default_factory=list)
    wifi_connected: Optional[Dict[str, Any]] = None
    wifi_last_update: Optional[datetime] = None
    wifi_scan_history: List[Dict[str, Any]] = field(default_factory=list)

    def reset(self) -> None:
        """Clear all scanner payload data."""
        self.towers = []
        self.device_location = None
        self.last_update_time = None
        self.wifi_networks = []
        self.wifi_connected = None
        self.wifi_last_update = None
        self.wifi_scan_history = []

    @property
    def has_real_towers(self) -> bool:
        return bool(self.towers)

    @property
    def tower_data_source(self) -> str:
        return 'real' if self.has_real_towers else 'mock'

    def current_towers(self) -> List[Dict[str, Any]]:
        """Return uploaded tower data when present, otherwise sample data."""
        return self.towers.copy() if self.towers else development_towers()

    def replace_towers(
        self,
        towers: List[Dict[str, Any]],
        device_location: Optional[Dict[str, Any]],
        updated_at: Optional[datetime] = None,
    ) -> None:
        """Store the latest enriched tower list and device location."""
        self.towers = towers.copy()
        self.device_location = device_location
        self.last_update_time = updated_at or datetime.now(timezone.utc)

    def replace_wifi(
        self,
        networks: List[Dict[str, Any]],
        connected: Optional[Dict[str, Any]],
        device_location: Optional[Dict[str, Any]],
        updated_at: Optional[datetime] = None,
    ) -> None:
        """Store the latest WiFi scan and optional scan-history record."""
        self.wifi_networks = networks.copy()
        self.wifi_connected = connected
        self.wifi_last_update = updated_at or datetime.now(timezone.utc)
        self._append_wifi_history_if_possible(device_location, self.wifi_last_update)

    def _append_wifi_history_if_possible(
        self,
        device_location: Optional[Dict[str, Any]],
        timestamp: datetime,
    ) -> None:
        if not device_location:
            return
        if 'latitude' not in device_location or 'heading' not in device_location:
            return

        scan_record = {
            'timestamp': timestamp.isoformat(),
            'location': {
                'latitude': device_location.get('latitude'),
                'longitude': device_location.get('longitude'),
                'accuracy': device_location.get('accuracy')
            },
            'orientation': {
                'heading': device_location.get('heading'),
                'pitch': device_location.get('pitch'),
                'roll': device_location.get('roll'),
                'cardinal_direction': device_location.get('cardinal_direction')
            },
            'networks': self.wifi_networks.copy()
        }

        self.wifi_scan_history.append(scan_record)
        if len(self.wifi_scan_history) > self.max_scan_history:
            self.wifi_scan_history.pop(0)

    def latest_wifi_history_record(self) -> Optional[Dict[str, Any]]:
        """Return the most recent WiFi scan-history record."""
        return self.wifi_scan_history[-1] if self.wifi_scan_history else None

    def latest_wifi_history_record_with_networks(self) -> Optional[Dict[str, Any]]:
        """Return the most recent WiFi scan-history record with networks."""
        return next(
            (
                record for record in reversed(self.wifi_scan_history)
                if record.get('networks')
            ),
            None
        )

    def wireless_snapshot(self) -> Dict[str, Any]:
        """
        Build one canonical wireless state payload for dashboard and 3D views.
        """
        history_record = self.latest_wifi_history_record()
        network_history_record = self.latest_wifi_history_record_with_networks()
        networks = self.wifi_networks.copy()
        data_source = 'real' if self.wifi_networks else 'none'

        if not networks and network_history_record:
            networks = network_history_record.get('networks', []).copy()
            data_source = 'history' if networks else data_source

        device_location = self.device_location
        if not device_location and history_record:
            location = history_record.get('location') or {}
            orientation = history_record.get('orientation') or {}
            device_location = {**location, **orientation}

        return {
            'networks': networks,
            'connected': self.wifi_connected,
            'device_location': device_location,
            'last_update': self.wifi_last_update.isoformat() if self.wifi_last_update else None,
            'scan_history_size': len(self.wifi_scan_history),
            'data_source': data_source
        }


scanner_state = ScannerState()
