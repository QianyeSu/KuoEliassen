# Fortran source files
fortran_sources = files(
  'fortran/KuoEliassen_Gradient.f90',
  'fortran/KuoEliassen_Operator.f90',
  'fortran/KuoEliassen_QGPV_Balance.f90',
  'fortran/KuoEliassen_RHS.f90',
  'fortran/SOR.f90',
)

# f2py signature file
f2py_sig = files('fortran/KuoEliassen_Fortran.pyf')

# Locate fortranobject.c (robustly handle different NumPy versions)
fortranobject_cmd = run_command(
  py,
  [
    '-c', '''
import numpy.f2py
import numpy
import os
import sys

candidates = []

# Try f2py include directory
try:
    fo_path = os.path.join(numpy.f2py.get_include(), "fortranobject.c")
    candidates.append(fo_path)
except:
    pass

# Try various known locations
numpy_base = numpy.__path__[0]
candidates.extend([
    os.path.join(numpy_base, "f2py", "src", "fortranobject.c"),
    os.path.join(numpy_base, "f2py", "fortranobject.c"),
    os.path.join(numpy_base, "_core", "src", "fortranobject.c"),
    os.path.join(numpy_base, "core", "src", "fortranobject.c"),
])

# Find first existing path
for candidate in candidates:
    if os.path.exists(candidate):
        print(candidate)
        break
else:
    print("")
''',
  ],
  check: true,
)
fortranobject_c = fortranobject_cmd.stdout().strip()

# Generate f2py wrapper
f2py_gen = custom_target(
  'KuoEliassen_Fortran_f2py',
  input: f2py_sig,
  output: [
    'kuoeliassen_modulemodule.c',
    'kuoeliassen_module-f2pywrappers.f',
  ],
  command: [
    py,
    '-m', 'numpy.f2py',
    '--lower', '@INPUT@',
    '--build-dir', '@OUTDIR@',
  ],
  build_by_default: true,
  install: false,
)

# Prepare sources for extension
kuoeliassen_sources = [fortran_sources, f2py_gen]

# Add fortranobject.c if found
if fortranobject_c != ''
  message('Found fortranobject.c: ' + fortranobject_c)
  fortran_obj_check = run_command(
    py,
    '-c', 'import os; import sys; sys.exit(0 if os.path.exists(r"'
    + fortranobject_c
    + '") else 1)',
    check: false,
  )
  if fortran_obj_check.returncode() == 0
    kuoeliassen_sources += files(fortranobject_c)
    message('Added fortranobject.c to build')
  else
    warning('fortranobject.c path found but file does not exist: ' + fortranobject_c)
  endif
else
  warning('fortranobject.c not found - trying to build without it')
endif

# Build dependency list
dependencies = [py_dep]
if openmp_dep.found()
  dependencies += openmp_dep
endif

# Build extension module
py.extension_module(
  'kuoeliassen_module',
  kuoeliassen_sources,
  include_directories: inc_np,
  dependencies: dependencies,
  fortran_args: fortran_args,
  c_args: c_args,
  install: true,
  subdir: 'kuoeliassen',
  build_by_default: true,
)

# Install Python files
python_sources = files(
  '__init__.py',
  'core.py',
  'utils.py',
  'xarray_interface.py',
)

py.install_sources(
  python_sources,
  subdir: 'kuoeliassen',
)