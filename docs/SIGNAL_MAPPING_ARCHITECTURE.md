# Signal Mapping Architecture

CellSeeU should treat the 3D scene as a measured signal field, not as a set of
guessed bearings from a single scan. A scan records where the device was, how it
was held, and which signals were detected there. Source positions are estimates
derived from many samples.

## Core Model

```text
Android sensors and radios
  -> signal samples
  -> Flask signal mapping service
  -> source estimates
  -> web and Android renderers
```

Each mapping sample uses one generic shape:

```json
{
  "session_id": "android-123",
  "device_pose": {
    "latitude": 53.3498,
    "longitude": -6.2603,
    "accuracy_m": 8,
    "heading": 240,
    "pitch": 3,
    "roll": -1
  },
  "signals": [
    {
      "type": "wifi",
      "source_id": "aa:bb:cc:dd:ee:ff",
      "label": "Kitchen AP",
      "strength_dbm": -52,
      "frequency_mhz": 2412,
      "channel": 1
    }
  ]
}
```

The same shape can later carry Bluetooth, cellular, and GNSS observations:

- `wifi`: BSSID, SSID, channel, frequency, RSSI
- `bluetooth`: device address/id, name, RSSI, tx power when available
- `cellular`: cell id, MCC/MNC, network type, RSRP/RSSI
- `gnss`: SVID/PRN, constellation, azimuth, elevation, C/N0

## Current Estimation

The first estimator is intentionally conservative: it groups samples by
`type + source_id` and uses a weighted centroid, where stronger readings pull
the estimate more than weaker readings. The source carries an explicit
`method` and `confidence`, so the UI can show estimates as likely areas rather
than pretending they are exact positions.

This is a good baseline for WiFi and Bluetooth walk mapping. GNSS should be
rendered differently: satellites belong on a sky dome using azimuth/elevation,
not as local floor-plan emitters.

## UI Direction

Avoid four cluttered dashboards. Prefer one primary exploration scene with
layer controls:

- WiFi sources and heat samples
- Bluetooth sources and nearby devices
- Cell towers and serving/neighbor cells
- GNSS sky dome

The UI should distinguish measured samples from estimated sources. A source
estimate should use confidence rings/clouds until enough data makes it reliable.
