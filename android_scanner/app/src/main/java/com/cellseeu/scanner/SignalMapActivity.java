package com.cellseeu.scanner;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Walk-and-scan signal mapping screen.
 *
 * Collects repeated WiFi observations with device pose and uploads them to the
 * generic Flask signal mapping API. The UI is intentionally sparse: the user
 * should be able to walk, glance, and understand whether mapping is working.
 */
public class SignalMapActivity extends AppCompatActivity {
    private static final int PERMISSION_REQUEST_CODE = 33;
    private static final long SAMPLE_INTERVAL_MS = 5000;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private Runnable sampleRunnable;

    private WiFiScanner wifiScanner;
    private OrientationSensor orientationSensor;
    private LocationManager locationManager;

    private CompassDialView compassDialView;
    private TextView headingText;
    private TextView sampleCountText;
    private TextView strongestText;
    private TextView locationText;
    private TextView uploadText;
    private TextView sessionText;
    private Button startStopButton;

    private boolean isMapping = false;
    private int sampleCount = 0;
    private String sessionId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        wifiScanner = new WiFiScanner(this);
        orientationSensor = new OrientationSensor(this);
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        sessionId = "android-map-" + System.currentTimeMillis();

        setContentView(createLayout());

        if (orientationSensor.sensorsAvailable()) {
            orientationSensor.start();
        }

        if (!hasPermissions()) {
            ActivityCompat.requestPermissions(
                    this,
                    new String[]{
                            Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION
                    },
                    PERMISSION_REQUEST_CODE
            );
        }

        startCompassLoop();
    }

    private View createLayout() {
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(0xFF07111F);

        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(28, 28, 28, 28);

        TextView title = new TextView(this);
        title.setText("Signal Map");
        title.setTextColor(0xFFFFFFFF);
        title.setTextSize(30);
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        title.setPadding(0, 0, 0, 8);
        content.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("Walk slowly and let CellSeeU build a signal field.");
        subtitle.setTextColor(0xFF9DB4C8);
        subtitle.setTextSize(15);
        subtitle.setGravity(Gravity.CENTER_HORIZONTAL);
        subtitle.setPadding(0, 0, 0, 22);
        content.addView(subtitle);

        compassDialView = new CompassDialView(this);
        LinearLayout.LayoutParams compassParams = new LinearLayout.LayoutParams(230, 230);
        compassParams.gravity = Gravity.CENTER_HORIZONTAL;
        compassParams.setMargins(0, 4, 0, 18);
        content.addView(compassDialView, compassParams);

        headingText = metricText("Heading: calibrating...");
        sampleCountText = metricText("Samples: 0");
        strongestText = metricText("Strongest WiFi: --");
        locationText = metricText("Location: waiting...");
        uploadText = metricText("Upload: idle");
        sessionText = metricText("Session: " + sessionId);

        content.addView(headingText);
        content.addView(sampleCountText);
        content.addView(strongestText);
        content.addView(locationText);
        content.addView(uploadText);
        content.addView(sessionText);

        startStopButton = new Button(this);
        startStopButton.setText("Start Mapping");
        startStopButton.setTextSize(18);
        startStopButton.setTextColor(Color.WHITE);
        startStopButton.setBackgroundColor(0xFF1E88E5);
        startStopButton.setOnClickListener(v -> {
            if (isMapping) {
                stopMapping();
            } else {
                startMapping();
            }
        });
        LinearLayout.LayoutParams buttonParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        buttonParams.setMargins(0, 26, 0, 0);
        content.addView(startStopButton, buttonParams);

        Button backButton = new Button(this);
        backButton.setText("Back");
        backButton.setTextSize(16);
        backButton.setTextColor(Color.WHITE);
        backButton.setBackgroundColor(0xFF263238);
        backButton.setOnClickListener(v -> finish());
        LinearLayout.LayoutParams backParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
        );
        backParams.setMargins(0, 12, 0, 0);
        content.addView(backButton, backParams);

        root.addView(content, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));
        return root;
    }

    private TextView metricText(String text) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTextColor(0xFFEAF2F8);
        label.setTextSize(16);
        label.setPadding(0, 8, 0, 8);
        return label;
    }

    private void startMapping() {
        if (!hasPermissions()) {
            Toast.makeText(this, "Location permission is required for mapping", Toast.LENGTH_SHORT).show();
            return;
        }

        isMapping = true;
        sampleCount = 0;
        sessionId = "android-map-" + System.currentTimeMillis();
        sessionText.setText("Session: " + sessionId);
        sampleCountText.setText("Samples: 0");
        startStopButton.setText("Stop Mapping");
        startStopButton.setBackgroundColor(0xFFD32F2F);
        uploadText.setText("Upload: starting...");

        sampleRunnable = new Runnable() {
            @Override
            public void run() {
                if (!isMapping) {
                    return;
                }
                collectAndUploadSample();
                handler.postDelayed(this, SAMPLE_INTERVAL_MS);
            }
        };
        handler.post(sampleRunnable);
    }

    private void stopMapping() {
        isMapping = false;
        handler.removeCallbacks(sampleRunnable);
        startStopButton.setText("Start Mapping");
        startStopButton.setBackgroundColor(0xFF1E88E5);
        uploadText.setText("Upload: stopped");
    }

    private void collectAndUploadSample() {
        new Thread(() -> {
            try {
                Location location = getBestLocation();
                JSONObject wifiData = wifiScanner.scanNetworks();
                JSONArray networks = wifiData.optJSONArray("networks");
                if (networks == null) {
                    networks = new JSONArray();
                }

                JSONObject sample = buildMappingSample(location, networks);
                JSONObject strongest = findStrongestNetwork(networks);
                boolean uploaded = ApiClient.postJson("/api/signal-mapping/samples", sample);

                int networkCount = networks.length();
                JSONObject strongestFinal = strongest;
                Location locationFinal = location;
                runOnUiThread(() -> {
                    if (uploaded) {
                        sampleCount++;
                    }
                    sampleCountText.setText("Samples: " + sampleCount + " (" + networkCount + " WiFi readings)");
                    strongestText.setText("Strongest WiFi: " + describeNetwork(strongestFinal));
                    locationText.setText(describeLocation(locationFinal));
                    uploadText.setText(uploaded ? "Upload: ok" : "Upload: failed");
                });
            } catch (Exception e) {
                runOnUiThread(() -> uploadText.setText("Upload: " + e.getMessage()));
            }
        }).start();
    }

    private JSONObject buildMappingSample(Location location, JSONArray networks) throws Exception {
        JSONObject sample = new JSONObject();
        sample.put("session_id", sessionId);

        JSONObject pose = new JSONObject();
        if (location != null) {
            pose.put("latitude", location.getLatitude());
            pose.put("longitude", location.getLongitude());
            pose.put("accuracy_m", location.getAccuracy());
            if (location.hasAltitude()) {
                pose.put("altitude", location.getAltitude());
            }
        }
        if (orientationSensor != null && orientationSensor.hasOrientation()) {
            JSONObject orientation = orientationSensor.getOrientationJSON();
            pose.put("heading", orientation.optDouble("heading"));
            pose.put("pitch", orientation.optDouble("pitch"));
            pose.put("roll", orientation.optDouble("roll"));
            pose.put("cardinal_direction", orientation.optString("cardinal_direction"));
        }
        sample.put("device_pose", pose);

        JSONArray signals = new JSONArray();
        for (int i = 0; i < networks.length(); i++) {
            JSONObject network = networks.getJSONObject(i);
            String bssid = network.optString("bssid", "");
            if (bssid.isEmpty()) {
                continue;
            }
            JSONObject signal = new JSONObject();
            signal.put("type", "wifi");
            signal.put("source_id", bssid);
            signal.put("label", network.optString("ssid", "<Hidden Network>"));
            signal.put("strength_dbm", network.optInt("signal_strength", -100));
            signal.put("frequency_mhz", network.optInt("frequency", 0));
            signal.put("channel", network.optInt("channel", 0));
            signal.put("security", network.optString("security", "Unknown"));
            signals.put(signal);
        }
        sample.put("signals", signals);
        return sample;
    }

    private JSONObject findStrongestNetwork(JSONArray networks) {
        JSONObject strongest = null;
        int strongestSignal = -999;
        for (int i = 0; i < networks.length(); i++) {
            JSONObject network = networks.optJSONObject(i);
            if (network == null) {
                continue;
            }
            int signal = network.optInt("signal_strength", -999);
            if (strongest == null || signal > strongestSignal) {
                strongest = network;
                strongestSignal = signal;
            }
        }
        return strongest;
    }

    private String describeNetwork(JSONObject network) {
        if (network == null) {
            return "--";
        }
        return network.optString("ssid", "<Hidden Network>")
                + " (" + network.optInt("signal_strength", -100) + " dBm)";
    }

    private String describeLocation(Location location) {
        if (location == null) {
            return "Location: waiting...";
        }
        return String.format(
                "Location: %.6f, %.6f (+/- %.0fm)",
                location.getLatitude(),
                location.getLongitude(),
                location.getAccuracy()
        );
    }

    private Location getBestLocation() {
        if (!hasPermissions()) {
            return null;
        }
        Location gps = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER);
        Location network = locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER);
        if (gps == null) {
            return network;
        }
        if (network == null) {
            return gps;
        }
        return gps.getAccuracy() <= network.getAccuracy() ? gps : network;
    }

    private boolean hasPermissions() {
        return ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
    }

    private void startCompassLoop() {
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (orientationSensor != null && orientationSensor.hasOrientation()) {
                    float heading = orientationSensor.getAzimuth();
                    String direction = orientationSensor.getCardinalDirection();
                    headingText.setText(String.format("Heading: %.1f deg %s", heading, direction));
                    compassDialView.updateHeading(heading, direction);
                } else {
                    headingText.setText("Heading: calibrating...");
                }
                handler.postDelayed(this, 200);
            }
        }, 200);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopMapping();
        handler.removeCallbacksAndMessages(null);
        if (orientationSensor != null) {
            orientationSensor.stop();
        }
    }

    private static class CompassDialView extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private float heading = 0f;
        private String direction = "N";

        CompassDialView(Context context) {
            super(context);
        }

        void updateHeading(float heading, String direction) {
            this.heading = heading;
            this.direction = direction != null ? direction : "";
            invalidate();
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            float cx = getWidth() / 2f;
            float cy = getHeight() / 2f;
            float radius = Math.min(getWidth(), getHeight()) * 0.44f;

            paint.setStyle(Paint.Style.FILL);
            paint.setColor(0xFF0B1828);
            canvas.drawCircle(cx, cy, radius, paint);

            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(5f);
            paint.setColor(0xFF4FC3F7);
            canvas.drawCircle(cx, cy, radius, paint);

            paint.setStyle(Paint.Style.FILL);
            paint.setTextAlign(Paint.Align.CENTER);
            paint.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
            paint.setTextSize(24f);
            paint.setColor(0xFFFF5252);
            canvas.drawText("N", cx, cy - radius + 28f, paint);
            paint.setColor(Color.WHITE);
            canvas.drawText("S", cx, cy + radius - 14f, paint);
            canvas.drawText("W", cx - radius + 26f, cy + 8f, paint);
            canvas.drawText("E", cx + radius - 26f, cy + 8f, paint);

            float headingRad = (float) Math.toRadians(heading - 90f);
            float needleLength = radius * 0.68f;
            float endX = cx + needleLength * (float) Math.cos(headingRad);
            float endY = cy + needleLength * (float) Math.sin(headingRad);

            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeWidth(8f);
            paint.setColor(0xFFFF5252);
            canvas.drawLine(cx, cy, endX, endY, paint);

            paint.setStyle(Paint.Style.FILL);
            paint.setColor(0xFF4FC3F7);
            canvas.drawCircle(cx, cy, 9f, paint);

            paint.setTextSize(18f);
            paint.setColor(Color.WHITE);
            canvas.drawText(String.format("%.1f deg %s", heading, direction), cx, cy + 36f, paint);
        }
    }
}
