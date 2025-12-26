"""
KuoEliassen - High-Performance Kuo-Eliassen Circulation Solver
"""

from .core import solve_ke, solve_ke_LHS
from .xarray_interface import solve_ke_xarray, solve_ke_LHS_xarray

__version__ = "0.2.1"
__author__ = "Qianye Su"
__all__ = ["solve_ke", "solve_ke_xarray"]
