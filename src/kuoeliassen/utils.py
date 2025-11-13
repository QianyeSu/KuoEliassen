"""
Utility functions for input validation and preprocessing
"""

import numpy as np
from typing import Tuple


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
