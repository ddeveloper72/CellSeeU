"""
Signal mapping service for walk-and-scan source estimation.

This module stores movement samples from the scanner and estimates likely
emitter positions from repeated signal observations. It is deliberately signal
type agnostic so WiFi, Bluetooth, cellular, and GNSS metadata can share the same
collection and rendering pipeline.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import cos, radians, sqrt
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4


ALLOWED_SIGNAL_TYPES = {'wifi', 'bluetooth', 'cellular', 'gnss', 'unknown'}


@dataclass
class SignalMappingService:
    """In-memory walk-and-scan mapping state."""

    max_samples: int = 1000
    samples: List[Dict[str, Any]] = field(default_factory=list)
    active_session_id: str = field(default_factory=lambda: f"session-{uuid4().hex[:12]}")

    def reset(self) -> None:
        """Clear all collected mapping samples and start a fresh session id."""
        self.samples = []
        self.active_session_id = f"session-{uuid4().hex[:12]}"

    def start_session(self, label: Optional[str] = None) -> Dict[str, Any]:
        """Start a fresh mapping session."""
        prefix = label.strip().lower().replace(' ', '-') if label else 'session'
        self.active_session_id = f"{prefix}-{uuid4().hex[:12]}"
        self.samples = []
        return {
            'session_id': self.active_session_id,
            'sample_count': 0,
            'started_at': datetime.now(timezone.utc).isoformat()
        }

    def add_sample(self, payload: Dict[str, Any], timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """Validate and store a generic mapping sample."""
        sample = self._normalise_sample(payload, timestamp)
        self.samples.append(sample)
        if len(self.samples) > self.max_samples:
            self.samples.pop(0)
        return sample

    def add_android_snapshot(self, payload: Dict[str, Any], timestamp: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Convert the existing Android scanner upload into a mapping sample."""
        device_location = payload.get('device_location') or {}
        signals = []

        for network in payload.get('wifi_networks') or []:
            source_id = network.get('bssid')
            if not source_id:
                continue
            signals.append({
                'type': 'wifi',
                'source_id': source_id,
                'label': network.get('ssid') or '<Hidden Network>',
                'strength_dbm': network.get('signal_strength'),
                'frequency_mhz': network.get('frequency'),
                'channel': network.get('channel'),
                'security': network.get('security'),
                'is_connected': network.get('is_connected', False)
            })

        for tower in payload.get('towers') or []:
            source_id = tower.get('cell_id')
            if source_id is None:
                continue
            signals.append({
                'type': 'cellular',
                'source_id': str(source_id),
                'label': tower.get('carrier') or tower.get('network_type') or 'Cell tower',
                'strength_dbm': tower.get('signal_strength'),
                'network_type': tower.get('network_type'),
                'mcc': tower.get('mcc'),
                'mnc': tower.get('mnc'),
                'registered': tower.get('registered', False)
            })

        if not signals:
            return None

        return self.add_sample({
            'session_id': payload.get('mapping_session_id') or self.active_session_id,
            'device_pose': {
                'latitude': device_location.get('latitude'),
                'longitude': device_location.get('longitude'),
                'altitude': device_location.get('altitude'),
                'accuracy_m': device_location.get('accuracy'),
                'heading': device_location.get('heading'),
                'pitch': device_location.get('pitch'),
                'roll': device_location.get('roll'),
                'cardinal_direction': device_location.get('cardinal_direction')
            },
            'signals': signals
        }, timestamp)

    def estimate_sources(
        self,
        signal_type: Optional[str] = None,
        min_samples: int = 2,
        min_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """Estimate source positions from collected samples."""
        grouped = defaultdict(list)
        for sample in self.samples:
            pose = sample.get('device_pose') or {}
            if not self._has_position(pose):
                continue

            for signal in sample.get('signals') or []:
                current_type = signal.get('type', 'unknown')
                if signal_type and current_type != signal_type:
                    continue
                source_id = signal.get('source_id')
                if not source_id:
                    continue
                grouped[(current_type, source_id)].append({
                    'timestamp': sample.get('timestamp'),
                    'pose': pose,
                    'signal': signal
                })

        estimates = []
        for (current_type, source_id), observations in grouped.items():
            if len(observations) < min_samples:
                continue
            estimate = self._estimate_source(current_type, source_id, observations)
            if estimate and estimate['confidence'] >= min_confidence:
                estimates.append(estimate)

        estimates.sort(key=lambda item: (item['type'], -item['confidence'], item['label']))
        return {
            'session_id': self.active_session_id,
            'sources': estimates,
            'count': len(estimates),
            'sample_count': len(self.samples),
            'min_samples': min_samples,
            'min_confidence': min_confidence
        }

    def _normalise_sample(self, payload: Dict[str, Any], timestamp: Optional[datetime]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError('Sample payload must be an object')

        pose = payload.get('device_pose') or payload.get('device_location') or {}
        if not isinstance(pose, dict):
            raise ValueError('device_pose must be an object')

        signals = payload.get('signals')
        if not isinstance(signals, list):
            raise ValueError('signals must be an array')

        normalised_signals = [self._normalise_signal(signal) for signal in signals]
        if not normalised_signals:
            raise ValueError('signals must contain at least one source reading')

        sample_time = timestamp or datetime.now(timezone.utc)
        return {
            'session_id': payload.get('session_id') or self.active_session_id,
            'timestamp': sample_time.isoformat(),
            'device_pose': self._normalise_pose(pose),
            'signals': normalised_signals
        }

    def _normalise_pose(self, pose: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'latitude': self._optional_float(pose.get('latitude')),
            'longitude': self._optional_float(pose.get('longitude')),
            'altitude': self._optional_float(pose.get('altitude')),
            'accuracy_m': self._optional_float(pose.get('accuracy_m', pose.get('accuracy'))),
            'heading': self._optional_float(pose.get('heading')),
            'pitch': self._optional_float(pose.get('pitch')),
            'roll': self._optional_float(pose.get('roll')),
            'cardinal_direction': pose.get('cardinal_direction')
        }

    def _normalise_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(signal, dict):
            raise ValueError('Each signal must be an object')

        signal_type = signal.get('type', 'unknown')
        if signal_type not in ALLOWED_SIGNAL_TYPES:
            raise ValueError(f'Unsupported signal type: {signal_type}')

        source_id = signal.get('source_id') or signal.get('bssid') or signal.get('id')
        if not source_id:
            raise ValueError('Each signal needs source_id')

        normalised = {
            'type': signal_type,
            'source_id': str(source_id),
            'label': signal.get('label') or signal.get('ssid') or str(source_id),
            'strength_dbm': self._optional_float(signal.get('strength_dbm', signal.get('signal_strength'))),
            'frequency_mhz': self._optional_float(signal.get('frequency_mhz', signal.get('frequency'))),
            'channel': signal.get('channel'),
        }

        for key, value in signal.items():
            if key not in normalised and key not in {'signal_strength', 'frequency', 'bssid', 'id', 'ssid'}:
                normalised[key] = value

        return normalised

    def _estimate_source(
        self,
        signal_type: str,
        source_id: str,
        observations: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        weighted_lat = 0.0
        weighted_lon = 0.0
        total_weight = 0.0
        strongest = None
        last_seen = None
        positions = []
        pose_accuracies = []

        for observation in observations:
            pose = observation['pose']
            signal = observation['signal']
            strength = signal.get('strength_dbm')
            weight = self._signal_weight(strength)

            weighted_lat += pose['latitude'] * weight
            weighted_lon += pose['longitude'] * weight
            total_weight += weight
            positions.append((pose['latitude'], pose['longitude']))
            if pose.get('accuracy_m') is not None:
                pose_accuracies.append(float(pose['accuracy_m']))

            if strongest is None or self._strength_value(strength) > self._strength_value(strongest['signal'].get('strength_dbm')):
                strongest = observation
            last_seen = observation.get('timestamp') or last_seen

        if total_weight == 0 or not strongest:
            return None

        latitude = weighted_lat / total_weight
        longitude = weighted_lon / total_weight
        position_spread_m = self._position_spread_m(latitude, longitude, positions)
        mean_pose_accuracy_m = (
            sum(pose_accuracies) / len(pose_accuracies)
            if pose_accuracies else 0.0
        )
        accuracy_m = max(position_spread_m, mean_pose_accuracy_m)
        confidence = self._confidence(len(observations), accuracy_m)
        strongest_signal = strongest['signal']

        return {
            'type': signal_type,
            'source_id': source_id,
            'label': strongest_signal.get('label') or source_id,
            'latitude': round(latitude, 7),
            'longitude': round(longitude, 7),
            'confidence': round(confidence, 2),
            'accuracy_m': round(accuracy_m, 1),
            'position_spread_m': round(position_spread_m, 1),
            'mean_pose_accuracy_m': round(mean_pose_accuracy_m, 1),
            'sample_count': len(observations),
            'strongest_strength_dbm': strongest_signal.get('strength_dbm'),
            'last_seen': last_seen,
            'method': 'weighted_signal_centroid'
        }

    def _signal_weight(self, strength: Optional[float]) -> float:
        if strength is None:
            return 1.0
        return max(1.0, 120.0 + float(strength))

    def _strength_value(self, strength: Optional[float]) -> float:
        return float(strength) if strength is not None else -999.0

    def _confidence(self, sample_count: int, accuracy_m: float) -> float:
        sample_score = min(1.0, sample_count / 8.0)
        spread_score = max(0.0, min(1.0, 1.0 - (accuracy_m / 80.0)))
        return max(0.0, min(1.0, 0.35 * sample_score + 0.65 * spread_score))

    def _position_spread_m(
        self,
        latitude: float,
        longitude: float,
        positions: Iterable[tuple[float, float]],
    ) -> float:
        distances = [
            self._distance_m(latitude, longitude, sample_lat, sample_lon)
            for sample_lat, sample_lon in positions
        ]
        if not distances:
            return 0.0
        return sqrt(sum(distance * distance for distance in distances) / len(distances))

    def _distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        meters_per_lat = 111_320.0
        meters_per_lon = meters_per_lat * cos(radians((lat1 + lat2) / 2.0))
        dx = (lon2 - lon1) * meters_per_lon
        dy = (lat2 - lat1) * meters_per_lat
        return sqrt(dx * dx + dy * dy)

    def _has_position(self, pose: Dict[str, Any]) -> bool:
        return pose.get('latitude') is not None and pose.get('longitude') is not None

    def _optional_float(self, value: Any) -> Optional[float]:
        if value in (None, ''):
            return None
        return float(value)


signal_mapping_service = SignalMappingService()
