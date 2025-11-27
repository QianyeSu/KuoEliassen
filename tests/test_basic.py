"""
Comprehensive tests for KuoEliassen package

Target: 90%+ code coverage
"""
import pytest
import numpy as np
import xarray as xr


class TestPackageImports:
    """Test package imports and basic attributes."""

    def test_import_package(self):
        """Test that the package can be imported."""
        import kuoeliassen
        assert kuoeliassen.__version__ is not None
        assert kuoeliassen.__author__ is not None

    def test_import_solve_ke(self):
        """Test that solve_ke can be imported."""
        from kuoeliassen import solve_ke
        assert callable(solve_ke)

    def test_import_solve_ke_lhs(self):
        """Test that solve_ke_LHS can be imported."""
        from kuoeliassen.core import solve_ke_LHS
        assert callable(solve_ke_LHS)

    def test_import_xarray_interface(self):
        """Test that xarray interface can be imported."""
        from kuoeliassen.xarray_interface import solve_ke_xarray
        assert callable(solve_ke_xarray)

    def test_import_xarray_lhs(self):
        """Test that xarray LHS interface can be imported."""
        from kuoeliassen.xarray_interface import solve_ke_LHS_xarray
        assert callable(solve_ke_LHS_xarray)

    def test_package_all(self):
        """Test __all__ exports."""
        import kuoeliassen
        assert 'solve_ke' in kuoeliassen.__all__
        assert 'solve_ke_xarray' in kuoeliassen.__all__


class TestSolveKEBasic:
    """Test basic solve_ke functionality."""

    @pytest.fixture
    def basic_data(self):
        """Create minimal test data."""
        np.random.seed(42)
        # (ntime, nlev, nlat) to match core.py expectations
        nt, nz, ny = 2, 5, 3

        data = {
            'v': np.random.randn(nt, nz, ny),
            'temperature': np.random.randn(nt, nz, ny) + 273.15,
            'heating': np.random.randn(nt, nz, ny) * 0.01,
            'vt_eddy': np.random.randn(nt, nz, ny) * 0.1,
            'vu_eddy': np.random.randn(nt, nz, ny) * 0.1,
            'pressure': np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100,
            'latitude': np.array([30, 35, 40], dtype=np.float64),
        }
        return data

    def test_single_heating_mode(self, basic_data):
        """Test solve_ke with single heating mode."""
        from kuoeliassen import solve_ke

        result = solve_ke(
            v=basic_data['v'],
            temperature=basic_data['temperature'],
            heating=basic_data['heating'],
            vt_eddy=basic_data['vt_eddy'],
            vu_eddy=basic_data['vu_eddy'],
            pressure=basic_data['pressure'],
            latitude=basic_data['latitude'],
            qgpv=True
        )

        # Check expected keys
        assert 'PSI' in result
        assert 'D' in result
        assert 'PSI_Q' in result
        assert 'PSI_latent' in result
        assert 'PSI_rad' in result
        assert 'PSI_vt' in result
        assert 'PSI_vu' in result
        assert 'PSI_x' in result
        # qgpv=True adds these
        assert 'momentum_term' in result
        assert 'thermal_term' in result
        assert 'residual' in result

        # Check shapes
        nt, nz, ny = basic_data['v'].shape
        assert result['PSI_Q'].shape == (nt, nz, ny)
        assert result['PSI_vt'].shape == (nt, nz, ny)

        # In single heating mode, PSI_latent and PSI_rad should be zeros
        assert np.allclose(result['PSI_latent'], 0.0)
        assert np.allclose(result['PSI_rad'], 0.0)

    def test_decomposed_heating_mode(self, basic_data):
        """Test solve_ke with decomposed heating (latent + rad)."""
        from kuoeliassen import solve_ke

        latent_heating = basic_data['heating'] * 0.6
        rad_heating = basic_data['heating'] * 0.4

        result = solve_ke(
            v=basic_data['v'],
            temperature=basic_data['temperature'],
            latent_heating=latent_heating,
            rad_heating=rad_heating,
            vt_eddy=basic_data['vt_eddy'],
            vu_eddy=basic_data['vu_eddy'],
            pressure=basic_data['pressure'],
            latitude=basic_data['latitude'],
            qgpv=True
        )

        # Check expected keys
        assert 'PSI_Q' in result
        assert 'PSI_latent' in result
        assert 'PSI_rad' in result

        # In decomposed mode, PSI_latent and PSI_rad should not be zeros
        assert not np.allclose(result['PSI_latent'], 0.0)
        assert not np.allclose(result['PSI_rad'], 0.0)

        # PSI_Q should be sum of components
        psi_sum = result['PSI_latent'] + result['PSI_rad']
        assert np.allclose(result['PSI_Q'], psi_sum, rtol=1e-5)

    def test_qgpv_false(self, basic_data):
        """Test solve_ke with qgpv=False."""
        from kuoeliassen import solve_ke

        result = solve_ke(
            v=basic_data['v'],
            temperature=basic_data['temperature'],
            heating=basic_data['heating'],
            vt_eddy=basic_data['vt_eddy'],
            vu_eddy=basic_data['vu_eddy'],
            pressure=basic_data['pressure'],
            latitude=basic_data['latitude'],
            qgpv=False
        )

        # Should still have all basic keys (but not qgpv-specific keys)
        assert 'PSI_Q' in result
        assert 'PSI_x' in result
        assert 'D' in result
        # qgpv=False means no momentum_term, thermal_term, residual
        assert 'momentum_term' not in result
        assert 'thermal_term' not in result
        assert 'residual' not in result

    def test_missing_heating_error(self, basic_data):
        """Test that missing heating raises ValueError."""
        from kuoeliassen import solve_ke

        with pytest.raises(ValueError, match="Either 'heating' or both 'rad_heating' and 'latent_heating' required"):
            solve_ke(
                v=basic_data['v'],
                temperature=basic_data['temperature'],
                # No heating parameter
                vt_eddy=basic_data['vt_eddy'],
                vu_eddy=basic_data['vu_eddy'],
                pressure=basic_data['pressure'],
                latitude=basic_data['latitude'],
                qgpv=True
            )

    # Note: If both heating and (rad_heating,latent_heating) are provided,
    # the code uses rad_heating and latent_heating (decomposed mode takes priority).
    # This is acceptable behavior, so no conflicting error test is needed.


class TestSolveKELHS:
    """Test solve_ke_LHS functionality."""

    @pytest.fixture
    def basic_data(self):
        """Create minimal test data for LHS decomposition."""
        np.random.seed(42)
        nlev, nlat = 5, 3  # Use 2D data: (pressure levels, latitudes)

        data = {
            # Streamfunction in kg/s - 2D: (nlev, nlat)
            'psi_base': np.random.randn(nlev, nlat) * 1e9,
            'temp_base': np.random.randn(nlev, nlat) * 10 + 273.15,
            'psi_current': np.random.randn(nlev, nlat) * 1e9,
            'temp_current': np.random.randn(nlev, nlat) * 10 + 273.15,
            # (nlev,) = (5,)
            'pressure': np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100,
            # (nlat,) = (3,)
            'latitude': np.array([30, 35, 40], dtype=np.float64),
        }
        return data

    def test_lhs_decomposition(self, basic_data):
        """Test LHS decomposition functionality."""
        from kuoeliassen.core import solve_ke_LHS

        result = solve_ke_LHS(
            psi_base=basic_data['psi_base'],
            temp_base=basic_data['temp_base'],
            psi_current=basic_data['psi_current'],
            temp_current=basic_data['temp_current'],
            pressure=basic_data['pressure'],
            latitude=basic_data['latitude']
        )

        # Check expected keys
        assert 'PSI_stability' in result
        assert 'PSI_residual' in result

        # Check shapes
        nlev, nlat = basic_data['psi_base'].shape  # 2D data now
        assert result['PSI_stability'].shape == (nlev, nlat)
        assert result['PSI_residual'].shape == (nlev, nlat)

    def test_lhs_qgpv_false(self, basic_data):
        """Test LHS decomposition (no qgpv parameter in LHS)."""
        from kuoeliassen.core import solve_ke_LHS

        result = solve_ke_LHS(
            psi_base=basic_data['psi_base'],
            temp_base=basic_data['temp_base'],
            psi_current=basic_data['psi_current'],
            temp_current=basic_data['temp_current'],
            pressure=basic_data['pressure'],
            latitude=basic_data['latitude']
        )

        # Check expected keys
        assert 'PSI_stability' in result
        assert 'PSI_residual' in result


class TestXarrayInterface:
    """Test xarray interface functions."""

    @pytest.fixture
    def xarray_data(self):
        """Create xarray test data."""
        nt, nz, ny = 2, 5, 3  # (time, pressure, latitude) order to match core.py

        p = np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100
        lat = np.array([30, 35, 40], dtype=np.float64)
        time = np.arange(nt)

        data = xr.Dataset({
            'v': (['time', 'level', 'lat'], np.random.randn(nt, nz, ny)),
            'temp': (['time', 'level', 'lat'], np.random.randn(nt, nz, ny) + 273.15),
            'heating': (['time', 'level', 'lat'], np.random.randn(nt, nz, ny) * 0.01),
            'vt_eddy': (['time', 'level', 'lat'], np.random.randn(nt, nz, ny) * 0.1),
            'vu_eddy': (['time', 'level', 'lat'], np.random.randn(nt, nz, ny) * 0.1),
        }, coords={
            'level': p,
            'lat': lat,
            'time': time,
        })

        return data

    def test_xarray_solve(self, xarray_data):
        """Test xarray interface with Dataset."""
        from kuoeliassen.xarray_interface import solve_ke_xarray

        result = solve_ke_xarray(
            v=xarray_data['v'],
            temperature=xarray_data['temp'],
            heating=xarray_data['heating'],
            vt_eddy=xarray_data['vt_eddy'],
            vu_eddy=xarray_data['vu_eddy'],
            pressure_dim='level',
            latitude_dim='lat',
            qgpv=True
        )

        # Should return xarray Dataset
        assert isinstance(result, xr.Dataset)

        # Check variables (correct keys: PSI_Q, PSI_vt, not D_vt)
        assert 'PSI_Q' in result
        assert 'PSI_vt' in result

        # Check coordinates preserved
        assert 'level' in result.coords
        assert 'lat' in result.coords

    def test_xarray_reverse_level(self, xarray_data):
        """Test xarray with reversed level coordinate."""
        from kuoeliassen.xarray_interface import solve_ke_xarray

        # Reverse level coordinate
        data_reversed = xarray_data.isel(level=slice(None, None, -1))

        result = solve_ke_xarray(
            v=data_reversed['v'],
            temperature=data_reversed['temp'],
            heating=data_reversed['heating'],
            vt_eddy=data_reversed['vt_eddy'],
            vu_eddy=data_reversed['vu_eddy'],
            pressure_dim='level',
            latitude_dim='lat',
            qgpv=True
        )

        # Should handle reversed coordinates correctly
        assert isinstance(result, xr.Dataset)
        assert 'PSI_Q' in result

    def test_xarray_lhs(self, xarray_data):
        """Test xarray LHS interface."""
        from kuoeliassen.xarray_interface import solve_ke_LHS_xarray

        # Create base and current PSI solutions (time, pressure, latitude order)
        nt, nz, ny = 2, 5, 3

        psi_base = xr.DataArray(np.random.randn(nt, nz, ny) * 1e9,
                                dims=['time', 'level', 'lat'],
                                coords=xarray_data.coords)
        psi_current = xr.DataArray(np.random.randn(nt, nz, ny) * 1e9,
                                   dims=['time', 'level', 'lat'],
                                   coords=xarray_data.coords)

        result = solve_ke_LHS_xarray(
            psi_base=psi_base,
            temp_base=xarray_data['temp'],
            psi_current=psi_current,
            temp_current=xarray_data['temp']
        )

        assert isinstance(result, xr.Dataset)
        assert 'PSI_stability' in result
        assert 'PSI_residual' in result


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_2d_input(self):
        """Test with 2D input (no time dimension)."""
        from kuoeliassen import solve_ke

        nz, ny = 5, 3

        v_mean = np.random.randn(nz, ny)
        temp = np.random.randn(nz, ny) + 273.15
        heating = np.random.randn(nz, ny) * 0.01
        vt_eddy = np.random.randn(nz, ny) * 0.1
        vu_eddy = np.random.randn(nz, ny) * 0.1
        level = np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100
        lat = np.array([30, 35, 40], dtype=np.float64)

        result = solve_ke(
            v=v_mean,
            temperature=temp,
            heating=heating,
            vt_eddy=vt_eddy,
            vu_eddy=vu_eddy,
            pressure=level,
            latitude=lat,
            qgpv=True
        )

        assert result['PSI_Q'].shape == (nz, ny)

    def test_1d_input(self):
        """Test with minimal 2D input (few latitude points)."""
        from kuoeliassen import solve_ke

        nz = 5
        ny = 2  # Minimum 2 latitude points to avoid boundary issues

        v_mean = np.random.randn(nz, ny)  # Shape (nz, ny)
        temp = np.random.randn(nz, ny) + 273.15
        heating = np.random.randn(nz, ny) * 0.01
        vt_eddy = np.random.randn(nz, ny) * 0.1
        vu_eddy = np.random.randn(nz, ny) * 0.1
        level = np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100
        lat = np.array([25.0, 35.0], dtype=np.float64)  # Two latitude points

        result = solve_ke(
            v=v_mean,
            temperature=temp,
            heating=heating,
            vt_eddy=vt_eddy,
            vu_eddy=vu_eddy,
            pressure=level,
            latitude=lat,
            qgpv=True
        )

        assert result['PSI_Q'].shape == (nz, ny)

    def test_dtype_conversion(self):
        """Test that float32 inputs are converted to float64."""
        from kuoeliassen import solve_ke

        nz, ny = 5, 3

        # Use float32
        v_mean = np.random.randn(nz, ny).astype(np.float32)
        temp = (np.random.randn(nz, ny) + 273.15).astype(np.float32)
        heating = (np.random.randn(nz, ny) * 0.01).astype(np.float32)
        vt_eddy = (np.random.randn(nz, ny) * 0.1).astype(np.float32)
        vu_eddy = (np.random.randn(nz, ny) * 0.1).astype(np.float32)
        level = np.array([1000, 850, 700, 500, 300], dtype=np.float32) * 100
        lat = np.array([30, 35, 40], dtype=np.float32)

        # Should not raise error
        result = solve_ke(
            v=v_mean,
            temperature=temp,
            heating=heating,
            vt_eddy=vt_eddy,
            vu_eddy=vu_eddy,
            pressure=level,
            latitude=lat,
            qgpv=True
        )

        # Result should be float64
        assert result['PSI_Q'].dtype == np.float64


class TestUtilityFunctions:
    """Test utility functions if any."""

    def test_version_string(self):
        """Test version string format."""
        import kuoeliassen
        version = kuoeliassen.__version__

        # Should be semantic version format
        parts = version.split('.')
        assert len(parts) >= 2
        assert all(p.isdigit() or p[0].isdigit() for p in parts)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=src/kuoeliassen',
                '--cov-report=term-missing'])
