"""
KuoEliassen - High-Performance Kuo-Eliassen Circulation Solver
"""

from .core import solve_ke
from .xarray_interface import solve_ke_xarray

__version__ = "0.1.0"
__author__ = "Qianye Su"
__all__ = ["solve_ke", "solve_ke_xarray"]
