# CellSeeU Android Scanner

Android companion app that collects real cell tower data from your device using TelephonyManager API and sends it to the Flask backend.

## Features

- **Real-time Cell Tower Detection**: Uses `TelephonyManager.getAllCellInfo()` to detect all nearby towers
- **Multiple Network Types**: LTE, 5G NR, WCDMA, GSM, CDMA
- **Signal Strength Monitoring**: Accurate dBm readings for each tower
- **Location Integration**: GPS coordinates for tower distance calculation
- **Background Service**: Continuous monitoring and automatic updates to server
- **Privacy-Focused**: All data stays on your local network

## Requirements

- Android 6.0 (API 23) or higher
- Location permissions (for cell tower access)
- Phone state permissions (for TelephonyManager)
- Network connection to Flask server (WiFi/Mobile data)

## Permissions Required

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.INTERNET" />
```

## Building

### Option 1: Android Studio
1. Open Android Studio
2. File → Open → Select `android_scanner` folder
3. Build → Make Project
4. Run → Run 'app'

### Option 2: Command Line (Gradle)
```bash
cd android_scanner
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Configuration

Edit `ServerConfig.java` to set your Flask server URL:
```java
public static final String SERVER_URL = "http://192.168.0.67:5000";
```

## Usage

1. Install app on Android device
2. Grant location and phone permissions
3. Enter Flask server IP address
4. Tap "Start Scanning"
5. View detected towers in CellSeeU web dashboard

## Data Sent to Server

The app sends tower data in JSON format:
```json
{
  "device_location": {
    "latitude": 53.3498,
    "longitude": -6.2603,
    "accuracy": 15.0
  },
  "towers": [
    {
      "cell_id": 45612378,
      "mcc": 272,
      "mnc": 1,
      "network_type": "LTE",
      "signal_strength": -75,
      "registered": true,
      "lac": 12345,
      "tac": 67890,
      "pci": 123
    }
  ]
}
```

## Privacy & Security

- **No internet access to external servers** - data only sent to your local Flask server
- **No personal information collected** - only technical tower data (MCC/MNC/signal strength)
- **Location stays local** - GPS coordinates never leave your network
- **Open source** - review all code before using

## Troubleshooting

### No towers detected
- Ensure location permissions are granted
- Check that phone permissions are granted
- Make sure you're not in airplane mode

### Can't connect to server
- Verify Flask server is running (`http://192.168.0.67:5000`)
- Check phone and PC are on same WiFi network
- Disable VPN if active
- Check firewall allows port 5000

## Architecture

```
Android Device                    Flask Server
┌──────────────────┐            ┌─────────────────┐
│ TelephonyManager │            │                 │
│    ↓             │            │   Flask API     │
│ Cell Tower Data  │  ──HTTP──→ │   /api/upload   │
│    ↓             │   POST     │      ↓          │
│ Location Service │            │  Store Towers   │
│    ↓             │            │      ↓          │
│  HTTP Client     │            │  Web Dashboard  │
└──────────────────┘            └─────────────────┘
```

## License

Same as parent CellSeeU project
