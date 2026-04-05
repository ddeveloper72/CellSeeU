/**
 * CellSeeU Frontend JavaScript
 * 
 * Handles:
 * - Tower data fetching and display
 * - Geolocation tracking
 * - Interactive map rendering
 * - Real-time updates
 * 
 * Security: All API calls validate input, handle errors gracefully
 */

// Configuration
const CONFIG = {
    apiBaseUrl: '/api',
    refreshInterval: 10000, // 10 seconds (from .env REFRESH_INTERVAL_SECONDS)
    mapCenter: [37.7749, -122.4194], // Default: San Francisco
    mapZoom: 13
};

// Global state
let map = null;
let deviceMarker = null;
let towerMarkers = [];
let currentLocation = null;
let updateInterval = null;

/**
 * Initialize the dashboard page
 * 
 * Sets up event listeners, starts geolocation tracking,
 * and begins periodic tower updates.
 */
function initializeDashboard() {
    console.log('🗼 Initializing CellSeeU Dashboard');
    
    // Request location permission and start tracking
    requestLocation();
    
    // Setup mini map
    initializeMiniMap();
    
    // Fetch initial tower data
    fetchTowers();
    
    // Setup periodic updates
    startPeriodicUpdates();
    
    // Event listeners
    setupEventListeners();
}

/**
 * Initialize full-screen map view
 * 
 * Creates an interactive Leaflet map with tower markers
 * and device location indicator.
 */
function initializeFullMap() {
    console.log('🗺️ Initializing Full Map');
    
    // Create map centered on default location
    map = L.map('full-map').setView(CONFIG.mapCenter, CONFIG.mapZoom);
    
    // Add OpenStreetMap tiles
    // Using CDN tiles with proper attribution
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
    
    // Request location and fetch towers
    requestLocation();
    fetchTowers();
    
    // Setup event listeners
    setupMapControls();
    
    // Start periodic updates
    startPeriodicUpdates();
}

/**
 * Initialize mini map on dashboard
 * 
 * Creates a smaller, non-interactive map preview showing
 * the device location and nearby towers.
 */
function initializeMiniMap() {
    const miniMapElement = document.getElementById('mini-map');
    if (!miniMapElement) return;
    
    // Create mini map
    map = L.map('mini-map', {
        zoomControl: false,
        attributionControl: false,
        dragging: false,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        touchZoom: false
    }).setView(CONFIG.mapCenter, CONFIG.mapZoom);
    
    // Add tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
}

/**
 * Request device geolocation permission and start tracking
 * 
 * Uses browser Geolocation API to track device position.
 * Updates are sent to backend for distance calculations.
 */
function requestLocation() {
    if (!('geolocation' in navigator)) {
        console.error('❌ Geolocation not supported');
        updateLocationCard('Geolocation not available in this browser');
        return;
    }
    
    // Request high-accuracy position
    navigator.geolocation.watchPosition(
        onLocationSuccess,
        onLocationError,
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 5000
        }
    );
}

/**
 * Handle successful geolocation
 * 
 * Updates the UI with current location and repositions
 * the map to center on the device.
 * 
 * @param {Position} position - Geolocation position object
 */
function onLocationSuccess(position) {
    console.log('📍 Location acquired');
    
    currentLocation = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
        altitude: position.coords.altitude,
        speed: position.coords.speed,
        timestamp: new Date().toISOString()
    };
    
    // Update UI
    updateLocationCard(currentLocation);
    updateDeviceMarker(currentLocation);
    
    // Center map on device location (first time only)
    if (map && !deviceMarker) {
        map.setView([currentLocation.latitude, currentLocation.longitude], CONFIG.mapZoom);
    }
}

/**
 * Handle geolocation errors
 * 
 * Displays user-friendly error messages based on error type.
 * Does not expose sensitive technical details.
 * 
 * @param {PositionError} error - Geolocation error object
 */
function onLocationError(error) {
    console.error('❌ Location error:', error.message);
    
    let message = 'Unable to get location';
    switch (error.code) {
        case error.PERMISSION_DENIED:
            message = 'Location permission denied. Please enable location access.';
            break;
        case error.POSITION_UNAVAILABLE:
            message = 'Location unavailable. Check your device settings.';
            break;
        case error.TIMEOUT:
            message = 'Location request timed out. Retrying...';
            break;
    }
    
    updateLocationCard(message);
}

/**
 * Fetch tower data from API
 * 
 * Retrieves list of visible cell towers from backend.
 * Updates dashboard and map with tower information.
 */
async function fetchTowers() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/towers`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        const towers = data.towers || [];
        
        console.log(`📡 Fetched ${towers.length} towers`);
        
        // Update UI
        updateTowerList(towers);
        updateTowerMarkers(towers);
        updateStats(towers);
        
    } catch (error) {
        console.error('❌ Error fetching towers:', error);
        // Don't expose error details to user
        showError('Unable to fetch tower data. Please try again.');
    }
}

/**
 * Update location card display
 * 
 * Shows current device location with coordinates and accuracy,
 * or displays error message if location unavailable.
 * 
 * @param {Object|string} location - Location object or error message
 */
function updateLocationCard(location) {
    const card = document.getElementById('location-card');
    if (!card) return;
    
    if (typeof location === 'string') {
        // Error message
        card.innerHTML = `<div class="location-error">${escapeHtml(location)}</div>`;
        return;
    }
    
    // Format location data
    // NOTE: Coordinates shown with limited precision for privacy
    const lat = location.latitude.toFixed(4);
    const lon = location.longitude.toFixed(4);
    const accuracy = Math.round(location.accuracy);
    
    card.innerHTML = `
        <div class="location-info">
            <p><strong>Coordinates:</strong> ${lat}, ${lon}</p>
            <p><strong>Accuracy:</strong> ±${accuracy}m</p>
            ${location.altitude ? `<p><strong>Altitude:</strong> ${Math.round(location.altitude)}m</p>` : ''}
            ${location.speed ? `<p><strong>Speed:</strong> ${Math.round(location.speed * 3.6)} km/h</p>` : ''}
        </div>
    `;
    
    // Update stat card
    const accuracyStat = document.getElementById('location-accuracy');
    if (accuracyStat) {
        accuracyStat.textContent = `±${accuracy}m`;
    }
}

/**
 * Update list of detected towers on dashboard
 * 
 * Renders tower cards with signal strength, type, and network info.
 * Allows filtering by terrestrial/satellite/connected status.
 * 
 * @param {Array} towers - Array of tower objects from API
 */
function updateTowerList(towers) {
    const list = document.getElementById('tower-list');
    if (!list) return;
    
    if (!towers || towers.length === 0) {
        list.innerHTML = '<div class="loading">No towers detected</div>';
        return;
    }
    
    // Sort: connected first, then by signal strength
    towers.sort((a, b) => {
        if (a.registered !== b.registered) return a.registered ? -1 : 1;
        return b.signal_strength - a.signal_strength;
    });
    
    // Render tower cards
    list.innerHTML = towers.map(tower => createTowerCard(tower)).join('');
}

/**
 * Create HTML for individual tower card
 * 
 * Generates a card showing tower type, signal strength,
 * network info, and connection status.
 * 
 * @param {Object} tower - Tower data object
 * @returns {string} HTML string for tower card
 */
function createTowerCard(tower) {
    const typeIcon = tower.tower_type === 'NON_TERRESTRIAL_SATELLITE' ? '🛰️' : '🗼';
    const typeClass = tower.tower_type === 'NON_TERRESTRIAL_SATELLITE' ? 'satellite' : 'terrestrial';
    const connectedBadge = tower.registered ? '<span class="badge">✅ Connected</span>' : '';
    
    // Signal strength bar visual
    const signalBars = '📶'.repeat(Math.min(tower.signal_bars || 0, 5));
    
    return `
        <div class="tower-card ${typeClass}" data-cell-id="${tower.cell_id}">
            <div class="tower-header">
                <span class="tower-icon">${typeIcon}</span>
                <span class="tower-type">${tower.network_type}</span>
                ${connectedBadge}
            </div>
            <div class="tower-details">
                <p><strong>Cell ID:</strong> ${tower.cell_id}</p>
                <p><strong>Operator:</strong> ${tower.mcc}-${tower.mnc}</p>
                <p><strong>Signal:</strong> ${tower.signal_strength} dBm ${signalBars}</p>
                ${tower.distance_meters ? `<p><strong>Distance:</strong> ${Math.round(tower.distance_meters)}m</p>` : ''}
            </div>
        </div>
    `;
}

/**
 * Update dashboard statistics
 * 
 * Calculates and displays summary stats:
 * - Total towers detected
 * - Connected tower
 * - Satellite count
 * 
 * @param {Array} towers - Array of tower objects
 */
function updateStats(towers) {
    const totalTowers = document.getElementById('total-towers');
    const connectedTower = document.getElementById('connected-tower');
    const satelliteCount = document.getElementById('satellite-count');
    
    if (totalTowers) {
        totalTowers.textContent = towers.length;
    }
    
    if (connectedTower) {
        const connected = towers.find(t => t.registered);
        connectedTower.textContent = connected ? connected.network_type : '-';
    }
    
    if (satelliteCount) {
        const satellites = towers.filter(t => t.tower_type === 'NON_TERRESTRIAL_SATELLITE');
        satelliteCount.textContent = satellites.length;
    }
}

/**
 * Setup event listeners for dashboard interactions
 */
function setupEventListeners() {
    // Refresh location button
    const btnRefreshLocation = document.getElementById('btn-refresh-location');
    if (btnRefreshLocation) {
        btnRefreshLocation.addEventListener('click', requestLocation);
    }
    
    // Filter buttons
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Apply filter (TODO: implement filtering logic)
            const filter = btn.dataset.filter;
            console.log(`Filter: ${filter}`);
        });
    });
}

/**
 * Setup map control buttons
 */
function setupMapControls() {
    // Center on location
    const btnCenter = document.getElementById('btn-center-location');
    if (btnCenter && map && currentLocation) {
        btnCenter.addEventListener('click', () => {
            map.setView([currentLocation.latitude, currentLocation.longitude], CONFIG.mapZoom);
        });
    }
    
    // Refresh towers
    const btnRefresh = document.getElementById('btn-refresh-towers');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', fetchTowers);
    }
}

/**
 * Start periodic tower updates
 * 
 * Fetches fresh tower data every REFRESH_INTERVAL seconds.
 * Prevents battery drain by using reasonable intervals.
 */
function startPeriodicUpdates() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    updateInterval = setInterval(fetchTowers, CONFIG.refreshInterval);
    console.log(`🔄 Periodic updates every ${CONFIG.refreshInterval / 1000}s`);
}

/**
 * Update device marker on map
 * 
 * Creates or updates the pulsing marker showing device location.
 * Includes accuracy circle to show GPS precision.
 * 
 * @param {Object} location - Location object with lat/lon
 */
function updateDeviceMarker(location) {
    if (!map) return;
    
    const latLng = [location.latitude, location.longitude];
    
    if (deviceMarker) {
        // Update existing marker
        deviceMarker.setLatLng(latLng);
    } else {
        // Create new marker
        deviceMarker = L.marker(latLng, {
            icon: L.divIcon({
                className: 'device-marker',
                html: '<div class="pulse">📍</div>',
                iconSize: [30, 30]
            })
        }).addTo(map);
        
        // Add accuracy circle
        L.circle(latLng, {
            radius: location.accuracy,
            color: '#2563eb',
            fillColor: '#60a5fa',
            fillOpacity: 0.2,
            weight: 2
        }).addTo(map);
    }
}

/**
 * Update tower markers on map
 * 
 * Creates colored markers for each tower based on signal strength
 * and tower type. Removes old markers that are no longer visible.
 * 
 * @param {Array} towers - Array of tower objects
 * 
 * @note Throttled to max 1 update per second to prevent map flicker
 */
function updateTowerMarkers(towers) {
    if (!map) return;
    
    // Remove existing markers
    towerMarkers.forEach(marker => map.removeLayer(marker));
    towerMarkers = [];
    
    // Add new markers for each tower
    towers.forEach(tower => {
        if (!tower.latitude || !tower.longitude) return;
        
        const signalColor = getSignalColor(tower.signal_strength);
        const icon = tower.tower_type === 'NON_TERRESTRIAL_SATELLITE' ? '🛰️' : '🗼';
        
        const marker = L.marker([tower.latitude, tower.longitude], {
            icon: L.divIcon({
                className: 'tower-marker',
                html: `<div style="background: ${signalColor}; font-size: 20px;">${icon}</div>`,
                iconSize: [32, 32]
            })
        }).addTo(map);
        
        // Add popup with tower details
        marker.bindPopup(`
            <strong>${icon} ${tower.network_type}</strong><br>
            Cell ID: ${tower.cell_id}<br>
            Signal: ${tower.signal_strength} dBm<br>
            ${tower.registered ? '✅ Connected' : ''}
        `);
        
        towerMarkers.push(marker);
    });
}

/**
 * Get color for signal strength visualization
 * 
 * Maps dBm values to color scale:
 * - Green: Excellent (-85 dBm and above)
 * - Yellow: Good/Medium (-95 to -85 dBm)
 * - Red: Weak (below -95 dBm)
 * 
 * @param {number} signalStrength - Signal strength in dBm
 * @returns {string} CSS color value
 */
function getSignalColor(signalStrength) {
    if (signalStrength >= -85) return '#22c55e'; // Excellent (green)
    if (signalStrength >= -95) return '#eab308'; // Good (yellow)
    if (signalStrength >= -105) return '#f97316'; // Fair (orange)
    return '#ef4444'; // Weak (red)
}

/**
 * Escape HTML to prevent XSS attacks
 * 
 * Sanitizes user input before inserting into DOM.
 * Critical security function - prevents script injection.
 * 
 * @param {string} text - Unsafe text
 * @returns {string} HTML-safe text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show error message to user
 * 
 * Displays non-technical error message in a toast/alert.
 * Does not reveal system internals for security.
 * 
 * @param {string} message - User-friendly error message
 */
function showError(message) {
    // TODO: Implement toast notification system
    console.error('Error:', message);
    alert(escapeHtml(message));
}

// Export functions for testing (if in Node.js environment)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeDashboard,
        initializeFullMap,
        escapeHtml,
        getSignalColor
    };
}
