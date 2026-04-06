package com.cellseeu.scanner;

/**
 * Data model representing a WiFi network in 3D space
 */
public class WiFiNetwork3D {
    public String ssid;
    public String bssid;
    public int signalStrength;  // RSSI in dBm
    public String security;
    public boolean isConnected;
    
    // 3D position (spherical coordinates)
    public float azimuth;       // Horizontal angle (0-360°)
    public float elevation;     // Vertical angle (-90 to 90°)
    public float distance;      // Distance from center (based on signal strength)
    
    // Visual properties
    public float[] color;       // RGB color based on signal strength
    public float alpha;         // Transparency
    
    public WiFiNetwork3D(String ssid, String bssid, int signalStrength, String security, boolean isConnected) {
        this.ssid = ssid;
        this.bssid = bssid;
        this.signalStrength = signalStrength;
        this.security = security;
        this.isConnected = isConnected;
        
        // Calculate distance based on signal strength
        // Strong signal (-30 dBm) = close (3 units)
        // Weak signal (-90 dBm) = far (15 units)
        this.distance = calculateDistance(signalStrength);
        
        // Calculate color based on signal strength
        this.color = calculateColor(signalStrength);
        this.alpha = 0.9f;
        
        // Distribute networks randomly in 3D space for now
        // This will be updated with actual compass bearings when available
        this.azimuth = (float) (Math.random() * 360);
        this.elevation = (float) ((Math.random() - 0.5) * 120); // ±60°
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
        this.azimuth = bearing;
    }
    
    @Override
    public String toString() {
        return String.format("%s (%d dBm) at (%.1f°, %.1f°, %.1fm)", 
            ssid != null ? ssid : "<Hidden>", 
            signalStrength, 
            azimuth, 
            elevation, 
            distance);
    }
}
