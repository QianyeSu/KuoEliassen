"""
Comprehensive tests for kuoeliassen.utils module

Tests all utility functions for input validation and preprocessing.
Target: 100% coverage for utils.py
"""

import pytest
import numpy as np
from kuoeliassen.utils import normalize_pressure, normalize_latitude


class TestNormalizePressure:
    """Test normalize_pressure function."""

    def test_pressure_in_pa(self):
        """Test pressure already in Pa (no conversion needed)."""
        # Pressure in increasing order (100hPa -> 1000hPa)
        p_pa = np.array([30000, 50000, 70000, 85000, 100000])
        result = normalize_pressure(p_pa)

        # Should not be modified (already in correct order)
        np.testing.assert_array_almost_equal(result, p_pa)

    def test_pressure_in_hpa(self):
        """Test pressure in hPa (needs conversion to Pa)."""
        # Pressure in increasing order (300hPa -> 1000hPa)
        p_hpa = np.array([300, 500, 700, 850, 1000])
        result = normalize_pressure(p_hpa)

        # Should convert to Pa (maintaining order)
        expected = p_hpa * 100.0
        np.testing.assert_array_almost_equal(result, expected)

    def test_pressure_reverse_order(self):
        """Test pressure in decreasing order (needs reversal to increasing)."""
        # Input in decreasing order (1000->100 hPa)
        p = np.array([100000, 85000, 70000, 50000, 30000])
        result = normalize_pressure(p)

        # Should be reversed to increasing order
        expected = p[::-1]
        np.testing.assert_array_almost_equal(result, expected)

    def test_pressure_hpa_and_reverse(self):
        """Test pressure in hPa and decreasing order."""
        # Input in decreasing order (1000->300 hPa)
        p_hpa = np.array([1000, 850, 700, 500, 300])
        result = normalize_pressure(p_hpa)

        # Should convert to Pa AND reverse to increasing order
        expected = p_hpa[::-1] * 100.0
        np.testing.assert_array_almost_equal(result, expected)

    def test_pressure_single_value(self):
        """Test with single pressure value."""
        p = np.array([85000])
        result = normalize_pressure(p)

        np.testing.assert_array_almost_equal(result, p)

    def test_pressure_list_input(self):
        """Test with list input (should convert to array)."""
        # Input in increasing order (300->1000 hPa)
        p_list = [300, 500, 700, 850, 1000]
        result = normalize_pressure(p_list)

        # Should convert to Pa (maintaining increasing order)
        expected = np.array(p_list, dtype=np.float64) * 100.0
        np.testing.assert_array_almost_equal(result, expected)

    def test_pressure_preserves_dtype(self):
        """Test that function preserves input dtype."""
        # Input in increasing order with float32
        p_f32 = np.array([30000, 70000, 100000], dtype=np.float32)
        result_f32 = normalize_pressure(p_f32)
        assert result_f32.dtype == np.float32

        # Input with float64
        p_f64 = np.array([30000, 70000, 100000], dtype=np.float64)
        result_f64 = normalize_pressure(p_f64)
        assert result_f64.dtype == np.float64

    def test_pressure_boundary_detection(self):
        """Test median threshold for unit detection (2000 Pa)."""
        # Just below threshold - should be treated as hPa
        p_below = np.array([1700, 1800, 1900])
        result_below = normalize_pressure(p_below)
        # Should convert to Pa and maintain increasing order
        np.testing.assert_array_almost_equal(result_below, p_below * 100.0)

        # Just above threshold - should be treated as Pa
        p_above = np.array([1900, 2000, 2100])
        result_above = normalize_pressure(p_above)
        # Should maintain order (already in Pa)
        np.testing.assert_array_almost_equal(result_above, p_above)


class TestNormalizeLatitude:
    """Test normalize_latitude function."""

    def test_latitude_in_degrees(self):
        """Test latitude already in degrees."""
        # Latitude in increasing order (south to north)
        lat_deg = np.array([-45, -30, 0, 30, 45])
        result = normalize_latitude(lat_deg)

        np.testing.assert_array_almost_equal(result, lat_deg)

    def test_latitude_in_radians(self):
        """Test latitude in radians (needs conversion)."""
        lat_rad = np.array([-np.pi/4, -np.pi/6, 0, np.pi /
                           6, np.pi/4])
        result = normalize_latitude(lat_rad)

        expected = np.rad2deg(lat_rad)
        np.testing.assert_array_almost_equal(result, expected)

    def test_latitude_reverse_order(self):
        """Test latitude in decreasing order (needs reversal to increasing)."""
        # Latitude in decreasing order (north to south)
        lat = np.array([45, 30, 0, -30, -45])
        result = normalize_latitude(lat)

        # Should be reversed to increasing order
        expected = lat[::-1]
        np.testing.assert_array_almost_equal(result, expected)

    def test_latitude_radians_and_reverse(self):
        """Test latitude in radians and decreasing order."""
        lat_rad = np.array([np.pi/4, np.pi/6, 0, -np.pi /
                           6, -np.pi/4])
        result = normalize_latitude(lat_rad)

        # Should convert to degrees AND reverse
        expected = np.rad2deg(lat_rad[::-1])
        np.testing.assert_array_almost_equal(result, expected)

    def test_latitude_single_value(self):
        """Test with single latitude value."""
        lat = np.array([30.0])
        result = normalize_latitude(lat)

        np.testing.assert_array_almost_equal(result, lat)

    def test_latitude_equator(self):
        """Test with equatorial latitudes."""
        lat = np.array([-5, 0, 5])
        result = normalize_latitude(lat)

        np.testing.assert_array_almost_equal(result, lat)

    def test_latitude_poles(self):
        """Test with polar latitudes."""
        lat = np.array([-90, -60, 0, 60, 90])
        result = normalize_latitude(lat)

        np.testing.assert_array_almost_equal(result, lat)

    def test_latitude_list_input(self):
        """Test with list input."""
        lat_list = [-30, 0, 30, 60]
        result = normalize_latitude(lat_list)

        expected = np.array(lat_list, dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)

    def test_latitude_preserves_dtype(self):
        """Test that function preserves input dtype."""
        # Input with float32
        lat_f32 = np.array([30, 40, 50], dtype=np.float32)
        result_f32 = normalize_latitude(lat_f32)
        assert result_f32.dtype == np.float32

        # Input with float64
        lat_f64 = np.array([30, 40, 50], dtype=np.float64)
        result_f64 = normalize_latitude(lat_f64)
        assert result_f64.dtype == np.float64

    def test_latitude_radian_detection_threshold(self):
        """Test threshold for radian detection (π/2)."""
        # Just below π/2 - should be treated as radians
        lat_rad = np.array([0, np.pi/4, np.pi/2 - 0.01])
        result = normalize_latitude(lat_rad)
        expected = np.rad2deg(lat_rad)
        np.testing.assert_array_almost_equal(result, expected)

        # Well above π/2 - should be treated as degrees
        lat_deg = np.array([0, 30, 60, 90])
        result = normalize_latitude(lat_deg)
        np.testing.assert_array_almost_equal(result, lat_deg)


class TestUtilsEdgeCases:
    """Test edge cases for utility functions."""

    def test_pressure_empty_array(self):
        """Test normalize_pressure with empty array."""
        p = np.array([])
        result = normalize_pressure(p)
        assert len(result) == 0

    def test_latitude_empty_array(self):
        """Test normalize_latitude with empty array."""
        lat = np.array([])
        result = normalize_latitude(lat)
        assert len(result) == 0

    def test_pressure_constant_values(self):
        """Test pressure with all same values."""
        p = np.array([85000, 85000, 85000])
        result = normalize_pressure(p)
        np.testing.assert_array_almost_equal(result, p)

    def test_latitude_constant_values(self):
        """Test latitude with all same values."""
        lat = np.array([30, 30, 30])
        result = normalize_latitude(lat)
        np.testing.assert_array_almost_equal(result, lat)

    def test_pressure_mixed_precision(self):
        """Test pressure with float32 input."""
        # Pressure in increasing order (300->1000 hPa)
        p_float32 = np.array([300, 700, 850, 1000], dtype=np.float32)
        result = normalize_pressure(p_float32)

        # Should work and preserve float32
        assert result.dtype == np.float32
        # Convert to Pa and maintain increasing order
        expected = p_float32 * 100.0
        np.testing.assert_array_almost_equal(result, expected)

    def test_latitude_mixed_precision(self):
        """Test latitude with float32 input."""
        lat_float32 = np.array([-30, 0, 30], dtype=np.float32)
        result = normalize_latitude(lat_float32)

        assert result.dtype == np.float32
        np.testing.assert_array_almost_equal(result, lat_float32)

    def test_pressure_very_small_values(self):
        """Test pressure with very small values (definitely hPa)."""
        # Small values in increasing order
        p = np.array([10, 50, 100, 300])
        result = normalize_pressure(p)

        expected = p * 100.0
        np.testing.assert_array_almost_equal(result, expected)

    def test_pressure_very_large_values(self):
        """Test pressure with very large values (definitely Pa)."""
        # Large values in increasing order
        p = np.array([100000, 105000, 110000])
        result = normalize_pressure(p)

        # Should not multiply by 100, maintain increasing order
        np.testing.assert_array_almost_equal(result, p)


class TestUtilsIntegration:
    """Integration tests for utility functions."""

    def test_typical_atmospheric_profile(self):
        """Test with typical atmospheric pressure and latitude."""
        # Typical pressure levels in hPa (in increasing order: 100->1000)
        p_hpa = np.array([100, 200, 300, 500, 700, 850, 925, 1000])
        # Typical latitudes in degrees (in increasing order: -60->60)
        lat = np.array([-60, -30, 0, 30, 60])

        p_normalized = normalize_pressure(p_hpa)
        lat_normalized = normalize_latitude(lat)

        # Check pressure is in Pa and increasing
        assert p_normalized[0] < p_normalized[-1]
        assert np.all(p_normalized >= 10000)  # At least 100 hPa

        # Check latitude is in degrees and increasing
        assert lat_normalized[0] < lat_normalized[-1]
        assert np.all(np.abs(lat_normalized) <= 90)

    def test_pressure_latitude_independence(self):
        """Test that functions don't interfere with each other."""
        # Pressure in increasing order
        p = np.array([300, 500, 850, 1000])
        # Latitude in decreasing order (needs reversal)
        lat = np.array([60, 30, 0, -30])

        p_norm = normalize_pressure(p)
        lat_norm = normalize_latitude(lat)

        # Both should be properly normalized
        assert p_norm[0] < p_norm[-1]  # Pressure increasing
        assert lat_norm[0] < lat_norm[-1]  # Latitude increasing

    def test_copy_behavior(self):
        """Test that functions don't modify input arrays."""
        # Pressure in increasing order
        p_original = np.array([300, 500, 850, 1000])
        # Latitude in decreasing order
        lat_original = np.array([60, 30, 0, -30])

        p_copy = p_original.copy()
        lat_copy = lat_original.copy()

        normalize_pressure(p_original)
        normalize_latitude(lat_original)

        # Original arrays should be unchanged
        np.testing.assert_array_equal(p_original, p_copy)
        np.testing.assert_array_equal(lat_original, lat_copy)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src/kuoeliassen',
                '--cov-report=term-missing'])
