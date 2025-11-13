#!/usr/bin/env python
"""
Convenience installer script for KuoEliassen package.

This script wraps the complex pip installation command with meson
configuration settings, making it easier to rebuild and reinstall
the package during development.

Usage:
    python setup.py              # Install/reinstall the package
    python setup.py --help       # Show this help message
"""

import sys
import subprocess
import os
from pathlib import Path


def main():
    """Execute the pip install command with all required configuration."""

    # Check for help flag
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        print("\nThis script is equivalent to running:")
        print("  pip install -e . --config-settings=setup-args=--native-file=native-gcc.ini \\")
        print("    --no-build-isolation --force-reinstall --no-deps")
        return 0

    # Get the directory where this script is located
    script_dir = Path(__file__).parent.resolve()

    # Change to the script directory
    os.chdir(script_dir)

    # Build the pip install command
    cmd = [
        sys.executable,  # Use the same Python interpreter
        "-m", "pip",
        "install",
        "-e", ".",
        "--config-settings=setup-args=--native-file=native-gcc.ini",
        "--no-build-isolation",
        "--force-reinstall",
        "--no-deps"
    ]

    print("=" * 70)
    print("KuoEliassen Package Installer")
    print("=" * 70)
    print(f"\nWorking directory: {script_dir}")
    print(f"Python interpreter: {sys.executable}")
    print(f"\nExecuting command:")
    print("  " + " ".join(cmd))
    print("\n" + "=" * 70 + "\n")

    # Execute the command
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 70)
        print("✓ Installation completed successfully!")
        print("=" * 70)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 70)
        print(f"✗ Installation failed with exit code {e.returncode}")
        print("=" * 70)
        return e.returncode
    except KeyboardInterrupt:
        print("\n\n✗ Installation interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
