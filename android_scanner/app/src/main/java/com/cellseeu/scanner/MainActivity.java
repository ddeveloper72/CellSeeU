package com.cellseeu.scanner;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import org.json.JSONObject;

public class MainActivity extends AppCompatActivity {
    private static final int PERMISSION_REQUEST_CODE = 1;
    private TextView statusText;
    private Button scanButton;
    private LocationManager locationManager;
    private OrientationSensor orientationSensor;
    private boolean isScanning = false;
    private String mappingSessionId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Create simple UI
        setContentView(createLayout());
        
        statusText = findViewById(R.id.status_text);
        scanButton = findViewById(R.id.scan_button);
        
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        
        // Initialize orientation sensor
        orientationSensor = new OrientationSensor(this);
        if (orientationSensor.sensorsAvailable()) {
            orientationSensor.start();
            Log.i("MainActivity", "Orientation sensors started");
        } else {
            Log.w("MainActivity", "Orientation sensors not available");
        }
        
        scanButton.setOnClickListener(v -> {
            if (!isScanning) {
                startScanning();
            } else {
                stopScanning();
            }
        });
        
        checkPermissions();
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (orientationSensor != null) {
            orientationSensor.stop();
        }
    }

    private android.view.View createLayout() {
        android.widget.LinearLayout layout = new android.widget.LinearLayout(this);
        layout.setOrientation(android.widget.LinearLayout.VERTICAL);
        layout.setPadding(50, 50, 50, 50);
        
        statusText = new TextView(this);
        statusText.setId(R.id.status_text);
        statusText.setText("Ready to scan");
        statusText.setTextSize(18);
        statusText.setPadding(0, 0, 0, 40);
        
        scanButton = new Button(this);
        scanButton.setId(R.id.scan_button);
        scanButton.setText("Start Scanning");
        scanButton.setTextSize(20);
        
        // WiFi 3D View button
        Button wifi3dButton = new Button(this);
        wifi3dButton.setText("WiFi 3D View");
        wifi3dButton.setTextSize(18);
        wifi3dButton.setBackgroundColor(0xFF4fc3f7);
        wifi3dButton.setTextColor(0xFFFFFFFF);
        wifi3dButton.setPadding(20, 20, 20, 20);
        android.widget.LinearLayout.LayoutParams btnParams = new android.widget.LinearLayout.LayoutParams(
                android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        );
        btnParams.setMargins(0, 20, 0, 0);
        wifi3dButton.setLayoutParams(btnParams);
        wifi3dButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, WiFi3DActivity.class);
            startActivity(intent);
        });

        Button signalMapButton = new Button(this);
        signalMapButton.setText("Signal Map");
        signalMapButton.setTextSize(18);
        signalMapButton.setBackgroundColor(0xFF1E88E5);
        signalMapButton.setTextColor(0xFFFFFFFF);
        signalMapButton.setPadding(20, 20, 20, 20);
        android.widget.LinearLayout.LayoutParams mapBtnParams = new android.widget.LinearLayout.LayoutParams(
                android.widget.LinearLayout.LayoutParams.MATCH_PARENT,
                android.widget.LinearLayout.LayoutParams.WRAP_CONTENT
        );
        mapBtnParams.setMargins(0, 16, 0, 0);
        signalMapButton.setLayoutParams(mapBtnParams);
        signalMapButton.setOnClickListener(v -> {
            Intent intent = new Intent(MainActivity.this, SignalMapActivity.class);
            startActivity(intent);
        });
        
        layout.addView(statusText);
        layout.addView(scanButton);
        layout.addView(signalMapButton);
        layout.addView(wifi3dButton);
        
        return layout;
    }

    private void checkPermissions() {
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED ||
            ActivityCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.READ_PHONE_STATE},
                    PERMISSION_REQUEST_CODE);
        }
    }

    private void startScanning() {
        // Check both permissions
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, "Location permission required", Toast.LENGTH_SHORT).show();
            checkPermissions();
            return;
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, "Phone State permission required for cell tower detection", Toast.LENGTH_LONG).show();
            checkPermissions();
            return;
        }

        isScanning = true;
        scanButton.setText("Stop Scanning");
        statusText.setText("Scanning...");

        // Get last known location or request updates
        Location location = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER);
        if (location == null) {
            location = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER);
        }
        
        if (location != null) {
            scanAndUpload(location);
        } else {
            statusText.setText("Getting location...");
            
            // Try to get last known location first (faster)
            Location gpsLocation = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER);
            Location networkLocation = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER);
            final Location lastKnown = (gpsLocation != null) ? gpsLocation : networkLocation;
            
            // If we have a recent location, use it immediately
            if (lastKnown != null && (System.currentTimeMillis() - lastKnown.getTime()) < 60000) {
                Log.i("MainActivity", "Using last known location (age: " + (System.currentTimeMillis() - lastKnown.getTime())/1000 + "s)");
                scanAndUpload(lastKnown);
                return;
            }
            
            // Otherwise request fresh location with timeout
            final boolean[] locationReceived = {false};
            
            locationManager.requestSingleUpdate(LocationManager.NETWORK_PROVIDER, new LocationListener() {
                @Override
                public void onLocationChanged(Location loc) {
                    if (!locationReceived[0]) {
                        locationReceived[0] = true;
                        Log.i("MainActivity", "Got fresh location: " + loc.getLatitude() + ", " + loc.getLongitude());
                        scanAndUpload(loc);
                    }
                }
                @Override
                public void onStatusChanged(String provider, int status, Bundle extras) {}
                @Override
                public void onProviderEnabled(String provider) {}
                @Override
                public void onProviderDisabled(String provider) {}
            }, null);
            
            // Timeout after 5 seconds - scan without location if GPS is slow
            new Thread(() -> {
                try {
                    Thread.sleep(5000);
                    if (!locationReceived[0]) {
                        Log.w("MainActivity", "Location timeout - scanning without GPS");
                        runOnUiThread(() -> statusText.setText("Location timeout - scanning without GPS..."));
                        scanAndUpload(lastKnown);  // Use stale location or null
                    }
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            }).start();
        }
    }

    private void scanAndUpload(Location location) {
        new Thread(() -> {
            try {
                // Scan cell towers
                CellTowerScanner cellScanner = new CellTowerScanner(this);
                JSONObject cellData = cellScanner.scanTowers(location);
                
                // Scan WiFi networks
                WiFiScanner wifiScanner = new WiFiScanner(this);
                JSONObject wifiData = wifiScanner.scanNetworks();
                JSONObject connectedWifi = wifiScanner.getConnectedNetwork();
                
                // Get orientation data
                JSONObject deviceLocation = cellData.optJSONObject("device_location");
                if (deviceLocation != null && orientationSensor != null && orientationSensor.hasOrientation()) {
                    JSONObject orientation = orientationSensor.getOrientationJSON();
                    deviceLocation.put("heading", orientation.getDouble("heading"));
                    deviceLocation.put("pitch", orientation.getDouble("pitch"));
                    deviceLocation.put("roll", orientation.getDouble("roll"));
                    deviceLocation.put("cardinal_direction", orientation.getString("cardinal_direction"));
                    Log.i("MainActivity", "Device pointing: " + orientation.getString("cardinal_direction") + 
                          " (" + Math.round(orientation.getDouble("heading")) + "°)");
                }
                
                // Combine data
                JSONObject combinedData = new JSONObject();
                combinedData.put("towers", cellData.getJSONArray("towers"));
                combinedData.put("device_location", deviceLocation);
                combinedData.put("wifi_networks", wifiData.getJSONArray("networks"));
                combinedData.put("wifi_connected", connectedWifi);
                combinedData.put("wifi_count", wifiData.optInt("count", 0));
                combinedData.put("mapping_session_id", getMappingSessionId());
                
                int towerCount = cellData.getJSONArray("towers").length();
                int wifiCount = wifiData.optInt("count", 0);
                
                // Build detailed info about each tower
                StringBuilder towerInfo = new StringBuilder();
                org.json.JSONArray towers = cellData.getJSONArray("towers");
                for (int i = 0; i < towers.length(); i++) {
                    org.json.JSONObject tower = towers.getJSONObject(i);
                    String type = tower.optString("network_type", "?");
                    int signal = tower.optInt("signal_strength", 0);
                    boolean registered = tower.optBoolean("registered", false);
                    towerInfo.append(String.format("\n• %s: %d dBm %s", 
                        type, signal, registered ? "(connected)" : ""));
                }
                
                // Add orientation info if available
                if (orientationSensor != null && orientationSensor.hasOrientation()) {
                    towerInfo.append(String.format("\n\nFacing: %s (%.0f°)", 
                        orientationSensor.getCardinalDirection(),
                        orientationSensor.getAzimuth()));
                }
                
                // Add WiFi info
                if (wifiCount > 0) {
                    towerInfo.append("\n\nWiFi Networks:");
                    org.json.JSONArray wifiNetworks = wifiData.getJSONArray("networks");
                    int displayCount = Math.min(3, wifiCount);  // Show top 3
                    for (int i = 0; i < displayCount; i++) {
                        org.json.JSONObject wifi = wifiNetworks.getJSONObject(i);
                        String ssid = wifi.optString("ssid", "?");
                        int signal = wifi.optInt("signal_strength", 0);
                        towerInfo.append(String.format("\n• %s: %d dBm", ssid, signal));
                    }
                    if (wifiCount > 3) {
                        towerInfo.append(String.format("\n• ...and %d more", wifiCount - 3));
                    }
                }
                
                boolean success = ApiClient.uploadTowerData(combinedData);
                
                String detailedInfo = towerInfo.toString();
                runOnUiThread(() -> {
                    if (success) {
                        String message = "Uploaded:\n" +
                                       towerCount + " cell towers\n" +
                                       wifiCount + " WiFi networks" + 
                                       detailedInfo;
                        
                        // Add note if only 1 tower detected
                        if (towerCount == 1) {
                            message += "\n\nNote: Most phones only detect the connected tower. Neighboring cells are often hidden by Android/carrier.";
                        }
                        
                        message += "\n\nServer: " + ServerConfig.SERVER_URL;
                        statusText.setText(message);
                    } else {
                        statusText.setText("Upload failed. Check network.");
                    }
                });
            } catch (Exception e) {
                runOnUiThread(() -> statusText.setText("Error: " + e.getMessage()));
            }
        }).start();
    }

    private void stopScanning() {
        isScanning = false;
        scanButton.setText("Start Scanning");
        statusText.setText("Stopped");
    }

    private String getMappingSessionId() {
        if (mappingSessionId == null) {
            mappingSessionId = "android-" + System.currentTimeMillis();
        }
        return mappingSessionId;
    }

    // Generate IDs for views
    public static class R {
        public static class id {
            public static final int status_text = 1;
            public static final int scan_button = 2;
        }
    }
}
