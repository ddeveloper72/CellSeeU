package com.cellseeu.scanner;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.util.Log;
import android.view.Surface;
import android.view.WindowManager;

import org.json.JSONException;
import org.json.JSONObject;

/**
 * OrientationSensor - Reads device orientation from compass and accelerometer
 * 
 * Provides:
 * - Heading (azimuth): 0-360° (0=North, 90=East, 180=South, 270=West)
 * - Pitch: Device tilt up/down (-180 to 180°)
 * - Roll: Device tilt left/right (-90 to 90°)
 * 
 * Used for WiFi directional positioning - "seeing" where WiFi signals come from
 */
public class OrientationSensor implements SensorEventListener {
    private static final String TAG = "OrientationSensor";
    private static final float UPRIGHT_Z_RATIO_THRESHOLD = 0.45f;
    
    private SensorManager sensorManager;
    private WindowManager windowManager;
    private Sensor accelerometer;
    private Sensor magnetometer;
    
    private float[] gravity = new float[3];
    private float[] geomagnetic = new float[3];
    private float[] rotationMatrix = new float[9];
    private float[] remappedRotationMatrix = new float[9];
    private float[] orientationAngles = new float[3];
    
    private boolean hasGravity = false;
    private boolean hasGeomagnetic = false;
    
    // Current orientation in degrees
    private float azimuth = 0f;    // Heading (0-360°)
    private float pitch = 0f;      // Tilt up/down
    private float roll = 0f;       // Tilt left/right
    
    private long lastUpdate = 0;
    
    /**
     * Initialize orientation sensors
     */
    public OrientationSensor(Context context) {
        sensorManager = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);
        windowManager = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
        
        if (sensorManager != null) {
            accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
            magnetometer = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD);
            
            if (accelerometer == null) {
                Log.w(TAG, "Accelerometer not available");
            }
            if (magnetometer == null) {
                Log.w(TAG, "Magnetometer not available");
            }
        }
    }
    
    /**
     * Start listening to orientation sensors
     */
    public void start() {
        if (sensorManager == null) {
            Log.e(TAG, "SensorManager not available");
            return;
        }
        
        if (accelerometer != null) {
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_UI);
            Log.d(TAG, "Accelerometer started");
        }
        
        if (magnetometer != null) {
            sensorManager.registerListener(this, magnetometer, SensorManager.SENSOR_DELAY_UI);
            Log.d(TAG, "Magnetometer started");
        }
    }
    
    /**
     * Stop listening to orientation sensors
     */
    public void stop() {
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
            Log.d(TAG, "Orientation sensors stopped");
        }
        hasGravity = false;
        hasGeomagnetic = false;
    }
    
    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            // Low-pass filter to smooth accelerometer data
            gravity[0] = 0.8f * gravity[0] + 0.2f * event.values[0];
            gravity[1] = 0.8f * gravity[1] + 0.2f * event.values[1];
            gravity[2] = 0.8f * gravity[2] + 0.2f * event.values[2];
            hasGravity = true;
        }
        
        if (event.sensor.getType() == Sensor.TYPE_MAGNETIC_FIELD) {
            // Low-pass filter to smooth magnetometer data
            geomagnetic[0] = 0.8f * geomagnetic[0] + 0.2f * event.values[0];
            geomagnetic[1] = 0.8f * geomagnetic[1] + 0.2f * event.values[1];
            geomagnetic[2] = 0.8f * geomagnetic[2] + 0.2f * event.values[2];
            hasGeomagnetic = true;
        }
        
        // Calculate orientation when both sensors have data
        if (hasGravity && hasGeomagnetic) {
            boolean success = SensorManager.getRotationMatrix(rotationMatrix, null, gravity, geomagnetic);
            
            if (success) {
                SensorManager.getOrientation(getDisplayAlignedRotationMatrix(), orientationAngles);
                
                // Convert radians to degrees
                float flatAzimuth = (float) Math.toDegrees(orientationAngles[0]);
                pitch = (float) Math.toDegrees(orientationAngles[1]);
                roll = (float) Math.toDegrees(orientationAngles[2]);
                
                // Normalize azimuth to 0-360°
                azimuth = normalizeDegrees(isDeviceUpright()
                        ? calculateBackFacingHeading()
                        : flatAzimuth);
                
                lastUpdate = System.currentTimeMillis();
            }
        }
    }

    private float[] getDisplayAlignedRotationMatrix() {
        int axisX = SensorManager.AXIS_X;
        int axisY = SensorManager.AXIS_Y;
        int rotation = windowManager != null
                ? windowManager.getDefaultDisplay().getRotation()
                : Surface.ROTATION_0;

        switch (rotation) {
            case Surface.ROTATION_90:
                axisX = SensorManager.AXIS_Y;
                axisY = SensorManager.AXIS_MINUS_X;
                break;
            case Surface.ROTATION_180:
                axisX = SensorManager.AXIS_MINUS_X;
                axisY = SensorManager.AXIS_MINUS_Y;
                break;
            case Surface.ROTATION_270:
                axisX = SensorManager.AXIS_MINUS_Y;
                axisY = SensorManager.AXIS_X;
                break;
            case Surface.ROTATION_0:
            default:
                break;
        }

        boolean remapped = SensorManager.remapCoordinateSystem(
                rotationMatrix,
                axisX,
                axisY,
                remappedRotationMatrix
        );
        return remapped ? remappedRotationMatrix : rotationMatrix;
    }

    private float normalizeDegrees(float degrees) {
        float normalized = degrees % 360f;
        return normalized < 0f ? normalized + 360f : normalized;
    }

    private boolean isDeviceUpright() {
        float magnitude = (float) Math.sqrt(
                gravity[0] * gravity[0]
                        + gravity[1] * gravity[1]
                        + gravity[2] * gravity[2]
        );
        if (magnitude == 0f) {
            return false;
        }

        float zRatio = Math.abs(gravity[2]) / magnitude;
        return zRatio < UPRIGHT_Z_RATIO_THRESHOLD;
    }

    private float calculateBackFacingHeading() {
        // R maps device axes into world axes: world X is east, world Y is north.
        // The user's forward view through an upright screen follows the phone back (-Z).
        float east = -rotationMatrix[2];
        float north = -rotationMatrix[5];
        return (float) Math.toDegrees(Math.atan2(east, north));
    }
    
    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        String accuracyStr = "";
        switch (accuracy) {
            case SensorManager.SENSOR_STATUS_UNRELIABLE:
                accuracyStr = "UNRELIABLE";
                break;
            case SensorManager.SENSOR_STATUS_ACCURACY_LOW:
                accuracyStr = "LOW";
                break;
            case SensorManager.SENSOR_STATUS_ACCURACY_MEDIUM:
                accuracyStr = "MEDIUM";
                break;
            case SensorManager.SENSOR_STATUS_ACCURACY_HIGH:
                accuracyStr = "HIGH";
                break;
        }
        Log.d(TAG, "" + sensor.getName() + " accuracy: " + accuracyStr);
    }
    
    /**
     * Get current heading (compass direction)
     * @return Azimuth in degrees (0=North, 90=East, 180=South, 270=West)
     */
    public float getAzimuth() {
        return azimuth;
    }
    
    /**
     * Get current pitch (tilt up/down)
     * @return Pitch in degrees
     */
    public float getPitch() {
        return pitch;
    }
    
    /**
     * Get current roll (tilt left/right)
     * @return Roll in degrees
     */
    public float getRoll() {
        return roll;
    }
    
    /**
     * Get compass direction as cardinal direction
     * @return "N", "NE", "E", "SE", "S", "SW", "W", "NW"
     */
    public String getCardinalDirection() {
        float degrees = azimuth;
        
        if (degrees >= 337.5 || degrees < 22.5) return "N";
        if (degrees >= 22.5 && degrees < 67.5) return "NE";
        if (degrees >= 67.5 && degrees < 112.5) return "E";
        if (degrees >= 112.5 && degrees < 157.5) return "SE";
        if (degrees >= 157.5 && degrees < 202.5) return "S";
        if (degrees >= 202.5 && degrees < 247.5) return "SW";
        if (degrees >= 247.5 && degrees < 292.5) return "W";
        if (degrees >= 292.5 && degrees < 337.5) return "NW";
        
        return "?";
    }
    
    /**
     * Check if orientation data is available
     * @return true if sensors have provided data
     */
    public boolean hasOrientation() {
        return hasGravity && hasGeomagnetic && (System.currentTimeMillis() - lastUpdate < 2000);
    }
    
    /**
     * Get orientation data as JSON
     * @return JSONObject with heading, pitch, roll, cardinal_direction
     */
    public JSONObject getOrientationJSON() {
        JSONObject json = new JSONObject();
        try {
            json.put("heading", Math.round(azimuth * 10) / 10.0); // Round to 1 decimal
            json.put("pitch", Math.round(pitch * 10) / 10.0);
            json.put("roll", Math.round(roll * 10) / 10.0);
            json.put("cardinal_direction", getCardinalDirection());
            json.put("has_orientation", hasOrientation());
            json.put("timestamp", System.currentTimeMillis());
        } catch (JSONException e) {
            Log.e(TAG, "Error creating orientation JSON", e);
        }
        return json;
    }
    
    /**
     * Check if sensors are available
     * @return true if both accelerometer and magnetometer exist
     */
    public boolean sensorsAvailable() {
        return accelerometer != null && magnetometer != null;
    }
}
