# CellSeeU - Privacy Awareness Dashboard

**Complete cellular, WiFi, and wireless tracking detection system**

Track what services can see your device in real-time using IMEI detection, WiFi signal mapping, and scanner location/orientation samples.

---

## What Does This Do?

**CellSeeU** shows you which services are tracking your phone by detecting:
- **Cell towers** that can see your IMEI number
- **WiFi networks** that can detect your MAC address and probe requests
- **Estimated WiFi router locations** using repeated signal samples

### Key Privacy Features:
1. **IMEI Detection Radius** - Visual circle showing which towers can track you
2. **WiFi MAC Tracking** - Shows which networks detect your WiFi probe requests
3. **WiFi Signal Mapping** - Estimates likely router positions using GPS + signal strength samples
4. **Real-time Dashboard** - Live updates as you move around

---

## System Architecture

```
Android App (Scanner)        Backend (Flask)         Frontend (Dashboard)
├─ CellTowerScanner.java  →  /api/towers/upload  →  Dashboard Tab
├─ WiFiScanner.java       →  /api/wifi           →  WiFi Tab
├─ OrientationSensor.java →  /api/signal-mapping/sources →  Map View
└─ GPS Location              (Source estimates)    (WiFi source markers)
```

---

## Quick Start

### 1. Start Backend Server

```powershell
cd C:\Users\Duncan\Visual_Studio_Projects\cell_see_u

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run Flask server
python app.py
```

Server runs at: `http://192.168.0.67:5000`

### 2. Build Android App

```powershell
cd android_scanner

# Build APK
.\gradlew assembleDebug

# APK location:
# android_scanner\app\build\outputs\apk\debug\app-debug.apk
```

### 3. Install & Scan

1. Transfer APK to phone
2. Install app (enable "Unknown Sources")
3. Grant permissions:
   - Location (GPS)
   - Phone State (IMEI)
   - WiFi State
4. Tap "Start Scanning"
5. Walk around to collect orientation data

### 4. View Dashboard

Navigate to: `http://192.168.0.67:5000`

Tabs:
- **Dashboard** - Stats and tower list
- **Map** - Cell towers + WiFi source estimates + detection radius
- **WiFi** - Network list + estimated source positions

---

## WiFi Signal Mapping (How It Works)

### The Model:
Each Android upload becomes a measured signal sample: where the device was,
how accurate the location was, how the device was held, and which WiFi sources
were seen there.

Samples are grouped by `type + source_id`. Stronger readings pull the source
estimate more than weaker readings, and each estimate reports confidence,
accuracy, sample count, and method metadata.

### Accuracy:
- **2 samples**: low-confidence baseline
- **3-5 samples**: useful rough estimate
- **8+ samples**: better confidence if samples are spatially useful

Factors affecting accuracy:
- WiFi reflections (multipath)
- Walls and obstacles
- GPS accuracy and sample spread
---

## Current Features

### Implemented:

**Android App:**
- Cell tower scanning (IMEI, signal, carrier)
- WiFi network scanning (SSID, BSSID, signal, security)
- Orientation sensors (compass heading, pitch, roll)
- GPS location tracking
- Combined data upload to server

**Backend (Flask + Python):**
- Tower data storage and enrichment
- OpenCelliD integration for tower locations
- WiFi scan history storage (100 scans max)
- WiFi signal mapping service (signal_mapping.py)
- API endpoints:
  - `/api/towers` - Get detected towers
  - `/api/towers/upload` - Upload scan data
  - `/api/towers/nearby` - Get OpenCelliD towers in viewport
  - `/api/wifi` - Get WiFi networks
  - `/api/signal-mapping/sources` - Get estimated signal source positions

**Frontend (HTML + JavaScript + Leaflet):**
- Interactive map with cell towers
- IMEI detection radius visualization
- Tracking panel showing services detecting device
- WiFi network list with security and signal info
- WiFi source estimate markers on map
- WiFi source confidence indicators (color-coded)
- Real-time auto-refresh

---

## API Endpoints

### GET /api/towers
Returns detected cell towers from Android app.

**Response:**
```json
{
  "towers": [
    {
      "cell_id": 12345,
      "carrier": "Three Ireland",
      "signal_strength": -72,
      "network_type": "LTE",
      "latitude": 53.2919,
      "longitude": -6.6860,
      "registered": true
    }
  ],
  "device_location": {"latitude": 53.2919, "longitude": -6.6860},
  "count": 1
}
```

### POST /api/towers/upload
Upload scan data from Android app.

**Request Body:**
```json
{
  "towers": [...],
  "wifi_networks": [...],
  "wifi_connected": {...},
  "device_location": {
    "latitude": 53.2919,
    "longitude": -6.6860,
    "heading": 287.5,
    "pitch": 12.3,
    "roll": -5.2
  }
}
```

### GET /api/wifi
Returns WiFi networks from last scan.

### GET /api/signal-mapping/sources
Returns estimated WiFi source positions from generic signal-mapping samples.

**Query Params:**
- `type` (`wifi`, `bluetooth`, `cellular`, `gnss`, `unknown`, or `all`)
- `min_confidence` (0-1, default 0.3)
- `min_samples` (default 2)

**Response:**
```json
{
  "sources": [
    {
      "type": "wifi",
      "source_id": "aa:bb:cc:dd:ee:ff",
      "label": "MyWiFi",
      "latitude": 53.2925,
      "longitude": -6.6863,
      "confidence": 0.75,
      "sample_count": 5,
      "accuracy_m": 25,
      "method": "weighted_signal_centroid"
    }
  ],
  "count": 1,
  "sample_count": 12
}
```

---

## File Structure

```
cell_see_u/
├── android_scanner/                 # Android app
│   └── app/src/main/java/com/cellseeu/scanner/
│       ├── MainActivity.java        # Main app, coordinates scanning
│       ├── CellTowerScanner.java    # Cell tower detection
│       ├── WiFiScanner.java         # WiFi network scanning
│       ├── OrientationSensor.java   # Compass + accelerometer
│       ├── ApiClient.java           # HTTP upload to server
│       └── ServerConfig.java        # Server URL config
│
├── src/
│   ├── dashboard/
│   │   └── routes.py                # Flask API endpoints
│   └── services/
│       ├── carrier_lookup.py        # MCC/MNC to carrier name
│       ├── tower_location.py        # OpenCelliD integration
│       └── signal_mapping.py         # Generic signal source estimates
│
├── templates/
│   ├── base.html                    # Base template with navigation
│   ├── dashboard.html               # Main dashboard page
│   ├── map.html                     # Full-screen map
│   └── wifi.html                    # WiFi network detection page
│
├── static/
│   ├── js/
│   │   └── scripts.js               # Frontend JavaScript
│   └── css/
│       └── styles.css               # Dashboard styling
│
├── app.py                           # Flask app entry point
├── requirements.txt                 # Python dependencies
└── .env                             # Configuration (SERVER_IP, etc.)
```

---

## Configuration

### Backend (.env)
```bash
FLASK_APP=app.py
FLASK_ENV=development
SERVER_IP=192.168.0.67
PORT=5000
DEBUG=true
OPENCELLID_API_KEY=pk.your_key_here
REFRESH_INTERVAL_SECONDS=10
```

### Android (ServerConfig.java)
```java
public class ServerConfig {
    public static final String SERVER_URL = "http://192.168.0.67:5000";
}
```

---


## Next Steps (Future Enhancements)

### Priority 1: Complete WiFi Visualization
- [x] Add WiFi source markers to map - **DONE**
- [x] Show estimated positions on WiFi page - **DONE**
- [ ] Add "View on Map" links from WiFi page
- [ ] Toggle WiFi source layer on/off on map

### Priority 2: Improve Triangulation
- [ ] Weighted average by signal confidence
- [ ] Outlier detection (remove bad scans)
- [ ] Multi-scan path visualization
- [ ] Show scan points on map with direction arrows

### Priority 3: Bluetooth Detection
- [ ] Create BluetoothScanner.java
- [ ] Scan for BLE and Classic devices
- [ ] Detect tracking beacons (AirTags, Tiles)
- [ ] "You're being followed" alerts
- [ ] /bluetooth page with tracker list

### Priority 4: Advanced Features
- [ ] WiFi signal heatmaps (signal strength overlay)
- [ ] 3D visualization (WiFi signal bubbles)
- [ ] Historical data storage (SQLite/PostgreSQL)
- [ ] Multi-device comparison
- [ ] Export data (CSV, JSON, KML)
- [ ] Privacy score calculation

---

## Known Issues

1. **Android 9+ WiFi Throttling**: `startScan()` throttled to 4 scans per 2 minutes
   - Workaround: Use cached scan results
   
2. **Single Tower Detection**: Most phones only report connected tower
   - Limitation: Android/carrier restriction
   - Solution: Use OpenCelliD for nearby towers

3. **Compass Accuracy**: Can drift indoors or near metal
   - Workaround: Calibrate compass (figure-8 motion)
   - Best results: Outdoors with clear sky view

4. **WiFi Multipath**: Signal reflections affect distance estimation
   - Impact: ±20-50m accuracy error
   - Mitigation: Multiple scans from different angles

---

## Privacy & Security

### Data Handling:
- **NO cloud storage** - All data stored in memory
- **NO external uploads** - Data stays on your local network
- **NO tracking** - App doesn't send your location anywhere
- **LOCAL ONLY** - Server only accepts connections from your WiFi

### Permissions Required:
- **ACCESS_FINE_LOCATION** - GPS for signal mapping
- **READ_PHONE_STATE** - Read IMEI and cell info
- **ACCESS_WIFI_STATE** - Scan WiFi networks
- **CHANGE_WIFI_STATE** - Trigger WiFi scans

**Note**: This app exists to SHOW you what others can track, not to track you!

---

## Troubleshooting

### Server won't start:
```powershell
# Check if port 5000 is in use
netstat -ano | findstr :5000

# Kill process if needed
taskkill /PID <process_id> /F

# Restart server
python app.py
```

### Android app can't connect:
1. Check phone and PC on same WiFi
2. Verify server IP in ServerConfig.java
3. Check Windows Firewall (allow port 5000)
4. Try from browser: `http://192.168.0.67:5000`

### No WiFi positions showing:
1. Need at least 2 scans from different locations
2. Device must have orientation data (heading)
3. Check `/api/signal-mapping/sources` in browser
4. Walk 20-30m between scans for better source estimates

### Compass not working:
1. Calibrate: Wave phone in figure-8 pattern
2. Move away from metal objects
3. Check sensor availability in logs

---

## Technical References

### WiFi Positioning:
- [Free Space Path Loss (FSPL)](https://en.wikipedia.org/wiki/Free-space_path_loss)
- [Haversine Formula](https://en.wikipedia.org/wiki/Haversine_formula)
- [WiFi Indoor Positioning](https://en.wikipedia.org/wiki/Indoor_positioning_system)

### Android APIs:
- [TelephonyManager](https://developer.android.com/reference/android/telephony/TelephonyManager)
- [WifiManager](https://developer.android.com/reference/android/net/wifi/WifiManager)
- [SensorManager](https://developer.android.com/reference/android/hardware/SensorManager)

### External Services:
- [OpenCelliD](https://opencellid.org/) - Cell tower database
- [WiGLE](https://wigle.net/) - WiFi AP database (not yet integrated)

---

## Learning Journey

This project is a **collaborative learning experience** between Duncan (user) and AI (developer).

**What we've built together:**
- Real-time privacy awareness tool
- Advanced sensor fusion (GPS + Compass + WiFi)
- Geospatial signal mapping and distance calculation
- Full-stack application (Android + Flask + JavaScript)
- Interactive data visualization (Leaflet maps)

**Technologies learned:**
- Android Java development
- Flask backend API development
- Geolocation and sensor APIs
- Signal propagation physics
- Frontend map rendering
- Git version control

---

## Getting Back Into It

**When you return:**

1. **Pull latest code** (if using Git remote):
   ```bash
   git pull origin master
   ```

2. **Start backend**:
   ```powershell
   cd C:\Users\Duncan\Visual_Studio_Projects\cell_see_u
   .\.venv\Scripts\Activate.ps1
   python app.py
   ```

3. **Open dashboard**:
   - Navigate to `http://192.168.0.67:5000`
   - Check **Map** tab for WiFi source markers (orange/yellow/green circles)
   - Check **WiFi** tab for estimated positions section

4. **Test WiFi signal mapping**:
   - Start Android app
   - Scan from current location (note compass direction shown)
   - Walk 20-30 meters away in a different direction
   - Scan again
   - Walk to third location at different angle
   - Scan again
   - Refresh WiFi page - estimated source positions should appear!

5. **View source positions on map**:
   - Open Map tab
   - Look for colored markers (WiFi sources)
   - Colors indicate confidence:
     - 🟢 Green = High confidence (70%+)
     - 🟡 Yellow = Medium (40-70%)
     - 🟠 Orange = Low (<40%)
   - Click marker to see details (position, confidence, accuracy)

---

**Have fun tracking the trackers!**
