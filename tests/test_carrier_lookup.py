"""
Tests for carrier lookup service

Verifies MCC-MNC to carrier name mapping functionality.
"""

import pytest
from src.services.carrier_lookup import (
    get_carrier_name,
    get_country_from_mcc,
    add_carrier_mapping,
    get_all_carriers_for_country
)


class TestCarrierLookup:
    """Test carrier name lookup from MCC-MNC codes"""
    
    def test_get_tmobile_usa(self):
        """Verify T-Mobile USA lookup"""
        carrier = get_carrier_name(310, 260)
        assert carrier == "T-Mobile USA"
    
    def test_get_verizon(self):
        """Verify Verizon lookup"""
        carrier = get_carrier_name(311, 480)
        assert carrier == "Verizon"
    
    def test_get_att(self):
        """Verify AT&T lookup"""
        carrier = get_carrier_name(310, 410)
        assert carrier == "AT&T"
    
    def test_get_vodafone_uk(self):
        """Verify Vodafone UK lookup"""
        carrier = get_carrier_name(234, 15)
        assert carrier == "Vodafone UK"
    
    def test_get_starlink_satellite(self):
        """Verify Starlink (satellite) lookup"""
        carrier = get_carrier_name(901, 88)
        assert carrier == "Starlink (SpaceX)"
    
    def test_get_oneweb_satellite(self):
        """Verify OneWeb (satellite) lookup"""
        carrier = get_carrier_name(901, 99)
        assert carrier == "OneWeb"
    
    def test_unknown_carrier_with_country(self):
        """Verify unknown carrier shows country if MCC is known"""
        # Use a valid MCC (310 = USA) but unknown MNC
        carrier = get_carrier_name(310, 999)
        assert "Unknown Carrier in United States" in carrier
        assert "310-999" in carrier
    
    def test_unknown_carrier_unknown_country(self):
        """Verify completely unknown carrier"""
        carrier = get_carrier_name(999, 999)
        assert "Unknown Carrier" in carrier
        assert "999-999" in carrier
    
    def test_mnc_formatting(self):
        """Verify MNC is zero-padded in output"""
        carrier = get_carrier_name(999, 1)
        assert "999-001" in carrier


class TestCountryLookup:
    """Test country identification from MCC"""
    
    def test_usa_mcc_range(self):
        """Verify USA MCC range (310-316)"""
        assert get_country_from_mcc(310) == "United States"
        assert get_country_from_mcc(316) == "United States"
    
    def test_uk_mcc(self):
        """Verify UK MCC"""
        assert get_country_from_mcc(234) == "United Kingdom"
    
    def test_ireland_mcc(self):
        """Verify Ireland MCC"""
        assert get_country_from_mcc(272) == "Ireland"
    
    def test_china_mcc(self):
        """Verify China MCC"""
        assert get_country_from_mcc(460) == "China"
    
    def test_satellite_mcc(self):
        """Verify international/satellite MCC"""
        country = get_country_from_mcc(901)
        assert country == "International/Satellite"
    
    def test_unknown_mcc(self):
        """Verify unknown MCC returns None"""
        assert get_country_from_mcc(999) is None


class TestCustomCarrierMapping:
    """Test adding custom carrier mappings"""
    
    def test_add_new_carrier(self):
        """Verify adding a new carrier mapping"""
        # Add a test carrier
        add_carrier_mapping(999, 100, "Test Carrier Network")
        
        # Verify it can be retrieved
        carrier = get_carrier_name(999, 100)
        assert carrier == "Test Carrier Network"
    
    def test_override_existing_carrier(self):
        """Verify overriding an existing carrier"""
        from src.services.carrier_lookup import CARRIER_DATABASE
        
        # Save original
        original = CARRIER_DATABASE.get((310, 260))
        
        try:
            # Override it
            add_carrier_mapping(310, 260, "New Carrier Name")
            updated = get_carrier_name(310, 260)
            
            assert updated == "New Carrier Name"
            assert updated != original
        finally:
            # Restore original
            if original:
                CARRIER_DATABASE[(310, 260)] = original


class TestGetAllCarriersForCountry:
    """Test retrieving all carriers for a country"""
    
    def test_get_usa_carriers(self):
        """Verify getting all USA carriers"""
        carriers = get_all_carriers_for_country("United States")
        
        # Should have multiple carriers
        assert len(carriers) > 0
        
        # Verify some known carriers are present
        carrier_names = carriers.values()
        assert any("T-Mobile" in name for name in carrier_names)
        assert any("Verizon" in name for name in carrier_names)
        assert any("AT&T" in name for name in carrier_names)
    
    def test_get_uk_carriers(self):
        """Verify getting all UK carriers"""
        carriers = get_all_carriers_for_country("United Kingdom")
        
        assert len(carriers) > 0
        carrier_names = carriers.values()
        assert any("Vodafone UK" in name for name in carrier_names)
        assert any("EE" in name for name in carrier_names)
    
    def test_get_satellite_carriers(self):
        """Verify getting satellite carriers"""
        carriers = get_all_carriers_for_country("International/Satellite")
        
        assert len(carriers) > 0
        carrier_names = carriers.values()
        assert any("Starlink" in name or "OneWeb" in name for name in carrier_names)
    
    def test_unknown_country(self):
        """Verify unknown country returns empty dict"""
        carriers = get_all_carriers_for_country("Atlantis")
        assert carriers == {}


class TestRealWorldScenarios:
    """Test with real-world operator codes"""
    
    def test_global_carriers(self):
        """Test lookup for major global carriers"""
        # Test a variety of carriers worldwide
        test_cases = [
            ((310, 260), "T-Mobile USA"),
            ((234, 15), "Vodafone UK"),
            ((272, 1), "Vodafone Ireland"),
            ((262, 1), "Telekom Deutschland"),
            ((440, 20), "SoftBank"),
            ((450, 5), "SK Telecom"),
            ((901, 88), "Starlink (SpaceX)"),
        ]
        
        for (mcc, mnc), expected_name in test_cases:
            carrier = get_carrier_name(mcc, mnc)
            assert carrier == expected_name, \
                f"Expected {expected_name} for {mcc}-{mnc}, got {carrier}"
    
    def test_carrier_lookup_performance(self):
        """Verify lookup is fast (should be O(1) dict lookup)"""
        import time
        
        start = time.time()
        for _ in range(1000):
            get_carrier_name(310, 260)
        elapsed = time.time() - start
        
        # 1000 lookups should complete in under 10ms
        assert elapsed < 0.01, f"Lookup too slow: {elapsed}s for 1000 calls"


class TestDataIntegrity:
    """Test data source and integrity"""
    
    def test_data_source_attribution(self):
        """Verify data source is documented"""
        from src.services import carrier_lookup
        
        assert hasattr(carrier_lookup, '__data_source__')
        assert hasattr(carrier_lookup, '__data_license__')
        assert "ITU-T" in carrier_lookup.__data_source__
    
    def test_no_duplicate_entries(self):
        """Verify no duplicate MCC-MNC entries in database"""
        from src.services.carrier_lookup import CARRIER_DATABASE
        
        # All keys should be unique (this is enforced by dict, but test it)
        keys = list(CARRIER_DATABASE.keys())
        assert len(keys) == len(set(keys))
    
    def test_all_entries_have_valid_mcc_mnc(self):
        """Verify all database entries have valid MCC-MNC ranges"""
        from src.services.carrier_lookup import CARRIER_DATABASE
        
        for (mcc, mnc) in CARRIER_DATABASE.keys():
            # MCC should be 3 digits (100-999)
            assert 100 <= mcc <= 999, f"Invalid MCC: {mcc}"
            
            # MNC should be reasonable (0-999)
            assert 0 <= mnc <= 999, f"Invalid MNC: {mnc}"
    
    def test_all_entries_have_non_empty_names(self):
        """Verify all carriers have non-empty names"""
        from src.services.carrier_lookup import CARRIER_DATABASE
        
        for carrier_name in CARRIER_DATABASE.values():
            assert carrier_name, "Empty carrier name found"
            assert len(carrier_name) > 0, "Empty carrier name found"
