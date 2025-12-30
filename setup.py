"""
Setup script for KuoEliassen - Meson-based build system with Fortran backend
"""
# $env:CC='gcc'; $env:FC='gfortran'; pip install -e . --no-build-isolation
import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install import install

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
    return False


# Check gfortran availability at setup time (skip in docs mode)
if not DOCS_BUILD_MODE:
    check_gfortran()
else:
    print("[INFO] Skipping gfortran check in documentation build mode")


class MesonBuildExt(build_ext):
    """Custom build extension to handle meson builds for Fortran modules"""

    def run(self):
        """Run the build process"""
        # Build meson modules first
        self.build_meson_modules()
        # Then run the standard build_ext (for any pure Python extensions)
        super().run()

    def build_meson_modules(self):
        """Build modules that use meson (kuoeliassen Fortran backend)"""
        # Skip meson builds in documentation mode
        if DOCS_BUILD_MODE:
            print("[INFO] Documentation build mode - skipping meson module builds")
            return

        # Auto-discover meson modules
        meson_modules = self._discover_meson_modules()

        for module in meson_modules:
            if self.should_build_meson_module(module):
                print(f"🔨 Building module {module['name']} with meson")
                self.build_meson_module(module)

    def should_build_meson_module(self, module):
        """Check if we should build this meson module"""
        meson_build_file = module["path"] / "meson.build"
        return meson_build_file.exists()

    def check_meson_available(self):
        """Check if meson and ninja are available"""
        try:
            # Check meson
            result = subprocess.run(
                ["meson", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return False, "meson not found"

            meson_version = result.stdout.strip()
            print(f"[OK] Found meson version: {meson_version}")

            # Check ninja
            result = subprocess.run(
                ["ninja", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return False, "ninja not found"

            ninja_version = result.stdout.strip()
            print(f"[OK] Found ninja version: {ninja_version}")

            return True, None

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
            return False, str(e)

    def build_meson_module(self, module):
        """
        Build a meson module using the meson build system.
        """
        print(f"[BUILD] Building {module['name']} with meson build system...")

        # Check if meson and ninja are available
        meson_available, error_msg = self.check_meson_available()
        if not meson_available:
            print(f"[ERROR] Meson build tools not available: {error_msg}")
            print("Please install meson and ninja:")
            print("  pip install meson ninja")
            print("  or: conda install meson ninja")
            raise RuntimeError(
                f"Meson build tools required but not available: {error_msg}"
            )

        module_path = module["path"]
        build_dir = module_path / "build"

        try:
            # Clean build directory
            if build_dir.exists():
                print(
                    f"[CLEAN] Cleaning existing build directory: {build_dir}")
                shutil.rmtree(build_dir)

            # Setup build directory
            build_dir.mkdir(parents=True, exist_ok=True)

            # Configure meson build
            print(f"[CONFIG] Configuring meson build in {build_dir}")

            setup_cmd = [
                "meson",
                "setup",
                "build",
                ".",
                "--buildtype=release",
                "-Db_lto=true",
            ]

            # For wheel builds, configure custom install directory
            if not self.inplace and hasattr(self, "build_lib") and self.build_lib:
                build_lib_path = Path(self.build_lib).resolve()
                setup_cmd.extend([
                    f"--python.purelibdir={build_lib_path}",
                    f"--python.platlibdir={build_lib_path}",
                ])
                print(
                    f"[CONFIG] Configuring meson to install to: {build_lib_path}")

            # Set up environment for conda gfortran
            env = os.environ.copy()
            import platform

            conda_prefix = env.get("CONDA_PREFIX", "")
            if conda_prefix:
                system = platform.system()
                current_path = env.get("PATH", "")

                if system == "Windows":
                    # Windows conda environment setup
                    conda_bin = os.path.join(conda_prefix, "bin")
                    conda_library_bin = os.path.join(
                        conda_prefix, "Library", "bin")
                    mingw_bin = os.path.join(
                        conda_prefix, "Library", "mingw-w64", "bin")
                    env["PATH"] = f"{conda_bin};{conda_library_bin};{mingw_bin};{current_path}"
                    print(f"[ENV] Enhanced PATH for Windows conda environment")

                elif system in ["Linux", "Darwin"]:
                    # Linux and macOS conda environment setup
                    conda_bin = os.path.join(conda_prefix, "bin")
                    env["PATH"] = f"{conda_bin}:{current_path}"

                    conda_lib = os.path.join(conda_prefix, "lib")
                    if system == "Linux":
                        current_lib_path = env.get("LD_LIBRARY_PATH", "")
                        env["LD_LIBRARY_PATH"] = (
                            f"{conda_lib}:{current_lib_path}"
                            if current_lib_path
                            else conda_lib
                        )
                        print(
                            f"[ENV] Enhanced PATH and LD_LIBRARY_PATH for Linux conda")
                    else:  # macOS
                        current_lib_path = env.get("DYLD_LIBRARY_PATH", "")
                        env["DYLD_LIBRARY_PATH"] = (
                            f"{conda_lib}:{current_lib_path}"
                            if current_lib_path
                            else conda_lib
                        )
                        print(
                            f"[ENV] Enhanced PATH and DYLD_LIBRARY_PATH for macOS conda")

            # Run meson setup
            subprocess.run(setup_cmd, cwd=str(
                module_path), check=True, env=env)

            # Build with ninja
            print(f"[BUILD] Building with ninja in {build_dir}")
            build_cmd = ["ninja", "-C", "build"]
            result = subprocess.run(
                build_cmd,
                cwd=str(module_path),
                check=True,
                capture_output=True,
                text=True,
            )

            if result.stdout:
                print("Build output:", result.stdout)
            if result.stderr:
                print("Build warnings:", result.stderr)

            # Install using meson
            if not self.inplace and hasattr(self, "build_lib") and self.build_lib:
                print(
                    f"[INSTALL] Installing meson build outputs to {self.build_lib}")
                install_cmd = ["meson", "install",
                               "-C", "build", "--only-changed"]

                try:
                    install_result = subprocess.run(
                        install_cmd,
                        cwd=str(module_path),
                        check=True,
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    if install_result.stdout:
                        print("Install output:", install_result.stdout)
                except subprocess.CalledProcessError as e:
                    print(f"[ERROR] Meson install failed: {e}")
                    raise
            else:
                print(
                    "[INFO] Inplace build - extensions handled by meson custom_target")

            print(
                f"[SUCCESS] Meson build for {module['name']} completed successfully!")

        except (subprocess.CalledProcessError, RuntimeError, FileNotFoundError) as e:
            print(f"[ERROR] Meson build failed for {module['name']}: {e}")
            if isinstance(e, subprocess.CalledProcessError):
                print(f"Command failed with exit code: {e.returncode}")
                if hasattr(e, "stdout") and e.stdout:
                    print("Stdout:", e.stdout)
                if hasattr(e, "stderr") and e.stderr:
                    print("Stderr:", e.stderr)
            raise

    def _discover_meson_modules(self):
        """
        Auto-discover meson modules by looking for meson.build files
        in kuoeliassen subpackages.
        """
        modules = []
        kuoeliassen_src = Path("src") / "kuoeliassen"

        if not kuoeliassen_src.exists():
            print(f"[WARNING] {kuoeliassen_src} not found")
            return modules

        def _find_meson_builds(base_path, relative_path=""):
            """Recursively find meson.build files"""
            for subdir in base_path.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("__"):
                    meson_file = subdir / "meson.build"
                    if meson_file.exists():
                        if relative_path:
                            module_name = f"{relative_path}.{subdir.name}"
                        else:
                            module_name = subdir.name
                        print(f"[DISCOVER] Found meson module: {module_name}")
                        modules.append({
                            "name": module_name,
                            "path": subdir,
                        })
                    # Continue searching in subdirectories
                    new_relative_path = (
                        f"{relative_path}.{subdir.name}"
                        if relative_path
                        else subdir.name
                    )
                    _find_meson_builds(subdir, new_relative_path)

        # Start recursive search from kuoeliassen root
        _find_meson_builds(kuoeliassen_src)

        return modules


class CustomDevelop(develop):
    """Custom develop command that builds meson modules"""

    def run(self):
        # Build meson modules in develop mode
        self.run_command("build_ext")
        super().run()


class CustomInstall(install):
    """Custom install command that ensures meson modules are built"""

    def run(self):
        # Ensure meson modules are built before install
        self.run_command("build_ext")
        super().run()


# Configuration for mixed build
setup_config = {
    "cmdclass": {
        "build_ext": MesonBuildExt,
        "develop": CustomDevelop,
        "install": CustomInstall,
    },
    # Dummy extension for compatibility (actual Fortran modules built by meson)
    "ext_modules": [
        Extension("kuoeliassen._dummy", sources=[
                  "src/kuoeliassen/_dummy.c"], optional=True)
    ],
}

if __name__ == "__main__":
    setup(**setup_config)
