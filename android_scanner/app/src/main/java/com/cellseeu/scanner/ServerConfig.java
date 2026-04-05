package com.cellseeu.scanner;

/**
 * Server configuration for CellSeeU Flask backend
 */
public class ServerConfig {
    
    /**
     * Flask server base URL
     * 
     * Update this to match your Flask server IP address:
     * - Local testing: http://127.0.0.1:5000
     * - Same WiFi network: http://192.168.0.67:5000
     * - Remote server: http://your-server-ip:5000
     */
    public static final String SERVER_URL = "http://192.168.0.67:5000";
    
    /**
     * API endpoint for uploading tower data
     */
    public static final String UPLOAD_ENDPOINT = "/api/towers/upload";
    
    /**
     * Scan interval in milliseconds (default: 10 seconds)
     */
    public static final long SCAN_INTERVAL_MS = 10000;
    
    /**
     * Location update interval in milliseconds (default: 5 seconds)
     */
    public static final long LOCATION_INTERVAL_MS = 5000;
    
    /**
     * Connection timeout in milliseconds (default: 30 seconds)
     */
    public static final int CONNECTION_TIMEOUT_MS = 30000;
    
    /**
     * Read timeout in milliseconds (default: 30 seconds)
     */
    public static final int READ_TIMEOUT_MS = 30000;
}
