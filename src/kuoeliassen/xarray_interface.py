"""
xarray interface for KuoEliassen Solver
"""

import numpy as np
import xarray as xr
from typing import Optional
from .core import solve_ke, solve_ke_LHS
from .utils import normalize_pressure, normalize_latitude


def solve_ke_xarray(
    v: xr.DataArray,
    temperature: xr.DataArray,
    vt_eddy: xr.DataArray,
    vu_eddy: xr.DataArray,
    pressure_dim: str = "level",
    latitude_dim: str = "lat",
    heating: Optional[xr.DataArray] = None,
    rad_heating: Optional[xr.DataArray] = None,
    latent_heating: Optional[xr.DataArray] = None,
    qgpv: bool = False
) -> xr.Dataset:
    """
    Solve Kuo-Eliassen equation with xarray interface.

    Parameters
    ----------
    v : xr.DataArray
        Mean meridional wind [m/s]
    temperature : xr.DataArray
        Temperature field [K]
    vt_eddy : xr.DataArray
        Eddy heat flux v'T' [K·m/s]
    vu_eddy : xr.DataArray
        Eddy momentum flux u'v' [m²/s²]
    pressure_dim : str, default='level'
        Name of pressure dimension
    latitude_dim : str, default='lat'
        Name of latitude dimension
    heating : xr.DataArray, optional
        Total diabatic heating rate [K/s] (use this OR rad_heating+latent_heating)
    rad_heating : xr.DataArray, optional
        Radiative heating rate [K/s] (must be used with latent_heating)
    latent_heating : xr.DataArray, optional
        Latent heating rate [K/s] (must be used with rad_heating)
    qgpv : bool, default=False
        If True, compute QGPV balance diagnostic terms

    Returns
    -------
    result : xr.Dataset
        Dataset containing:
        - PSI: Total streamfunction [kg/s]
        - D: Total RHS forcing [K/s]
        - PSI_Q: Total heating component [kg/s]
        - PSI_latent: Latent heating component [kg/s] (zeros if single heating mode)
        - PSI_rad: Radiative heating component [kg/s] (zeros if single heating mode)
        - PSI_vt: Eddy heat flux component [kg/s]
        - PSI_vu: Eddy momentum flux component [kg/s]
        - PSI_x: Friction component [kg/s]

        If qgpv=True, also includes:
        - momentum_term: Momentum forcing [s⁻²]
        - thermal_term: Thermal forcing [s⁻²]
        - residual: QGPV balance residual [s⁻²]

    Notes
    -----
    Heating input modes:
    - Mode 1: Only `heating` provided → single total heating (PSI_latent/PSI_rad are zeros)
    - Mode 2: Both `rad_heating` and `latent_heating` → decomposed heating components

    Examples
    --------
    # Mode 1: Single heating
    result = solve_ke_xarray(v, T, vt, vu, heating=Q, pressure_dim='plev', latitude_dim='lat')

    # Mode 2: Decomposed heating
    result = solve_ke_xarray(v, T, vt, vu, rad_heating=Q_rad, latent_heating=Q_lat,
                             pressure_dim='plev', latitude_dim='lat')

    # With QGPV diagnostics
    result = solve_ke_xarray(v, T, vt, vu, heating=Q, qgpv=True,
                             pressure_dim='plev', latitude_dim='lat')
    """
    # Normalize and sort coordinates
    pressure_pa = normalize_pressure(temperature[pressure_dim].values)
    latitude_deg = normalize_latitude(temperature[latitude_dim].values)

    # Sort input arrays by normalized coordinates
    temp_sorted = temperature.sortby(
        [pressure_dim, latitude_dim], ascending=True)
    v_sorted = v.sortby([pressure_dim, latitude_dim], ascending=True)
    vt_sorted = vt_eddy.sortby([pressure_dim, latitude_dim], ascending=True)
    vu_sorted = vu_eddy.sortby([pressure_dim, latitude_dim], ascending=True)

    # Handle heating inputs
    kwargs = {'qgpv': qgpv}
    if rad_heating is not None and latent_heating is not None:
        kwargs['rad_heating'] = rad_heating.sortby(
            [pressure_dim, latitude_dim], ascending=True).values
        kwargs['latent_heating'] = latent_heating.sortby(
            [pressure_dim, latitude_dim], ascending=True).values
    elif heating is not None:
        kwargs['heating'] = heating.sortby(
            [pressure_dim, latitude_dim], ascending=True).values
    else:
        raise ValueError(
            "Either 'heating' or both 'rad_heating' and 'latent_heating' must be provided")

    # Call core solver
    result_dict = solve_ke(
        v_sorted.values, temp_sorted.values, vt_sorted.values, vu_sorted.values,
        pressure_pa, latitude_deg, **kwargs
    )

    # Build output Dataset with original coordinates
    has_time = temperature.ndim == 3
    dims = (['time', pressure_dim, latitude_dim]
            if has_time else [pressure_dim, latitude_dim])

    coords = {pressure_dim: pressure_pa, latitude_dim: latitude_deg}
    if has_time:
        coords['time'] = temperature.coords['time']

    # Create DataArrays
    data_vars = {}
    for key, values in result_dict.items():
        if key.startswith('PSI'):
            attrs = {'units': 'kg/s',
                     'long_name': f'{key} streamfunction component'}
        elif key == 'D':
            attrs = {'units': 'K/s', 'long_name': 'Total RHS forcing'}
        elif key in ['momentum_term', 'thermal_term', 'residual']:
            attrs = {'units': 's^-2',
                     'long_name': key.replace('_', ' ').title()}
        else:
            attrs = {}

        data_vars[key] = xr.DataArray(
            values, dims=dims, coords=coords, attrs=attrs)

    result_ds = xr.Dataset(data_vars)
    result_ds.attrs['title'] = 'Kuo-Eliassen Circulation Solution'
    result_ds.attrs['solver'] = 'KuoEliassen v2.0'

    # Restore original coordinate order
    return result_ds.reindex({pressure_dim: temperature[pressure_dim], latitude_dim: temperature[latitude_dim]})


def solve_ke_LHS_xarray(
    psi_base: xr.DataArray,
    temp_base: xr.DataArray,
    psi_current: xr.DataArray,
    temp_current: xr.DataArray,
    pressure_dim: Optional[str] = None,
    latitude_dim: Optional[str] = None
) -> xr.Dataset:
    """
    Decompose streamfunction anomaly into stability and residual components (xarray interface).

    Parameters
    ----------
    psi_base : xr.DataArray
        Base period streamfunction [kg/s]
    temp_base : xr.DataArray
        Base period temperature [K]
    psi_current : xr.DataArray
        Current period streamfunction [kg/s]
    temp_current : xr.DataArray
        Current period temperature [K]
    pressure_dim : str, optional
        Name of pressure dimension (auto-detected if None)
    latitude_dim : str, optional
        Name of latitude dimension (auto-detected if None)

    Returns
    -------
    result : xr.Dataset
        Dataset containing:
        - PSI_stability: Static stability change component [kg/s]
        - PSI_residual: Residual/nonlinear component [kg/s]

    Notes
    -----
    The forcing component can be computed as:
        PSI_forcing = (psi_current - psi_base) - PSI_stability - PSI_residual

    Examples
    --------
    # Multi-year mean baseline
    result_base = solve_ke_xarray(v_mean, T_mean, vt_mean, vu_mean, heating=Q_mean)
    psi_base = result_base['PSI']

    result_curr = solve_ke_xarray(v_curr, T_curr, vt_curr, vu_curr, heating=Q_curr)
    psi_curr = result_curr['PSI']

    decomp = solve_ke_LHS_xarray(psi_base, T_mean, psi_curr, T_curr)
    psi_forcing = psi_curr - psi_base - decomp['PSI_stability'] - decomp['PSI_residual']
    """
    # Auto-detect dimension names if not provided
    if pressure_dim is None:
        pressure_candidates = ['pressure', 'plev', 'lev', 'level', 'pfull']
        for candidate in pressure_candidates:
            if candidate in temp_base.dims:
                pressure_dim = candidate
                break
        if pressure_dim is None:
            raise ValueError(
                f"Could not auto-detect pressure dimension. Available dims: {temp_base.dims}")

    if latitude_dim is None:
        latitude_candidates = ['latitude', 'lat', 'y']
        for candidate in latitude_candidates:
            if candidate in temp_base.dims:
                latitude_dim = candidate
                break
        if latitude_dim is None:
            raise ValueError(
                f"Could not auto-detect latitude dimension. Available dims: {temp_base.dims}")

    # Normalize and sort coordinates
    pressure_pa = normalize_pressure(temp_base[pressure_dim].values)
    latitude_deg = normalize_latitude(temp_base[latitude_dim].values)

    # Sort arrays
    psi_base_sorted = psi_base.sortby(
        [pressure_dim, latitude_dim], ascending=True)
    temp_base_sorted = temp_base.sortby(
        [pressure_dim, latitude_dim], ascending=True)
    psi_curr_sorted = psi_current.sortby(
        [pressure_dim, latitude_dim], ascending=True)
    temp_curr_sorted = temp_current.sortby(
        [pressure_dim, latitude_dim], ascending=True)

    # Call core solver
    result_dict = solve_ke_LHS(
        psi_base_sorted.values, temp_base_sorted.values,
        psi_curr_sorted.values, temp_curr_sorted.values,
        pressure_pa, latitude_deg
    )

    # Build output Dataset
    has_time = temp_base.ndim == 3
    dims = (['time', pressure_dim, latitude_dim]
            if has_time else [pressure_dim, latitude_dim])

    coords = {pressure_dim: pressure_pa, latitude_dim: latitude_deg}
    if has_time:
        coords['time'] = temp_base.coords['time']

    # Create DataArrays
    data_vars = {}
    for key, values in result_dict.items():
        attrs = {'units': 'kg/s', 'long_name': key.replace('_', ' ').title()}
        data_vars[key] = xr.DataArray(
            values, dims=dims, coords=coords, attrs=attrs)

    result_ds = xr.Dataset(data_vars)
    result_ds.attrs['title'] = 'Kuo-Eliassen LHS Decomposition'
    result_ds.attrs['solver'] = 'KuoEliassen v2.0'

    # Restore original coordinate order
    return result_ds.reindex({pressure_dim: temp_base[pressure_dim], latitude_dim: temp_base[latitude_dim]})
