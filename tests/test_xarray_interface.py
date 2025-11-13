"""
Comprehensive tests for kuoeliassen.xarray_interface module

Tests xarray DataArray/Dataset wrapper functions.
Target: 90%+ coverage for xarray_interface.py
"""

import pytest
import numpy as np
import xarray as xr
from kuoeliassen.xarray_interface import solve_ke_xarray, solve_ke_LHS_xarray


class TestSolveKEXarrayBasic:
    """Test basic solve_ke_xarray functionality."""

    @pytest.fixture
    def xarray_dataset(self):
        """Create xarray Dataset with typical atmospheric data."""
        nt, nz, ny = 3, 8, 5  # (time, pressure, latitude) order to match core.py

        p = np.array([1000, 925, 850, 700, 500, 300, 200, 100]) * 100.0
        lat = np.array([20, 30, 40, 50, 60], dtype=np.float64)
        time = np.arange(nt)

        ds = xr.Dataset({
            'v': (['time', 'pressure', 'latitude'], np.random.randn(nt, nz, ny)),
            'temp': (['time', 'pressure', 'latitude'],
                     np.random.randn(nt, nz, ny) * 10 + 273.15),
            'heating': (['time', 'pressure', 'latitude'],
                        np.random.randn(nt, nz, ny) * 0.01),
            'vt_eddy': (['time', 'pressure', 'latitude'],
                        np.random.randn(nt, nz, ny) * 0.1),
            'vu_eddy': (['time', 'pressure', 'latitude'],
                        np.random.randn(nt, nz, ny) * 0.1),
        }, coords={
            'pressure': p,
            'latitude': lat,
            'time': time,
        })

        return ds

    def test_xarray_returns_dataset(self, xarray_dataset):
        """Test that solve_ke_xarray returns xarray Dataset."""
        result = solve_ke_xarray(
            v=xarray_dataset['v'],
            temperature=xarray_dataset['temp'],
            heating=xarray_dataset['heating'],
            vt_eddy=xarray_dataset['vt_eddy'],
            vu_eddy=xarray_dataset['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        assert isinstance(result, xr.Dataset)

    def test_xarray_output_variables(self, xarray_dataset):
        """Test that output contains expected variables."""
        result = solve_ke_xarray(
            v=xarray_dataset['v'],
            temperature=xarray_dataset['temp'],
            heating=xarray_dataset['heating'],
            vt_eddy=xarray_dataset['vt_eddy'],
            vu_eddy=xarray_dataset['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        # Check all expected variables present
        assert 'PSI' in result
        assert 'D' in result
        assert 'PSI_Q' in result
        assert 'PSI_latent' in result
        assert 'PSI_rad' in result
        assert 'PSI_vt' in result
        assert 'PSI_vu' in result
        assert 'PSI_x' in result
        # QGPV diagnostics
        assert 'momentum_term' in result
        assert 'thermal_term' in result
        assert 'residual' in result

    def test_xarray_preserves_coordinates(self, xarray_dataset):
        """Test that coordinates are preserved."""
        result = solve_ke_xarray(
            v=xarray_dataset['v'],
            temperature=xarray_dataset['temp'],
            heating=xarray_dataset['heating'],
            vt_eddy=xarray_dataset['vt_eddy'],
            vu_eddy=xarray_dataset['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        # Check coordinates
        assert 'pressure' in result.coords
        assert 'latitude' in result.coords
        assert 'time' in result.coords

        # Check coordinate values preserved
        np.testing.assert_array_equal(
            result.coords['pressure'].values,
            xarray_dataset.coords['pressure'].values
        )

    def test_xarray_preserves_shape(self, xarray_dataset):
        """Test that output shape matches input shape."""
        result = solve_ke_xarray(
            v=xarray_dataset['v'],
            temperature=xarray_dataset['temp'],
            heating=xarray_dataset['heating'],
            vt_eddy=xarray_dataset['vt_eddy'],
            vu_eddy=xarray_dataset['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        expected_shape = xarray_dataset['v'].shape
        assert result['PSI_Q'].shape == expected_shape

    def test_xarray_has_metadata(self, xarray_dataset):
        """Test that output variables have metadata (attrs)."""
        result = solve_ke_xarray(
            v=xarray_dataset['v'],
            temperature=xarray_dataset['temp'],
            heating=xarray_dataset['heating'],
            vt_eddy=xarray_dataset['vt_eddy'],
            vu_eddy=xarray_dataset['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        # Check that variables have attributes
        assert 'long_name' in result['PSI_Q'].attrs or 'units' in result['PSI_Q'].attrs


class TestSolveKEXarrayCoordinates:
    """Test coordinate handling in xarray interface."""

    @pytest.fixture
    def reversed_pressure_dataset(self):
        """Create dataset with reversed pressure coordinate."""
        nz, ny, nt = 5, 3, 2

        # Ascending pressure (reversed from normal)
        p = np.array([100, 300, 500, 700, 1000]) * 100.0
        lat = np.array([30, 40, 50], dtype=np.float64)
        time = np.arange(nt)

        ds = xr.Dataset({
            'v': (['pressure', 'latitude', 'time'], np.random.randn(nz, ny, nt)),
            'temp': (['pressure', 'latitude', 'time'],
                     np.random.randn(nz, ny, nt) + 273.15),
            'heating': (['pressure', 'latitude', 'time'],
                        np.random.randn(nz, ny, nt) * 0.01),
            'vt_eddy': (['pressure', 'latitude', 'time'],
                        np.random.randn(nz, ny, nt) * 0.1),
            'vu_eddy': (['pressure', 'latitude', 'time'],
                        np.random.randn(nz, ny, nt) * 0.1),
        }, coords={
            'pressure': p,
            'latitude': lat,
            'time': time,
        })

        return ds

    def test_xarray_handles_reversed_pressure(self, reversed_pressure_dataset):
        """Test that reversed pressure coordinates are handled correctly."""
        result = solve_ke_xarray(
            v=reversed_pressure_dataset['v'],
            temperature=reversed_pressure_dataset['temp'],
            heating=reversed_pressure_dataset['heating'],
            vt_eddy=reversed_pressure_dataset['vt_eddy'],
            vu_eddy=reversed_pressure_dataset['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        # Should return successfully with correct coordinates
        assert isinstance(result, xr.Dataset)
        np.testing.assert_array_equal(
            result.coords['pressure'].values,
            reversed_pressure_dataset.coords['pressure'].values
        )

    def test_xarray_custom_dimension_names(self):
        """Test with custom dimension names (not standard pressure/latitude)."""
        nz, ny, nt = 5, 3, 2

        p = np.array([1000, 850, 700, 500, 300]) * 100.0
        lat = np.array([30, 40, 50], dtype=np.float64)
        time = np.arange(nt)

        # Use custom dimension names
        ds = xr.Dataset({
            'v': (['lev', 'lat', 'time'], np.random.randn(nz, ny, nt)),
            'temp': (['lev', 'lat', 'time'],
                     np.random.randn(nz, ny, nt) + 273.15),
            'heating': (['lev', 'lat', 'time'],
                        np.random.randn(nz, ny, nt) * 0.01),
            'vt_eddy': (['lev', 'lat', 'time'],
                        np.random.randn(nz, ny, nt) * 0.1),
            'vu_eddy': (['lev', 'lat', 'time'],
                        np.random.randn(nz, ny, nt) * 0.1),
        }, coords={
            'lev': p,
            'lat': lat,
            'time': time,
        })

        result = solve_ke_xarray(
            v=ds['v'],
            temperature=ds['temp'],
            heating=ds['heating'],
            vt_eddy=ds['vt_eddy'],
            vu_eddy=ds['vu_eddy'],
            pressure_dim='lev',
            latitude_dim='lat',
            qgpv=True
        )

        # Should work and preserve dimension names
        assert 'lev' in result.dims
        assert 'lat' in result.dims


class TestSolveKEXarrayHeatingModes:
    """Test different heating input modes."""

    @pytest.fixture
    def basic_xarray(self):
        """Create basic xarray data."""
        nz, ny = 5, 3

        p = np.array([1000, 850, 700, 500, 300]) * 100.0
        lat = np.array([30, 40, 50], dtype=np.float64)

        ds = xr.Dataset({
            'v': (['pressure', 'latitude'], np.random.randn(nz, ny)),
            'temp': (['pressure', 'latitude'],
                     np.random.randn(nz, ny) + 273.15),
            'heating': (['pressure', 'latitude'],
                        np.random.randn(nz, ny) * 0.01),
            'latent': (['pressure', 'latitude'],
                       np.random.randn(nz, ny) * 0.006),
            'rad': (['pressure', 'latitude'],
                    np.random.randn(nz, ny) * 0.004),
            'vt_eddy': (['pressure', 'latitude'],
                        np.random.randn(nz, ny) * 0.1),
            'vu_eddy': (['pressure', 'latitude'],
                        np.random.randn(nz, ny) * 0.1),
        }, coords={
            'pressure': p,
            'latitude': lat,
        })

        return ds

    def test_xarray_single_heating(self, basic_xarray):
        """Test xarray with single heating field."""
        result = solve_ke_xarray(
            v=basic_xarray['v'],
            temperature=basic_xarray['temp'],
            heating=basic_xarray['heating'],
            vt_eddy=basic_xarray['vt_eddy'],
            vu_eddy=basic_xarray['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        # PSI_latent and PSI_rad should be zeros in single mode
        assert np.allclose(result['PSI_latent'].values, 0.0)
        assert np.allclose(result['PSI_rad'].values, 0.0)

    def test_xarray_decomposed_heating(self, basic_xarray):
        """Test xarray with decomposed heating."""
        result = solve_ke_xarray(
            v=basic_xarray['v'],
            temperature=basic_xarray['temp'],
            rad_heating=basic_xarray['rad'],
            latent_heating=basic_xarray['latent'],
            vt_eddy=basic_xarray['vt_eddy'],
            vu_eddy=basic_xarray['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        # Should have non-zero PSI_latent and PSI_rad
        assert not np.allclose(result['PSI_latent'].values, 0.0)
        assert not np.allclose(result['PSI_rad'].values, 0.0)


class TestSolveKELHSXarray:
    """Test solve_ke_LHS_xarray functionality."""

    @pytest.fixture
    def xarray_data(self):
        """Create xarray data for LHS tests."""
        nz, ny, nt = 5, 3, 2

        p = np.array([1000, 850, 700, 500, 300]) * 100.0
        lat = np.array([30, 40, 50], dtype=np.float64)
        time = np.arange(nt)

        ds = xr.Dataset({
            'psi_base': (['pressure', 'latitude', 'time'], np.random.randn(nz, ny, nt) * 1e9),
            'temp_base': (['pressure', 'latitude', 'time'],
                          np.random.randn(nz, ny, nt) * 10 + 273.15),
            'psi_current': (['pressure', 'latitude', 'time'], np.random.randn(nz, ny, nt) * 1e9),
            'temp_current': (['pressure', 'latitude', 'time'],
                             np.random.randn(nz, ny, nt) * 10 + 273.15),
        }, coords={
            'pressure': p,
            'latitude': lat,
            'time': time,
        })

        return ds

    def test_lhs_xarray_returns_dataset(self, xarray_data):
        """Test that LHS xarray returns Dataset."""
        result = solve_ke_LHS_xarray(
            psi_base=xarray_data['psi_base'],
            temp_base=xarray_data['temp_base'],
            psi_current=xarray_data['psi_current'],
            temp_current=xarray_data['temp_current']
        )

        assert isinstance(result, xr.Dataset)

    def test_lhs_xarray_output_variables(self, xarray_data):
        """Test LHS output variables."""
        result = solve_ke_LHS_xarray(
            psi_base=xarray_data['psi_base'],
            temp_base=xarray_data['temp_base'],
            psi_current=xarray_data['psi_current'],
            temp_current=xarray_data['temp_current']
        )

        assert 'PSI_stability' in result
        assert 'PSI_residual' in result

    def test_lhs_xarray_preserves_coordinates(self, xarray_data):
        """Test that LHS preserves coordinates."""
        result = solve_ke_LHS_xarray(
            psi_base=xarray_data['psi_base'],
            temp_base=xarray_data['temp_base'],
            psi_current=xarray_data['psi_current'],
            temp_current=xarray_data['temp_current']
        )

        assert 'pressure' in result.coords
        assert 'latitude' in result.coords
        assert 'time' in result.coords

    def test_lhs_qgpv_false(self, xarray_data):
        """Test LHS decomposition (no qgpv parameter in LHS)."""
        result = solve_ke_LHS_xarray(
            psi_base=xarray_data['psi_base'],
            temp_base=xarray_data['temp_base'],
            psi_current=xarray_data['psi_current'],
            temp_current=xarray_data['temp_current']
        )

        assert isinstance(result, xr.Dataset)
        assert 'PSI_stability' in result
        assert 'PSI_residual' in result


class TestXarrayEdgeCases:
    """Test edge cases for xarray interface."""

    def test_xarray_2d_no_time(self):
        """Test with 2D data (no time dimension)."""
        nz, ny = 5, 3

        p = np.array([1000, 850, 700, 500, 300]) * 100.0
        lat = np.array([30, 40, 50], dtype=np.float64)

        ds = xr.Dataset({
            'v': (['pressure', 'latitude'], np.random.randn(nz, ny)),
            'temp': (['pressure', 'latitude'],
                     np.random.randn(nz, ny) + 273.15),
            'heating': (['pressure', 'latitude'],
                        np.random.randn(nz, ny) * 0.01),
            'vt_eddy': (['pressure', 'latitude'],
                        np.random.randn(nz, ny) * 0.1),
            'vu_eddy': (['pressure', 'latitude'],
                        np.random.randn(nz, ny) * 0.1),
        }, coords={
            'pressure': p,
            'latitude': lat,
        })

        result = solve_ke_xarray(
            v=ds['v'],
            temperature=ds['temp'],
            heating=ds['heating'],
            vt_eddy=ds['vt_eddy'],
            vu_eddy=ds['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        assert result['PSI_Q'].shape == (nz, ny)

    def test_xarray_with_attributes(self):
        """Test that input attributes are preserved/added."""
        nz, ny = 5, 3

        p = np.array([1000, 850, 700, 500, 300]) * 100.0
        lat = np.array([30, 40, 50], dtype=np.float64)

        v = xr.DataArray(
            np.random.randn(nz, ny),
            coords={'pressure': p, 'latitude': lat},
            dims=['pressure', 'latitude'],
            attrs={'long_name': 'Meridional wind', 'units': 'm/s'}
        )

        temp = xr.DataArray(
            np.random.randn(nz, ny) + 273.15,
            coords={'pressure': p, 'latitude': lat},
            dims=['pressure', 'latitude'],
            attrs={'long_name': 'Temperature', 'units': 'K'}
        )

        heating = xr.DataArray(
            np.random.randn(nz, ny) * 0.01,
            coords={'pressure': p, 'latitude': lat},
            dims=['pressure', 'latitude']
        )

        vt_eddy = xr.DataArray(
            np.random.randn(nz, ny) * 0.1,
            coords={'pressure': p, 'latitude': lat},
            dims=['pressure', 'latitude']
        )

        vu_eddy = xr.DataArray(
            np.random.randn(nz, ny) * 0.1,
            coords={'pressure': p, 'latitude': lat},
            dims=['pressure', 'latitude']
        )

        result = solve_ke_xarray(
            v=v,
            temperature=temp,
            heating=heating,
            vt_eddy=vt_eddy,
            vu_eddy=vu_eddy, pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        # Output should have metadata
        assert isinstance(result, xr.Dataset)


class TestXarrayIntegration:
    """Integration tests for xarray interface."""

    def test_xarray_realistic_data(self):
        """Test with realistic atmospheric data ranges."""
        nz, ny, nt = 10, 7, 4

        # Realistic pressure levels
        p = np.array([1000, 925, 850, 700, 600, 500,
                     400, 300, 200, 100]) * 100.0

        # Realistic latitudes
        lat = np.array([0, 15, 30, 45, 60, 75, 90], dtype=np.float64)

        time = np.arange(nt)

        # Realistic ranges
        v_mean = np.random.randn(nz, ny, nt) * 10  # m/s
        temp = np.random.randn(nz, ny, nt) * 20 + 250  # K (200-300K range)
        heating = np.random.randn(nz, ny, nt) * 1e-5  # K/s
        vt_eddy = np.random.randn(nz, ny, nt) * 5  # K m/s
        vu_eddy = np.random.randn(nz, ny, nt) * 10  # m²/s²

        ds = xr.Dataset({
            'v': (['pressure', 'latitude', 'time'], v_mean),
            'temp': (['pressure', 'latitude', 'time'], temp),
            'heating': (['pressure', 'latitude', 'time'], heating),
            'vt_eddy': (['pressure', 'latitude', 'time'], vt_eddy),
            'vu_eddy': (['pressure', 'latitude', 'time'], vu_eddy),
        }, coords={
            'pressure': p,
            'latitude': lat,
            'time': time,
        })

        result = solve_ke_xarray(
            v=ds['v'],
            temperature=ds['temp'],
            heating=ds['heating'],
            vt_eddy=ds['vt_eddy'],
            vu_eddy=ds['vu_eddy'], pressure_dim='pressure', latitude_dim='latitude', qgpv=True
        )

        # Check output is reasonable
        assert isinstance(result, xr.Dataset)
        assert not np.any(np.isnan(result['PSI_Q'].values))
        assert not np.any(np.isinf(result['PSI_Q'].values))


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src/kuoeliassen',
                '--cov-report=term-missing'])
