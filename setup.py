#!/usr/bin/env python
"""
Setup script for KuoEliassen - Meson-based build system with Fortran backend

This is a compatibility wrapper for 'python setup.py install' style installation.
For modern installation, use: pip install .
"""

import os
import subprocess
import sys
from pathlib import Path

# Check if we're in documentation build mode
DOCS_BUILD_MODE = (
    os.environ.get("KUOELIASSEN_DOCS_BUILD") == "1"
    or os.environ.get("SKIP_FORTRAN") == "1"
)

if DOCS_BUILD_MODE:
    print("[INFO] Documentation build mode detected - skipping Fortran compilation")
else:
    # Force gfortran compiler usage
    os.environ["FC"] = os.environ.get("FC", "gfortran")
    os.environ["F77"] = os.environ.get("F77", "gfortran")
    os.environ["F90"] = os.environ.get("F90", "gfortran")
    os.environ["CC"] = os.environ.get("CC", "gcc")


def check_gfortran():
    """Check if gfortran is available"""
    try:
        result = subprocess.run(
            ["gfortran", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"[OK] Found gfortran: {version_line}")
            return True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        pass

    print("[WARNING] gfortran not found. Fortran extensions may not build correctly.")
    print("\nPlease install gfortran:")
    print("  Linux:   sudo apt-get install gfortran")
    print("  macOS:   brew install gcc")
    print("  Windows: conda install m2w64-toolchain")
    print("           or: choco install msys2")
    return False


def check_meson_ninja():
    """Check if meson and ninja are available"""
    missing = []

    try:
        result = subprocess.run(
            ["meson", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"[OK] Found meson: {result.stdout.strip()}")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        missing.append("meson")

    try:
        result = subprocess.run(
            ["ninja", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"[OK] Found ninja: {result.stdout.strip()}")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        missing.append("ninja")

    if missing:
        print(f"[WARNING] {', '.join(missing)} not found.")
        print("\nInstall with: pip install meson ninja")
        return False

    return True


def main():
    """Check build environment and provide guidance."""

    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        print("\n" + "=" * 70)
        print("KuoEliassen Build System")
        print("=" * 70)
        print("\nDevelopment Installation:")
        print("  pip install -e .")
        print("  or: pip install -e . --no-build-isolation")
        print("\nTraditional Installation:")
        print("  python setup.py install")
        print("\nWheel Build:")
        print("  pip install build")
        print("  python -m build")
        print("\n" + "=" * 70)
        return 0

    print("\n" + "=" * 70)
    print("KuoEliassen Package - Build Environment Check")
    print("=" * 70 + "\n")

    # Check build tools
    if not DOCS_BUILD_MODE:
        check_gfortran()
        check_meson_ninja()
    else:
        print("[INFO] Documentation build mode - skipping compiler checks")

    print("\n" + "=" * 70)
    print("Installation Commands")
    print("=" * 70)
    print("\nFor development:")
    print("  pip install -e .")
    print("\nFor traditional installation:")
    print("  python setup.py install")
    print("\nFor building wheels:")
    print("  python -m build")
    print("\nFor clean reinstall:")
    print("  pip install -e . --force-reinstall --no-deps")
    print("\n" + "=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())


# Traditional setup() support for 'python setup.py install'
# This allows backward compatibility with older installation methods
# while still using meson-python as the build backend
try:
    from setuptools import setup

    # If called directly with setup.py commands, delegate to pip
    if len(sys.argv) > 1 and sys.argv[1] in ['install', 'develop', 'build', 'bdist_wheel', 'sdist']:
        import setuptools

        # For 'develop' command, use pip install -e .
        if sys.argv[1] == 'develop':
            print(
                "\n[INFO] Using 'pip install -e .' for development installation...")
            sys.exit(subprocess.call(
                [sys.executable, '-m', 'pip', 'install', '-e', '.']))

        # For other commands, use pip install
        elif sys.argv[1] == 'install':
            print("\n[INFO] Using 'pip install .' for installation...")
            sys.exit(subprocess.call(
                [sys.executable, '-m', 'pip', 'install', '.']))

        # For build commands, use python -m build
        elif sys.argv[1] in ['build', 'bdist_wheel', 'sdist']:
            print("\n[INFO] Using 'python -m build' for building...")
            try:
                import build
                sys.exit(subprocess.call([sys.executable, '-m', 'build']))
            except ImportError:
                print(
                    "\n[WARNING] 'build' module not found. Install with: pip install build")
                sys.exit(1)

    # Minimal setup() call for metadata (actual build done by meson-python)
    setup()

except ImportError:
    # setuptools not available, skip setup() call
    pass
