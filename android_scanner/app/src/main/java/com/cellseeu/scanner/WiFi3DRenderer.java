package com.cellseeu.scanner;

import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.opengl.Matrix;
import android.util.Log;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.List;

/**
 * OpenGL ES 2.0 Renderer for 3D WiFi visualization
 * Renders WiFi networks as spheres in 3D space with signal beams
 */
public class WiFi3DRenderer implements GLSurfaceView.Renderer {
    private static final String TAG = "WiFi3DRenderer";
    
    // Matrices for 3D transformation
    private final float[] projectionMatrix = new float[16];
    private final float[] viewMatrix = new float[16];
    private final float[] modelMatrix = new float[16];
    private final float[] mvpMatrix = new float[16];
    
    // Camera position
    private float cameraDistance = 25f;
    private float cameraAngleX = 30f;
    private float cameraAngleY = 0f;
    
    // Device orientation (from compass)
    private float deviceHeading = 0f;
    
    // WiFi networks to render
    private List<WiFiNetwork3D> wifiNetworks = new ArrayList<>();
    
    // Viewport dimensions for screen projection
    private int viewportWidth = 1;
    private int viewportHeight = 1;
    
    // OpenGL program handles
    private int shaderProgram;
    private int positionHandle;
    private int colorHandle;
    private int mvpMatrixHandle;
    
    // Geometry for rendering
    private Sphere deviceSphere;
    private Sphere networkSphere;
    private Grid gridFloor;
    private CompassRing compassRing;
    
    @Override
    public void onSurfaceCreated(GL10 unused, EGLConfig config) {
        // Set clear color (dark blue background)
        GLES20.glClearColor(0.05f, 0.05f, 0.1f, 1.0f);
        
        // Enable depth testing
        GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        GLES20.glDepthFunc(GLES20.GL_LEQUAL);
        
        // Enable blending for transparency
        GLES20.glEnable(GLES20.GL_BLEND);
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);
        
        // Load and compile shaders
        shaderProgram = createProgram(VERTEX_SHADER_CODE, FRAGMENT_SHADER_CODE);
        
        // Get shader uniform/attribute locations
        positionHandle = GLES20.glGetAttribLocation(shaderProgram, "vPosition");
        colorHandle = GLES20.glGetUniformLocation(shaderProgram, "vColor");
        mvpMatrixHandle = GLES20.glGetUniformLocation(shaderProgram, "uMVPMatrix");
        
        // Create geometry objects
        deviceSphere = new Sphere(0.5f, 16, 16);
        networkSphere = new Sphere(0.3f, 12, 12);
        gridFloor = new Grid(40f, 20);
        compassRing = new CompassRing(8f, 0.2f, 64);
        
        Log.i(TAG, "OpenGL initialized successfully");
    }
    
    @Override
    public void onSurfaceChanged(GL10 unused, int width, int height) {
        GLES20.glViewport(0, 0, width, height);
        
        this.viewportWidth = width;
        this.viewportHeight = height;
        
        float ratio = (float) width / height;
        
        // Projection matrix (perspective)
        Matrix.frustumM(projectionMatrix, 0, -ratio, ratio, -1, 1, 2, 100);
    }
    
    @Override
    public void onDrawFrame(GL10 unused) {
        // Clear color and depth buffers
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);
        
        // Set up camera position (view matrix)
        float eyeX = (float) (cameraDistance * Math.sin(Math.toRadians(cameraAngleY)) * Math.cos(Math.toRadians(cameraAngleX)));
        float eyeY = (float) (cameraDistance * Math.sin(Math.toRadians(cameraAngleX)));
        float eyeZ = (float) (cameraDistance * Math.cos(Math.toRadians(cameraAngleY)) * Math.cos(Math.toRadians(cameraAngleX)));
        
        Matrix.setLookAtM(viewMatrix, 0,
                eyeX, eyeY, eyeZ,  // Eye position
                0f, 0f, 0f,         // Look at center
                0f, 1f, 0f);        // Up vector
        
        // Use shader program
        GLES20.glUseProgram(shaderProgram);
        
        // Draw grid floor
        Matrix.setIdentityM(modelMatrix, 0);
        Matrix.translateM(modelMatrix, 0, 0f, -0.1f, 0f);
        drawObject(gridFloor.getVertexBuffer(), gridFloor.getVertexCount(), 
                  new float[]{0.3f, 0.3f, 0.3f, 0.5f}, GLES20.GL_LINES);
        
        // Draw compass ring
        Matrix.setIdentityM(modelMatrix, 0);
        drawObject(compassRing.getVertexBuffer(), compassRing.getVertexCount(),
                  new float[]{0.3f, 0.7f, 1.0f, 0.4f}, GLES20.GL_LINE_LOOP);

        // Draw fixed cardinal markers around the compass ring.
        drawCompassMarker(0f, new float[]{1.0f, 0.15f, 0.15f, 1.0f});
        drawCompassMarker(90f, new float[]{0.0f, 1.0f, 0.0f, 1.0f});
        drawCompassMarker(180f, new float[]{1.0f, 1.0f, 1.0f, 1.0f});
        drawCompassMarker(270f, new float[]{0.0f, 1.0f, 1.0f, 1.0f});

        // Draw device heading as a red arrow from the device.
        drawHeadingArrow();
        
        // Draw device sphere (you) at center
        Matrix.setIdentityM(modelMatrix, 0);
        float pulse = 1.0f + (float) Math.sin(System.currentTimeMillis() * 0.003) * 0.1f;
        Matrix.scaleM(modelMatrix, 0, pulse, pulse, pulse);
        drawObject(deviceSphere.getVertexBuffer(), deviceSphere.getVertexCount(),
                  new float[]{0.3f, 0.7f, 1.0f, 1.0f}, GLES20.GL_TRIANGLE_FAN);
        
        // Draw WiFi networks
        synchronized (wifiNetworks) {
            for (WiFiNetwork3D network : wifiNetworks) {
                drawWiFiNetwork(network);
            }
        }
    }
    
    private void drawWiFiNetwork(WiFiNetwork3D network) {
        float[] pos = network.getCartesianPosition();
        
        // Draw signal beam from device to network
        float[] beamVertices = {
                0f, 0f, 0f,    // Center (device)
                pos[0], pos[1], pos[2]  // Network position
        };
        
        FloatBuffer beamBuffer = ByteBuffer.allocateDirect(beamVertices.length * 4)
                .order(ByteOrder.nativeOrder()).asFloatBuffer();
        beamBuffer.put(beamVertices).position(0);
        
        Matrix.setIdentityM(modelMatrix, 0);
        float[] beamColor = new float[]{network.color[0], network.color[1], network.color[2], 0.2f};
        drawObject(beamBuffer, 2, beamColor, GLES20.GL_LINES);
        
        // Draw network sphere
        Matrix.setIdentityM(modelMatrix, 0);
        Matrix.translateM(modelMatrix, 0, pos[0], pos[1], pos[2]);
        
        // Make connected network slightly larger
        if (network.isConnected) {
            Matrix.scaleM(modelMatrix, 0, 1.3f, 1.3f, 1.3f);
        }
        
        float[] networkColor = new float[]{network.color[0], network.color[1], network.color[2], network.alpha};
        drawObject(networkSphere.getVertexBuffer(), networkSphere.getVertexCount(),
                  networkColor, GLES20.GL_TRIANGLE_FAN);
        
        // Note: Connector lines now drawn in 2D screen space (WiFi3DActivity)
        // 3D lines removed - they can't properly connect to 2D labels due to coordinate system mismatch
    }

    private void drawCompassMarker(float bearing, float[] color) {
        float bearingRad = (float) Math.toRadians(bearing);
        float x = 9.5f * (float) Math.sin(bearingRad);
        float z = 9.5f * (float) Math.cos(bearingRad);

        Matrix.setIdentityM(modelMatrix, 0);
        Matrix.translateM(modelMatrix, 0, x, 0f, z);
        Matrix.scaleM(modelMatrix, 0, 0.55f, 0.55f, 0.55f);
        drawObject(networkSphere.getVertexBuffer(), networkSphere.getVertexCount(),
                color, GLES20.GL_TRIANGLE_FAN);
    }

    private void drawHeadingArrow() {
        float headingRad = (float) Math.toRadians(deviceHeading);
        float endX = 7.0f * (float) Math.sin(headingRad);
        float endZ = 7.0f * (float) Math.cos(headingRad);

        float[] arrowVertices = {
                0f, 0.15f, 0f,
                endX, 0.15f, endZ
        };

        FloatBuffer arrowBuffer = ByteBuffer.allocateDirect(arrowVertices.length * 4)
                .order(ByteOrder.nativeOrder()).asFloatBuffer();
        arrowBuffer.put(arrowVertices).position(0);

        Matrix.setIdentityM(modelMatrix, 0);
        drawObject(arrowBuffer, 2, new float[]{1.0f, 0.25f, 0.25f, 1.0f}, GLES20.GL_LINES);

        Matrix.setIdentityM(modelMatrix, 0);
        Matrix.translateM(modelMatrix, 0, endX, 0.15f, endZ);
        Matrix.scaleM(modelMatrix, 0, 0.75f, 0.75f, 0.75f);
        drawObject(networkSphere.getVertexBuffer(), networkSphere.getVertexCount(),
                new float[]{1.0f, 0.25f, 0.25f, 1.0f}, GLES20.GL_TRIANGLE_FAN);
    }
    
    private void drawObject(FloatBuffer vertexBuffer, int vertexCount, float[] color, int drawMode) {
        // Calculate MVP matrix
        float[] tempMatrix = new float[16];
        Matrix.multiplyMM(tempMatrix, 0, viewMatrix, 0, modelMatrix, 0);
        Matrix.multiplyMM(mvpMatrix, 0, projectionMatrix, 0, tempMatrix, 0);
        
        // Pass matrices and color to shader
        GLES20.glUniformMatrix4fv(mvpMatrixHandle, 1, false, mvpMatrix, 0);
        GLES20.glUniform4fv(colorHandle, 1, color, 0);
        
        // Enable vertex array and set vertex data
        GLES20.glEnableVertexAttribArray(positionHandle);
        GLES20.glVertexAttribPointer(positionHandle, 3, GLES20.GL_FLOAT, false, 0, vertexBuffer);
        
        // Draw
        GLES20.glDrawArrays(drawMode, 0, vertexCount);
        
        // Disable vertex array
        GLES20.glDisableVertexAttribArray(positionHandle);
    }
    
    // ===== PUBLIC METHODS =====
    
    public void updateWiFiNetworks(List<WiFiNetwork3D> networks) {
        synchronized (wifiNetworks) {
            this.wifiNetworks = new ArrayList<>(networks);
        }
    }
    
    public void updateDeviceHeading(float heading) {
        this.deviceHeading = heading;
    }
    
    public void updateCamera(float angleX, float angleY, float distance) {
        this.cameraAngleX = Math.max(-89f, Math.min(89f, angleX));
        this.cameraAngleY = angleY % 360f;
        this.cameraDistance = Math.max(5f, Math.min(50f, distance));
    }
    
    /**
     * Project 3D world coordinate to 2D screen coordinate
     * Returns float[2] with x, y screen coordinates (or null if behind camera)
     */
    private float[] projectToScreen(float worldX, float worldY, float worldZ) {
        // Create point in homogeneous coordinates
        float[] point = {worldX, worldY, worldZ, 1.0f};
        float[] result = new float[4];
        
        // Transform by view matrix
        Matrix.multiplyMV(result, 0, viewMatrix, 0, point, 0);
        
        // Transform by projection matrix
        float[] projected = new float[4];
        Matrix.multiplyMV(projected, 0, projectionMatrix, 0, result, 0);
        
        // Check if point is in front of camera (positive w)
        if (projected[3] <= 0) {
            return null; // Behind camera
        }
        
        // Perspective divide (convert to NDC: -1 to 1)
        float ndcX = projected[0] / projected[3];
        float ndcY = projected[1] / projected[3];
        
        // Check if within view frustum
        if (Math.abs(ndcX) > 1.5f || Math.abs(ndcY) > 1.5f) {
            return null; // Outside view
        }
        
        // Convert NDC to screen coordinates
        // NDC: (-1, -1) = bottom-left, (1, 1) = top-right
        // Screen: (0, 0) = top-left, (width, height) = bottom-right
        float screenX = (ndcX + 1.0f) * 0.5f * viewportWidth;
        float screenY = (1.0f - ndcY) * 0.5f * viewportHeight; // Flip Y
        
        return new float[]{screenX, screenY};
    }
    
    /**
     * Get screen positions for all WiFi networks
     * Returns list of {network, screenX, screenY} or null if not visible
     */
    public static class NetworkScreenPosition {
        public WiFiNetwork3D network;
        public float screenX;
        public float screenY;
        
        public NetworkScreenPosition(WiFiNetwork3D network, float x, float y) {
            this.network = network;
            this.screenX = x;
            this.screenY = y;
        }
    }
    
    public List<NetworkScreenPosition> getNetworkScreenPositions() {
        List<NetworkScreenPosition> positions = new ArrayList<>();
        
        synchronized (wifiNetworks) {
            for (WiFiNetwork3D network : wifiNetworks) {
                float[] pos = network.getCartesianPosition();
                float[] screenPos = projectToScreen(pos[0], pos[1], pos[2]);
                
                if (screenPos != null) {
                    positions.add(new NetworkScreenPosition(network, screenPos[0], screenPos[1]));
                }
            }
        }
        
        return positions;
    }
    
    // ===== SHADER CODE =====
    
    private static final String VERTEX_SHADER_CODE =
            "uniform mat4 uMVPMatrix;" +
            "attribute vec4 vPosition;" +
            "void main() {" +
            "  gl_Position = uMVPMatrix * vPosition;" +
            "}";
    
    private static final String FRAGMENT_SHADER_CODE =
            "precision mediump float;" +
            "uniform vec4 vColor;" +
            "void main() {" +
            "  gl_FragColor = vColor;" +
            "}";
    
    private int createProgram(String vertexSource, String fragmentSource) {
        int vertexShader = loadShader(GLES20.GL_VERTEX_SHADER, vertexSource);
        int fragmentShader = loadShader(GLES20.GL_FRAGMENT_SHADER, fragmentSource);
        
        int program = GLES20.glCreateProgram();
        GLES20.glAttachShader(program, vertexShader);
        GLES20.glAttachShader(program, fragmentShader);
        GLES20.glLinkProgram(program);
        
        return program;
    }
    
    private int loadShader(int type, String shaderCode) {
        int shader = GLES20.glCreateShader(type);
        GLES20.glShaderSource(shader, shaderCode);
        GLES20.glCompileShader(shader);
        return shader;
    }
    
    // ===== GEOMETRY CLASSES =====
    
    /**
     * Sphere geometry
     */
    private static class Sphere {
        private FloatBuffer vertexBuffer;
        private int vertexCount;
        
        public Sphere(float radius, int stacks, int slices) {
            List<Float> vertices = new ArrayList<>();
            
            for (int i = 0; i <= stacks; i++) {
                float phi = (float) Math.PI * i / stacks;
                float y = radius * (float) Math.cos(phi);
                float r = radius * (float) Math.sin(phi);
                
                for (int j = 0; j <= slices; j++) {
                    float theta = 2 * (float) Math.PI * j / slices;
                    float x = r * (float) Math.cos(theta);
                    float z = r * (float) Math.sin(theta);
                    
                    vertices.add(x);
                    vertices.add(y);
                    vertices.add(z);
                }
            }
            
            vertexCount = vertices.size() / 3;
            
            float[] vertexArray = new float[vertices.size()];
            for (int i = 0; i < vertices.size(); i++) {
                vertexArray[i] = vertices.get(i);
            }
            
            vertexBuffer = ByteBuffer.allocateDirect(vertexArray.length * 4)
                    .order(ByteOrder.nativeOrder()).asFloatBuffer();
            vertexBuffer.put(vertexArray).position(0);
        }
        
        public FloatBuffer getVertexBuffer() { return vertexBuffer; }
        public int getVertexCount() { return vertexCount; }
    }
    
    /**
     * Grid floor geometry
     */
    private static class Grid {
        private FloatBuffer vertexBuffer;
        private int vertexCount;
        
        public Grid(float size, int divisions) {
            List<Float> vertices = new ArrayList<>();
            float step = size / divisions;
            float half = size / 2;
            
            // Horizontal lines
            for (int i = 0; i <= divisions; i++) {
                float pos = -half + i * step;
                vertices.add(-half); vertices.add(0f); vertices.add(pos);
                vertices.add(half);  vertices.add(0f); vertices.add(pos);
            }
            
            // Vertical lines
            for (int i = 0; i <= divisions; i++) {
                float pos = -half + i * step;
                vertices.add(pos); vertices.add(0f); vertices.add(-half);
                vertices.add(pos); vertices.add(0f); vertices.add(half);
            }
            
            vertexCount = vertices.size() / 3;
            
            float[] vertexArray = new float[vertices.size()];
            for (int i = 0; i < vertices.size(); i++) {
                vertexArray[i] = vertices.get(i);
            }
            
            vertexBuffer = ByteBuffer.allocateDirect(vertexArray.length * 4)
                    .order(ByteOrder.nativeOrder()).asFloatBuffer();
            vertexBuffer.put(vertexArray).position(0);
        }
        
        public FloatBuffer getVertexBuffer() { return vertexBuffer; }
        public int getVertexCount() { return vertexCount; }
    }
    
    /**
     * Compass ring geometry
     */
    private static class CompassRing {
        private FloatBuffer vertexBuffer;
        private int vertexCount;
        
        public CompassRing(float radius, float thickness, int segments) {
            List<Float> vertices = new ArrayList<>();
            
            for (int i = 0; i <= segments; i++) {
                float angle = 2 * (float) Math.PI * i / segments;
                float x = radius * (float) Math.cos(angle);
                float z = radius * (float) Math.sin(angle);
                
                vertices.add(x);
                vertices.add(0f);
                vertices.add(z);
            }
            
            vertexCount = vertices.size() / 3;
            
            float[] vertexArray = new float[vertices.size()];
            for (int i = 0; i < vertices.size(); i++) {
                vertexArray[i] = vertices.get(i);
            }
            
            vertexBuffer = ByteBuffer.allocateDirect(vertexArray.length * 4)
                    .order(ByteOrder.nativeOrder()).asFloatBuffer();
            vertexBuffer.put(vertexArray).position(0);
        }
        
        public FloatBuffer getVertexBuffer() { return vertexBuffer; }
        public int getVertexCount() { return vertexCount; }
    }
}
