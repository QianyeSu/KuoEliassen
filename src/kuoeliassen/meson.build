# Fortran source files
fortran_sources = files(
  'fortran/KuoEliassen_Gradient.f90',
  'fortran/KuoEliassen_Operator.f90',
  'fortran/KuoEliassen_QGPV_Balance.f90',
  'fortran/KuoEliassen_RHS.f90',
  'fortran/SOR.f90',
  'fortran/KuoEliassen_Bindings.f90',
)

# Prepare sources for extension
kuoeliassen_sources = [files('_kuoeliassen_module.c'), fortran_sources]

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
