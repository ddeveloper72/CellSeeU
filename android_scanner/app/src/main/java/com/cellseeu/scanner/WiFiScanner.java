package com.cellseeu.scanner;

import android.content.Context;
import android.content.pm.PackageManager;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiManager;
import android.util.Log;

import androidx.core.app.ActivityCompat;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.List;

/**
 * Scans for WiFi networks using Android WifiManager API
 * 
 * Detects all nearby WiFi access points including:
 * - SSID (network name)
 * - BSSID (MAC address)
 * - Signal strength (dBm and RSSI)
 * - Frequency and channel
 * - Security/encryption type
 * - Hidden networks
 */
public class WiFiScanner {
    
    private static final String TAG = "WiFiScanner";
    
    private final Context context;
    private final WifiManager wifiManager;
    
    public WiFiScanner(Context context) {
        this.context = context;
        this.wifiManager = (WifiManager) context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
    }
    
    /**
     * Scan for all nearby WiFi networks
     * 
     * @return JSON object containing WiFi network data
     */
    public JSONObject scanNetworks() {
        JSONObject result = new JSONObject();
        
        try {
            // Check if WiFi is enabled
            if (wifiManager == null) {
                Log.w(TAG, "WiFi manager not available");
                result.put("networks", new JSONArray());
                result.put("error", "WiFi manager not available");
                return result;
            }
            
            if (!wifiManager.isWifiEnabled()) {
                Log.w(TAG, "WiFi is disabled");
                result.put("networks", new JSONArray());
                result.put("error", "WiFi is disabled - please enable WiFi");
                return result;
            }
            
            // Trigger a new scan
            boolean scanStarted = wifiManager.startScan();
            if (!scanStarted) {
                Log.w(TAG, "WiFi scan failed to start - throttled or permission denied");
            }
            
            // Get scan results (may be cached if scan throttled)
            List<ScanResult> scanResults = wifiManager.getScanResults();
            
            if (scanResults == null || scanResults.isEmpty()) {
                Log.w(TAG, "No WiFi networks detected");
                result.put("networks", new JSONArray());
                result.put("error", "No WiFi networks detected");
                return result;
            }
            
            Log.i(TAG, "Found " + scanResults.size() + " WiFi network(s)");
            
            JSONArray networksArray = new JSONArray();
            
            for (ScanResult scan : scanResults) {
                JSONObject networkJson = parseScanResult(scan);
                if (networkJson != null) {
                    networksArray.put(networkJson);
                    Log.d(TAG, "Detected: " + 
                          (scan.SSID.isEmpty() ? "<hidden>" : scan.SSID) + 
                          " (" + scan.level + " dBm)");
                }
            }
            
            result.put("networks", networksArray);
            result.put("count", networksArray.length());
            result.put("wifi_enabled", true);
            
        } catch (JSONException e) {
            Log.e(TAG, "Error creating WiFi scan JSON", e);
        } catch (SecurityException e) {
            Log.e(TAG, "Permission denied for WiFi scanning", e);
            try {
                result.put("error", "Permission denied - location access required for WiFi scanning");
            } catch (JSONException ex) {}
        }
        
        return result;
    }
    
    /**
     * Parse a ScanResult into JSON
     */
    private JSONObject parseScanResult(ScanResult scan) {
        try {
            JSONObject network = new JSONObject();
            
            // Network identification
            network.put("ssid", scan.SSID.isEmpty() ? "<Hidden Network>" : scan.SSID);
            network.put("bssid", scan.BSSID);  // MAC address
            
            // Signal strength
            network.put("signal_strength", scan.level);  // dBm
            network.put("signal_quality", calculateSignalQuality(scan.level));  // 0-100%
            
            // Frequency and channel
            network.put("frequency", scan.frequency);  // MHz
            network.put("channel", getChannelFromFrequency(scan.frequency));
            network.put("band", scan.frequency > 5000 ? "5GHz" : "2.4GHz");
            
            // Security/capabilities
            network.put("capabilities", scan.capabilities);
            network.put("security", parseSecurityType(scan.capabilities));
            network.put("is_open", !scan.capabilities.contains("WPA") && 
                                   !scan.capabilities.contains("WEP"));
            
            // Hidden network detection
            network.put("is_hidden", scan.SSID.isEmpty());
            
            // Timestamp
            network.put("timestamp", System.currentTimeMillis());
            
            return network;
            
        } catch (JSONException e) {
            Log.e(TAG, "Error parsing WiFi scan result", e);
            return null;
        }
    }
    
    /**
     * Calculate signal quality percentage from dBm
     * 
     * -30 dBm = 100% (excellent)
     * -90 dBm = 0% (unusable)
     */
    private int calculateSignalQuality(int dBm) {
        if (dBm >= -30) return 100;
        if (dBm <= -90) return 0;
        return 2 * (dBm + 100);  // Linear scale from -90 to -30
    }
    
    /**
     * Get WiFi channel from frequency
     */
    private int getChannelFromFrequency(int frequency) {
        // 2.4 GHz channels
        if (frequency >= 2412 && frequency <= 2484) {
            if (frequency == 2484) return 14;  // Japan-only channel
            return (frequency - 2407) / 5;
        }
        
        // 5 GHz channels (simplified)
        if (frequency >= 5170 && frequency <= 5825) {
            return (frequency - 5000) / 5;
        }
        
        return 0;  // Unknown
    }
    
    /**
     * Parse security type from capabilities string
     */
    private String parseSecurityType(String capabilities) {
        if (capabilities.contains("WPA3")) return "WPA3";
        if (capabilities.contains("WPA2")) return "WPA2";
        if (capabilities.contains("WPA")) return "WPA";
        if (capabilities.contains("WEP")) return "WEP";
        return "Open";
    }
    
    /**
     * Get currently connected WiFi network info
     */
    public JSONObject getConnectedNetwork() {
        try {
            JSONObject connected = new JSONObject();
            
            android.net.wifi.WifiInfo wifiInfo = wifiManager.getConnectionInfo();
            
            if (wifiInfo != null && wifiInfo.getNetworkId() != -1) {
                connected.put("ssid", wifiInfo.getSSID().replace("\"", ""));  // Remove quotes
                connected.put("bssid", wifiInfo.getBSSID());
                connected.put("signal_strength", wifiInfo.getRssi());
                connected.put("link_speed", wifiInfo.getLinkSpeed());  // Mbps
                connected.put("frequency", wifiInfo.getFrequency());
                connected.put("is_connected", true);
                
                return connected;
            }
            
        } catch (Exception e) {
            Log.e(TAG, "Error getting connected network", e);
        }
        
        try {
            JSONObject disconnected = new JSONObject();
            disconnected.put("is_connected", false);
            return disconnected;
        } catch (JSONException e) {
            return null;
        }
    }
}
