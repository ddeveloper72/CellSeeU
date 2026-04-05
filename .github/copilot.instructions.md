---
description: Instructions for CellSeeU - Android Cell Tower Detection App
applyTo: '**'
---

# CellSeeU - Android Cell Tower Detection Application

## Project Overview

CellSeeU is a **legal** Android application built with Python that detects and displays nearby cell towers using Android's public APIs. The app provides visibility into cell tower information without root access, decryption, or interception capabilities.

## Technology Stack

- **Language**: Python 3
- **Backend Framework**: Flask (dashboard and API server)
- **Mobile Framework**: Kivy (Android UI framework)
- **Android Bridge**: Pyjnius (Python-to-Java bridge) or Chaquopy
- **Build Tool**: Buildozer or Chaquopy
- **Frontend**: 
  - Mobile-first responsive design
  - Vanilla JavaScript (scripts.js)
  - Custom CSS (styles.css)
  - Leaflet.js or Mapbox for mapping
- **Environment Management**: 
  - .venv for Python virtual environment
  - .env for secrets and configuration
- **IDE**: VS Code with Python extension
- **Version Control**: Git with regular incremental commits
- **Target Platform**: Android (no root required) + Web Dashboard

## Core Functionality

### 1. Cell Tower Detection
The app uses Android's `TelephonyManager` API to retrieve:
- **Cell ID (CID)**: Unique identifier for the cell tower
- **Location Area Code (LAC)** / **Tracking Area Code (TAC)**: Network area identifiers
- **Mobile Country Code (MCC)**: Country identifier
- **Mobile Network Code (MNC)**: Network operator identifier
- **Signal Strength**: RSSI, RSRP, RSRQ, etc.
- **Radio Type**: LTE, 5G NR, UMTS, GSM, etc.
- **Registration Status**: Whether currently connected or just visible

### 2. Data Access Pattern
```python
# Using Pyjnius to access Android TelephonyManager
from jnius import autoclass

PythonActivity = autoclass('org.kivy.android.PythonActivity')
Context = autoclass('android.content.Context')
telephony_service = PythonActivity.mActivity.getSystemService(Context.TELEPHONY_SERVICE)
cell_info_list = telephony_service.getAllCellInfo()
```

### 3. Optional Features
- **Tower Mapping**: Integration with OpenCellID or Mozilla Location Service APIs
- **Location Plotting**: Using Folium or Leaflet for map visualization
- **Signal Strength Visualization**: Display and track signal metrics over time

## Architecture Guidelines

### Code Organization
```
cell_see_u/
├── .env                   # Secrets & configuration (NEVER commit!)
├── .env.example           # Template for required env variables
├── .gitignore             # Exclude .env, .venv, secrets
├── .venv/                 # Python virtual environment
├── requirements.txt       # Python dependencies
├── buildozer.spec         # Buildozer configuration
├── app.py                 # Flask application entry point
├── main.py                # Kivy Android app entry point
├── src/
│   ├── android/
│   │   ├── tower_detector.py  # TelephonyManager wrapper
│   │   └── ui/
│   │       ├── main_screen.py # Main UI screen
│   │       └── tower_list.py  # Tower list widget
│   ├── dashboard/
│   │   ├── routes.py      # Flask routes
│   │   └── api.py         # REST API endpoints
│   ├── services/
│   │   ├── tower_mapper.py    # OpenCellID integration
│   │   ├── geolocation.py     # Device location services
│   │   └── tower_classifier.py # Terrestrial vs Non-Terrestrial
│   └── models/
│       └── tower.py       # Tower data model
├── static/
│   ├── css/
│   │   └── styles.css     # Mobile-first CSS
│   ├── js/
│   │   └── scripts.js     # Frontend JavaScript
│   └── images/
│       ├── terrestrial-tower.svg
│       └── satellite-tower.svg
├── templates/
│   ├── base.html          # Base template
│   ├── dashboard.html     # Main dashboard
│   └── map.html           # Interactive map view
└── .github/
    └── copilot.instructions.md
```

### Android Permissions Required
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
```

## Development Best Practices

### 1. Security & Privacy - **CRITICAL**
- **NEVER commit .env file** - Add to .gitignore immediately
- **NEVER expose API keys** in code, logs, or UI
- **NEVER store personal information** without explicit consent
- Store secrets in .env:
  ```
  OPENCELLID_API_KEY=your_key_here
  MAPBOX_ACCESS_TOKEN=your_token_here
  FLASK_SECRET_KEY=generate_random_secret
  ```
- Use `python-dotenv` to load environment variables
- Sanitize all user-facing data displays
- Don't log sensitive information (tokens, coordinates with high precision)

### 2. Version Control
- **Make regular incremental commits** after each feature/fix
- Use descriptive commit messages:
  ```
  ✅ "Add terrestrial tower classification logic"
  ✅ "Implement mobile-first dashboard layout"
  ✅ "Fix: Geolocation permission handling on Android 12+"
  ❌Flask Dashboard Features

### 1. Mobile-First Design Principles
- **Design for mobile screens first**, then scale up to desktop
- Touch-friendly UI elements (minimum 44x44px tap targets)
- Responsive breakpoints:
  ```css
  /* Mobile first (default) */
  /* Tablet: 768px and up */
  /* Desktop: 1024px and up */
  ```
- Optimize for one-handed use on phones
- Fast load times (<3 seconds on 3G)
- Minimal data usage - lazy load images and map tiles

### 2. Dashboard Components

#### Geolocation Display
- Show current device location with accuracy radius
- Update location in real-time when moving
- Visual indicator: pulsing dot on map
- Display coordinates (with user permission only)
- Altitude and speed if available

#### Cell Tower Map
- Interactive map showing:
  - 🔵 **Terrestrial towers** - Traditional cell towers
  - 🛰️ **Non-Terrestrial towers** - Satellite/NTN (5G NR-NTN)
- Color-coded by signal strength (green=strong, yellow=medium, red=weak)
- Click tower for details panel
- Distance from device to each tower
- Connection lines from device to registered tower

#### Tower Classification Logic
```python
def classify_tower_type(cell_info):
    """Distinguish terrestrial vs non-terrestrial networks"""
    # Non-Terrestrial Network indicators:
    # - 5G NR with NTN capability flag
    # - Very high altitude (satellite orbit)
    # - Specific PLMNs used for satellite operators
    # - Cell ID patterns for LEO/GEO satellites
    
    if is_5g_nr(cell_info):
        if has_ntn_capability(cell_info):
            return "NON_TERRESTRIAL_SATELLITE"
        if is_starlink_plmn(cell_info.mcc, cell_info.mnc):
            return "NON_TERRESTRIAL_SATELLITE"
    
    return "TERRESTRIAL"
```

#### Signal Visualization
- Real-time signal strength meters
- Historical signal strength graphs (last hour)
- Network type badges (LTE, 5G, NR-NTN)
- Handover events timeline

#### Fun & Engaging Elements
- 🎯 "Tower Hunt" mode - gamified collection of unique towers
- 📊 Stats: Total towers discovered, coverage maps
- 🏆 Achievements: "5G Explorer", "Satellite Seeker", etc.
- 🌈 Signal quality animations (smooth transitions, particle effects)
- 🔊 Optional sound effects for new tower detection
- 📸 Screenshot sharing of tower maps

### 3. Flask Routes Structure
```python
# app.py
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/map')
def map_view():
    """Interactive map view"""
    return render_template('map.html')

# API endpoints
@app.route('/api/towers')
def get_towers():
    """Return all detected towers as JSON"""
    
@app.route('/api/location')
def get_location():
    """Return current device location"""
    
@app.route('/api/tower/<int:cell_id>')
def get_tower_details(cell_id):
    """Get detailed info for specific tower"""
```

### 4. Static Files Organization

#### styles.css - Mobile-First CSS
```css
/* Mobile-first base styles */
:root {
  --primary-color: #2563eb;
  --terrestrial-color: #10b981;
  --satellite-color: #8b5cf6;
  --signal-strong: #22c55e;
  --signal-medium: #eab308;
  --signal-weak: #ef4444;
}

/* Touch-friendly buttons */
.tower-card {
  min-height: 88px;
  padding: 16px;
  margin: 8px 0;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* Responsive grid */
.tower-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

@media (min-width: 768px) {
  .tower-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .tower-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

#### scripts.js - Frontend Logic
```javascript
// Real-time tower updates
function fetchTowers() {
  fetch('/api/towers')
    .then(res => res.json())
    .then(towers => {
      updateMap(towers);
      updateTowerList(towers);
      updateStats(towers);
    });
}

// Geolocation tracking
function startLocationTracking() {
  if ('geolocation' in navigator) {
    navigator.geolocation.watchPosition(
      position => {
        updateDeviceMarker(position.coords);
        calculateDistances(position.coords);
      },
      error => console.error('Location error:', error),
      { enableHighAccuracy: true, maximumAge: 5000 }
    );
  }
}

// Tower classification rendering
function renderTowerMarker(tower) {
  const icon = tower.type === 'NON_TERRESTRIAL_SATELLITE' 
    ? 'satellite-tower.svg' 
    : 'terrestrial-tower.svg';
  
  const color = getSignalColor(tower.signal_strength);
  Terrestrial vs Non-Terrestrial Networks (NTN)

### What are Non-Terrestrial Networks?
- **Satellite-based cellular** connectivity (LEO, MEO, GEO satellites)
- **5G NR-NTN** standard (3GPP Release 17+)
- Examples: Starlink, AST SpaceMobile, Lynk Global
- Provides coverage in remote areas where terrestrial towers don't reach

### Detection Methods
```Required Dependencies

### requirements.txt
```
# Flask web framework
Flask==3.0.0
flask-cors==4.0.0

# Environment management
python-dotenv==1.0.0

# Android (Kivy/Buildozer)
kivy==2.2.1
pyjnius==1.5.0
plyer==2.1.0

# Data processing
requests==2.31.0
python-dateutil==2.8.2

# Optional: Database
# flask-sqlalchemy==3.0.5
# pymongo==4.6.0  # If using MongoDB/Cosmos DB
```

### .env.example Template
```
# OpenCellID API (free tier: https://opencellid.org/)
OPENCELLID_API_KEY=your_key_here

# Mapbox or other mapping service
MAPBOX_ACCESS_TOKEN=your_token_here

# Flask configuration
FLASK_SECRET_KEY=generate_a_random_secret_key
FLASK_ENV=development
FLASK_DEBUG=True

# Optional: Database
# DATABASE_URL=sqlite:///cell_towers.db
# COSMOS_DB_ENDPOINT=https://your-account.documents.azure.com:443/
# COSMOS_DB_KEY=your_key_here

# App settings
REFRESH_INTERVAL_SECONDS=10
MAX_TOWER_HISTORY=1000
```

### .gitignore Template
```
# Environment
.env
.venv
venv/
ENV/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Flask
instance/
.webassets-cache

# Android build
bin/
.buildozer/
*.apk

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Secrets (double protection)
*secret*
*token*
*key*.txt
```

## Git Workflow

### Initial Setup
```bash
# Initialize repository
git init
git add .gitignore .env.example README.md
git commit -m "Initial commit: Project structure and configuration templates"

# Create development branch
git checkout -b develop
```

### Regular Commit Pattern
```bash
# After completing a discrete task (30-60 min work)
git add .
git status  # Review what's being committed
git diff --cached  # Review changes
git commit -m "Add: Geolocation service with error handling"

# Examples of good commit messages:
# "Add: Flask dashboard with mobile-first layout"
# "Implement: Terrestrial vs NTN tower classification"
# "Fix: Signal strength calculation for 5G NR towers"
# "Update: styles.css with responsive breakpoints"
# "Refactor: Tower detection service for better error handling"
# "Docs: Update README with installation instructions"
```

### Commit Checklist (Before Every Commit)
- [ ] .env file is NOT in the commit
- [ ] No API keys or tokens in code
- [ ] .venv is NOT in the commit
- [ ] Code has been tested
- [ ] No sensitive user data exposed
- [ ] Commit message is descriptive

## Legal Disclaimer Template
```
This application displays publicly available cell tower information
for educational and network diagnostic purposes only. It does NOT:
- Decrypt or intercept cellular communications
- Perform IMSI catching or device tracking
- Violate carrier terms of service or telecommunications law
- Store or share personal location data without consent

Users are responsible for compliance with local laws and regulations.
```

## Privacy Notice Template
```
CellSeeU Privacy Notice:
- Location data stays on your device
- No personal information is transmitted to external servers
- OpenCellID API calls are anonymous (tower lookup only)
- You can disable geolocation at any time in settings
- We do not track, profile, or monetize user data
        (901, 88),   # Example satellite PLMN
        # Add known satellite operator MCC/MNC pairs
    ]
    if (cell_info.mcc, cell_info.mnc) in satellite_plmns:
        return True
    
    # Method 3: Analyze signal characteristics
    # - Very long round-trip time (satellite latency)
    # - Unusual timing advance values
    # - Low signal strength with wide coverage
    
    return False
```

### UI Differentiation
- **Icons**: Tower 🗼 vs Satellite 🛰️
- **Colors**: Green (terrestrial) vs Purple (satellite)
- **Labels**: "Terrestrial LTE" vs "Satellite 5G NTN"
- **Info panels**: Show latency, orbit type (LEO/GEO), satellite name if known

## Development Notes

When implementing features:
1. **Always handle permissions first** - The app cannot function without location permissions
2. **Parse cell info defensively** - Different Android versions format cell data differently
3. **Provide visual feedback** - Show signal strength with visual indicators
4. **Cache tower data** - Avoid excessive API calls to getAllCellInfo()
5. **Consider battery usage** - Polling cell towers drains battery; use appropriate refresh intervals
6. **Use .venv exclusively** - Never install packages globally
7. **Commit frequently** - Every feature, bug fix, or refactor gets its own commit
8. **Test on mobile first** - Open dashboard on phone browser before desktop
9. **Keep it fun** - Add animations, achievements, and interactive elements
10. **Protect secrets** - Double-check .gitignore before every commit
}
```

## Deployment Process

### Flask Development Server
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

# Run development server
flask run --host=0.0.0.0 --port=5000

# Or with auto-reload
python app.py
``` stuff"
  ```
- Commit frequency: Every 30-60 minutes or after completing discrete tasks
- Never commit .env, .venv, __pycache__, *.pyc files

### 3. Python Environment Management
- **Always use .venv** for dependency isolation
- Activate before working:
  ```bash
  # Windows
  .venv\Scripts\activate
  
  # Linux/Mac
  source .venv/bin/activate
  ```
- Install dependencies: `pip install -r requirements.txt`
- Update requirements: `pip freeze > requirements.txt` after adding packages

### 4. API Access
- Always check if `getAllCellInfo()` returns `None` before iterating
- Handle permission denials gracefully with user-friendly messages
- Request runtime permissions on Android 6.0+ using Kivy's Android module

### 5. Data Parsing
- Cell tower objects vary by type: `CellInfoLte`, `CellInfoNr`, `CellInfoGsm`, etc.
- Extract common fields: registered status, signal strength, cell identity
- Use try-except blocks when parsing cell info strings

### 6. Signal Strength Interpretation
- **LTE**: RSRP (Reference Signal Received Power), RSRQ (Quality)
- **5G NR**: SS-RSRP, SS-RSRQ, SS-SINR
- **GSM/UMTS**: RSSI (Received Signal Strength Indicator)
- Display in both dBm and user-friendly bars/percentages

### 7. Legal & Ethical Compliance
- ✅ **Legal**: Reading public cell tower information via official APIs
- ❌ **Illegal**: Decrypting communications, intercepting data, IMSI catching
- Always display disclaimers about intended educational/diagnostic use

## Deployment Process

### Building with Buildozer
```bash
# Install buildozer
pip install buildozer

# Initialize buildozer.spec
buildozer init

# Build APK
buildozer -v android debug

# Deploy to connected device
buildozer android deploy run
```

### Building with Chaquopy
```gradle
plugins {
    id 'com.chaquo.python'
}

chaquopy {
    defaultConfig {
        version "3.9"
    }
}
```

## Code Examples

### Tower Detection Service
```python
class CellTowerDetector:
    def __init__(self):
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        self.telephony = PythonActivity.mActivity.getSystemService(Context.TELEPHONY_SERVICE)
    
    def get_visible_towers(self):
        """Returns list of all visible cell towers"""
        cell_info_list = self.telephony.getAllCellInfo()
        if not cell_info_list:
            return []
        
        towers = []
        for cell in cell_info_list:
            tower_data = self._parse_cell_info(cell)
            if tower_data:
                towers.append(tower_data)
        return towers
```

### Expected Output Format
```python
{
    'type': 'LTE',  # or 5G, UMTS, GSM
    'registered': True,  # Currently connected
    'cell_id': 12345678,
    'tracking_area_code': 45678,
    'mcc': 310,  # USA
    'mnc': 260,  # T-Mobile
    'signal_strength': -85,  # dBm
    'signal_quality': -10,   # dB
    'bandwidth': 20000       # kHz
}
```

## Testing & Debugging

### Local Testing
- Cannot fully test TelephonyManager APIs on emulators (limited cell info)
- Use real Android devices for accurate tower detection
- Test on different Android versions (API 21-34+)
- Test with various carriers (different MCC/MNC combinations)

### Debug Commands
```bash
# View Android logs
adb logcat | grep -i cell

# Check permissions at runtime
adb shell dumpsys package <your.package.name> | grep permission

# Install debug APK
adb install -r bin/*.apk
```

## Integration with External APIs

### OpenCellID Tower Location Lookup
```python
import requests

def lookup_tower_location(mcc, mnc, lac, cid):
    url = f"https://opencellid.org/cell/get?key=YOUR_API_KEY&mcc={mcc}&mnc={mnc}&lac={lac}&cellid={cid}&format=json"
    response = requests.get(url)
    if response.ok:
        data = response.json()
        return {
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'accuracy': data.get('range')
        }
    return None
```

## Common Issues & Solutions

### Issue: getAllCellInfo() returns None
- **Cause**: Missing location permissions
- **Solution**: Request ACCESS_FINE_LOCATION at runtime

### Issue: Empty cell info list
- **Cause**: Airplane mode, no signal, or carrier restrictions
- **Solution**: Check device connectivity and move to area with better signal

### Issue: Build fails with Buildozer
- **Cause**: Missing Android SDK/NDK tools
- **Solution**: Run `buildozer android clean` then rebuild

## References

- [Android TelephonyManager Documentation](https://developer.android.com/reference/android/telephony/TelephonyManager)
- [Kivy Android Documentation](https://kivy.org/doc/stable/guide/android.html)
- [Pyjnius Documentation](https://pyjnius.readthedocs.io/)
- [OpenCellID API](https://opencellid.org/)
- [Mozilla Location Service](https://location.services.mozilla.com/)

## Development Notes

When implementing features:
1. **Always handle permissions first** - The app cannot function without location permissions
2. **Parse cell info defensively** - Different Android versions format cell data differently
3. **Provide visual feedback** - Show signal strength with visual indicators
4. **Cache tower data** - Avoid excessive API calls to getAllCellInfo()
5. **Consider battery usage** - Polling cell towers drains battery; use appropriate refresh intervals

## Legal Disclaimer Template
```
This application displays publicly available cell tower information
for educational and network diagnostic purposes only. It does NOT:
- Decrypt or intercept cellular communications
- Perform IMSI catching or device tracking
- Violate carrier terms of service or telecommunications law

Users are responsible for compliance with local laws and regulations.
```
