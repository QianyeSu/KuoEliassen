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
        nz, ny, nt = 5, 3, 2

        data = {
            'v_mean': np.random.randn(nz, ny, nt),
            'temperature': np.random.randn(nz, ny, nt) + 273.15,
            'heating': np.random.randn(nz, ny, nt) * 0.01,
            'vt_eddy': np.random.randn(nz, ny, nt) * 0.1,
            'vu_eddy': np.random.randn(nz, ny, nt) * 0.1,
            'p': np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100,
            'phi': np.array([30, 35, 40], dtype=np.float64),
        }
        return data

    def test_single_heating_mode(self, basic_data):
        """Test solve_ke with single heating mode."""
        from kuoeliassen import solve_ke

        result = solve_ke(
            v_mean=basic_data['v_mean'],
            temperature=basic_data['temperature'],
            heating=basic_data['heating'],
            vt_eddy=basic_data['vt_eddy'],
            vu_eddy=basic_data['vu_eddy'],
            p=basic_data['p'],
            phi=basic_data['phi'],
            qgpv=True
        )

        # Check expected keys
        assert 'PSI_Q' in result
        assert 'PSI_latent' in result
        assert 'PSI_rad' in result
        assert 'D_vt' in result
        assert 'D_vu' in result
        assert 'D_x' in result
        assert 'F_friction' in result

        # Check shapes
        nz, ny, nt = basic_data['v_mean'].shape
        assert result['PSI_Q'].shape == (nz, ny, nt)
        assert result['D_vt'].shape == (nz, ny, nt)

        # In single heating mode, PSI_latent and PSI_rad should be zeros
        assert np.allclose(result['PSI_latent'], 0.0)
        assert np.allclose(result['PSI_rad'], 0.0)

    def test_decomposed_heating_mode(self, basic_data):
        """Test solve_ke with decomposed heating (latent + rad)."""
        from kuoeliassen import solve_ke

        latent_heating = basic_data['heating'] * 0.6
        rad_heating = basic_data['heating'] * 0.4

        result = solve_ke(
            v_mean=basic_data['v_mean'],
            temperature=basic_data['temperature'],
            latent_heating=latent_heating,
            rad_heating=rad_heating,
            vt_eddy=basic_data['vt_eddy'],
            vu_eddy=basic_data['vu_eddy'],
            p=basic_data['p'],
            phi=basic_data['phi'],
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
            v_mean=basic_data['v_mean'],
            temperature=basic_data['temperature'],
            heating=basic_data['heating'],
            vt_eddy=basic_data['vt_eddy'],
            vu_eddy=basic_data['vu_eddy'],
            p=basic_data['p'],
            phi=basic_data['phi'],
            qgpv=False
        )

        # Should still have all keys
        assert 'PSI_Q' in result
        assert 'D_x' in result
        assert 'F_friction' in result

    def test_missing_heating_error(self, basic_data):
        """Test that missing heating raises ValueError."""
        from kuoeliassen import solve_ke

        with pytest.raises(ValueError, match="Either heating or both"):
            solve_ke(
                v_mean=basic_data['v_mean'],
                temperature=basic_data['temperature'],
                # No heating parameter
                vt_eddy=basic_data['vt_eddy'],
                vu_eddy=basic_data['vu_eddy'],
                p=basic_data['p'],
                phi=basic_data['phi'],
                qgpv=True
            )

    def test_conflicting_heating_error(self, basic_data):
        """Test that providing both heating modes raises ValueError."""
        from kuoeliassen import solve_ke

        with pytest.raises(ValueError, match="Cannot provide both"):
            solve_ke(
                v_mean=basic_data['v_mean'],
                temperature=basic_data['temperature'],
                heating=basic_data['heating'],
                latent_heating=basic_data['heating'],
                rad_heating=basic_data['heating'],
                vt_eddy=basic_data['vt_eddy'],
                vu_eddy=basic_data['vu_eddy'],
                p=basic_data['p'],
                phi=basic_data['phi'],
                qgpv=True
            )


class TestSolveKELHS:
    """Test solve_ke_LHS functionality."""

    @pytest.fixture
    def basic_data(self):
        """Create minimal test data."""
        nz, ny, nt = 5, 3, 2

        data = {
            'v_mean': np.random.randn(nz, ny, nt),
            'temperature': np.random.randn(nz, ny, nt) + 273.15,
            'vt_eddy': np.random.randn(nz, ny, nt) * 0.1,
            'vu_eddy': np.random.randn(nz, ny, nt) * 0.1,
            'p': np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100,
            'phi': np.array([30, 35, 40], dtype=np.float64),
        }
        return data

    def test_lhs_decomposition(self, basic_data):
        """Test LHS decomposition functionality."""
        from kuoeliassen.core import solve_ke_LHS

        result = solve_ke_LHS(
            v_mean=basic_data['v_mean'],
            temperature=basic_data['temperature'],
            vt_eddy=basic_data['vt_eddy'],
            vu_eddy=basic_data['vu_eddy'],
            p=basic_data['p'],
            phi=basic_data['phi'],
            qgpv=True
        )

        # Check expected keys
        assert 'PSI_vt' in result
        assert 'PSI_vu' in result
        assert 'PSI_x' in result
        assert 'PSI_friction' in result

        # Check shapes
        nz, ny, nt = basic_data['v_mean'].shape
        assert result['PSI_vt'].shape == (nz, ny, nt)
        assert result['PSI_vu'].shape == (nz, ny, nt)

    def test_lhs_qgpv_false(self, basic_data):
        """Test LHS with qgpv=False."""
        from kuoeliassen.core import solve_ke_LHS

        result = solve_ke_LHS(
            v_mean=basic_data['v_mean'],
            temperature=basic_data['temperature'],
            vt_eddy=basic_data['vt_eddy'],
            vu_eddy=basic_data['vu_eddy'],
            p=basic_data['p'],
            phi=basic_data['phi'],
            qgpv=False
        )

        assert 'PSI_vt' in result
        assert 'PSI_vu' in result


class TestXarrayInterface:
    """Test xarray interface functions."""

    @pytest.fixture
    def xarray_data(self):
        """Create xarray test data."""
        nz, ny, nt = 5, 3, 2

        p = np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100
        lat = np.array([30, 35, 40], dtype=np.float64)
        time = np.arange(nt)

        data = xr.Dataset({
            'v': (['pressure', 'latitude', 'time'], np.random.randn(nz, ny, nt)),
            'temp': (['pressure', 'latitude', 'time'], np.random.randn(nz, ny, nt) + 273.15),
            'heating': (['pressure', 'latitude', 'time'], np.random.randn(nz, ny, nt) * 0.01),
            'vt_eddy': (['pressure', 'latitude', 'time'], np.random.randn(nz, ny, nt) * 0.1),
            'vu_eddy': (['pressure', 'latitude', 'time'], np.random.randn(nz, ny, nt) * 0.1),
        }, coords={
            'pressure': p,
            'latitude': lat,
            'time': time,
        })

        return data

    def test_xarray_solve(self, xarray_data):
        """Test xarray interface with Dataset."""
        from kuoeliassen.xarray_interface import solve_ke_xarray

        result = solve_ke_xarray(
            v_mean=xarray_data['v'],
            temperature=xarray_data['temp'],
            heating=xarray_data['heating'],
            vt_eddy=xarray_data['vt_eddy'],
            vu_eddy=xarray_data['vu_eddy'],
            qgpv=True
        )

        # Should return xarray Dataset
        assert isinstance(result, xr.Dataset)

        # Check variables
        assert 'PSI_Q' in result
        assert 'D_vt' in result

        # Check coordinates preserved
        assert 'pressure' in result.coords
        assert 'latitude' in result.coords

    def test_xarray_reverse_pressure(self, xarray_data):
        """Test xarray with reversed pressure coordinate."""
        from kuoeliassen.xarray_interface import solve_ke_xarray

        # Reverse pressure coordinate
        data_reversed = xarray_data.isel(pressure=slice(None, None, -1))

        result = solve_ke_xarray(
            v_mean=data_reversed['v'],
            temperature=data_reversed['temp'],
            heating=data_reversed['heating'],
            vt_eddy=data_reversed['vt_eddy'],
            vu_eddy=data_reversed['vu_eddy'],
            qgpv=True
        )

        # Should handle reversed coordinates correctly
        assert isinstance(result, xr.Dataset)
        assert 'PSI_Q' in result

    def test_xarray_lhs(self, xarray_data):
        """Test xarray LHS interface."""
        from kuoeliassen.xarray_interface import solve_ke_LHS_xarray

        result = solve_ke_LHS_xarray(
            v_mean=xarray_data['v'],
            temperature=xarray_data['temp'],
            vt_eddy=xarray_data['vt_eddy'],
            vu_eddy=xarray_data['vu_eddy'],
            qgpv=True
        )

        assert isinstance(result, xr.Dataset)
        assert 'PSI_vt' in result
        assert 'PSI_vu' in result


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
        p = np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100
        phi = np.array([30, 35, 40], dtype=np.float64)

        result = solve_ke(
            v_mean=v_mean,
            temperature=temp,
            heating=heating,
            vt_eddy=vt_eddy,
            vu_eddy=vu_eddy,
            p=p,
            phi=phi,
            qgpv=True
        )

        assert result['PSI_Q'].shape == (nz, ny)

    def test_1d_input(self):
        """Test with 1D input (single profile)."""
        from kuoeliassen import solve_ke

        nz = 5

        v_mean = np.random.randn(nz)
        temp = np.random.randn(nz) + 273.15
        heating = np.random.randn(nz) * 0.01
        vt_eddy = np.random.randn(nz) * 0.1
        vu_eddy = np.random.randn(nz) * 0.1
        p = np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100
        phi = np.array([30.0], dtype=np.float64)

        result = solve_ke(
            v_mean=v_mean,
            temperature=temp,
            heating=heating,
            vt_eddy=vt_eddy,
            vu_eddy=vu_eddy,
            p=p,
            phi=phi,
            qgpv=True
        )

        assert result['PSI_Q'].shape == (nz,)

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
        p = np.array([1000, 850, 700, 500, 300], dtype=np.float32) * 100
        phi = np.array([30, 35, 40], dtype=np.float32)

        # Should not raise error
        result = solve_ke(
            v_mean=v_mean,
            temperature=temp,
            heating=heating,
            vt_eddy=vt_eddy,
            vu_eddy=vu_eddy,
            p=p,
            phi=phi,
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
