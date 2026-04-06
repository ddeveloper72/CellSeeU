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
let nearbyTowerMarkers = []; // For lazy-loaded towers from OpenCelliD
let detectionRadiusCircle = null; // Visual radius showing IMEI detection zone
let trackingTowers = new Set(); // Towers currently in detection range
let currentLocation = null;
let updateInterval = null;
let locationWatchId = null;
let isFirstLocationFix = true;

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
    
    // Lazy load nearby towers when map moves
    map.on('moveend', function() {
        fetchNearbyTowers();
    });
    
    // Initial fetch of nearby towers
    fetchNearbyTowers();
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
    
    // Nearby towers will be fetched automatically when location is set
}

/**
 * Request device geolocation permission and start tracking
 * 
 * Uses browser Geolocation API to track device position.
 * Updates are sent to backend for distance calculations.
 * 
 * Why these settings:
 * - enableHighAccuracy: true - Use GPS instead of WiFi/cell triangulation
 * - timeout: 30000 - GPS needs time for first fix (up to 30s)
 * - maximumAge: 0 - Always get fresh position, never use cache
 */
function requestLocation() {
    if (!('geolocation' in navigator)) {
        console.error('❌ Geolocation not supported');
        updateLocationCard('Geolocation not available in this browser');
        return;
    }

    // Clear any existing watch to prevent conflicts
    if (locationWatchId !== null) {
        navigator.geolocation.clearWatch(locationWatchId);
    }

    // Show "acquiring location" message
    updateLocationCard('🔍 Acquiring GPS location...');

    // Get initial position with longer timeout for first GPS fix
    navigator.geolocation.getCurrentPosition(
        onLocationSuccess,
        onLocationError,
        {
            enableHighAccuracy: true,
            timeout: 30000,  // 30 seconds for initial GPS fix
            maximumAge: 0     // Force fresh position, no cache
        }
    );

    // Then start continuous tracking with shorter timeout
    locationWatchId = navigator.geolocation.watchPosition(
        onLocationSuccess,
        onLocationError,
        {
            enableHighAccuracy: true,
            timeout: 15000,   // 15 seconds for updates
            maximumAge: 0     // Always get fresh position
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
 * 
 * @note Only centers map on first position to avoid jarring user experience
 */
function onLocationSuccess(position) {
    const accuracy = Math.round(position.coords.accuracy);
    console.log(`📍 Location acquired (±${accuracy}m accuracy)`);

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

    // Center map on device location (first fix only)
    // After that, let user control the map
    if (map && isFirstLocationFix) {
        map.setView([currentLocation.latitude, currentLocation.longitude], 15);
        isFirstLocationFix = false;
        console.log('📍 Map centered on your location');
    }

    // Log accuracy warning if GPS is not precise
    if (accuracy > 100) {
        console.warn(`⚠️ Location accuracy is low (±${accuracy}m). Move to area with better GPS signal.`);
    }
}

/**
 * Handle geolocation errors
 * 
 * Displays user-friendly error messages for location failures
 * and implements retry logic for temporary issues (timeout, unavailable).
 * 
 * @param {GeolocationPositionError} error - Geolocation error object
 * @note Implements retry logic for timeout errors
 */
function onLocationError(error) {
    console.error('❌ Location error:', error.message);

    let message = 'Unable to get location';
    let shouldRetry = false;

    switch (error.code) {
        case error.PERMISSION_DENIED:
            message = 'Location permission denied. Please enable location access in your browser settings.';
            break;
        case error.POSITION_UNAVAILABLE:
            message = 'Location unavailable. Make sure GPS is enabled and you\'re not indoors.';
            shouldRetry = true;
            break;
        case error.TIMEOUT:
            message = 'GPS is taking longer than expected. Move to an area with clear sky view.';
            shouldRetry = true;
            break;
    }

    updateLocationCard(message);

    // Retry after delay for timeout/unavailable errors
    // GPS often needs more time for first fix outdoors
    if (shouldRetry) {
        console.log('🔄 Will retry location in 5 seconds...');
        setTimeout(() => {
            console.log('🔄 Retrying location request...');
            requestLocation();
        }, 5000);
    }
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
        
        // Use device location from Android app if available
        if (data.device_location && data.device_location.latitude) {
            console.log('📍 Using location from Android app:', data.device_location);
            currentLocation = {
                latitude: data.device_location.latitude,
                longitude: data.device_location.longitude,
                accuracy: data.device_location.accuracy || 0,
                altitude: data.device_location.altitude || 0,
                timestamp: new Date().toISOString()
            };
            
            // Update UI with Android GPS location
            updateLocationCard(currentLocation);
            updateDeviceMarker(currentLocation);
            
            // Update IMEI tracking visualization
            const connectedTower = towers.find(t => t.registered);
            if (connectedTower) {
                updateDetectionRadius(currentLocation, connectedTower.signal_strength);
                updateTrackingPanel(towers, currentLocation, calculateDetectionRadius(connectedTower.signal_strength));
            }
            
            // Center map on location (first time only)
            if (map && isFirstLocationFix) {
                map.setView([currentLocation.latitude, currentLocation.longitude], 15);
                isFirstLocationFix = false;
                console.log('📍 Map centered on your location from Android');
                
                // Load nearby towers now that we have user location
                fetchNearbyTowers();
            }
        } else if (!currentLocation) {
            // Fallback to browser geolocation if no Android location
            console.log('📍 No location from Android, trying browser GPS...');
            requestLocation();
        }

    } catch (error) {
        console.error('❌ Error fetching towers:', error);
        // Don't expose error details to user
        showError('Unable to fetch tower data. Please try again.');
    }
}

/**
 * Fetch nearby cell towers visible in current map view (lazy loading)
 * 
 * Calls OpenCelliD API to get all towers within the visible map bounds.
 * Displays them as gray markers (potential towers to connect to).
 */
async function fetchNearbyTowers() {
    if (!map) {
        console.log('⏸️ Map not initialized, skipping nearby tower fetch');
        return;
    }
    
    try {
        // Get map bounds
        const bounds = map.getBounds();
        const minLat = bounds.getSouth();
        const maxLat = bounds.getNorth();
        const minLon = bounds.getWest();
        const maxLon = bounds.getEast();
        
        console.log(`🗺️ Fetching towers in view: ${minLat.toFixed(3)},${minLon.toFixed(3)} to ${maxLat.toFixed(3)},${maxLon.toFixed(3)}`);
        
        // Fetch from API
        const response = await fetch(
            `${CONFIG.apiBaseUrl}/towers/nearby?bbox=${minLat},${minLon},${maxLat},${maxLon}`
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        const towers = data.towers || [];
        
        console.log(`📡 Found ${towers.length} nearby towers from OpenCelliD`);
        
        // Cluster nearby cells into tower sites (cells within 100m = same tower)
        const clusteredTowers = clusterNearbyTowers(towers, 0.1); // 0.1 km = 100m
        console.log(`📍 Clustered ${towers.length} cells into ${clusteredTowers.length} tower sites`);
        
        // Update map with clustered tower sites
        updateNearbyTowerMarkers(clusteredTowers);
        
    } catch (error) {
        console.error('⚠️ Error fetching nearby towers:', error);
        // Fail silently - this is a nice-to-have feature
    }
}

/**
 * Cluster nearby cells into physical tower locations
 * 
 * Groups cells that are within distance threshold (likely same physical tower).
 * A single tower site often has multiple cells (sectors, bands, technologies).
 * 
 * @param {Array} towers - Individual cell records from OpenCelliD
 * @param {number} distanceThresholdKm - Max distance to consider same tower (default: 0.1km = 100m)
 * @returns {Array} Clustered tower sites with cell counts
 */
function clusterNearbyTowers(towers, distanceThresholdKm = 0.1) {
    if (!towers || towers.length === 0) return [];
    
    const clusters = [];
    const used = new Set();
    
    // Helper: Calculate distance between two points (Haversine formula)
    function distance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth radius in km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }
    
    // Cluster towers by proximity
    towers.forEach((tower, i) => {
        if (used.has(i)) return;
        
        // Create new cluster with this tower as center
        const cluster = {
            latitude: tower.latitude,
            longitude: tower.longitude,
            cells: [tower],
            carriers: new Set([tower.carrier]),
            technologies: new Set([tower.network_type]),
            cell_count: 1,
            location_source: tower.location_source,
            tower_type: tower.tower_type
        };
        
        used.add(i);
        
        // Find nearby towers (within threshold)
        towers.forEach((other, j) => {
            if (used.has(j)) return;
            
            const dist = distance(tower.latitude, tower.longitude, other.latitude, other.longitude);
            
            if (dist <= distanceThresholdKm) {
                cluster.cells.push(other);
                cluster.carriers.add(other.carrier);
                cluster.technologies.add(other.network_type);
                cluster.cell_count++;
                used.add(j);
                
                // Update cluster center (average position)
                cluster.latitude = cluster.cells.reduce((sum, c) => sum + c.latitude, 0) / cluster.cells.length;
                cluster.longitude = cluster.cells.reduce((sum, c) => sum + c.longitude, 0) / cluster.cells.length;
            }
        });
        
        // Convert Sets to Arrays for display
        cluster.carriers = Array.from(cluster.carriers);
        cluster.technologies = Array.from(cluster.technologies);
        
        clusters.push(cluster);
    });
    
    return clusters;
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
                <p><strong>Carrier:</strong> ${escapeHtml(tower.carrier || `${tower.mcc}-${tower.mnc}`)}</p>
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
        btnRefreshLocation.addEventListener('click', () => {
            isFirstLocationFix = true;  // Allow re-centering
            requestLocation();
        });
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
    if (btnCenter) {
        btnCenter.addEventListener('click', () => {
            if (currentLocation && map) {
                map.setView([currentLocation.latitude, currentLocation.longitude], 15);
                console.log('📍 Map re-centered on your location');
            } else {
                console.warn('⚠️ Location not available yet');
                showError('Waiting for GPS location...');
            }
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
 * Calculate IMEI detection radius based on signal strength
 * 
 * Uses propagation model to estimate how far nearby towers
 * can detect device signals. Stronger signal = device is closer,
 * so detection radius is smaller (fewer towers in range).
 * 
 * @param {number} signalDbm - Current signal strength in dBm
 * @returns {number} Detection radius in meters
 */
function calculateDetectionRadius(signalDbm) {
    // Path loss model: weaker signal = farther from tower
    // Detection range: how far other towers can "hear" the device
    // At -77 dBm (excellent): ~500m detection radius
    // At -105 dBm (weak): ~3000m detection radius
    
    if (signalDbm >= -70) return 300;   // Very close, small detection zone
    if (signalDbm >= -85) return 800;   // Good signal, moderate zone
    if (signalDbm >= -95) return 1500;  // Fair signal, larger zone
    if (signalDbm >= -105) return 2500; // Weak signal, wide detection
    return 3500; // Very weak, maximum detection range
}

/**
 * Update IMEI detection radius circle on map
 * 
 * Shows visual radius where nearby towers can detect device signals.
 * Circle size varies based on current signal strength.
 * 
 * @param {Object} location - Current device location
 * @param {number} signalDbm - Signal strength in dBm
 */
function updateDetectionRadius(location, signalDbm) {
    if (!map) return;
    
    const radius = calculateDetectionRadius(signalDbm);
    
    // Remove old circle
    if (detectionRadiusCircle) {
        map.removeLayer(detectionRadiusCircle);
    }
    
    // Add new detection radius circle
    detectionRadiusCircle = L.circle([location.latitude, location.longitude], {
        radius: radius,
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.1,
        weight: 2,
        dashArray: '5, 5'
    }).addTo(map);
    
    detectionRadiusCircle.bindPopup(`
        <strong>🔴 IMEI Detection Zone</strong><br>
        Radius: ${radius}m<br>
        Signal: ${signalDbm} dBm<br>
        Towers in this zone can detect your device
    `);
    
    console.log(`🔴 IMEI detection radius: ${radius}m (signal: ${signalDbm} dBm)`);
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
        const registeredClass = tower.registered ? ' registered' : '';

        const marker = L.marker([tower.latitude, tower.longitude], {
            icon: L.divIcon({
                className: `tower-marker${registeredClass}`,
                html: `<div style="background: ${signalColor};">${icon}</div>`,
                iconSize: [40, 40]
            })
        }).addTo(map);

        // Add popup with tower details
        marker.bindPopup(`
            <strong>${icon} ${tower.network_type}</strong><br>
            Carrier: ${escapeHtml(tower.carrier || `${tower.mcc}-${tower.mnc}`)}<br>
            Cell ID: ${tower.cell_id}<br>
            Signal: ${tower.signal_strength} dBm (${tower.signal_bars}📶)<br>
            ${tower.distance_meters ? `Distance: ${Math.round(tower.distance_meters)}m<br>` : ''}
            ${tower.registered ? '✅ Connected' : ''}
        `);

        towerMarkers.push(marker);
    });

    console.log(`🗺️ Added ${towerMarkers.length} tower markers to map`);

    // Auto-fit map bounds to show all towers (if we have any)
    if (towerMarkers.length > 0) {
        const bounds = L.latLngBounds(
            towerMarkers.map(marker => marker.getLatLng())
        );
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
}

/**
 * Update nearby tower markers (lazy-loaded from OpenCelliD)
 * 
 * Displays potential towers device could connect to in gray.
 * Different from connected towers shown in color.
 * Towers are clustered - each marker represents a physical site with multiple cells.
 * 
 * @param {Array} towers - List of clustered tower sites
 */
function updateNearbyTowerMarkers(towers) {
    if (!map) return;

    // Remove existing nearby markers
    nearbyTowerMarkers.forEach(marker => map.removeLayer(marker));
    nearbyTowerMarkers = [];

    // Add new markers for each nearby tower site
    towers.forEach(tower => {
        if (!tower.latitude || !tower.longitude) return;

        const icon = tower.tower_type === 'NON_TERRESTRIAL_SATELLITE' ? '🛰️' : '📡';
        const cellCount = tower.cell_count || 1;
        const carriers = tower.carriers || [tower.carrier];
        const technologies = tower.technologies || [tower.network_type];

        const marker = L.marker([tower.latitude, tower.longitude], {
            icon: L.divIcon({
                className: 'nearby-tower-marker',
                html: `<div>${icon}${cellCount > 1 ? '<span class="cell-count">' + cellCount + '</span>' : ''}</div>`,
                iconSize: [30, 30]
            })
        }).addTo(map);
        
        // Store tower data on marker for later reference
        marker._towerData = tower;

        // Build popup content
        let popupContent = `<strong>${icon} Tower Site</strong><br>`;
        popupContent += `📱 ${cellCount} cell${cellCount > 1 ? 's' : ''}<br>`;
        popupContent += `📡 ${carriers.join(', ')}<br>`;
        popupContent += `🔧 ${technologies.join(', ')}<br>`;
        
        // If cluster, show cell details
        if (tower.cells && tower.cells.length > 1) {
            popupContent += `<br><em style="font-size: 0.9em;">Cells at this site:</em><br>`;
            popupContent += `<div style="max-height: 150px; overflow-y: auto; font-size: 0.85em;">`;
            tower.cells.slice(0, 10).forEach(cell => {
                const carrierShort = (cell.carrier || '').replace(' Ireland', '');
                popupContent += `• ${cell.network_type} - ${carrierShort} (${cell.cell_id})<br>`;
            });
            if (tower.cells.length > 10) {
                popupContent += `<em>...and ${tower.cells.length - 10} more</em><br>`;
            }
            popupContent += `</div>`;
        }
        
        popupContent += `<br><em style="color: #888;">From OpenCelliD</em>`;

        marker.bindPopup(popupContent);
        nearbyTowerMarkers.push(marker);
    });

    console.log(`🗺️ Added ${nearbyTowerMarkers.length} nearby tower markers`);
}

/**
 * Calculate distance between two coordinates (Haversine formula)
 * 
 * @param {number} lat1 - Latitude 1
 * @param {number} lon1 - Longitude 1
 * @param {number} lat2 - Latitude 2
 * @param {number} lon2 - Longitude 2
 * @returns {number} Distance in meters
 */
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000; // Earth's radius in meters
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
        Math.cos(φ1) * Math.cos(φ2) *
        Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c; // Distance in meters
}

/**
 * Calculate IMEI detection radius based on signal strength
 * 
 * Uses propagation model to estimate how far nearby towers
 * can detect device signals. Stronger signal = device is closer,
 * so detection radius is smaller (fewer towers in range).
 * 
 * @param {number} signalDbm - Current signal strength in dBm
 * @returns {number} Detection radius in meters
 */
function calculateDetectionRadius(signalDbm) {
    // Path loss model: weaker signal = farther from tower
    // Detection range: how far other towers can "hear" the device
    // At -77 dBm (excellent): ~500m detection radius
    // At -105 dBm (weak): ~3000m detection radius
    
    if (signalDbm >= -70) return 300;   // Very close, small detection zone
    if (signalDbm >= -85) return 800;   // Good signal, moderate zone
    if (signalDbm >= -95) return 1500;  // Fair signal, larger zone
    if (signalDbm >= -105) return 2500; // Weak signal, wide detection
    return 3500; // Very weak, maximum detection range
}

/**
 * Update IMEI detection radius circle on map
 * 
 * Shows visual radius where nearby towers can detect device signals.
 * Circle size varies based on current signal strength.
 * 
 * @param {Object} location - Current device location
 * @param {number} signalDbm - Signal strength in dBm
 */
function updateDetectionRadius(location, signalDbm) {
    if (!map) return;
    
    const radius = calculateDetectionRadius(signalDbm);
    
    // Remove old circle
    if (detectionRadiusCircle) {
        map.removeLayer(detectionRadiusCircle);
    }
    
    // Add new detection radius circle
    detectionRadiusCircle = L.circle([location.latitude, location.longitude], {
        radius: radius,
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.1,
        weight: 2,
        dashArray: '5, 5'
    }).addTo(map);
    
    detectionRadiusCircle.bindPopup(`
        <strong>🔴 IMEI Detection Zone</strong><br>
        Radius: ${radius}m<br>
        Signal: ${signalDbm} dBm<br>
        Towers in this zone can detect your device
    `);
    
    console.log(`🔴 IMEI detection radius: ${radius}m (signal: ${signalDbm} dBm)`);
}

/**
 * Update tracking panel showing services detecting IMEI
 * 
 * Displays list of towers currently in detection range
 * that can potentially see device IMEI and signals.
 * 
 * @param {Array} towers - All tower data
 * @param {Object} location - Current device location
 * @param {number} detectionRadius - Detection radius in meters
 */
function updateTrackingPanel(towers, location, detectionRadius) {
    const trackingPanel = document.getElementById('tracking-panel');
    if (!trackingPanel) return;
    
    trackingTowers.clear();
    
    // Find nearby towers in detection range
    const towersInRange = nearbyTowerMarkers
        .map(marker => {
            const tower = marker._towerData;
            if (!tower) {
                // Extract tower data from marker popup
                const lat = marker.getLatLng().lat;
                const lng = marker.getLatLng().lng;
                return {
                    latitude: lat,
                    longitude: lng,
                    carrier: 'Unknown',
                    network_type: 'Unknown'
                };
            }
            
            const distance = calculateDistance(
                location.latitude, location.longitude,
                tower.latitude, tower.longitude
            );
            
            if (distance <= detectionRadius) {
                trackingTowers.add(tower.cell_id || tower.cellid || Math.random());
                return { ...tower, distance };
            }
            return null;
        })
        .filter(t => t !== null)
        .sort((a, b) => a.distance - b.distance);
    
    // Check nearby markers that have position
    nearbyTowerMarkers.forEach(marker => {
        const lat = marker.getLatLng().lat;
        const lng = marker.getLatLng().lng;
        const distance = calculateDistance(
            location.latitude, location.longitude,
            lat, lng
        );
        
        if (distance <= detectionRadius && !towersInRange.some(t => t.latitude === lat && t.longitude === lng)) {
            towersInRange.push({
                latitude: lat,
                longitude: lng,
                carrier: 'Unknown Operator',
                network_type: 'Cellular',
                distance: distance
            });
        }
    });
    
    // Add currently connected tower (always tracking)
    const connectedTower = towers.find(t => t.registered);
    
    let html = `
        <h3>🔴 Services Detecting Your IMEI</h3>
        <div class="tracking-warning">
            ⚠️ These services can currently see your device identifier
        </div>
    `;
    
    // Connected tower (definitely tracking)
    if (connectedTower) {
        html += `
            <div class="tracking-item active-connection">
                <div class="tracking-badge">🔴 ACTIVE CONNECTION</div>
                <strong>${escapeHtml(connectedTower.carrier || 'Unknown')}</strong><br>
                <small>Cell ID: ${connectedTower.cell_id}</small><br>
                <small>Signal: ${connectedTower.signal_strength} dBm</small><br>
                <small>📍 Definitely tracking IMEI</small>
            </div>
        `;
    }
    
    // Nearby towers in detection range
    if (towersInRange.length > 0) {
        html += `<h4>⚠️ Nearby Towers (${towersInRange.length} in range)</h4>`;
        towersInRange.slice(0, 10).forEach(tower => {
            html += `
                <div class="tracking-item potential-detection">
                    <div class="tracking-badge">⚠️ IN RANGE</div>
                    <strong>${escapeHtml(tower.carrier || 'Unknown Operator')}</strong><br>
                    <small>${tower.network_type || tower.radio || 'Cellular'}</small><br>
                    <small>Distance: ${Math.round(tower.distance)}m</small><br>
                    <small>📡 Can detect scanning signals</small>
                </div>
            `;
        });
        if (towersInRange.length > 10) {
            html += `<p><small>...and ${towersInRange.length - 10} more</small></p>`;
        }
    } else {
        html += `<p><small>No nearby towers in detection range</small></p>`;
    }
    
    trackingPanel.innerHTML = html;
    
    console.log(`🔴 Tracking update: ${trackingTowers.size} towers can detect device`);
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
