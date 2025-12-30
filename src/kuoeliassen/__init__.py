"""
KuoEliassen - A High-Performance Solver for the Kuo-Eliassen Equation
Author: Qianye Su 
Email: suqianye2000@gmail.com
Created: 2025/11/12 12:05
"""

from .core import solve_ke, solve_ke_LHS
from .xarray_interface import solve_ke_xarray, solve_ke_LHS_xarray
__version__ = '0.2.3'
__author__ = "Qianye Su"
__all__ = ["solve_ke", "solve_ke_xarray"]
