"""
KuoEliassen - High-Performance Kuo-Eliassen Circulation Solver
"""

from .core import solve_ke, solve_ke_LHS
from .xarray_interface import solve_ke_xarray, solve_ke_LHS_xarray
import re
from pathlib import Path
_pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
__version__ = re.search(  # Read version from pyproject.toml
    r'version\s*=\s*"([^"]+)"', _pyproject.read_text()).group(1)
__author__ = "Qianye Su"
__all__ = ["solve_ke", "solve_ke_xarray"]
