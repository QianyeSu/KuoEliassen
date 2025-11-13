"""
xarray interface for KuoEliassen Solver
"""

import numpy as np
import xarray as xr
from typing import Optional
from .core import solve_ke
from .utils import validate_grid_data, normalize_pressure, normalize_latitude


def solve_ke_xarray(
    v_mean: xr.DataArray,
    temperature: xr.DataArray,
    heating: xr.DataArray,
    vt_eddy: xr.DataArray,
    vu_eddy: xr.DataArray,
    pressure_dim: str = 'plev',
    latitude_dim: str = 'lat'
) -> xr.Dataset:
    """
    Solve Kuo-Eliassen equation with xarray interface.

    Parameters
    ----------
    v_mean : xr.DataArray
        Mean meridional wind [m/s]
    temperature : xr.DataArray
        Temperature field [K]
    heating : xr.DataArray
        Diabatic heating rate [K/s]
    vt_eddy : xr.DataArray
        Eddy heat flux v'T' [K·m/s]
    vu_eddy : xr.DataArray
        Eddy momentum flux u'v' [m²/s²]
    pressure_dim : str
        Name of pressure dimension
    latitude_dim : str
        Name of latitude dimension

    Returns
    -------
    result : xr.Dataset
        Dataset with PSI and all components (PSI_latent, PSI_rad, PSI_vt, PSI_vu, PSI_x)
    """
    # Extract coordinates
    pressure = temperature[pressure_dim].values
    latitude = temperature[latitude_dim].values

    # Normalize
    pressure_pa = normalize_pressure(pressure)
    latitude_deg = normalize_latitude(latitude)

    # Check reversals
    pressure_reversed = not np.allclose(pressure_pa, pressure)
    latitude_reversed = not np.allclose(latitude_deg, latitude)

    # Extract and reorder data
    def get_data(da: xr.DataArray) -> np.ndarray:
        data = da.values
        if data.ndim == 2:
            if pressure_reversed:
                data = data[::-1, :]
            if latitude_reversed:
                data = data[:, ::-1]
        elif data.ndim == 3:
            if pressure_reversed:
                data = data[:, ::-1, :]
            if latitude_reversed:
                data = data[:, :, ::-1]
        return data

    temp_data = get_data(temperature)
    vmean_data = get_data(v_mean)
    vt_data = get_data(vt_eddy)
    vu_data = get_data(vu_eddy)
    heating_data = get_data(heating)

    # Handle time dimension
    has_time = temp_data.ndim == 3
    if has_time:
        ntime = temp_data.shape[0]
        results_list = []

        for t in range(ntime):
            result_t = solve_ke(
                vmean_data[t], temp_data[t], heating_data[t],
                vt_data[t], vu_data[t],
                pressure_pa, latitude_deg
            )
            results_list.append(result_t)

        result_dict = {}
        for key in results_list[0].keys():
            result_dict[key] = np.stack([r[key] for r in results_list], axis=0)
    else:
        result_dict = solve_ke(
            vmean_data, temp_data, heating_data,
            vt_data, vu_data,
            pressure_pa, latitude_deg
        )

    # Build xarray Dataset
    coords = {
        pressure_dim: pressure,
        latitude_dim: latitude,
    }

    if has_time:
        time_coord = temperature.coords.get('time', None)
        if time_coord is not None:
            coords['time'] = time_coord
        dims = ['time', pressure_dim, latitude_dim]
    else:
        dims = [pressure_dim, latitude_dim]

    # Create DataArrays
    data_vars = {}
    for key, values in result_dict.items():
        # Reverse back if needed
        if has_time:
            if pressure_reversed:
                values = values[:, ::-1, :]
            if latitude_reversed:
                values = values[:, :, ::-1]
        else:
            if pressure_reversed:
                values = values[::-1, :]
            if latitude_reversed:
                values = values[:, ::-1]

        attrs = {'units': 'kg/s' if key.startswith('PSI') else 'K/s'}
        data_vars[key] = xr.DataArray(
            values, dims=dims, coords=coords, attrs=attrs)

    result_ds = xr.Dataset(data_vars)
    result_ds.attrs['title'] = 'Kuo-Eliassen Circulation Solution'

    return result_ds
