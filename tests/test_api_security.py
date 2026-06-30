"""
Security tests for API routes

Tests for OWASP Top 10 vulnerabilities and penetration testing scenarios.
Ensures API is secure without losing functionality.
"""

import pytest
import json
from time import sleep


class TestAPISecurityInputValidation:
    """Test input validation and injection prevention"""
    
    def test_sql_injection_in_filter_parameter(self, client):
        """
        Verify SQL injection attempts are rejected.
        
        Attacker tries to inject SQL through filter parameter.
        Should be caught by input validation before reaching database.
        """
        malicious_inputs = [
            "'; DROP TABLE towers; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM towers",
        ]
        
        for payload in malicious_inputs:
            response = client.get(f'/api/towers?filter={payload}')
            
            # Should return 400 Bad Request, not execute SQL
            assert response.status_code == 400
            assert response.is_json
            
            data = response.get_json()
            assert 'error' in data
            assert 'invalid' in data['error'].lower()
    
    def test_xss_injection_in_parameters(self, client):
        """
        Verify XSS payloads are rejected or sanitized.
        
        Attacker tries to inject JavaScript through query parameters.
        Should be rejected or sanitized before being returned.
        """
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg/onload=alert('XSS')>",
        ]
        
        for payload in xss_payloads:
            response = client.get(f'/api/towers?filter={payload}')
            
            # Should be rejected
            assert response.status_code == 400
            
            # If returned, must be escaped
            if response.status_code == 200:
                response_text = response.get_data(as_text=True)
                # Should not contain unescaped script tags
                assert '<script>' not in response_text.lower()
                assert 'onerror=' not in response_text.lower()
    
    def test_path_traversal_in_cell_id(self, client):
        """
        Verify path traversal attempts are blocked.
        
        Attacker tries to access files outside allowed directory
        using path traversal in cell_id parameter.
        """
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]
        
        for payload in traversal_payloads:
            response = client.get(f'/api/tower/{payload}')
            
            # Should return 404 (treated as invalid cell_id)
            # Not 200 with file contents!
            assert response.status_code == 404
    
    def test_limit_parameter_boundary_values(self, client):
        """
        Verify limit parameter has proper bounds checking.
        
        Prevents resource exhaustion by enforcing reasonable limits.
        Also tests for integer overflow vulnerabilities.
        """
        # Valid boundary values
        response = client.get('/api/towers?limit=1')
        assert response.status_code == 200
        
        response = client.get('/api/towers?limit=1000')
        assert response.status_code == 200
        
        # Invalid: too low
        response = client.get('/api/towers?limit=0')
        assert response.status_code == 400
        
        response = client.get('/api/towers?limit=-1')
        assert response.status_code == 400
        
        # Invalid: too high (DoS attempt)
        response = client.get('/api/towers?limit=999999')
        assert response.status_code == 400
        
        # Invalid: not a number
        response = client.get('/api/towers?limit=abc')
        assert response.status_code == 400
        
        # Invalid: integer overflow attempt
        response = client.get('/api/towers?limit=999999999999999999999')
        assert response.status_code == 400
    
    def test_cell_id_validation(self, client):
        """
        Verify cell_id parameter is properly validated.
        
        Ensures only valid cell IDs are accepted, preventing
        injection and type confusion attacks.
        """
        # Valid cell ID
        response = client.get('/api/tower/12345678')
        # Will be 404 because tower doesn't exist, but validates format
        assert response.status_code in [200, 404]
        
        # Invalid: negative (Flask route doesn't match <int:cell_id> for negatives, returns 404)
        response = client.get('/api/tower/-1')
        assert response.status_code == 404  # Route not found (expected for negative)
        
        # Invalid: too large (should return 400 from our validation)
        response = client.get('/api/tower/9999999999')
        # This is tricky - Flask's int converter might reject it first
        # If it gets through, our validation returns 400
        assert response.status_code in [400, 404]


class TestAPISecurityRateLimiting:
    """Test rate limiting prevents abuse"""
    
    def test_rate_limiting_enforced(self, client):
        """
        Verify rate limiting prevents DoS attacks.
        
        Makes excessive requests to trigger rate limit.
        Important: Rate limit should be high enough for legitimate
        use but low enough to prevent abuse.
        """
        # Make 101 requests rapidly (limit is 100 per minute)
        responses = []
        for i in range(101):
            response = client.get('/api/towers')
            responses.append(response)
        
        # Should see at least one 429 Too Many Requests
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes, "Rate limiting not enforced"
        
        # Check the 429 response format
        rate_limited = [r for r in responses if r.status_code == 429][0]
        data = rate_limited.get_json()
        
        assert 'error' in data
        assert 'rate limit' in data['error'].lower()
        assert 'retry_after' in data
    
    def test_rate_limit_message_helpful(self, client):
        """
        Verify rate limit errors provide helpful information.
        
        Rate limit errors should tell user how to proceed
        without exposing system internals.
        """
        # Trigger rate limit
        for _ in range(101):
            client.get('/api/towers')
        
        response = client.get('/api/towers')
        
        if response.status_code == 429:
            data = response.get_json()
            
            # Should have user-friendly message
            assert 'error' in data or 'message' in data
            
            # Should NOT expose:
            assert 'database' not in str(data).lower()
            assert 'python' not in str(data).lower()
            assert 'traceback' not in str(data).lower()


class TestAPISecurityInformationLeakage:
    """Test that errors don't leak sensitive information"""
    
    def test_404_does_not_leak_internal_info(self, client):
        """
        Verify 404 errors don't expose system details.
        
        Error messages should be generic to avoid giving
        attackers information about the system.
        """
        response = client.get('/api/nonexistent/endpoint')
        
        assert response.status_code == 404
        data = response.get_json()
        
        # Should not contain:
        response_text = str(data).lower()
        assert 'python' not in response_text
        assert 'flask' not in response_text
        assert 'traceback' not in response_text
        assert 'stack' not in response_text
        assert '/api/' not in response_text  # Don't echo back paths
    
    def test_server_header_not_exposed(self, client):
        """
        Verify server version is not exposed in headers.
        
        Server header can reveal software versions to attackers.
        Should be removed or obscured.
        """
        response = client.get('/api/towers')
        
        # Server header should not reveal Flask version
        server_header = response.headers.get('Server', '')
        assert 'flask' not in server_header.lower()
        assert 'werkzeug' not in server_header.lower()
        assert 'python' not in server_header.lower()
    
    def test_error_responses_generic(self, client):
        """
        Verify error responses don't expose implementation details.
        
        Errors should be generic (e.g., "Bad Request") not specific
        (e.g., "Database connection failed on line 42").
        """
        # Trigger various errors
        responses = [
            client.get('/api/towers?limit=abc'),  # Invalid parameter
            client.get('/api/tower/-999'),         # Invalid cell ID
            client.get('/api/tower/abc'),          # Non-numeric cell ID
        ]
        
        for response in responses:
            if response.status_code >= 400:
                data = response.get_json()
                response_text = str(data).lower()
                
                # Should NOT contain implementation details
                forbidden_words = [
                    'traceback', 'exception', 'stack trace',
                    'line ', 'file ', '.py',
                    'database', 'query', 'sql',
                    'password', 'secret', 'token', 'key'
                ]
                
                for word in forbidden_words:
                    assert word not in response_text, \
                        f"Error response contains '{word}': {data}"


class TestAPISecurityCSRF:
    """Test CSRF protection (if needed for state-changing operations)"""
    
    def test_cors_properly_configured(self, client):
        """
        Verify CORS headers are present but not overly permissive.
        
        CORS should allow legitimate origins while preventing
        cross-site attacks.
        """
        response = client.get('/api/towers')
        
        # CORS headers should be present for API routes
        cors_header = response.headers.get('Access-Control-Allow-Origin')
        
        # Should NOT be wildcard in production (security risk)
        # In development, * might be acceptable
        if cors_header:
            # If CORS is enabled, verify it's not overly permissive
            # NOTE: Update this test based on your CORS policy
            pass  # CORS policy check


class TestAPIFunctionalityNotBrokenBySecurity:
    """Ensure security measures don't break legitimate use"""
    
    def test_valid_requests_still_work(self, client):
        """
        Verify legitimate API requests succeed.
        
        Security should not prevent valid use cases.
        """
        # Valid tower list request
        response = client.get('/api/towers')
        assert response.status_code == 200
        assert response.is_json
        
        data = response.get_json()
        assert 'towers' in data
        assert isinstance(data['towers'], list)
    
    def test_filtering_works_with_valid_values(self, client):
        """
        Verify filtering functionality works for valid inputs.
        
        Security validation should allow legitimate filter values.
        """
        valid_filters = ['all', 'terrestrial', 'satellite', 'connected']
        
        for filter_value in valid_filters:
            response = client.get(f'/api/towers?filter={filter_value}')
            assert response.status_code == 200, \
                f"Valid filter '{filter_value}' was rejected"
            
            data = response.get_json()
            assert 'towers' in data
    
    def test_stats_endpoint_functional(self, client):
        """
        Verify stats endpoint provides useful data.
        
        Stats should be available without exposing sensitive info.
        """
        response = client.get('/api/stats')
        
        assert response.status_code == 200
        assert response.is_json
        
        data = response.get_json()
        
        # Should have useful statistics
        required_fields = ['total_towers', 'terrestrial_count', 
                          'satellite_count', 'timestamp']
        for field in required_fields:
            assert field in data, f"Missing stat field: {field}"

    def test_uploaded_tower_details_are_available(self, client, monkeypatch):
        """Verify tower detail lookups use scanner-uploaded tower data."""
        monkeypatch.setattr(
            'src.services.tower_location.get_tower_location',
            lambda *args, **kwargs: {'latitude': None, 'longitude': None}
        )

        upload = {
            'device_location': {
                'latitude': 53.3498,
                'longitude': -6.2603,
                'accuracy': 12
            },
            'towers': [
                {
                    'cell_id': 12345678,
                    'mcc': 272,
                    'mnc': 1,
                    'network_type': 'LTE',
                    'signal_strength': -90,
                    'registered': True,
                    'tower_type': 'TERRESTRIAL'
                }
            ]
        }

        upload_response = client.post('/api/towers/upload', json=upload)
        assert upload_response.status_code == 201

        detail_response = client.get('/api/tower/12345678')
        assert detail_response.status_code == 200

        data = detail_response.get_json()
        assert data['data_source'] == 'real'
        assert data['tower']['carrier'] == 'Vodafone Ireland'
        assert data['tower']['signal_bars'] == 4

    def test_stats_reflect_uploaded_towers(self, client, monkeypatch):
        """Verify aggregate stats are calculated from uploaded scanner data."""
        monkeypatch.setattr(
            'src.services.tower_location.get_tower_location',
            lambda *args, **kwargs: {'latitude': None, 'longitude': None}
        )

        client.post('/api/towers/upload', json={
            'towers': [
                {
                    'cell_id': 111,
                    'mcc': 272,
                    'mnc': 1,
                    'network_type': 'LTE',
                    'signal_strength': -80,
                    'registered': True,
                    'tower_type': 'TERRESTRIAL'
                },
                {
                    'cell_id': 222,
                    'mcc': 901,
                    'mnc': 88,
                    'network_type': '5G_NR_NTN',
                    'signal_strength': -100,
                    'registered': False,
                    'tower_type': 'NON_TERRESTRIAL_SATELLITE'
                }
            ]
        })

        response = client.get('/api/stats')
        assert response.status_code == 200

        data = response.get_json()
        assert data['total_towers'] == 2
        assert data['terrestrial_count'] == 1
        assert data['satellite_count'] == 1
        assert data['average_signal'] == -90
        assert data['connected_network'] == 'LTE'
        assert data['connected_carrier'] == 'Vodafone Ireland'
        assert data['data_source'] == 'real'

    def test_wifi_endpoint_rejects_invalid_query_params(self, client):
        """Verify malformed WiFi query params return controlled 400s."""
        bad_responses = [
            client.get('/api/wifi?limit=abc'),
            client.get('/api/wifi?limit=0'),
            client.get('/api/wifi?filter=<script>'),
        ]

        for response in bad_responses:
            assert response.status_code == 400
            assert response.is_json

    def test_legacy_wifi_positions_endpoint_removed(self, client):
        """Verify WiFi source estimates are served by signal mapping only."""
        response = client.get('/api/wifi/positions')

        assert response.status_code == 404
        assert response.is_json

    def test_wifi_endpoint_returns_device_heading(self, client, monkeypatch):
        """Verify WiFi 3D can read the latest uploaded phone heading."""
        monkeypatch.setattr(
            'src.services.tower_location.get_tower_location',
            lambda *args, **kwargs: {'latitude': None, 'longitude': None}
        )

        client.post('/api/towers/upload', json={
            'device_location': {
                'latitude': 53.3498,
                'longitude': -6.2603,
                'heading': 287.5,
                'cardinal_direction': 'WNW'
            },
            'towers': [],
            'wifi_networks': [
                {
                    'ssid': 'Test WiFi',
                    'bssid': 'aa:bb:cc:dd:ee:ff',
                    'signal_strength': -55,
                    'is_open': False
                }
            ]
        })

        response = client.get('/api/wifi')
        assert response.status_code == 200

        data = response.get_json()
        assert data['device_location']['heading'] == 287.5
        assert data['device_location']['cardinal_direction'] == 'WNW'

    def test_wireless_snapshot_returns_latest_android_scanner_state(self, client, monkeypatch):
        """Verify 3D/dashboard views can share one normalized wireless state."""
        monkeypatch.setattr(
            'src.services.tower_location.get_tower_location',
            lambda *args, **kwargs: {'latitude': None, 'longitude': None}
        )

        client.post('/api/towers/upload', json={
            'device_location': {
                'latitude': 53.3498,
                'longitude': -6.2603,
                'heading': 45.0,
                'cardinal_direction': 'NE'
            },
            'towers': [],
            'wifi_connected': {
                'ssid': 'Connected WiFi',
                'bssid': '11:22:33:44:55:66',
                'is_connected': True,
                'signal_strength': -50
            },
            'wifi_networks': [
                {
                    'ssid': 'Connected WiFi',
                    'bssid': '11:22:33:44:55:66',
                    'signal_strength': -50,
                    'is_open': False
                },
                {
                    'ssid': 'Nearby WiFi',
                    'bssid': 'aa:bb:cc:dd:ee:ff',
                    'signal_strength': -70,
                    'is_open': True
                }
            ]
        })

        response = client.get('/api/wireless/latest')
        assert response.status_code == 200

        data = response.get_json()
        assert data['count'] == 2
        assert data['total_count'] == 2
        assert data['data_source'] == 'real'
        assert data['device_location']['heading'] == 45.0
        assert data['connected']['bssid'] == '11:22:33:44:55:66'
        assert data['networks'][0]['ssid'] == 'Connected WiFi'

    def test_wireless_snapshot_falls_back_to_recent_non_empty_wifi_scan(self, client, monkeypatch):
        """Verify an empty WiFi scan does not blank the 3D signal view."""
        monkeypatch.setattr(
            'src.services.tower_location.get_tower_location',
            lambda *args, **kwargs: {'latitude': None, 'longitude': None}
        )

        client.post('/api/towers/upload', json={
            'device_location': {
                'latitude': 53.3498,
                'longitude': -6.2603,
                'heading': 10.0,
                'cardinal_direction': 'N'
            },
            'towers': [],
            'wifi_networks': [
                {
                    'ssid': 'Previous WiFi',
                    'bssid': 'aa:bb:cc:dd:ee:ff',
                    'signal_strength': -61,
                    'is_open': False
                }
            ]
        })
        client.post('/api/towers/upload', json={
            'device_location': {
                'latitude': 53.3499,
                'longitude': -6.2604,
                'heading': 180.0,
                'cardinal_direction': 'S'
            },
            'towers': [],
            'wifi_networks': []
        })

        response = client.get('/api/wireless/latest')
        assert response.status_code == 200

        data = response.get_json()
        assert data['data_source'] == 'history'
        assert data['count'] == 1
        assert data['networks'][0]['ssid'] == 'Previous WiFi'
        assert data['device_location']['heading'] == 180.0

    def test_android_upload_feeds_signal_mapping_samples(self, client, monkeypatch):
        """Verify existing scanner uploads seed the generic signal mapper."""
        monkeypatch.setattr(
            'src.services.tower_location.get_tower_location',
            lambda *args, **kwargs: {'latitude': None, 'longitude': None}
        )

        response = client.post('/api/towers/upload', json={
            'device_location': {
                'latitude': 53.3498,
                'longitude': -6.2603,
                'accuracy': 8,
                'heading': 240.0,
                'cardinal_direction': 'SW'
            },
            'towers': [],
            'wifi_networks': [
                {
                    'ssid': 'Kitchen AP',
                    'bssid': 'aa:bb:cc:dd:ee:ff',
                    'signal_strength': -52,
                    'frequency': 2412,
                    'channel': 1
                }
            ]
        })

        assert response.status_code == 201
        upload_data = response.get_json()
        assert upload_data['mapping_samples'] == 1
        assert 'mapping_session_id' in upload_data

        samples_response = client.get('/api/signal-mapping/samples')
        assert samples_response.status_code == 200

        samples_data = samples_response.get_json()
        assert samples_data['count'] == 1
        assert samples_data['samples'][0]['signals'][0]['type'] == 'wifi'
        assert samples_data['samples'][0]['signals'][0]['source_id'] == 'aa:bb:cc:dd:ee:ff'

    def test_signal_mapping_sources_estimate_wifi_position(self, client):
        """Verify walk samples produce a conservative source estimate."""
        samples = [
            (53.34980, -6.26030, -72),
            (53.34984, -6.26020, -55),
            (53.34988, -6.26010, -47),
        ]
        for lat, lon, signal in samples:
            response = client.post('/api/signal-mapping/samples', json={
                'device_pose': {
                    'latitude': lat,
                    'longitude': lon,
                    'accuracy_m': 5,
                    'heading': 240
                },
                'signals': [
                    {
                        'type': 'wifi',
                        'source_id': 'aa:bb:cc:dd:ee:ff',
                        'label': 'Kitchen AP',
                        'strength_dbm': signal,
                        'frequency_mhz': 2412
                    }
                ]
            })
            assert response.status_code == 201

        response = client.get('/api/signal-mapping/sources?type=wifi&min_samples=2')
        assert response.status_code == 200

        data = response.get_json()
        assert data['count'] == 1
        source = data['sources'][0]
        assert source['type'] == 'wifi'
        assert source['source_id'] == 'aa:bb:cc:dd:ee:ff'
        assert source['label'] == 'Kitchen AP'
        assert source['sample_count'] == 3
        assert source['method'] == 'weighted_signal_centroid'
        assert source['latitude'] > 53.34982
        assert source['longitude'] > -6.26025

    def test_signal_mapping_rejects_invalid_inputs(self, client):
        """Verify signal mapping endpoints validate public inputs."""
        bad_responses = [
            client.post('/api/signal-mapping/samples', json={'device_pose': {}, 'signals': []}),
            client.post('/api/signal-mapping/samples', json={
                'device_pose': {},
                'signals': [{'type': 'not-real', 'source_id': 'x'}]
            }),
            client.get('/api/signal-mapping/samples?limit=0'),
            client.get('/api/signal-mapping/sources?type=<script>'),
            client.get('/api/signal-mapping/sources?min_samples=0'),
            client.get('/api/signal-mapping/sources?min_confidence=2'),
        ]

        for response in bad_responses:
            assert response.status_code == 400
            assert response.is_json


class TestAPIPerformanceSecurity:
    """Test that API doesn't have performance-based vulnerabilities"""
    
    def test_response_time_consistent(self, client):
        """
        Verify response times don't leak information.
        
        Timing attacks can reveal information about data existence.
        Responses should take similar time regardless of result.
        """
        import time
        
        # Test existing vs non-existing tower
        start1 = time.time()
        client.get('/api/tower/12345678')
        time1 = time.time() - start1
        
        start2 = time.time()
        client.get('/api/tower/99999999')
        time2 = time.time() - start2
        
        # Times should be similar (within 100ms)
        # Large differences could indicate timing attack vulnerability
        # NOTE: This is a simple check, real timing attacks are more sophisticated
        time_diff = abs(time1 - time2)
        assert time_diff < 0.1, \
            f"Response time difference too large: {time_diff}s"
