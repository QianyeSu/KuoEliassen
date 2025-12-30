"""
Additional tests to achieve 95%+ code coverage
Tests edge cases and error handling paths
"""

import pytest
import numpy as np
import xarray as xr
from kuoeliassen import solve_ke, solve_ke_LHS
from kuoeliassen.xarray_interface import solve_ke_xarray, solve_ke_LHS_xarray


class TestSORSolver:
    """Test SOR solver path (lines 72-100 in core.py)"""

    def test_sor_solver_basic(self):
        """Test SOR solver execution"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        # Create test data
        v = np.random.rand(nlev, nlat) * 0.1
        temperature = np.random.rand(nlev, nlat) * 50 + 250
        vt_eddy = np.random.rand(nlev, nlat) * 0.01
        vu_eddy = np.random.rand(nlev, nlat) * 0.01
        heating = np.random.rand(nlev, nlat) * 1e-5

        # Test with SOR solver
        result = solve_ke(
            v, temperature, vt_eddy, vu_eddy,
            pressure, latitude,
            heating=heating,
            solver='sor',
            omega=1.5,
            tol=1e-6,
            max_iter=5000
        )

        assert 'PSI' in result
        assert result['PSI'].shape == (nlev, nlat)

    def test_sor_solver_with_custom_params(self):
        """Test SOR with different parameters"""
        nlev, nlat = 4, 6
        pressure = np.linspace(20000, 90000, nlev)
        latitude = np.linspace(-45, 45, nlat)

        v = np.random.rand(nlev, nlat) * 0.05
        temperature = np.random.rand(nlev, nlat) * 40 + 260
        vt_eddy = np.random.rand(nlev, nlat) * 0.005
        vu_eddy = np.random.rand(nlev, nlat) * 0.005
        heating = np.random.rand(nlev, nlat) * 5e-6

        # Test with different omega and tolerance
        result = solve_ke(
            v, temperature, vt_eddy, vu_eddy,
            pressure, latitude,
            heating=heating,
            solver='sor',
            omega=1.8,
            tol=1e-7,
            max_iter=10000
        )

        assert result['PSI'].shape == (nlev, nlat)


class TestShapeValidation:
    """Test shape validation error paths"""

    def test_temperature_shape_mismatch(self):
        """Test temperature shape validation (line 260)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat + 1)  # Wrong shape
        vt_eddy = np.random.rand(nlev, nlat)
        vu_eddy = np.random.rand(nlev, nlat)
        heating = np.random.rand(nlev, nlat)

        with pytest.raises(ValueError, match="temperature shape mismatch"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude, heating=heating)

    def test_vt_eddy_shape_mismatch(self):
        """Test vt_eddy shape validation (line 260)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat)
        vt_eddy = np.random.rand(nlev + 1, nlat)  # Wrong shape
        vu_eddy = np.random.rand(nlev, nlat)
        heating = np.random.rand(nlev, nlat)

        with pytest.raises(ValueError, match="vt_eddy shape mismatch"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude, heating=heating)

    def test_vu_eddy_shape_mismatch(self):
        """Test vu_eddy shape validation (line 260)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat)
        vt_eddy = np.random.rand(nlev, nlat)
        vu_eddy = np.random.rand(nlev, nlat - 1)  # Wrong shape
        heating = np.random.rand(nlev, nlat)

        with pytest.raises(ValueError, match="vu_eddy shape mismatch"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude, heating=heating)

    def test_pressure_shape_mismatch(self):
        """Test pressure shape validation (line 263)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev + 1)  # Wrong shape
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat)
        vt_eddy = np.random.rand(nlev, nlat)
        vu_eddy = np.random.rand(nlev, nlat)
        heating = np.random.rand(nlev, nlat)

        with pytest.raises(ValueError, match="pressure shape mismatch"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude, heating=heating)

    def test_latitude_shape_mismatch(self):
        """Test latitude shape validation (line 263)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat - 1)  # Wrong shape

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat)
        vt_eddy = np.random.rand(nlev, nlat)
        vu_eddy = np.random.rand(nlev, nlat)
        heating = np.random.rand(nlev, nlat)

        with pytest.raises(ValueError, match="latitude shape mismatch"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude, heating=heating)

    def test_rad_heating_shape_mismatch(self):
        """Test rad_heating shape validation (line 272)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat)
        vt_eddy = np.random.rand(nlev, nlat)
        vu_eddy = np.random.rand(nlev, nlat)
        rad_heating = np.random.rand(nlev + 1, nlat)  # Wrong shape
        latent_heating = np.random.rand(nlev, nlat)

        with pytest.raises(ValueError, match="rad_heating shape mismatch"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude,
                     rad_heating=rad_heating,
                     latent_heating=latent_heating)

    def test_latent_heating_shape_mismatch(self):
        """Test latent_heating shape validation (line 272)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat)
        vt_eddy = np.random.rand(nlev, nlat)
        vu_eddy = np.random.rand(nlev, nlat)
        rad_heating = np.random.rand(nlev, nlat)
        latent_heating = np.random.rand(nlev, nlat + 1)  # Wrong shape

        with pytest.raises(ValueError, match="latent_heating shape mismatch"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude,
                     rad_heating=rad_heating,
                     latent_heating=latent_heating)

    def test_single_heating_shape_mismatch(self):
        """Test single heating shape validation (line 276)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat)
        vt_eddy = np.random.rand(nlev, nlat)
        vu_eddy = np.random.rand(nlev, nlat)
        heating = np.random.rand(nlev - 1, nlat)  # Wrong shape

        with pytest.raises(ValueError, match="heating shape mismatch"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude, heating=heating)

    def test_no_heating_provided(self):
        """Test missing heating error (line 282)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat)
        temperature = np.random.rand(nlev, nlat)
        vt_eddy = np.random.rand(nlev, nlat)
        vu_eddy = np.random.rand(nlev, nlat)

        # Don't provide any heating
        with pytest.raises(ValueError, match="Either 'heating' or both"):
            solve_ke(v, temperature, vt_eddy, vu_eddy,
                     pressure, latitude)


class TestLHSShapeValidation:
    """Test solve_ke_LHS shape validation (lines 498, 540, 544, 546)"""

    def test_lhs_3d_shape_mismatch(self):
        """Test 3D shape validation in solve_ke_LHS (line 498)"""
        nlev, nlat, ntime = 5, 8, 3
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        psi_base = np.random.rand(ntime, nlev, nlat) * 1e10
        temp_base = np.random.rand(ntime, nlev, nlat) * 50 + 250
        psi_current = np.random.rand(
            ntime + 1, nlev, nlat) * 1e10  # Wrong time dimension
        temp_current = np.random.rand(ntime, nlev, nlat) * 50 + 260

        with pytest.raises(ValueError, match="shape"):
            solve_ke_LHS(psi_base, temp_base, psi_current, temp_current,
                         pressure, latitude)

    def test_lhs_3d_base_dim_mismatch(self):
        """Test 3D base state dimension validation (line 438)"""
        nlev, nlat, ntime = 5, 8, 3
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        psi_base = np.random.rand(nlev) * 1e10  # Wrong dim (1D)
        temp_base = np.random.rand(ntime, nlev, nlat) * 50 + 250
        psi_current = np.random.rand(ntime, nlev, nlat) * 1e10
        temp_current = np.random.rand(ntime, nlev, nlat) * 50 + 260

        with pytest.raises(ValueError, match="psi_base must be 2D or 3D"):
            solve_ke_LHS(psi_base, temp_base, psi_current, temp_current,
                         pressure, latitude)

    def test_lhs_2d_psi_base_mismatch(self):
        """Test 2D psi_base shape validation (line 540)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        psi_base = np.random.rand(nlev, nlat + 1) * 1e10  # Wrong lat dimension
        temp_base = np.random.rand(nlev, nlat) * 50 + 250
        psi_current = np.random.rand(nlev, nlat) * 1e10
        temp_current = np.random.rand(nlev, nlat) * 50 + 260

        with pytest.raises(ValueError, match="shape"):
            solve_ke_LHS(psi_base, temp_base, psi_current, temp_current,
                         pressure, latitude)

    def test_lhs_2d_pressure_mismatch(self):
        """Test pressure shape validation in LHS (line 544)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev - 1)  # Wrong shape
        latitude = np.linspace(-60, 60, nlat)

        psi_base = np.random.rand(nlev, nlat)
        temp_base = np.random.rand(nlev, nlat)
        psi_current = np.random.rand(nlev, nlat)
        temp_current = np.random.rand(nlev, nlat)

        with pytest.raises(ValueError, match="pressure shape"):
            solve_ke_LHS(psi_base, temp_base, psi_current, temp_current,
                         pressure, latitude)

    def test_lhs_2d_latitude_mismatch(self):
        """Test latitude shape validation in LHS (line 546)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat + 1)  # Wrong shape

        psi_base = np.random.rand(nlev, nlat)
        temp_base = np.random.rand(nlev, nlat)
        psi_current = np.random.rand(nlev, nlat)
        temp_current = np.random.rand(nlev, nlat)

        with pytest.raises(ValueError, match="latitude shape"):
            solve_ke_LHS(psi_base, temp_base, psi_current, temp_current,
                         pressure, latitude)


class TestXarrayEdgeCases:
    """Test xarray interface edge cases"""

    def test_xarray_dimension_mismatch(self):
        """Test xarray dimension mismatch error (line 237)"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        # Base with dims ['level', 'latitude']
        temp_base = xr.DataArray(
            np.random.rand(nlev, nlat) * 50 + 250,
            dims=['level', 'latitude'],
            coords={'level': pressure, 'latitude': latitude}
        )

        # Current with different dims ['plev', 'lat']
        temp_current = xr.DataArray(
            np.random.rand(nlev, nlat) * 50 + 260,
            dims=['plev', 'lat'],
            coords={'plev': pressure, 'lat': latitude}
        )

        psi_base = xr.DataArray(
            np.random.rand(nlev, nlat) * 1e10,
            dims=['level', 'latitude'],
            coords={'level': pressure, 'latitude': latitude}
        )

        psi_current = xr.DataArray(
            np.random.rand(nlev, nlat) * 1e10,
            dims=['plev', 'lat'],
            coords={'plev': pressure, 'lat': latitude}
        )

        # Should raise dimension mismatch error
        with pytest.raises(ValueError, match="Dimension mismatch"):
            solve_ke_LHS_xarray(psi_base, temp_base, psi_current, temp_current)

    def test_xarray_qgpv_true(self):
        """Test xarray with qgpv=True to cover line 125"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = xr.DataArray(
            np.random.rand(nlev, nlat) * 0.1,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        temperature = xr.DataArray(
            np.random.rand(nlev, nlat) * 50 + 250,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        heating = xr.DataArray(
            np.random.rand(nlev, nlat) * 1e-5,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        vt_eddy = xr.DataArray(
            np.random.rand(nlev, nlat) * 0.01,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        vu_eddy = xr.DataArray(
            np.random.rand(nlev, nlat) * 0.01,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        # Test with qgpv=True
        result = solve_ke_xarray(
            v, temperature, vt_eddy, vu_eddy,
            heating=heating,
            pressure_dim='pressure',
            latitude_dim='latitude',
            qgpv=True
        )

        # Verify QGPV terms are in result
        assert 'momentum_term' in result
        assert 'thermal_term' in result
        assert 'residual' in result

    def test_xarray_lhs_with_sor(self):
        """Test xarray LHS with solver='sor' to cover line 268"""
        nlev, nlat = 5, 8
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        psi_base = xr.DataArray(
            np.random.rand(nlev, nlat) * 1e10,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        temp_base = xr.DataArray(
            np.random.rand(nlev, nlat) * 50 + 250,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        psi_current = xr.DataArray(
            np.random.rand(nlev, nlat) * 1e10,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        temp_current = xr.DataArray(
            np.random.rand(nlev, nlat) * 50 + 260,
            dims=['pressure', 'latitude'],
            coords={'pressure': pressure, 'latitude': latitude}
        )

        # Test with solver='sor'
        result = solve_ke_LHS_xarray(
            psi_base, temp_base, psi_current, temp_current,
            pressure_dim='pressure',
            latitude_dim='latitude',
            solver='sor',
            omega=1.5,
            tol=1e-6,
            max_iter=5000
        )

        assert 'PSI_stability' in result
        assert 'PSI_residual' in result


class TestSolverRegistry:
    """Test solver registry and edge cases"""

    def test_unknown_solver_falls_back_to_lu(self):
        """Test that unknown solver falls back to LU"""
        nlev, nlat = 4, 6
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat) * 0.1
        temperature = np.random.rand(nlev, nlat) * 50 + 250
        vt_eddy = np.random.rand(nlev, nlat) * 0.01
        vu_eddy = np.random.rand(nlev, nlat) * 0.01
        heating = np.random.rand(nlev, nlat) * 1e-5

        # Use an unknown solver name - should fall back to LU
        result = solve_ke(
            v, temperature, vt_eddy, vu_eddy,
            pressure, latitude,
            heating=heating,
            solver='unknown_solver'  # Not in registry
        )

        # Should still work (fallback to LU)
        assert 'PSI' in result
        assert result['PSI'].shape == (nlev, nlat)

    def test_lu_solver_explicit(self):
        """Test explicit LU solver call"""
        nlev, nlat = 4, 6
        pressure = np.linspace(10000, 100000, nlev)
        latitude = np.linspace(-60, 60, nlat)

        v = np.random.rand(nlev, nlat) * 0.1
        temperature = np.random.rand(nlev, nlat) * 50 + 250
        vt_eddy = np.random.rand(nlev, nlat) * 0.01
        vu_eddy = np.random.rand(nlev, nlat) * 0.01
        heating = np.random.rand(nlev, nlat) * 1e-5

        # Explicitly use LU
        result = solve_ke(
            v, temperature, vt_eddy, vu_eddy,
            pressure, latitude,
            heating=heating,
            solver='lu'
        )

        assert 'PSI' in result
        assert result['PSI'].shape == (nlev, nlat)
