# Local Build Instructions

## Prerequisites

### All Platforms
- Python 3.9+
- NumPy >= 1.24.0
- meson-python
- ninja (optional, speeds up builds)

### Fortran Compiler

#### Windows
- Install MinGW-w64 gfortran (via conda or MSYS2)
- **Important**: Set environment variables before building:
  ```powershell
  $env:CC = "gcc"
  $env:FC = "gfortran"
  ```

#### Linux
```bash
sudo apt-get install gfortran  # Debian/Ubuntu
sudo dnf install gcc-gfortran  # Fedora/RHEL
```

#### macOS
```bash
brew install gcc
```

## Installation

### Standard Installation
```bash
pip install -e .
```

### Windows Installation (Recommended)
```powershell
# Set compilers
$env:CC = "gcc"
$env:FC = "gfortran"

# Install
pip install -e .
```

### Development Installation
```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ --cov=src/kuoeliassen
```

## Troubleshooting

### Windows: "Compiler cl cannot compile programs"
**Cause**: Meson detects MSVC `cl` compiler but it's not properly configured.

**Solution**: Set environment variables to force GCC usage:
```powershell
$env:CC = "gcc"
$env:FC = "gfortran"
pip install -e .
```

### Linux/macOS: "gfortran not found"
**Solution**: Install gfortran:
```bash
# Ubuntu/Debian
sudo apt-get install gfortran

# Fedora/RHEL
sudo dnf install gcc-gfortran

# macOS
brew install gcc
```

### Import Error: "DLL load failed"
**Solution**: Ensure gfortran runtime libraries are in PATH:
```powershell
# Windows (conda environment)
conda install libgfortran

# Or add MinGW bin to PATH
$env:PATH += ";C:\tools\msys64\mingw64\bin"
```

## Verifying Installation

```python
import kuoeliassen
print(f"KuoEliassen version: {kuoeliassen.__version__}")

# Test import
from kuoeliassen import solve_ke, solve_ke_LHS
print("Import successful!")
```

## CI/CD

The project uses GitHub Actions for automated builds:
- **test.yml**: Multi-platform testing (Linux/macOS/Windows)
- **build-wheels.yml**: Wheel building for PyPI distribution

See `.github/CICD_README.md` for details.
