# Build Instructions for CellSeeU Android Scanner

## Quick Start (Easiest Option)

### Option 1: Install Pre-Built APK (Recommended)
1. Download the APK to your Android device (when available)
2. Enable "Install from Unknown Sources" in Android Settings
3. Install the APK
4. Grant permissions when prompted
5. Enter your Flask server IP: `192.168.0.67:5000`
6. Tap "Start Scanning"

## Build From Source

### Requirements
- Android Studio (latest version recommended)
- Android SDK Build Tools
- Java Development Kit (JDK) 11 or higher
- Android device or emulator (API 23+)

### Step 1: Open Project in Android Studio
```bash
# Open Android Studio
# File → Open → Navigate to:
C:\Users\Duncan\Visual_Studio_Projects\cell_see_u\android_scanner
```

### Step 2: Configure Gradle
Android Studio will auto-generate `build.gradle` files. If missing,create:

**app/build.gradle:**
```gradle
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.cellseeu.scanner'
    compileSdk 34

    defaultConfig {
        applicationId "com.cellseeu.scanner"
        minSdk 23
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
    
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_11
        targetCompatibility JavaVersion.VERSION_11
    }
}

dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.11.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
}
```

### Step 3: Build APK
```bash
# In Android Studio:
Build → Build Bundle(s) / APK(s) → Build APK(s)

# Or via command line:
cd android_scanner
./gradlew assembleDebug

# APK will be in:
app/build/outputs/apk/debug/app-debug.apk
```

### Step 4: Install on Device

**Via USB (ADB):**
```powershell
# Check device connected
adb devices

# Install APK
adb install app/build/outputs/apk/debug/app-debug.apk
```

**Via File Transfer:**
1. Copy APK to device (USB/Email/Cloud)
2. Open file on device
3. Tap "Install"
4. Grant permissions

## Configuration

### Update Server URL
Before building, edit `ServerConfig.java`:
```java
public static final String SERVER_URL = "http://192.168.0.67:5000";
```

Change `192.168.0.67` to your Flask server's IP address.

### Finding Your Flask Server IP
```powershell
# On Windows (where Flask is running):
ipconfig

# Look for "IPv4 Address" under your active network adapter
# Example: 192.168.0.67
```

## Permissions

The app will request these permissions on first run:
- **Location (Fine)**: Required to access cell tower data
- **Phone State**: Required to read TelephonyManager
- **Internet**: Required to send data to Flask server

All permissions are necessary for the app to function.

## Troubleshooting

### Build Errors
- **Gradle sync failed**: File → Sync Project with Gradle Files
- **SDK not found**: File → Settings → Android SDK → Install required SDK
- **Java version**: Ensure JDK 11+ is installed

### Runtime Errors
- **No towers detected**: Grant all permissions in Android Settings
- **Can't connect to server**: Ensure phone and PC on same WiFi network
- **Crashes on start**: Check Logcat in Android Studio for error details

### Network Issues
```powershell
# Test Flask server is accessible from phone:
# On phone browser, navigate to:
http://192.168.0.67:5000

# Should show CellSeeU dashboard
```

### ADB Not Found
```powershell
# Install Android SDK Platform Tools
winget install Google.PlatformTools

# Or download from:
# https://developer.android.com/tools/releases/platform-tools
```

## Testing

### Test Without Building
If you have issues building, you can test with a simple HTTP request:
```bash
curl -X POST http://192.168.0.67:5000/api/towers/upload \
  -H "Content-Type: application/json" \
  -d '{
    "towers": [
      {
        "cell_id": 12345,
        "mcc": 272,
        "mnc": 1,
        "network_type": "LTE",
        "signal_strength": -80,
        "registered": true,
        "tower_type": "TERRESTRIAL"
      }
    ]
  }'
```

## Next Steps

Once installed and running:
1. Open CellSeeU Scanner app on Android
2. Grant all permissions
3. Verify server URL is correct
4. Tap "Start Scanning"
5. Open web browser to http://192.168.0.67:5000
6. You should see REAL tower data from your device!

## Support

For issues or questions:
- Check logs in Android Studio's Logcat
- Review Flask server console for HTTP requests
- Ensure firewall allows port 5000
- Verify both devices on same network
