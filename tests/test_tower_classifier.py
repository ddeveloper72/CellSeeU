"""
Tests for tower classification service

Tests the logic that distinguishes between terrestrial cell towers
and non-terrestrial (satellite) networks.
"""

import pytest
from datetime import datetime
from src.services.tower_classifier import (
    classify_tower_type,
    is_satellite_plmn,
    is_5g_ntn_capable,
    get_network_type_from_radio
)


class TestTowerClassification:
    """Test suite for tower type classification logic"""
    
    def test_classify_terrestrial_lte_tower(self):
        """
        Verify standard LTE tower is classified as TERRESTRIAL.
        
        Regular cell towers (LTE, 5G terrestrial) should be
        identified as TERRESTRIAL type.
        """
        # Mock cell info data for typical T-Mobile LTE tower
        cell_data = {
            'radio': 'LTE',
            'mcc': 310,
            'mnc': 260,
            'has_ntn_capability': False
        }
        
        tower_type = classify_tower_type(cell_data)
        
        assert tower_type == "TERRESTRIAL"
    
    def test_classify_satellite_5g_ntn_with_capability_flag(self):
        """
        Verify 5G NR tower with NTN capability is classified as satellite.
        
        Android 13+ provides isNonTerrestrialNetwork() API flag.
        This is the most reliable detection method when available.
        """
        cell_data = {
            'radio': '5G_NR',
            'mcc': 310,
            'mnc': 260,
            'has_ntn_capability': True  # Direct NTN flag from Android API
        }
        
        tower_type = classify_tower_type(cell_data)
        
        assert tower_type == "NON_TERRESTRIAL_SATELLITE"
    
    def test_classify_satellite_by_plmn(self):
        """
        Verify satellite network detected by known PLMN codes.
        
        Some satellite operators use specific MCC/MNC combinations.
        This is the fallback detection method for older Android versions.
        """
        # Example satellite PLMN (901-88 is often used for satellite trials)
        cell_data = {
            'radio': '5G_NR',
            'mcc': 901,
            'mnc': 88,
            'has_ntn_capability': False  # May not be available on older Android
        }
        
        tower_type = classify_tower_type(cell_data)
        
        assert tower_type == "NON_TERRESTRIAL_SATELLITE"
    
    def test_is_satellite_plmn_returns_true_for_known_satellite(self):
        """
        Verify known satellite PLMNs are correctly identified.
        
        Satellite operators use specific MCC/MNC codes that we can
        maintain in a database for identification.
        """
        assert is_satellite_plmn(901, 88) is True   # Example satellite
        assert is_satellite_plmn(901, 14) is True   # Example satellite
    
    def test_is_satellite_plmn_returns_false_for_terrestrial(self):
        """
        Verify regular carrier PLMNs are not mistaken for satellites.
        
        Common carriers should not be classified as satellite networks.
        """
        assert is_satellite_plmn(310, 260) is False  # T-Mobile USA
        assert is_satellite_plmn(310, 410) is False  # AT&T USA
        assert is_satellite_plmn(310, 120) is False  # Sprint USA
    
    def test_is_5g_ntn_capable_with_flag(self):
        """
        Verify NTN capability detection from API flag.
        
        Android 13+ provides direct NTN capability flag which is
        the most reliable method.
        """
        cell_data_with_ntn = {'has_ntn_capability': True}
        cell_data_without_ntn = {'has_ntn_capability': False}
        cell_data_missing_flag = {}  # Older Android versions
        
        assert is_5g_ntn_capable(cell_data_with_ntn) is True
        assert is_5g_ntn_capable(cell_data_without_ntn) is False
        assert is_5g_ntn_capable(cell_data_missing_flag) is False
    
    def test_get_network_type_from_radio_lte(self):
        """
        Verify LTE radio type is correctly mapped to network type.
        """
        assert get_network_type_from_radio('LTE') == 'LTE'
    
    def test_get_network_type_from_radio_5g_nr(self):
        """
        Verify 5G NR radio type mapping.
        """
        assert get_network_type_from_radio('5G_NR') == '5G_NR'
        assert get_network_type_from_radio('NR') == '5G_NR'
    
    def test_get_network_type_from_radio_5g_ntn(self):
        """
        Verify 5G NR-NTN (satellite) radio type mapping.
        """
        assert get_network_type_from_radio('5G_NR_NTN') == '5G_NR_NTN'
    
    def test_get_network_type_from_radio_legacy(self):
        """
        Verify legacy network types (GSM, UMTS) are correctly mapped.
        """
        assert get_network_type_from_radio('GSM') == 'GSM'
        assert get_network_type_from_radio('UMTS') == 'UMTS'
        assert get_network_type_from_radio('WCDMA') == 'UMTS'  # Alias
    
    def test_get_network_type_unknown_defaults(self):
        """
        Verify unknown radio types return a default value.
        
        Future-proofing: If we encounter an unknown network type,
        don't crash - return a sensible default.
        """
        assert get_network_type_from_radio('UNKNOWN') == 'UNKNOWN'
        assert get_network_type_from_radio(None) == 'UNKNOWN'


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_classify_with_missing_mcc_mnc(self):
        """
        Verify classification handles missing MCC/MNC gracefully.
        
        Some cell info might be incomplete. Don't crash - make
        best effort classification or default to TERRESTRIAL.
        """
        cell_data = {
            'radio': 'LTE',
            # MCC and MNC missing
            'has_ntn_capability': False
        }
        
        # Should not raise exception
        tower_type = classify_tower_type(cell_data)
        assert tower_type in ["TERRESTRIAL", "NON_TERRESTRIAL_SATELLITE"]
    
    def test_classify_with_null_data(self):
        """
        Verify classification handles null/None input gracefully.
        
        Defensive programming: handle bad input without crashing.
        """
        with pytest.raises(TypeError):
            classify_tower_type(None)
    
    def test_is_satellite_plmn_with_invalid_codes(self):
        """
        Verify PLMN checking handles invalid MCC/MNC codes.
        
        Input validation: MCC should be 3 digits, MNC 2-3 digits.
        """
        # These should not crash
        assert is_satellite_plmn(0, 0) is False
        assert is_satellite_plmn(9999, 9999) is False
        assert is_satellite_plmn(-1, -1) is False


class TestRealWorldScenarios:
    """Test real-world tower classification scenarios"""
    
    def test_tmobile_5g_terrestrial(self):
        """
        Real-world test: T-Mobile 5G terrestrial network.
        
        T-Mobile USA operates terrestrial 5G (not satellite).
        Should be classified as TERRESTRIAL.
        """
        cell_data = {
            'radio': '5G_NR',
            'mcc': 310,
            'mnc': 260,  # T-Mobile
            'has_ntn_capability': False
        }
        
        tower_type = classify_tower_type(cell_data)
        assert tower_type == "TERRESTRIAL"
    
    def test_starlink_satellite_when_plmn_available(self):
        """
        Real-world test: Starlink satellite cellular (future).
        
        If Starlink launches satellite cellular, it would use
        a specific PLMN and have NTN capability.
        """
        cell_data = {
            'radio': '5G_NR_NTN',
            'mcc': 901,  # International
            'mnc': 88,   # Example satellite allocation
            'has_ntn_capability': True
        }
        
        tower_type = classify_tower_type(cell_data)
        assert tower_type == "NON_TERRESTRIAL_SATELLITE"
