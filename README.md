# KuoEliassen

[![PyPI version](https://badge.fury.io/py/KuoEliassen.svg)](https://badge.fury.io/py/KuoEliassen)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/KuoEliassen)](https://pypi.org/project/KuoEliassen/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/KuoEliassen)](https://pypi.org/project/KuoEliassen/)
[![Tests](https://github.com/QianyeSu/KuoEliassen/actions/workflows/test-coverage.yml/badge.svg?branch=main)](https://github.com/QianyeSu/KuoEliassen/actions/workflows/test-coverage.yml)
[![codecov](https://codecov.io/gh/QianyeSu/KuoEliassen/graph/badge.svg?)](https://codecov.io/gh/QianyeSu/KuoEliassen)
[![Build Status](https://github.com/QianyeSu/KuoEliassen/actions/workflows/build-wheels.yml/badge.svg)](https://github.com/QianyeSu/KuoEliassen/actions/workflows/build-wheels.yml)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/QianyeSu/KuoEliassen)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)

High-Performance Kuo-Eliassen Circulation Solver with Fortran Backend

## Features

- **Fast Fortran Backend**: Core numerical operations implemented in optimized Fortran 90
- **Easy Python Interface**: Simple, Pythonic API with NumPy and xarray support
- **Cross-Platform**: Works on Windows, macOS, and Linux (x86_64 and arm64)
- **Well-Tested**: Comprehensive test suite with >90% code coverage
- **Decomposition Analysis**: Separate contributions from different forcing terms

## Installation

### From PyPI (Recommended)

Pre-built binary wheels are available for Python 3.9-3.13 on all major platforms:

```bash
pip install kuoeliassen
```

No compiler required! Wheels are provided for:
- **Linux**: x86_64 (manylinux_2_28)
- **macOS**: x86_64 (Intel) and arm64 (Apple Silicon)
- **Windows**: x86_64

### From Source (Development)

If you want to contribute or modify the code:

1. **Prerequisites**: Install a Fortran compiler
   - Windows: `conda install -c conda-forge gcc-gfortran -y`
   - macOS: `brew install gcc`
   - Linux: `sudo apt-get install gfortran` (Ubuntu/Debian)

2. **Clone and install**:
   ```bash
   git clone https://github.com/QianyeSu/KuoEliassen.git
   cd KuoEliassen
   pip install -e .
   ```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development instructions.

## Quick Start

### Basic Usage

```python
import numpy as np
from kuoeliassen import solve_ke

# Set up atmospheric grid
pressure = np.linspace(100000, 10000, 20)  # Pa (1000 to 100 hPa)
latitude = np.linspace(-80, 80, 40)        # degrees

# Define atmospheric state (nlev, nlat)
v = np.random.randn(20, 40) * 0.1          # Meridional wind [m/s]
T = np.random.randn(20, 40) * 10 + 250     # Temperature [K]
vt_eddy = np.random.randn(20, 40) * 0.1    # Eddy heat flux [K⋅m/s]
vu_eddy = np.random.randn(20, 40) * 0.1    # Eddy momentum flux [m²/s²]
heating = np.random.randn(20, 40) * 1e-5   # Diabatic heating [K/s]

# Solve Kuo-Eliassen equation
result = solve_ke(v, T, vt_eddy, vu_eddy, pressure, latitude, heating=heating)

# Access results
psi = result['PSI']  # Total streamfunction [kg/s]
```

### With xarray

```python
import xarray as xr
from kuoeliassen import solve_ke_xarray

# Load your data
ds = xr.open_dataset('atmospheric_data.nc')

# Solve (automatically handles coordinates)
result_ds = solve_ke_xarray(
    ds['v'], ds['T'], ds['vt'], ds['vu'],
    heating=ds['heating']
)

# Result is an xarray Dataset with proper metadata
psi = result_ds['PSI']  # Includes coordinates, attributes, etc.
```

### Decomposition Analysis

```python
# Decompose into individual forcing components
result = solve_ke(
    v, T, vt_eddy, vu_eddy, pressure, latitude,
    rad_heating=rad_heating,      # Radiative heating
    latent_heating=latent_heating  # Latent heating
)

# Access individual components
psi_total = result['PSI']          # Total circulation
psi_rad = result['PSI_rad']        # Radiative component
psi_latent = result['PSI_latent']  # Latent heating component
psi_vt = result['PSI_vt']          # Eddy heat flux component
psi_vu = result['PSI_vu']          # Eddy momentum component
```

## Documentation

- [Development Guide](DEVELOPMENT.md) - Building from source, contributing
- [API Reference](docs/api.md) - Detailed function documentation
- [Examples](examples/) - Jupyter notebooks with usage examples

## Platform Support

| Platform | Python Versions | Architecture | Status |
|----------|----------------|--------------|--------|
| Linux    | 3.9 - 3.13     | x86_64       | ✅ Tested |
| macOS    | 3.9 - 3.13     | x86_64       | ✅ Tested |
| macOS    | 3.9 - 3.13     | arm64 (M1/M2)| ✅ Tested |
| Windows  | 3.9 - 3.13     | x86_64       | ✅ Tested |

## Requirements

- Python ≥ 3.9
- NumPy ≥ 1.24.0
- SciPy ≥ 1.7.0
- xarray ≥ 0.19.0 (optional, for xarray interface)

## License

This project is licensed under the BSD-3-Clause License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use KuoEliassen in your research, please cite:

```bibtex
@software{kuoeliassen2025,
  author = {Su, Qianye},
  title = {KuoEliassen: High-Performance Kuo-Eliassen Circulation Solver},
  year = {2025},
  url = {https://github.com/QianyeSu/KuoEliassen}
}
```

## Contributing

Contributions are welcome! Please see [DEVELOPMENT.md](DEVELOPMENT.md) for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a Pull Request

## Contact

- **Author**: Qianye Su
- **Email**: suqianye2000@gmail.com
- **GitHub**: https://github.com/QianyeSu/KuoEliassen

## Acknowledgments

This solver is based on the Kuo-Eliassen equation for atmospheric meridional circulation. The numerical methods are optimized for modern computational efficiency while maintaining physical accuracy.