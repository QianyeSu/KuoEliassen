"""
Utility functions for input validation and preprocessing
"""

import numpy as np
from typing import Tuple


def validate_grid_data(
    temperature: np.ndarray,
    u_wind: np.ndarray,
    v_wind: np.ndarray,
    heating: np.ndarray,
    pressure: np.ndarray,
    latitude: np.ndarray
) -> Tuple[int, int]:
    """
    Validate input data shapes and consistency.

    Returns
    -------
    nlev : int
        Number of vertical levels
    nlat : int
        Number of latitudes
    """
    if temperature.ndim < 2:
        raise ValueError(
            f"temperature must be at least 2D, got {temperature.ndim}D")

    shape = temperature.shape[-2:]
    nlev, nlat = shape

    for name, arr in [('u_wind', u_wind), ('v_wind', v_wind), ('heating', heating)]:
        if arr.shape[-2:] != shape:
            raise ValueError(
                f"{name} shape {arr.shape} != temperature {temperature.shape}")

    if pressure.shape[-1] != nlev:
        raise ValueError(
            f"pressure length {pressure.shape[-1]} != nlev {nlev}")

    if latitude.shape[-1] != nlat:
        raise ValueError(
            f"latitude length {latitude.shape[-1]} != nlat {nlat}")

    return nlev, nlat


def normalize_pressure(pressure: np.ndarray) -> np.ndarray:
    """
    Ensure pressure is in Pa and decreasing order.
    """
    p = np.asarray(pressure).copy()

    # Detect units
    if np.median(p) < 2000:
        p = p * 100.0  # hPa to Pa

    # Ensure decreasing order
    if p[0] > p[-1]:
        p = p[::-1]

    return p


def normalize_latitude(latitude: np.ndarray) -> np.ndarray:
    """
    Ensure latitude is in degrees and increasing order.
    """
    lat = np.asarray(latitude).copy()

    # Check if in radians
    if np.max(np.abs(lat)) <= 2 * np.pi:
        lat = np.rad2deg(lat)

    # Ensure south-to-north order
    if lat[0] > lat[-1]:
        lat = lat[::-1]

    return lat
