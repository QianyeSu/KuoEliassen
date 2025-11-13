"""
Basic tests for KuoEliassen package
"""
import pytest
import numpy as np


def test_import():
    """Test that the package can be imported"""
    import kuoeliassen
    assert kuoeliassen.__version__ is not None


def test_import_solve_ke():
    """Test that solve_ke can be imported"""
    from kuoeliassen import solve_ke
    assert callable(solve_ke)


def test_import_xarray_interface():
    """Test that xarray interface can be imported"""
    from kuoeliassen.xarray_interface import solve_ke_xarray
    assert callable(solve_ke_xarray)


def test_basic_solve():
    """Test basic solve_ke functionality with minimal data"""
    from kuoeliassen import solve_ke

    # Create minimal test data (5 pressure levels, 3 latitudes, 2 time steps)
    nz, ny, nt = 5, 3, 2

    # Create dummy input arrays
    v_mean = np.random.randn(nz, ny, nt)
    temp = np.random.randn(nz, ny, nt) + 273.15  # Temperature in Kelvin
    heating = np.random.randn(nz, ny, nt) * 0.01  # Small heating rate
    vt_eddy = np.random.randn(nz, ny, nt) * 0.1
    vu_eddy = np.random.randn(nz, ny, nt) * 0.1

    # Pressure and latitude coordinates
    p = np.array([1000, 850, 700, 500, 300], dtype=np.float64) * 100  # Pa
    phi = np.array([30, 35, 40], dtype=np.float64)  # degrees

    # Call solve_ke
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

    # Check that result contains expected keys
    assert 'PSI_Q' in result
    assert 'PSI_latent' in result
    assert 'PSI_rad' in result
    assert 'D_vt' in result
    assert 'D_vu' in result
    assert 'D_x' in result
    assert 'F_friction' in result

    # Check shapes
    assert result['PSI_Q'].shape == (nz, ny, nt)
    assert result['D_vt'].shape == (nz, ny, nt)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
