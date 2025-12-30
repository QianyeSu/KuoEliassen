"""
Utility functions for input validation and preprocessing
"""

import numpy as np


def normalize_pressure(pressure: np.ndarray) -> np.ndarray:
    """Ensure pressure is in Pa and increasing order."""
    p = np.asarray(pressure)
    if p.size > 0 and np.median(p) < 2000:
        p = p * 100.0
    return np.sort(p)


def normalize_latitude(latitude: np.ndarray) -> np.ndarray:
    """Ensure latitude is in degrees and increasing order."""
    lat = np.asarray(latitude)
    if lat.size > 0 and np.max(np.abs(lat)) <= np.pi / 2:
        lat = np.rad2deg(lat)
    return np.sort(lat)
