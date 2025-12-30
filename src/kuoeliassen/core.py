"""
Core solver interface for KuoEliassen package
Uses Fortran backend with COO format sparse matrices
Supports LU decomposition and SOR iterative solvers
"""

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from typing import Dict, Optional, Callable

from . import kuoeliassen_module as KuoEliassen_module


# ============================================================================
# Helpers
# ============================================================================

def _validate_shapes(checks: list):
    """Validate shapes of multiple arrays."""
    for arr, expected, name in checks:
        if arr.shape != expected:
            raise ValueError(
                f"{name} shape mismatch: {arr.shape} != {expected}")


def _to_fortran(*arrays):
    """Convert arrays to Fortran-contiguous float32."""
    return [np.asfortranarray(arr, dtype=np.float32) for arr in arrays]


def _reshape_solution(psi_flat: np.ndarray, nlat: int, nlev: int) -> np.ndarray:
    """
    Reshape flattened solution vector to (nlev, nlat) array.

    Parameters
    ----------
    psi_flat : ndarray, shape (nlev * nlat,)
        Flattened solution vector (Fortran order: lat varies fastest)
    nlat : int
        Number of latitude points
    nlev : int
        Number of pressure levels

    Returns
    -------
    psi_2d : ndarray, shape (nlev, nlat)
        Reshaped 2D solution array
    """
    return psi_flat.reshape((nlat, nlev), order='F').T

# ============================================================================
# Solvers
# ============================================================================


def _solve_lu(rhs_matrix: np.ndarray,
              row_coo: Optional[np.ndarray] = None,
              col_coo: Optional[np.ndarray] = None,
              val_coo: Optional[np.ndarray] = None, **kwargs) -> np.ndarray:
    """LU decomposition solver (default, fast for multiple RHS).

    Parameters
    ----------
    rhs_matrix : ndarray, shape (n, nrhs)
        Right-hand side vectors
    row_coo, col_coo, val_coo : ndarray, optional
        COO format arrays (0-indexed). Used to build CSC.
    """
    # Build CSC matrix from COO
    n = rhs_matrix.shape[0]
    lu = splu(coo_matrix((val_coo, (row_coo, col_coo)), shape=(n, n)).tocsc())
    return np.array([lu.solve(rhs_matrix[:, i]) for i in range(rhs_matrix.shape[1])]).T


def _solve_sor(rhs_matrix: np.ndarray,
               omega: float = 1.8, tol: float = 1e-8,
               max_iter: int = 50000,
               row_coo: Optional[np.ndarray] = None,
               col_coo: Optional[np.ndarray] = None,
               val_coo: Optional[np.ndarray] = None, **kwargs) -> np.ndarray:
    """
    SOR (Successive Over-Relaxation) iterative solver.

    Uses Fortran backend for optimized performance.
    Directly uses COO arrays from Python (no redundant format conversion).

    Parameters
    ----------
    rhs_matrix : ndarray, shape (n, nrhs)
        Right-hand side vectors
    omega : float
        Relaxation factor (1.0 = Gauss-Seidel, ~1.8 conservative optimal for KE)
    tol : float  
        Convergence tolerance for residual norm (default: 1e-8)
    max_iter : int
        Maximum iterations before stopping (default: 50000)
    row_coo, col_coo, val_coo : ndarray, required
        COO arrays (0-indexed, will be converted to 1-indexed for Fortran)
    """
    n, n_rhs = rhs_matrix.shape
    # Fortran sor_solve_coo expects 0-indexed COO (like build_ke_operator_coo output)
    # Internal coo_to_csr_local will convert to 1-indexed
    # All arrays must match Fortran interface types: int32 for indices, float32 for values
    row_coo_f = np.asfortranarray(row_coo, dtype=np.int32)
    col_coo_f = np.asfortranarray(col_coo, dtype=np.int32)
    val_coo_f = np.asfortranarray(val_coo, dtype=np.float32)
    rhs_f = np.asfortranarray(rhs_matrix, dtype=np.float32)
    # Call Fortran SOR solver with pre-built matrix (1-indexed COO)
    solutions, iterations, residuals, status = KuoEliassen_module.sor_solve_coo(
        row_coo=row_coo_f, col_coo=col_coo_f, val_coo=val_coo_f,
        rhs=rhs_f, n=n, nnz=len(row_coo), nrhs=n_rhs,
        omega=omega, tol=tol, max_iter=max_iter
    )

    # Print convergence information for each RHS
    for i in range(n_rhs):
        converged = "converged" if status[i] == 0 else "not converged"
        print(
            f"SOR solver RHS#{i+1}: {converged} | iterations={iterations[i]:5d} | residual={residuals[i]:.3e}")

    return solutions


# Solver registry: maps method name to solver function
_SOLVERS: Dict[str, Callable] = {
    'lu': _solve_lu,
    'sor': _solve_sor,
}


def solve_ke(
    v: np.ndarray,
    temperature: np.ndarray,
    vt_eddy: np.ndarray,
    vu_eddy: np.ndarray,
    pressure: np.ndarray,
    latitude: np.ndarray,
    heating: Optional[np.ndarray] = None,
    rad_heating: Optional[np.ndarray] = None,
    latent_heating: Optional[np.ndarray] = None,
    qgpv: bool = False,
    solver: str = 'lu',
    omega: float = 1.8,
    tol: float = 1e-8,
    max_iter: int = 50000
) -> Dict[str, np.ndarray]:
    """
    Solve the Kuo-Eliassen equation for meridional circulation.

    Supports 2D (nlev, nlat) or 3D (ntime, nlev, nlat) input arrays.
    For 3D input, solves for each time step and returns 3D results.

    Parameters
    ----------
    v : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Mean meridional wind [m/s]
    temperature : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Temperature field [K]
    vt_eddy : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Eddy heat flux v'T' [K·m/s]
    vu_eddy : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Eddy momentum flux u'v' [m²/s²]
    pressure : ndarray, shape (nlev,)
        Pressure levels [Pa], must be in ascending order (top to surface)
    latitude : ndarray, shape (nlat,)
        Latitude in degrees [-90, 90]
    heating : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat), optional
        Total diabatic heating rate [K/s] (Latent + Radiative)
    rad_heating : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat), optional
        Radiative heating rate [K/s]
    latent_heating : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat), optional
        Latent heating rate [K/s]
    qgpv : bool, optional
        If True, compute and return QGPV balance diagnostic terms (default: False)
        Friction forcing is automatically computed from mean wind and eddy fluxes
    solver : str, optional
        Solver method: 'lu' (default, direct) or 'sor' (iterative)
    omega : float, optional
        SOR relaxation factor (only used when solver='sor', default: 1.8)
        Conservative setting for stability across different datasets
    tol : float, optional
        SOR convergence tolerance (only used when solver='sor', default: 1e-8)
    max_iter : int, optional
        SOR maximum iterations (only used when solver='sor', default: 50000)

    Returns
    -------
    result : dict
        Dictionary containing:
        - 'PSI': Total streamfunction [kg/s]
        - 'D': Total RHS forcing
        - 'PSI_latent': Latent heating component
        - 'PSI_rad': Radiative heating component
        - 'PSI_vt': Eddy heat flux component
        - 'PSI_vu': Eddy momentum flux component
        - 'PSI_x': Friction component

        If qgpv=True, also includes:
        - 'momentum_term': ∂F_total/∂y [s⁻²] - Momentum forcing term
        - 'thermal_term': f*(∂Q_θ/∂p)/(∂θ/∂p) [s⁻²] - Thermal forcing term
        - 'qgpv_residual': momentum_term - thermal_term [s⁻²] - Balance residual

        Note: Friction forcing (F) is automatically computed from v and vu_eddy
              as: F = d(u'v'*cos²φ)/dφ / cos²φ - v*f

        For 3D input, all output arrays have shape (ntime, nlev, nlat)

    Notes
    -----
    - **Latitude Grid**: The input latitude grid **must not** include the exact poles (±90°).
      The equation is singular at the poles due to 1/cos(phi) terms.
      Ensure latitude values are within (-90, 90), e.g., [-89.9, 89.9].
    - **Pressure Grid**: Pressure levels must be in ascending order (e.g., 100 to 100000 Pa).
    Heating input modes:
    - Mode 1: Only `heating` provided → single total heating term
    - Mode 2: Both `rad_heating` and `latent_heating` provided → 
      separate radiative and latent heating components (heating ignored)

    Examples
    --------
    # Mode 1: Single heating
    result = solve_ke(v, T, vt, vu, p, lat, heating=Q)

    # Mode 2: Decomposed heating (separate radiative and latent)
    result = solve_ke(v, T, vt, vu, p, lat, 
                      rad_heating=Q_rad, latent_heating=Q_latent)

    # 3D time series
    result = solve_ke(v_3d, T_3d, vt_3d, vu_3d, p, lat, heating=Q_3d)
    """
    # Handle 3D input by recursive call
    if v.ndim == 3:
        ntime, nlev, nlat = v.shape
        if rad_heating is not None and latent_heating is not None:
            h_kwargs = [{'rad_heating': rad_heating[t],
                         'latent_heating': latent_heating[t]} for t in range(ntime)]
        elif heating is not None:
            h_kwargs = [{'heating': heating[t]} for t in range(ntime)]
        else:
            raise ValueError(
                "Either 'heating' or both 'rad_heating' and 'latent_heating' required")

        results = [solve_ke(v[t], temperature[t], vt_eddy[t], vu_eddy[t], pressure, latitude,
                            qgpv=qgpv, solver=solver, omega=omega, tol=tol, max_iter=max_iter, **h_kwargs[t])
                   for t in range(ntime)]
        return {key: np.stack([r[key] for r in results], axis=0) for key in results[0].keys()}

    # 2D mode - validate shapes
    nlev, nlat = v.shape
    _validate_shapes([
        (temperature, (nlev, nlat), 'temperature'), (vt_eddy, (nlev, nlat), 'vt_eddy'),
        (vu_eddy, (nlev, nlat), 'vu_eddy'), (pressure,
                                             (nlev,), 'pressure'), (latitude, (nlat,), 'latitude')
    ])

    single_heating_mode = False
    if rad_heating is not None and latent_heating is not None:
        _validate_shapes([(rad_heating, (nlev, nlat), 'rad_heating'),
                         (latent_heating, (nlev, nlat), 'latent_heating')])
    elif heating is not None:
        _validate_shapes([(heating, (nlev, nlat), 'heating')])
        latent_heating, rad_heating, single_heating_mode = heating, np.zeros_like(
            heating), True
    else:
        raise ValueError(
            "Either 'heating' or both 'rad_heating' and 'latent_heating' required")

    # Convert latitude to radians and prepare Fortran arrays
    v_f, temp_f, lh_f, rh_f, vt_f, vu_f, p_f, phi_f = _to_fortran(
        v, temperature, latent_heating, rad_heating, vt_eddy, vu_eddy, pressure, np.deg2rad(latitude))

    # Compute RHS components using Fortran - single call with both heating inputs
    # Fortran computes all 6 components in one pass:
    #   D_latent: Latent heating component
    #   D_rad: Radiative heating component
    #   D_vt: Eddy heat flux convergence (heating-independent)
    #   D_vu: Eddy momentum flux convergence (heating-independent)
    #   D_x: Friction term = -f * dF/dp (heating-independent)
    #   F_friction: Friction force X = d(u'v'*cos²)/dφ / cos² - v̄*f [m/s²]
    D_latent, D_rad, D_vt, D_vu, D_x, F_friction = KuoEliassen_module.compute_rhs_components(
        v_f, temp_f, lh_f, rh_f, vt_f, vu_f, p_f, phi_f, 1)
    D_total = D_latent + D_rad + D_vt + D_vu + D_x

    # Build operator matrix using Fortran (COO format)
    row_idx, col_idx, values, nnz = KuoEliassen_module.build_ke_operator_coo(
        temp_f, p_f, phi_f, 1, nlev * nlat * 5)  # 5-point stencil
    row_idx, col_idx, values = row_idx[:nnz], col_idx[:nnz], values[:nnz]

    # Prepare RHS vectors and solve
    rhs_list = [D_latent, D_rad, D_vt, D_vu, D_x, D_total]
    rhs_matrix = np.column_stack(
        [rhs[:, :nlat].T.ravel('F') for rhs in rhs_list])

    psi_solutions = _SOLVERS.get(solver, _solve_lu)(
        rhs_matrix, omega=omega, tol=tol, max_iter=max_iter,
        row_coo=row_idx, col_coo=col_idx, val_coo=values)

    # Build result dictionary
    psi_q = _reshape_solution(
        psi_solutions[:, 0] + psi_solutions[:, 1], nlat, nlev)
    result = {
        'PSI': _reshape_solution(psi_solutions[:, -1], nlat, nlev), 'D': D_total, 'PSI_Q': psi_q,
        'PSI_latent': np.zeros((nlev, nlat)) if single_heating_mode else _reshape_solution(psi_solutions[:, 0], nlat, nlev),
        'PSI_rad': np.zeros((nlev, nlat)) if single_heating_mode else _reshape_solution(psi_solutions[:, 1], nlat, nlev),
        'PSI_vt': _reshape_solution(psi_solutions[:, 2], nlat, nlev),
        'PSI_vu': _reshape_solution(psi_solutions[:, 3], nlat, nlev),
        'PSI_x': _reshape_solution(psi_solutions[:, 4], nlat, nlev)
    }

    if qgpv:
        Q_total_f = np.asfortranarray(
            latent_heating + rad_heating, dtype=np.float32)
        F_friction_f = np.asfortranarray(F_friction, dtype=np.float32)
        mt, tt = KuoEliassen_module.compute_qgpv_balance_terms(
            temp_f, v_f, F_friction_f, Q_total_f, vt_f, vu_f, p_f, phi_f)
        result.update(
            {'momentum_term': mt, 'thermal_term': tt, 'residual': mt - tt})

    return result


def solve_ke_LHS(
    psi_base: np.ndarray,
    temp_base: np.ndarray,
    psi_current: np.ndarray,
    temp_current: np.ndarray,
    pressure: np.ndarray,
    latitude: np.ndarray,
    solver: str = 'lu',
    omega: float = 1.8,
    tol: float = 1e-8,
    max_iter: int = 50000
) -> Dict[str, np.ndarray]:
    """
    Decompose streamfunction anomaly δΨ into stability and residual components.

    Solves the left-hand side (LHS) decomposition of the KE equation:
        L_base * δΨ = δD - δL * Ψ_base - δL * δΨ

    This function computes the last two terms on the RHS:
        - δΨ_stability: L_base * δΨ_stability = -δL * Ψ_base
        - δΨ_residual:  L_base * δΨ_residual = -δL * δΨ

    The forcing component δΨ_forcing (first term, related to δD) can be derived as:
        δΨ_forcing = δΨ_total - δΨ_stability - δΨ_residual
    where δΨ_total = Ψ_current - Ψ_base

    Physical interpretation:
        - δL = L_current - L_base represents changes in the operator due to 
          static stability changes (temperature structure changes)
        - δΨ_stability: How operator changes affect the base state circulation
        - δΨ_residual: Nonlinear interaction between operator and circulation changes

    Parameters
    ----------
    psi_base : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Base period streamfunction (e.g., 1979 or multi-year mean) [kg/s]
    temp_base : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Base period temperature [K]
    psi_current : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Current period streamfunction [kg/s]
    temp_current : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Current period temperature [K]
    pressure : ndarray, shape (nlev,)
        Pressure levels [Pa]
    latitude : ndarray, shape (nlat,)
        Latitude in degrees [-90, 90]
    solver : str, optional
        Solver method: 'lu' (default, direct) or 'sor' (iterative)
    omega : float, optional
        SOR relaxation factor (only used when solver='sor', default: 1.8)
    tol : float, optional
        SOR convergence tolerance (only used when solver='sor', default: 1e-8)
    max_iter : int, optional
        SOR maximum iterations (only used when solver='sor', default: 50000)

    Returns
    -------
    result : dict
        Dictionary containing:
        - 'psi_stability': δΨ_stability - Static stability change component
        - 'psi_residual': δΨ_residual - Residual/nonlinear component

        Note: The forcing component can be computed as:
              δΨ_forcing = (Ψ_current - Ψ_base) - δΨ_stability - δΨ_residual

        For 3D input, all arrays have shape (ntime, nlev, nlat)

    Notes
    -----
    This decomposition does NOT require D_base or D_current because:
    - We only compute the operator-related terms (-δL * Ψ_base and -δL * δΨ)
    - The forcing term δD can be obtained from the full solve_ke results
    - This simplifies the interface when you only need LHS decomposition

    For multi-year analysis:
    - Use multi-year mean as base: psi_base = psi.mean(axis=0)
    - Apply to each year's streamfunction

    For reference year analysis (e.g., 1979):
    - Use reference year fields as base
    - Apply to subsequent years

    Examples
    --------
    # Multi-year mean baseline
    result_base = solve_ke(v, T_mean, vt_mean, vu_mean, p, lat, heating=Q_mean)
    psi_base = result_base['PSI']
    T_base = T_mean

    result_curr = solve_ke(v_curr, T_curr, vt_curr, vu_curr, p, lat, heating=Q_curr)
    psi_curr = result_curr['PSI']

    decomp = solve_ke_LHS(psi_base, T_base, psi_curr, T_curr, p, lat)

    # Compute forcing component
    delta_psi = psi_curr - psi_base
    psi_forcing = delta_psi - decomp['psi_stability'] - decomp['psi_residual']
    """
    if psi_current.ndim == 3:
        ntime, nlev, nlat = psi_current.shape
        _validate_shapes([(temp_current, (ntime, nlev, nlat), 'temp_current')])
        for name, arr in [('psi_base', psi_base), ('temp_base', temp_base)]:
            if arr.ndim not in (2, 3):
                raise ValueError(f"{name} must be 2D or 3D")
            expected = (ntime, nlev, nlat) if arr.ndim == 3 else (nlev, nlat)
            _validate_shapes([(arr, expected, name)])

        results = [solve_ke_LHS(
            psi_base[t] if psi_base.ndim == 3 else psi_base,
            temp_base[t] if temp_base.ndim == 3 else temp_base,
            psi_current[t], temp_current[t], pressure, latitude,
            solver=solver, omega=omega, tol=tol, max_iter=max_iter) for t in range(ntime)]
        return {key: np.stack([r[key] for r in results], axis=0) for key in results[0].keys()}

    nlev, nlat = psi_current.shape
    _validate_shapes([
        (psi_base, (nlev, nlat), 'psi_base'), (temp_base, (nlev, nlat), 'temp_base'),
        (psi_current, (nlev, nlat), 'psi_current'), (temp_current,
                                                     (nlev, nlat), 'temp_current'),
        (pressure, (nlev,), 'pressure'), (latitude, (nlat,), 'latitude')
    ])

    tb_f, tc_f, p_f, phi_f = _to_fortran(
        temp_base, temp_current, pressure, np.deg2rad(latitude))
    n_total = nlev * nlat

    def _build_op(temp_f):
        row, col, val, nnz = KuoEliassen_module.build_ke_operator_coo(
            temp_f, p_f, phi_f, 1, n_total * 5)   # 5-point stencil
        return coo_matrix((val[:nnz], (row[:nnz], col[:nnz])), shape=(n_total, n_total)).tocsc(), row[:nnz], col[:nnz], val[:nnz]

    L_base_csc, row, col, val = _build_op(tb_f)
    L_curr_csc, _, _, _ = _build_op(tc_f)

    delta_L = L_curr_csc - L_base_csc
    rhs_mat = np.column_stack([
        # Term 1: stability change effect -δL * Ψ_base (static stability change effect on base state)
        -delta_L.dot(psi_base.T.ravel('F')),
        # Term 2: residual/nonlinear term -δL * δΨ (residual/nonlinear term)
        -delta_L.dot((psi_current - psi_base).T.ravel('F'))
    ])

    psi_sols = _SOLVERS.get(solver, _solve_lu)(
        rhs_mat, omega=omega, tol=tol, max_iter=max_iter, row_coo=row, col_coo=col, val_coo=val)

    return {
        'PSI_stability': _reshape_solution(psi_sols[:, 0], nlat, nlev),
        'PSI_residual': _reshape_solution(psi_sols[:, 1], nlat, nlev)
    }
