package com.cellseeu.scanner;

import android.Manifest;
import android.content.pm.PackageManager;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import android.widget.ToggleButton;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/**
 * 3D WiFi Visualization Activity
 * 
 * Real-time 3D visualization of WiFi networks around you.
 * Hold your phone like a compass and watch the WiFi landscape update live!
 * 
 * Features:
 * - OpenGL ES 3D rendering
 * - Real-time compass integration
 * - Touch gestures (rotate, zoom)
 * - Color-coded signal strength
 * - Signal beams showing connection paths
 * - Auto-updating WiFi scans
 */
public class WiFi3DActivity extends AppCompatActivity {
    private static final String TAG = "WiFi3DActivity";
    private static final int SCAN_INTERVAL_MS = 5000; // 5 seconds
    
    private GLSurfaceView glSurfaceView;
    private WiFi3DRenderer renderer;
    private TextView statusText;
    private TextView networkCountText;
    private TextView compassText;
    private Button refreshButton;
    
    // Label controls
    private ToggleButton labelToggle;
    private Spinner labelModeSpinner;
    private FrameLayout labelOverlay;
    private boolean showLabels = true;
    private WiFiNetwork3D.LabelMode labelMode = WiFiNetwork3D.LabelMode.NAME;
    private List<WiFiNetwork3D> currentNetworks = new ArrayList<>();
    
    private WiFiScanner wifiScanner;
    private OrientationSensor orientationSensor;
    
    private Handler scanHandler = new Handler(Looper.getMainLooper());
    private boolean isScanning = false;
    
    // Touch gesture handling
    private GestureDetector gestureDetector;
    private ScaleGestureDetector scaleGestureDetector;
    private float cameraAngleX = 30f;
    private float cameraAngleY = 0f;
    private float cameraDistance = 25f;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Create layout programmatically with FrameLayout for overlays
        FrameLayout rootLayout = new FrameLayout(this);
        rootLayout.setBackgroundColor(0xFF0a0a1a);
        
        // Main vertical layout
        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setLayoutParams(new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));
        
        // Info panel at top
        LinearLayout infoPanel = createInfoPanel();
        mainLayout.addView(infoPanel);
        
        // GLSurfaceView for 3D rendering
        glSurfaceView = new GLSurfaceView(this);
        glSurfaceView.setEGLContextClientVersion(2); // OpenGL ES 2.0
        
        renderer = new WiFi3DRenderer();
        glSurfaceView.setRenderer(renderer);
        glSurfaceView.setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);
        
        LinearLayout.LayoutParams glParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1.0f // Weight 1 for remaining space
        );
        glSurfaceView.setLayoutParams(glParams);
        mainLayout.addView(glSurfaceView);
        
        // Control panel at bottom
        LinearLayout controlPanel = createControlPanel();
        mainLayout.addView(controlPanel);
        
        // Add main layout to root
        rootLayout.addView(mainLayout);
        
        // Add label overlay (on top of everything)
        labelOverlay = new FrameLayout(this);
        labelOverlay.setLayoutParams(new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));
        rootLayout.addView(labelOverlay);
        
        setContentView(rootLayout);
        
        // Initialize sensors
        wifiScanner = new WiFiScanner(this);
        orientationSensor = new OrientationSensor(this);
        
        if (orientationSensor.sensorsAvailable()) {
            orientationSensor.start();
            Log.i(TAG, "🧭 Orientation sensors started");
        } else {
            Toast.makeText(this, "Compass not available", Toast.LENGTH_SHORT).show();
        }
        
        // Setup touch gestures
        setupGestures();
        
        // Check permissions and start scanning
        if (checkPermissions()) {
            startScanning();
        }
    }
    
    private LinearLayout createInfoPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(30, 30, 30, 20);
        panel.setBackgroundColor(0xCC000000);
        
        // Title
        TextView title = new TextView(this);
        title.setText("📡 WiFi 3D View");
        title.setTextColor(0xFF4fc3f7);
        title.setTextSize(24);
        title.setPadding(0, 0, 0, 15);
        panel.addView(title);
        
        // Network count
        networkCountText = new TextView(this);
        networkCountText.setText("Networks: 0");
        networkCountText.setTextColor(0xFFFFFFFF);
        networkCountText.setTextSize(14);
        panel.addView(networkCountText);
        
        // Compass heading
        compassText = new TextView(this);
        compassText.setText("Heading: --°");
        compassText.setTextColor(0xFFFFFFFF);
        compassText.setTextSize(14);
        panel.addView(compassText);
        
        // Status
        statusText = new TextView(this);
        statusText.setText("Initializing...");
        statusText.setTextColor(0xFFaaaaaa);
        statusText.setTextSize(12);
        statusText.setPadding(0, 10, 0, 0);
        panel.addView(statusText);
        
        return panel;
    }
    
    private LinearLayout createControlPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(15, 10, 15, 10);
        panel.setBackgroundColor(0xCC000000);
        
        // First row: Label controls
        LinearLayout labelRow = new LinearLayout(this);
        labelRow.setOrientation(LinearLayout.HORIZONTAL);
        labelRow.setPadding(5, 5, 5, 10);
        
        // Label toggle
        labelToggle = new ToggleButton(this);
        labelToggle.setTextOn("Labels ON");
        labelToggle.setTextOff("Labels OFF");
        labelToggle.setChecked(showLabels);
        labelToggle.setTextColor(0xFFFFFFFF);
        labelToggle.setBackgroundColor(0xFF4fc3f7);
        labelToggle.setOnCheckedChangeListener((buttonView, isChecked) -> {
            showLabels = isChecked;
            updateNetworkLabels();
        });
        
        LinearLayout.LayoutParams toggleParams = new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                0.4f
        );
        toggleParams.setMargins(0, 0, 10, 0);
        labelToggle.setLayoutParams(toggleParams);
        labelRow.addView(labelToggle);
        
        // Label mode spinner
        labelModeSpinner = new Spinner(this);
        String[] modes = {"Network Names", "Signal Strength", "Security Type", "WiFi Channel"};
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, 
                android.R.layout.simple_spinner_dropdown_item, modes);
        labelModeSpinner.setAdapter(adapter);
        labelModeSpinner.setSelection(0);
        labelModeSpinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                switch (position) {
                    case 0: labelMode = WiFiNetwork3D.LabelMode.NAME; break;
                    case 1: labelMode = WiFiNetwork3D.LabelMode.SIGNAL; break;
                    case 2: labelMode = WiFiNetwork3D.LabelMode.SECURITY; break;
                    case 3: labelMode = WiFiNetwork3D.LabelMode.CHANNEL; break;
                }
                updateNetworkLabels();
            }
            
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });
        
        LinearLayout.LayoutParams spinnerParams = new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                0.6f
        );
        labelModeSpinner.setLayoutParams(spinnerParams);
        labelRow.addView(labelModeSpinner);
        
        panel.addView(labelRow);
        
        // Second row: Action buttons
        LinearLayout buttonRow = new LinearLayout(this);
        buttonRow.setOrientation(LinearLayout.HORIZONTAL);
        buttonRow.setPadding(5, 0, 5, 5);
        
        // Refresh button
        refreshButton = new Button(this);
        refreshButton.setText("Refresh WiFi");
        refreshButton.setTextColor(0xFFFFFFFF);
        refreshButton.setBackgroundColor(0xFF4fc3f7);
        refreshButton.setOnClickListener(v -> scanWiFi());
        
        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f
        );
        btnParams.setMargins(5, 0, 5, 0);
        refreshButton.setLayoutParams(btnParams);
        buttonRow.addView(refreshButton);
        
        // Back button
        Button backButton = new Button(this);
        backButton.setText("Back");
        backButton.setTextColor(0xFFFFFFFF);
        backButton.setBackgroundColor(0xFF666666);
        backButton.setOnClickListener(v -> finish());
        backButton.setLayoutParams(btnParams);
        buttonRow.addView(backButton);
        
        panel.addView(buttonRow);
        
        return panel;
    }
    
    private void setupGestures() {
        // Rotation gestures
        gestureDetector = new GestureDetector(this, new GestureDetector.SimpleOnGestureListener() {
            @Override
            public boolean onScroll(MotionEvent e1, MotionEvent e2, float distanceX, float distanceY) {
                cameraAngleY += distanceX * 0.3f;
                cameraAngleX -= distanceY * 0.3f;
                renderer.updateCamera(cameraAngleX, cameraAngleY, cameraDistance);
                return true;
            }
        });
        
        // Zoom gestures
        scaleGestureDetector = new ScaleGestureDetector(this, new ScaleGestureDetector.SimpleOnScaleGestureListener() {
            @Override
            public boolean onScale(ScaleGestureDetector detector) {
                cameraDistance *= detector.getScaleFactor();
                renderer.updateCamera(cameraAngleX, cameraAngleY, cameraDistance);
                return true;
            }
        });
        
        glSurfaceView.setOnTouchListener((v, event) -> {
            gestureDetector.onTouchEvent(event);
            scaleGestureDetector.onTouchEvent(event);
            return true;
        });
    }
    
    private boolean checkPermissions() {
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) 
                != PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, "Location permission required", Toast.LENGTH_SHORT).show();
            finish();
            return false;
        }
        return true;
    }
    
    private void startScanning() {
        if (isScanning) return;
        
        isScanning = true;
        statusText.setText("Scanning WiFi networks...");
        
        scanWiFi();
        
        // Auto-refresh every 5 seconds
        scanHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (isScanning) {
                    scanWiFi();
                    scanHandler.postDelayed(this, SCAN_INTERVAL_MS);
                }
            }
        }, SCAN_INTERVAL_MS);
        
        // Update compass continuously (fast!)
        startCompassUpdates();
    }
    
    private void stopScanning() {
        isScanning = false;
        scanHandler.removeCallbacksAndMessages(null);
    }
    
    private void scanWiFi() {
        new Thread(() -> {
            try {
                JSONObject wifiData = wifiScanner.scanNetworks();
                JSONObject connectedWifi = wifiScanner.getConnectedNetwork();
                String connectedBSSID = connectedWifi != null ? connectedWifi.optString("bssid", "") : "";
                
                JSONArray networks = wifiData.getJSONArray("networks");
                List<WiFiNetwork3D> network3DList = new ArrayList<>();
                
                for (int i = 0; i < networks.length(); i++) {
                    JSONObject network = networks.getJSONObject(i);
                    String ssid = network.optString("ssid", "<Hidden>");
                    String bssid = network.optString("bssid", "");
                    int signal = network.optInt("signal_strength", -90);
                    String security = network.optString("security", "Unknown");
                    int channel = network.optInt("channel", 0);
                    int frequency = network.optInt("frequency", 0);
                    String band = network.optString("band", "Unknown");
                    boolean isConnected = bssid.equals(connectedBSSID);
                    
                    WiFiNetwork3D network3D = new WiFiNetwork3D(ssid, bssid, signal, security, 
                                                                 channel, frequency, band, isConnected);
                    
                    // Use compass bearing to position network (if available)
                    if (orientationSensor != null && orientationSensor.hasOrientation()) {
                        // For now, distribute networks evenly around compass
                        // TODO: Use actual bearing from triangulation data
                        float bearing = (360f * i / networks.length());
                        network3D.updateBearing(bearing);
                    }
                    
                    network3DList.add(network3D);
                }
                
                // Update renderer with new network data
                renderer.updateWiFiNetworks(network3DList);
                
                // Store networks for label updates
                synchronized (currentNetworks) {
                    currentNetworks = new ArrayList<>(network3DList);
                }
                
                int count = networks.length();
                runOnUiThread(() -> {
                    networkCountText.setText("Networks: " + count);
                    statusText.setText("Last scan: " + count + " networks detected");
                    updateNetworkLabels();
                });
                
                Log.i(TAG, "📶 Updated 3D view with " + count + " networks");
                
            } catch (Exception e) {
                Log.e(TAG, "Error scanning WiFi", e);
                runOnUiThread(() -> statusText.setText("Error: " + e.getMessage()));
            }
        }).start();
    }
    
    private void startCompassUpdates() {
        // Update compass at 30 Hz for smooth rotation
        Handler compassHandler = new Handler(Looper.getMainLooper());
        compassHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (isScanning && orientationSensor != null && orientationSensor.hasOrientation()) {
                    float heading = orientationSensor.getAzimuth();
                    String direction = orientationSensor.getCardinalDirection();
                    
                    // Update renderer
                    renderer.updateDeviceHeading(heading);
                    
                    // Update UI
                    compassText.setText(String.format("Heading: %.0f° %s", heading, direction));
                    
                    // Update label positions as device rotates
                    updateNetworkLabels();
                    
                    // Continue updating
                    compassHandler.postDelayed(this, 33); // ~30 FPS
                }
            }
        }, 33);
    }
    
    /**
     * Update network labels overlay
     * Projects 3D positions to 2D screen coordinates using renderer's camera matrices
     */
    private void updateNetworkLabels() {
        if (labelOverlay == null || renderer == null) return;
        
        runOnUiThread(() -> {
            // Clear existing labels
            labelOverlay.removeAllViews();
            
            if (!showLabels || currentNetworks.isEmpty()) {
                return;
            }
            
            // Get screen positions from renderer (uses actual 3D projection)
            List<WiFi3DRenderer.NetworkScreenPosition> positions = renderer.getNetworkScreenPositions();
            
            // Add labels at projected screen positions
            for (WiFi3DRenderer.NetworkScreenPosition pos : positions) {
                TextView label = new TextView(this);
                label.setText(pos.network.getShortLabel(labelMode));
                label.setTextColor(0xFFFFFFFF);
                label.setTextSize(11);
                label.setBackgroundColor(0xCC000000);
                label.setPadding(8, 4, 8, 4);
                label.setShadowLayer(3, 0, 0, 0xFF000000);
                
                // Position label at projected screen coordinates
                FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.WRAP_CONTENT,
                        FrameLayout.LayoutParams.WRAP_CONTENT
                );
                
                // Center label on the sphere position
                // (We'll adjust after measuring the label, but this is close enough)
                params.leftMargin = (int)pos.screenX - 50;  // Approximate center offset
                params.topMargin = (int)pos.screenY - 20;   // Position above sphere
                
                label.setLayoutParams(params);
                labelOverlay.addView(label);
            }
        });
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        glSurfaceView.onResume();
        if (orientationSensor != null) {
            orientationSensor.start();
        }
        if (!isScanning) {
            startScanning();
        }
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        glSurfaceView.onPause();
        if (orientationSensor != null) {
            orientationSensor.stop();
        }
        stopScanning();
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (orientationSensor != null) {
            orientationSensor.stop();
        }
        stopScanning();
    }
}
