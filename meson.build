project(
  'KuoEliassen',
  'c', 'fortran',
  version: '0.2.2',  # Update this when releasing new versions
  license: 'BSD-3-Clause',
  meson_version: '>=1.1.0',
  default_options: [
    'buildtype=release',
    'warning_level=2',
    'b_lto=true',
    'c_std=c99',
  ],
)

# Python and NumPy dependencies
py_mod = import('python')
py = py_mod.find_installation('python', pure: false)
py_dep = py.dependency()

# Get NumPy include directories (robustly handle different NumPy versions)
incdir_numpy_cmd = run_command(
  py,
  ['-c', '''
import numpy
import os
paths = [
    numpy.get_include(),
    os.path.join(numpy.__path__[0], "core", "include"),
    os.path.join(numpy.__path__[0], "_core", "include")
]
for path in paths:
    if os.path.exists(os.path.join(path, "numpy", "npy_os.h")):
        print(path)
        break
else:
    print(numpy.get_include())
'''],
  check: true,
)
incdir_numpy = incdir_numpy_cmd.stdout().strip()

# Try to get f2py include
incdir_f2py_cmd = run_command(
  py,
  ['-c', '''
import numpy
import os
try:
    import numpy.f2py
    f2py_path = numpy.f2py.get_include()
    if os.path.exists(f2py_path):
        print(f2py_path)
    else:
        print(numpy.get_include())
except:
    print(numpy.get_include())
'''],
  check: true,
)
incdir_f2py = incdir_f2py_cmd.stdout().strip()

message('NumPy include directory: ' + incdir_numpy)
message('F2PY include directory: ' + incdir_f2py)

inc_np = include_directories(incdir_numpy, incdir_f2py)

# NumPy API settings
numpy_nodepr_api = ['-DNPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION']

# Detect platform for optimization flags
host_system = host_machine.system()
host_cpu = host_machine.cpu_family()

message('Host system: ' + host_system)
message('Host CPU family: ' + host_cpu)

# Fortran compiler
fc = meson.get_compiler('fortran')
cc = meson.get_compiler('c')

# Optimization flags (portable, no -march=native)
fortran_args = [
  '-O3',
  '-fPIC',
  '-fno-second-underscore',
  '-funroll-loops',
  '-finline-functions',
  '-ftree-vectorize',
  '-ffree-line-length-none',
  '-fno-common',
  '-std=legacy',
]

c_args = [
  '-DNPY_NO_DEPRECATED_API=NPY_1_7_API_VERSION',
  '-fPIC',
  '-fno-trapping-math',
]

# Platform-specific optimizations (portable, not native)
if host_system == 'darwin' and host_cpu == 'aarch64'
  # Apple Silicon optimizations
  fortran_args += ['-march=armv8-a', '-mtune=apple-m1']
  c_args += ['-march=armv8-a', '-mtune=apple-m1']
elif host_system == 'windows'
  # Windows-specific optimizations (generic x86-64)
  fortran_args += ['-march=x86-64', '-mtune=generic']
  c_args += ['-march=x86-64', '-mtune=generic']
else
  # Linux x86-64 optimizations (generic, not native)
  fortran_args += ['-march=x86-64', '-mtune=generic']
  c_args += ['-march=x86-64', '-mtune=generic']
endif

# OpenMP support
openmp_dep = dependency('openmp', language: 'fortran', required: false)
if openmp_dep.found()
  fortran_args += ['-fopenmp']
  c_args += ['-fopenmp']
  message('OpenMP enabled for parallel processing')
else
  warning('OpenMP not found - building without parallel support')
endif

message('Fortran args: ' + ' '.join(fortran_args))
message('C args: ' + ' '.join(c_args))

# Build
subdir('src')
