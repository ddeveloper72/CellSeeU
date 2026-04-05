# 🗼 CellSeeU - Cell Tower Detection & Visualization

A **legal** Android + Web dashboard application that detects and visualizes nearby cell towers, including terrestrial and non-terrestrial (satellite) networks.

## ✨ Features

- 📡 **Real-time Cell Tower Detection** - Detect all visible towers using Android TelephonyManager API
- 🗺️ **Interactive Geolocation Map** - See your location and all towers on an interactive map
- 🛰️ **NTN Classification** - Distinguish between terrestrial towers and satellite/5G NR-NTN networks
- 📊 **Signal Visualization** - Real-time signal strength meters and historical graphs
- 📱 **Mobile-First Dashboard** - Responsive Flask-powered web dashboard
- 🎯 **Gamification** - Tower Hunt mode with achievements and stats
- 🔒 **Privacy-Focused** - All data stays on your device

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
cd cell_see_u

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env and add your API keys:
# - OPENCELLID_API_KEY (get from https://opencellid.org/)
# - MAPBOX_ACCESS_TOKEN (get from https://www.mapbox.com/)
# - FLASK_SECRET_KEY (generate random string)
```

### 3. Run Flask Dashboard

```bash
# Set Flask app
export FLASK_APP=app.py  # Linux/Mac
set FLASK_APP=app.py     # Windows

# Run development server
flask run --host=0.0.0.0 --port=5000
```

Open browser to: `http://localhost:5000`

### 4. Build Android App (Optional)

```bash
# Install buildozer
pip install buildozer

# Build APK
buildozer -v android debug

# Deploy to phone
buildozer android deploy run
```

## 📁 Project Structure

```
cell_see_u/
├── .env                   # Secrets (DO NOT COMMIT!)
├── .env.example           # Template
├── .venv/                 # Virtual environment
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/
│   │   └── styles.css     # Mobile-first CSS
│   ├── js/
│   │   └── scripts.js     # Frontend JavaScript
│   └── images/            # Tower/satellite icons
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   └── map.html
└── src/
    ├── android/           # Android-specific code
    ├── dashboard/         # Flask routes & API
    └── services/          # Tower detection, geolocation
```

## 🛰️ Terrestrial vs Non-Terrestrial Networks

**Terrestrial** 🗼
- Traditional cell towers (LTE, 5G)
- Ground-based infrastructure
- Low latency, high bandwidth

**Non-Terrestrial (NTN)** 🛰️
- Satellite-based 5G (3GPP Release 17+)
- LEO/GEO satellite constellations
- Global coverage in remote areas
- Examples: Starlink, AST SpaceMobile

## 🔒 Security & Privacy

- ✅ No data leaves your device without consent
- ✅ API keys stored securely in `.env` (never committed)
- ✅ Anonymous tower lookups via OpenCellID
- ✅ Location data is not transmitted to external servers
- ✅ Full GDPR/privacy compliance

## 📜 Legal Disclaimer

This application displays **publicly available** cell tower information for educational and network diagnostic purposes only.

**This app does NOT:**
- ❌ Decrypt or intercept cellular communications
- ❌ Perform IMSI catching or device tracking
- ❌ Violate carrier terms of service or telecommunications law

Users are responsible for compliance with local laws and regulations.

## 🛠️ Development

### Git Workflow

```bash
# Make changes, then commit regularly
git add .
git status
git commit -m "Add: Feature description"

# Commit frequency: every 30-60 minutes or after completing a task
```

### Commit Message Format
- `Add:` New feature
- `Fix:` Bug fix
- `Update:` Improvements to existing feature
- `Refactor:` Code restructuring
- `Docs:` Documentation changes

### Dependencies

Install in `.venv` only:
```bash
pip install flask flask-cors python-dotenv requests
```

## 🎯 Roadmap

- [x] Flask dashboard with mobile-first design
- [x] Cell tower detection via Android API
- [x] Geolocation tracking
- [x] Terrestrial vs NTN classification
- [ ] Real-time signal strength graphs
- [ ] Tower Hunt gamification mode
- [ ] Achievement system
- [ ] Export tower data (CSV/JSON)
- [ ] Offline mode with cached data

## 📚 Resources

- [Android TelephonyManager Docs](https://developer.android.com/reference/android/telephony/TelephonyManager)
- [5G NR-NTN Overview](https://www.3gpp.org/technologies/non-terrestrial-networks)
- [OpenCellID API](https://opencellid.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 📄 License

MIT License - See LICENSE file for details

---

**Built with ❤️ for network exploration and education**
