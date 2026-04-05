package com.cellseeu.scanner;

import android.util.Log;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * HTTP client for sending tower data to Flask API
 */
public class ApiClient {
    
    private static final String TAG = "ApiClient";
    
    /**
     * Upload tower data to Flask server
     * 
     * @param towerData JSON object containing tower scan results
     * @return true if upload successful, false otherwise
     */
    public static boolean uploadTowerData(JSONObject towerData) {
        HttpURLConnection connection = null;
        
        try {
            // Build URL
            String fullUrl = ServerConfig.SERVER_URL + ServerConfig.UPLOAD_ENDPOINT;
            URL url = new URL(fullUrl);
            
            Log.i(TAG, "Uploading to: " + fullUrl);
            
            // Open connection
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            connection.setRequestProperty("Accept", "application/json");
            connection.setConnectTimeout(ServerConfig.CONNECTION_TIMEOUT_MS);
            connection.setReadTimeout(ServerConfig.READ_TIMEOUT_MS);
            connection.setDoOutput(true);
            connection.setDoInput(true);
            
            // Send JSON data
            String jsonString = towerData.toString();
            byte[] outputBytes = jsonString.getBytes(StandardCharsets.UTF_8);
            
            try (OutputStream os = connection.getOutputStream()) {
                os.write(outputBytes);
                os.flush();
            }
            
            // Get response code
            int responseCode = connection.getResponseCode();
            
            Log.i(TAG, "Response code: " + responseCode);
            
            if (responseCode == HttpURLConnection.HTTP_OK || responseCode == HttpURLConnection.HTTP_CREATED) {
                // Read response
                StringBuilder response = new StringBuilder();
                try (BufferedReader br = new BufferedReader(
                        new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = br.readLine()) != null) {
                        response.append(line.trim());
                    }
                }
                
                Log.i(TAG, "Upload successful: " + response.toString());
                return true;
                
            } else {
                // Read error response
                StringBuilder errorResponse = new StringBuilder();
                try (BufferedReader br = new BufferedReader(
                        new InputStreamReader(connection.getErrorStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = br.readLine()) != null) {
                        errorResponse.append(line.trim());
                    }
                }
                
                Log.e(TAG, "Upload failed: " + responseCode + " - " + errorResponse.toString());
                return false;
            }
            
        } catch (Exception e) {
            Log.e(TAG, "Error uploading tower data", e);
            return false;
            
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }
    
    /**
     * Test connection to Flask server
     * 
     * @return true if server is reachable, false otherwise
     */
    public static boolean testConnection() {
        HttpURLConnection connection = null;
        
        try {
            URL url = new URL(ServerConfig.SERVER_URL + "/");
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(5000);
            connection.setReadTimeout(5000);
            
            int responseCode = connection.getResponseCode();
            
            Log.i(TAG, "Connection test: " + responseCode);
            return responseCode == HttpURLConnection.HTTP_OK;
            
        } catch (Exception e) {
            Log.e(TAG, "Connection test failed", e);
            return false;
            
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }
}
