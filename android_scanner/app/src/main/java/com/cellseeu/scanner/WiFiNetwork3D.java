package com.cellseeu.scanner;

/**
 * Data model representing a WiFi network in 3D space
 */
public class WiFiNetwork3D {
    public String ssid;
    public String bssid;
    public int signalStrength;  // RSSI in dBm
    public String security;
    public int channel;         // WiFi channel (1-14, 36-165)
    public int frequency;       // Frequency in MHz
    public String band;         // "2.4GHz" or "5GHz"
    public boolean isConnected;
    
    // 3D position (spherical coordinates)
    public float azimuth;       // Horizontal angle (0-360Â°)
    public float elevation;     // Vertical angle (-90 to 90Â°)
    public float distance;      // Distance from center (based on signal strength)
    
    // Visual properties
    public float[] color;       // RGB color based on signal strength
    public float alpha;         // Transparency
    
    // Label display modes
    public enum LabelMode {
        NAME,           // SSID
        SIGNAL,         // Signal strength in dBm
        SECURITY,       // Security type (WPA2, Open, etc)
        CHANNEL         // Channel number and band
    }
    
    public WiFiNetwork3D(String ssid, String bssid, int signalStrength, String security, 
                         int channel, int frequency, String band, boolean isConnected) {
        this.ssid = ssid;
        this.bssid = bssid;
        this.signalStrength = signalStrength;
        this.security = security;
        this.channel = channel;
        this.frequency = frequency;
        this.band = band;
        this.isConnected = isConnected;
        
        // Calculate distance based on signal strength
        // Strong signal (-30 dBm) = close (3 units)
        // Weak signal (-90 dBm) = far (15 units)
        this.distance = calculateDistance(signalStrength);
        
        // Calculate color based on signal strength
        this.color = calculateColor(signalStrength);
        this.alpha = 0.9f;
        
        // Use stable defaults; activity updates bearings from compass data.
        float stableOffset = stableOffset();
        this.azimuth = stableOffset * 360f;
        this.elevation = (stableOffset - 0.5f) * 80f;
    }
    
    /**
     * Calculate distance from signal strength (RSSI to distance conversion)
     */
    private float calculateDistance(int rssi) {
        // Free Space Path Loss formula approximation
        // Distance increases exponentially as signal weakens
        float minRSSI = -90f;
        float maxRSSI = -30f;
        float minDistance = 3f;
        float maxDistance = 15f;
        
        float normalized = (rssi - minRSSI) / (maxRSSI - minRSSI);
        normalized = Math.max(0f, Math.min(1f, normalized)); // Clamp 0-1
        
        return maxDistance - (normalized * (maxDistance - minDistance));
    }
    
    /**
     * Calculate color based on signal strength
     * Green (strong) -> Yellow -> Orange -> Red (weak)
     */
    private float[] calculateColor(int rssi) {
        if (rssi >= -50) {
            // Excellent: Green
            return new float[]{0.0f, 1.0f, 0.0f};
        } else if (rssi >= -60) {
            // Good: Chartreuse
            return new float[]{0.5f, 1.0f, 0.0f};
        } else if (rssi >= -70) {
            // Fair: Yellow
            return new float[]{1.0f, 1.0f, 0.0f};
        } else if (rssi >= -80) {
            // Weak: Orange
            return new float[]{1.0f, 0.65f, 0.0f};
        } else {
            // Very weak: Red
            return new float[]{1.0f, 0.0f, 0.0f};
        }
    }
    
    /**
     * Get Cartesian coordinates from spherical
     */
    public float[] getCartesianPosition() {
        float azimuthRad = (float) Math.toRadians(azimuth);
        float elevationRad = (float) Math.toRadians(elevation);
        
        float x = distance * (float) Math.cos(elevationRad) * (float) Math.sin(azimuthRad);
        float y = distance * (float) Math.sin(elevationRad);
        float z = distance * (float) Math.cos(elevationRad) * (float) Math.cos(azimuthRad);
        
        return new float[]{x, y, z};
    }
    
    /**
     * Update azimuth based on actual compass bearing
     */
    public void updateBearing(float bearing) {
        this.azimuth = normalizeDegrees(bearing);
    }

    /**
     * Update azimuth using the phone heading and stable spacing by network index.
     */
    public void updateBearing(float heading, int index, int total) {
        float spacing = total > 0 ? (360f * index / total) : 0f;
        this.azimuth = normalizeDegrees(heading + spacing);
    }
    
    /**
     * Get label text based on display mode
     */
    public String getLabel(LabelMode mode) {
        switch (mode) {
            case NAME:
                String name = (ssid != null && !ssid.isEmpty()) ? ssid : "<Hidden>";
                return isConnected ? name + " *" : name;
            
            case SIGNAL:
                return signalStrength + " dBm";
            
            case SECURITY:
                return security;
            
            case CHANNEL:
                return "Ch " + channel + " (" + band + ")";
            
            default:
                return ssid != null ? ssid : "<Hidden>";
        }
    }
    
    /**
     * Get short label (first word only for less clutter)
     */
    public String getShortLabel(LabelMode mode) {
        String full = getLabel(mode);
        if (mode == LabelMode.NAME && full.contains(" ")) {
            return full.split(" ")[0];
        }
        return full;
    }
    
    @Override
    public String toString() {
        return String.format("%s (%d dBm, Ch %d) at (%.1f deg, %.1f deg, %.1fm)",
            ssid != null ? ssid : "<Hidden>", 
            signalStrength,
            channel,
            azimuth, 
            elevation, 
            distance);
    }

    private float stableOffset() {
        String key = bssid != null && !bssid.isEmpty() ? bssid : ssid;
        if (key == null) {
            key = "";
        }

        int hash = 0;
        for (int i = 0; i < key.length(); i++) {
            hash = 31 * hash + key.charAt(i);
        }
        return (Math.abs(hash) % 1000) / 1000f;
    }

    private float normalizeDegrees(float degrees) {
        float normalized = degrees % 360f;
        return normalized < 0 ? normalized + 360f : normalized;
    }
}
