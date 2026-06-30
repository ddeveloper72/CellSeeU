package com.cellseeu.scanner;

import android.Manifest;
import android.content.res.Configuration;
import android.content.pm.PackageManager;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
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
    private CompassDialView compassDialView;
    private Button refreshButton;
    
    // Label controls
    private ToggleButton labelToggle;
    private ToggleButton band24Toggle;
    private ToggleButton band5Toggle;
    private FrameLayout labelOverlay;
    private boolean showLabels = true;
    private boolean show24GHz = true;
    private boolean show5GHz = true;
    private WiFiNetwork3D.LabelMode labelMode = WiFiNetwork3D.LabelMode.NAME;
    private List<WiFiNetwork3D> currentNetworks = new ArrayList<>();
    
    private WiFiScanner wifiScanner;
    private OrientationSensor orientationSensor;
    
    private Handler scanHandler = new Handler(Looper.getMainLooper());
    private Handler compassHandler = new Handler(Looper.getMainLooper());
    private Runnable compassUpdateRunnable;
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
        
        // Full-screen 3D scene with overlays, matching the browser WiFi 3D view.
        FrameLayout rootLayout = new FrameLayout(this);
        rootLayout.setBackgroundColor(0xFF0a0a1a);

        // GLSurfaceView for 3D rendering
        glSurfaceView = new GLSurfaceView(this);
        glSurfaceView.setEGLContextClientVersion(2); // OpenGL ES 2.0
        
        renderer = new WiFi3DRenderer();
        glSurfaceView.setRenderer(renderer);
        glSurfaceView.setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);

        rootLayout.addView(glSurfaceView, new FrameLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
        ));

        boolean isLandscape = getResources().getConfiguration().orientation
                == Configuration.ORIENTATION_LANDSCAPE;

        rootLayout.addView(createInfoPanel(), topLeftParams(18, 18, 380));
        rootLayout.addView(
                createCollapsiblePanel("Controls", createControlPanel(), isLandscape),
                topRightParams(18, 18, 230)
        );
        rootLayout.addView(
                createCollapsiblePanel("Legend", createLegendPanel(), isLandscape),
                bottomRightParams(18, 18, 300)
        );

        compassDialView = new CompassDialView(this);
        rootLayout.addView(compassDialView, bottomLeftParams(18, 18, 170, 170));

        TextView helpText = createOverlayText("Drag to rotate - pinch to zoom");
        rootLayout.addView(helpText, bottomCenterParams(260, 18));
        
        // Add label overlay (on top of everything)
        labelOverlay = new FrameLayout(this);
        labelOverlay.setLayoutParams(new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));
        labelOverlay.setClickable(false);
        rootLayout.addView(labelOverlay);
        
        setContentView(rootLayout);
        
        // Initialize sensors
        wifiScanner = new WiFiScanner(this);
        orientationSensor = new OrientationSensor(this);
        
        if (orientationSensor.sensorsAvailable()) {
            orientationSensor.start();
            Log.i(TAG, "Orientation sensors started");
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
        panel.setPadding(18, 18, 18, 18);
        panel.setBackgroundColor(0xCC000000);

        TextView title = new TextView(this);
        title.setText("Your Device");
        title.setTextColor(0xFF4fc3f7);
        title.setTextSize(18);
        title.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        title.setPadding(0, 0, 0, 12);
        panel.addView(title);

        compassText = createOverlayText("Compass heading: -- deg");
        panel.addView(compassText);

        networkCountText = createOverlayText("Networks: 0");
        networkCountText.setPadding(0, 7, 0, 0);
        panel.addView(networkCountText);

        statusText = createOverlayText("Initializing...");
        statusText.setTextColor(0xFFaaaaaa);
        statusText.setTextSize(12);
        statusText.setPadding(0, 10, 0, 0);
        panel.addView(statusText);

        return panel;
    }

    private LinearLayout createControlPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(12, 12, 12, 12);
        panel.setBackgroundColor(0xCC000000);

        Button resetButton = createOverlayButton("Reset View", 0xFF4fc3f7);
        resetButton.setOnClickListener(v -> {
            cameraAngleX = 30f;
            cameraAngleY = 0f;
            cameraDistance = 25f;
            renderer.updateCamera(cameraAngleX, cameraAngleY, cameraDistance);
        });
        panel.addView(resetButton, overlayButtonParams());

        labelToggle = new ToggleButton(this);
        labelToggle.setTextOn("Labels: ON");
        labelToggle.setTextOff("Labels: OFF");
        labelToggle.setChecked(showLabels);
        labelToggle.setTextColor(0xFFFFFFFF);
        labelToggle.setBackgroundColor(0xFF4fc3f7);
        labelToggle.setOnCheckedChangeListener((buttonView, isChecked) -> {
            showLabels = isChecked;
            updateNetworkLabels();
        });
        panel.addView(labelToggle, overlayButtonParams());

        band24Toggle = new ToggleButton(this);
        band24Toggle.setTextOn("2.4GHz ON");
        band24Toggle.setTextOff("2.4GHz OFF");
        band24Toggle.setChecked(show24GHz);
        band24Toggle.setTextColor(0xFFFFFFFF);
        band24Toggle.setBackgroundColor(0xFF66BB6A);
        band24Toggle.setOnCheckedChangeListener((buttonView, isChecked) -> {
            show24GHz = isChecked;
            filterAndUpdateNetworks();
        });
        panel.addView(band24Toggle, overlayButtonParams());

        band5Toggle = new ToggleButton(this);
        band5Toggle.setTextOn("5GHz ON");
        band5Toggle.setTextOff("5GHz OFF");
        band5Toggle.setChecked(show5GHz);
        band5Toggle.setTextColor(0xFFFFFFFF);
        band5Toggle.setBackgroundColor(0xFFEF5350);
        band5Toggle.setOnCheckedChangeListener((buttonView, isChecked) -> {
            show5GHz = isChecked;
            filterAndUpdateNetworks();
        });
        panel.addView(band5Toggle, overlayButtonParams());

        refreshButton = createOverlayButton("Refresh Data", 0xFF4fc3f7);
        refreshButton.setOnClickListener(v -> scanWiFi());
        panel.addView(refreshButton, overlayButtonParams());

        Button backButton = createOverlayButton("Back", 0xFF666666);
        backButton.setOnClickListener(v -> finish());
        panel.addView(backButton, overlayButtonParams());

        return panel;
    }

    private LinearLayout createLegendPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(16, 16, 16, 16);
        panel.setBackgroundColor(0xCC000000);

        TextView title = createOverlayText("Signal Strength");
        title.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        panel.addView(title);
        panel.addView(createLegendRow(0xFF00FF00, "Excellent (-30 to -50 dBm)"));
        panel.addView(createLegendRow(0xFF7FFF00, "Good (-50 to -60 dBm)"));
        panel.addView(createLegendRow(0xFFFFFF00, "Fair (-60 to -70 dBm)"));
        panel.addView(createLegendRow(0xFFFFA500, "Weak (-70 to -80 dBm)"));
        panel.addView(createLegendRow(0xFFFF0000, "Very Weak (< -80 dBm)"));
        return panel;
    }

    private LinearLayout createLegendRow(int color, String labelText) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, 8, 0, 0);

        View swatch = new View(this);
        android.graphics.drawable.GradientDrawable circle = new android.graphics.drawable.GradientDrawable();
        circle.setShape(android.graphics.drawable.GradientDrawable.OVAL);
        circle.setColor(color);
        swatch.setBackground(circle);
        LinearLayout.LayoutParams swatchParams = new LinearLayout.LayoutParams(24, 24);
        swatchParams.setMargins(0, 0, 12, 0);
        row.addView(swatch, swatchParams);

        TextView label = createOverlayText(labelText);
        label.setTextSize(11);
        row.addView(label);
        return row;
    }

    private LinearLayout createCollapsiblePanel(String title, View content, boolean startCollapsed) {
        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setBackgroundColor(0xCC000000);
        container.setPadding(8, 8, 8, 8);

        Button toggle = createOverlayButton(
                startCollapsed ? title : title + " -",
                0xFF26364A
        );
        toggle.setAllCaps(false);
        content.setVisibility(startCollapsed ? View.GONE : View.VISIBLE);
        toggle.setOnClickListener(v -> {
            boolean willShow = content.getVisibility() != View.VISIBLE;
            content.setVisibility(willShow ? View.VISIBLE : View.GONE);
            toggle.setText(willShow ? title + " -" : title);
        });

        container.addView(toggle, overlayButtonParams());
        container.addView(content);
        return container;
    }

    private Button createOverlayButton(String text, int backgroundColor) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextColor(0xFFFFFFFF);
        button.setBackgroundColor(backgroundColor);
        return button;
    }

    private TextView createOverlayText(String text) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTextColor(0xFFFFFFFF);
        label.setTextSize(14);
        return label;
    }

    private LinearLayout.LayoutParams overlayButtonParams() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, 0, 0, 8);
        return params;
    }

    private FrameLayout.LayoutParams topLeftParams(int left, int top, int width) {
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(width, FrameLayout.LayoutParams.WRAP_CONTENT);
        params.leftMargin = left;
        params.topMargin = top;
        return params;
    }

    private FrameLayout.LayoutParams topRightParams(int right, int top, int width) {
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(width, FrameLayout.LayoutParams.WRAP_CONTENT);
        params.gravity = android.view.Gravity.TOP | android.view.Gravity.RIGHT;
        params.rightMargin = right;
        params.topMargin = top;
        return params;
    }

    private FrameLayout.LayoutParams bottomRightParams(int right, int bottom, int width) {
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(width, FrameLayout.LayoutParams.WRAP_CONTENT);
        params.gravity = android.view.Gravity.BOTTOM | android.view.Gravity.RIGHT;
        params.rightMargin = right;
        params.bottomMargin = bottom;
        return params;
    }

    private FrameLayout.LayoutParams bottomLeftParams(int left, int bottom, int width, int height) {
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(width, height);
        params.gravity = android.view.Gravity.BOTTOM | android.view.Gravity.LEFT;
        params.leftMargin = left;
        params.bottomMargin = bottom;
        return params;
    }

    private FrameLayout.LayoutParams bottomCenterParams(int width, int bottom) {
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(width, FrameLayout.LayoutParams.WRAP_CONTENT);
        params.gravity = android.view.Gravity.BOTTOM | android.view.Gravity.CENTER_HORIZONTAL;
        params.bottomMargin = bottom;
        return params;
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
        compassHandler.removeCallbacksAndMessages(null);
    }
    
    private void scanWiFi() {
        new Thread(() -> {
            try {
                JSONObject wifiData = wifiScanner.scanNetworks();
                JSONObject connectedWifi = wifiScanner.getConnectedNetwork();
                String connectedBSSID = connectedWifi != null ? connectedWifi.optString("bssid", "") : "";
                
                JSONArray networks = wifiData.getJSONArray("networks");
                List<WiFiNetwork3D> network3DList = new ArrayList<>();
                float heading = (orientationSensor != null && orientationSensor.hasOrientation())
                        ? orientationSensor.getAzimuth()
                        : 0f;
                
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
                    
                    network3D.updateBearing(heading, i, networks.length());
                    
                    network3DList.add(network3D);
                }
                
                // Update renderer with new network data
                renderer.updateWiFiNetworks(network3DList);
                
                // Store networks for label updates and filtering
                synchronized (currentNetworks) {
                    currentNetworks = new ArrayList<>(network3DList);
                }
                
                // Apply band filtering
                int totalCount = network3DList.size();
                runOnUiThread(() -> {
                    filterAndUpdateNetworks();
                    statusText.setText(String.format("Last scan: %d networks detected", totalCount));
                });
                
            } catch (Exception e) {
                Log.e(TAG, "Error scanning WiFi", e);
                runOnUiThread(() -> statusText.setText("Error: " + e.getMessage()));
            }
        }).start();
    }
    
    private void startCompassUpdates() {
        compassHandler.removeCallbacksAndMessages(null);
        compassUpdateRunnable = new Runnable() {
            @Override
            public void run() {
                if (!isScanning) {
                    return;
                }

                if (orientationSensor != null && orientationSensor.hasOrientation()) {
                    float heading = orientationSensor.getAzimuth();
                    String direction = orientationSensor.getCardinalDirection();
                    
                    // Update renderer
                    renderer.updateDeviceHeading(heading);
                    
                    // Update UI
                    compassText.setText(String.format("Compass heading: %.1f deg %s", heading, direction));
                    if (compassDialView != null) {
                        compassDialView.updateHeading(heading, direction);
                    }
                    
                    // Update label positions as device rotates
                    updateNetworkLabels();
                } else if (orientationSensor != null && orientationSensor.sensorsAvailable()) {
                    compassText.setText("Compass heading: calibrating...");
                }

                compassHandler.postDelayed(this, 33); // ~30 FPS
            }
        };
        compassHandler.postDelayed(compassUpdateRunnable, 33);
    }
    
    /**
     * Filter networks by band and update display
     */
    private void filterAndUpdateNetworks() {
        List<WiFiNetwork3D> filteredNetworks = new ArrayList<>();
        
        synchronized (currentNetworks) {
            for (WiFiNetwork3D network : currentNetworks) {
                boolean include = false;
                
                if (network.band.equals("2.4GHz") && show24GHz) {
                    include = true;
                } else if (network.band.equals("5GHz") && show5GHz) {
                    include = true;
                } else if (!network.band.equals("2.4GHz") && !network.band.equals("5GHz")) {
                    include = true;
                }
                
                if (include) {
                    filteredNetworks.add(network);
                }
            }
        }
        
        // Update renderer with filtered networks
        renderer.updateWiFiNetworks(filteredNetworks);
        
        // Update labels
        updateNetworkLabels();
        
        // Update network count
        int total = currentNetworks.size();
        int shown = filteredNetworks.size();
        runOnUiThread(() -> {
            networkCountText.setText(String.format("Networks: %d/%d", shown, total));
        });
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
            
            // Filter positions by band
            List<WiFi3DRenderer.NetworkScreenPosition> filteredPositions = new ArrayList<>();
            for (WiFi3DRenderer.NetworkScreenPosition pos : positions) {
                boolean include = false;
                
                if (pos.network.band.equals("2.4GHz") && show24GHz) {
                    include = true;
                } else if (pos.network.band.equals("5GHz") && show5GHz) {
                    include = true;
                } else if (!pos.network.band.equals("2.4GHz") && !pos.network.band.equals("5GHz")) {
                    include = true;
                }
                
                if (include) {
                    filteredPositions.add(pos);
                }
            }
            
            // Add labels with connector lines at projected screen positions
            for (WiFi3DRenderer.NetworkScreenPosition pos : filteredPositions) {
                // Create label with connector line
                addLabelWithConnector(pos);
            }
        });
    }
    
    /**
     * Add a label with a 2D connector line to its WiFi source
     */
    private void addLabelWithConnector(WiFi3DRenderer.NetworkScreenPosition pos) {
        // Label position - very close to sphere (~5-8 pixels)
        int labelOffsetX = 8;   // Offset to the right
        int labelOffsetY = -8;  // Offset upward (negative = up)
        
        int labelX = (int)pos.screenX + labelOffsetX;
        int labelY = (int)pos.screenY + labelOffsetY;
        
        // Calculate sphere position within connector view (account for negative offsets)
        // If label is ABOVE sphere (negative Y offset), sphere is below view's top
        // If label is LEFT of sphere (negative X offset), sphere is right of view's left
        final int sphereInViewX = Math.max(0, -labelOffsetX);
        final int sphereInViewY = Math.max(0, -labelOffsetY);
        final int labelInViewX = sphereInViewX + labelOffsetX;
        final int labelInViewY = sphereInViewY + labelOffsetY;
        
        // Create a 2D connector line in screen space (CORRECT APPROACH!)
        // This View draws from sphere screen position to label position
        View connector = new View(this) {
            @Override
            protected void onDraw(android.graphics.Canvas canvas) {
                super.onDraw(canvas);
                
                android.graphics.Paint paint = new android.graphics.Paint();
                paint.setAntiAlias(true);
                
                // Draw line from sphere to label (both in view coordinates)
                paint.setColor(0xFFFFFFFF);  // White line
                paint.setStrokeWidth(2);
                canvas.drawLine(sphereInViewX, sphereInViewY, labelInViewX, labelInViewY, paint);
                
                // Draw anchor circle at sphere
                paint.setStyle(android.graphics.Paint.Style.FILL);
                paint.setColor(0xFFFFFF00);  // Yellow anchor
                canvas.drawCircle(sphereInViewX, sphereInViewY, 6, paint);
                
                // White outline
                paint.setStyle(android.graphics.Paint.Style.STROKE);
                paint.setColor(0xFFFFFFFF);
                paint.setStrokeWidth(1);
                canvas.drawCircle(sphereInViewX, sphereInViewY, 6, paint);
            }
        };
        
        // Enable drawing
        connector.setWillNotDraw(false);
        
        // Position connector view at topmost/leftmost point of bounding box
        FrameLayout.LayoutParams connectorParams = new FrameLayout.LayoutParams(
                Math.abs(labelOffsetX) + 20,
                Math.abs(labelOffsetY) + 20
        );
        connectorParams.leftMargin = (int)pos.screenX + Math.min(0, labelOffsetX);  // Account for negative X
        connectorParams.topMargin = (int)pos.screenY + Math.min(0, labelOffsetY);   // Account for negative Y
        connector.setLayoutParams(connectorParams);
        labelOverlay.addView(connector);
        
        // Create label
        TextView label = new TextView(this);
        label.setText(pos.network.getShortLabel(labelMode));
        label.setTextColor(0xFFFFFFFF);
        label.setTextSize(12);
        label.setBackgroundColor(0xDD000000);
        label.setPadding(8, 4, 8, 4);
        label.setShadowLayer(3, 0, 0, 0xFF000000);
        
        // Prevent text wrapping - single line only
        label.setSingleLine(true);
        label.setMaxLines(1);
        
        // Add colored border matching signal strength
        android.graphics.drawable.GradientDrawable border = new android.graphics.drawable.GradientDrawable();
        border.setColor(0xDD000000);  // Background
        border.setStroke(3, android.graphics.Color.rgb(
                (int)(pos.network.color[0] * 255),
                (int)(pos.network.color[1] * 255),
                (int)(pos.network.color[2] * 255)
        ));  // Border color matches WiFi sphere
        border.setCornerRadius(4);
        label.setBackground(border);
        
        // Position label offset from sphere
        FrameLayout.LayoutParams labelParams = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
        );
        labelParams.leftMargin = labelX;
        labelParams.topMargin = labelY;
        
        label.setLayoutParams(labelParams);
        labelOverlay.addView(label);
    }

    private static class CompassDialView extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private float heading = 0f;
        private String direction = "N";

        public CompassDialView(android.content.Context context) {
            super(context);
            setWillNotDraw(false);
        }

        public void updateHeading(float heading, String direction) {
            this.heading = heading;
            this.direction = direction != null ? direction : "";
            invalidate();
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);

            float cx = getWidth() / 2f;
            float cy = getHeight() / 2f;
            float radius = Math.min(getWidth(), getHeight()) * 0.43f;

            paint.setStyle(Paint.Style.FILL);
            paint.setColor(0xCC000000);
            canvas.drawCircle(cx, cy, radius, paint);

            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(4f);
            paint.setColor(0xFF4fc3f7);
            canvas.drawCircle(cx, cy, radius, paint);

            paint.setStyle(Paint.Style.FILL);
            paint.setTextAlign(Paint.Align.CENTER);
            paint.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
            paint.setTextSize(22f);

            paint.setColor(0xFFFF5252);
            canvas.drawText("N", cx, cy - radius + 24f, paint);
            paint.setColor(Color.WHITE);
            canvas.drawText("S", cx, cy + radius - 12f, paint);
            canvas.drawText("W", cx - radius + 22f, cy + 8f, paint);
            canvas.drawText("E", cx + radius - 22f, cy + 8f, paint);

            float headingRad = (float) Math.toRadians(heading - 90f);
            float needleLength = radius * 0.68f;
            float endX = cx + needleLength * (float) Math.cos(headingRad);
            float endY = cy + needleLength * (float) Math.sin(headingRad);

            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(7f);
            paint.setColor(0xFFFF5252);
            canvas.drawLine(cx, cy, endX, endY, paint);

            paint.setStyle(Paint.Style.FILL);
            paint.setColor(0xFF4fc3f7);
            canvas.drawCircle(cx, cy, 8f, paint);

            paint.setTextSize(18f);
            paint.setTextAlign(Paint.Align.CENTER);
            paint.setColor(Color.WHITE);
            canvas.drawText(String.format("%.1f deg %s", heading, direction), cx, cy + 33f, paint);
        }
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
