"""
Core solver interface for KuoEliassen package
Uses Fortran backend with COO format sparse matrices
Only uses LU decomposition solver
"""

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from typing import Dict

from . import kuoeliassen_module as KuoEliassen_module


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


def solve_ke(
    v: np.ndarray,
    temperature: np.ndarray,
    vt_eddy: np.ndarray,
    vu_eddy: np.ndarray,
    pressure: np.ndarray,
    latitude: np.ndarray,
    heating: np.ndarray = None,
    rad_heating: np.ndarray = None,
    latent_heating: np.ndarray = None,
    qgpv: bool = False
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
        Pressure levels [Pa], must be in ascending order (surface to top)
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
        results = []
        for t in range(ntime):
            # Extract 2D slice and recursively call
            kwargs = {'qgpv': qgpv}
            if rad_heating is not None and latent_heating is not None:
                kwargs.update(
                    {'rad_heating': rad_heating[t], 'latent_heating': latent_heating[t]})
            elif heating is not None:
                kwargs['heating'] = heating[t]
            else:
                raise ValueError(
                    "Either 'heating' or both 'rad_heating' and 'latent_heating' required")

            results.append(solve_ke(v[t], temperature[t], vt_eddy[t], vu_eddy[t],
                                    pressure, latitude, **kwargs))

        # Stack results
        return {key: np.stack([r[key] for r in results], axis=0) for key in results[0].keys()}

    # 2D mode - validate shapes
    nlev, nlat = v.shape
    for name, arr in [('temperature', temperature), ('vt_eddy', vt_eddy), ('vu_eddy', vu_eddy)]:
        if arr.shape != (nlev, nlat):
            raise ValueError(
                f"{name} shape mismatch: {arr.shape} != {(nlev, nlat)}")
    if pressure.shape != (nlev,) or latitude.shape != (nlat,):
        raise ValueError(f"pressure/latitude shape mismatch")

    # Determine heating mode and prepare heating arrays
    single_heating_mode = False  # Track if only single heating was provided

    if rad_heating is not None and latent_heating is not None:
        # Mode 1: Both heating components provided separately (decomposed mode)
        for arr, name in [(rad_heating, 'rad'), (latent_heating, 'latent')]:
            if arr.shape != (nlev, nlat):
                raise ValueError(f"{name}_heating shape mismatch")
    elif heating is not None:
        # Mode 2: Single total heating - split into latent (all) and rad (zero)
        if heating.shape != (nlev, nlat):
            raise ValueError("heating shape mismatch")
        latent_heating = heating.copy()
        rad_heating = np.zeros_like(heating)
        single_heating_mode = True  # Mark single heating mode
    else:
        raise ValueError(
            "Either 'heating' or both 'rad_heating' and 'latent_heating' required")

    # Convert latitude to radians
    phi = np.deg2rad(latitude)

    # Ensure Fortran-contiguous arrays with float32 for Python interface
    # Using tuple unpacking for memory efficiency (avoids dictionary overhead)
    v_f, temp_f, latent_heating_f, rad_heating_f, vt_eddy_f, vu_eddy_f, p_f, phi_f = (
        np.asfortranarray(arr, dtype=np.float32) for arr in
        (v, temperature, latent_heating,
         rad_heating, vt_eddy, vu_eddy, pressure, phi)
    )

    # Always keep all data points (keep_poles=True, which is 1 in Fortran)
    keep_poles_int = 1

    # Compute RHS components using Fortran - single call with both heating inputs
    # Fortran computes all 6 components in one pass:
    #   D_latent: Latent heating component
    #   D_rad: Radiative heating component
    #   D_vt: Eddy heat flux convergence (heating-independent)
    #   D_vu: Eddy momentum flux convergence (heating-independent)
    #   D_x: Friction term = -f * dF/dp (heating-independent)
    #   F_friction: Friction force X = d(u'v'*cos²)/dφ / cos² - v̄*f [m/s²]
    D_latent, D_rad, D_vt, D_vu, D_x, F_friction = KuoEliassen_module.compute_rhs_components(
        v_f, temp_f, latent_heating_f, rad_heating_f, vt_eddy_f, vu_eddy_f, p_f, phi_f, keep_poles_int
    )

    # Total RHS
    D_total = D_latent + D_rad + D_vt + D_vu + D_x

    # Build operator matrix using Fortran (COO format)
    nlat_used = nlat  # Use all latitude points
    n_total = nlev * nlat_used
    max_nnz = n_total * 5  # 5-point stencil

    row_idx, col_idx, values, nnz = KuoEliassen_module.build_ke_operator_coo(
        temp_f, p_f, phi_f, keep_poles_int, max_nnz
    )

    # Trim to actual nnz
    row_idx = row_idx[:nnz]
    col_idx = col_idx[:nnz]
    values = values[:nnz]

    # Create scipy sparse matrix (COO format, then convert to CSC for solver)
    L_sparse = coo_matrix((values, (row_idx, col_idx)),
                          shape=(n_total, n_total))
    L_csc = L_sparse.tocsc()

    # Prepare RHS vectors - use all latitude points
    j_start = 0
    j_end = nlat

    # Stack all RHS components for multi-RHS solve
    # Order: latent, rad, eddy heat, eddy momentum, friction, total
    rhs_list = [D_latent, D_rad, D_vt, D_vu, D_x, D_total]

    rhs_matrix = np.column_stack(
        [rhs[:, j_start:j_end].T.ravel('F') for rhs in rhs_list])

    # Solve using LU decomposition (efficient for multiple RHS)
    lu = splu(L_csc)
    psi_solutions = np.array([lu.solve(rhs_matrix[:, i])
                             for i in range(rhs_matrix.shape[1])]).T

    # Build result dictionary - single vs decomposed heating modes
    psi_q = _reshape_solution(
        psi_solutions[:, 0] + psi_solutions[:, 1], nlat_used, nlev)
    result = {
        'PSI': _reshape_solution(psi_solutions[:, -1], nlat_used, nlev),
        'D': D_total,
        'PSI_Q': psi_q,
        'PSI_latent': np.zeros((nlev, nlat)) if single_heating_mode else _reshape_solution(psi_solutions[:, 0], nlat_used, nlev),
        'PSI_rad': np.zeros((nlev, nlat)) if single_heating_mode else _reshape_solution(psi_solutions[:, 1], nlat_used, nlev),
        'PSI_vt': _reshape_solution(psi_solutions[:, 2], nlat_used, nlev),
        'PSI_vu': _reshape_solution(psi_solutions[:, 3], nlat_used, nlev),
        'PSI_x': _reshape_solution(psi_solutions[:, 4], nlat_used, nlev)
    }

    if qgpv:
        Q_total = latent_heating + rad_heating
        Q_total_f = np.asfortranarray(Q_total, dtype=np.float32)
        F_friction_f = np.asfortranarray(F_friction, dtype=np.float32)

        momentum_term, thermal_term = KuoEliassen_module.compute_qgpv_balance_terms(
            temp_f, v_f, F_friction_f, Q_total_f, vt_eddy_f, vu_eddy_f, p_f, phi_f
        )

        result.update({
            'momentum_term': momentum_term,
            'thermal_term': thermal_term,
            'residual': momentum_term - thermal_term
        })

    return result


def solve_ke_LHS(
    psi_base: np.ndarray,
    temp_base: np.ndarray,
    psi_current: np.ndarray,
    temp_current: np.ndarray,
    pressure: np.ndarray,
    latitude: np.ndarray
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
    # Check if 3D input
    is_3d = psi_base.ndim == 3

    if is_3d:
        # 3D mode: solve for each time step
        ntime, nlev, nlat = psi_current.shape

        # Validate shapes
        expected_shape = (ntime, nlev, nlat)
        arrays_to_check = {
            'psi_base': psi_base,
            'temp_base': temp_base,
            'psi_current': psi_current,
            'temp_current': temp_current
        }

        for name, arr in arrays_to_check.items():
            if arr.shape != expected_shape:
                raise ValueError(
                    f"{name} shape {arr.shape} != {expected_shape}")

        # Solve for each time step
        results_list = []
        for t in range(ntime):
            result_t = solve_ke_LHS(
                psi_base[t, :, :],
                temp_base[t, :, :],
                psi_current[t, :, :],
                temp_current[t, :, :],
                pressure,
                latitude
            )
            results_list.append(result_t)

        # Stack results along time dimension
        result_3d = {}
        for key in results_list[0].keys():
            result_3d[key] = np.stack([r[key] for r in results_list], axis=0)

        return result_3d

    else:
        # 2D mode
        nlev, nlat = psi_base.shape
        expected_shape = (nlev, nlat)

        # Validate shapes
        arrays_to_check = {
            'psi_base': psi_base,
            'temp_base': temp_base,
            'psi_current': psi_current,
            'temp_current': temp_current
        }

        for name, arr in arrays_to_check.items():
            if arr.shape != expected_shape:
                raise ValueError(
                    f"{name} shape {arr.shape} != {expected_shape}")

        if pressure.shape != (nlev,):
            raise ValueError(f"pressure shape {pressure.shape} != ({nlev},)")
        if latitude.shape != (nlat,):
            raise ValueError(f"latitude shape {latitude.shape} != ({nlat},)")

    # Convert latitude to radians
    phi = np.deg2rad(latitude)

    # Prepare arrays (Fortran-contiguous, float32)
    arrays_f32 = {name: np.asfortranarray(arr, dtype=np.float32)
                  for name, arr in [('temp_base', temp_base), ('temp_current', temp_current),
                                    ('p', pressure), ('phi', phi)]}
    temp_base_f, temp_current_f = arrays_f32['temp_base'], arrays_f32['temp_current']
    p_f, phi_f = arrays_f32['p'], arrays_f32['phi']

    keep_poles_int = 1
    n_total = nlev * nlat
    max_nnz = n_total * 5

    # Build base operator L_base (from base temperature)
    row_base, col_base, val_base, nnz_base = KuoEliassen_module.build_ke_operator_coo(
        temp_base_f, p_f, phi_f, keep_poles_int, max_nnz
    )

    # Trim to actual nnz
    row_base = row_base[:nnz_base]
    col_base = col_base[:nnz_base]
    val_base = val_base[:nnz_base]

    # Create L_base sparse matrix
    L_base_coo = coo_matrix(
        (val_base, (row_base, col_base)), shape=(n_total, n_total))
    L_base_csc = L_base_coo.tocsc()

    # Build current operator L_current (from current temperature)
    row_curr, col_curr, val_curr, nnz_curr = KuoEliassen_module.build_ke_operator_coo(
        temp_current_f, p_f, phi_f, keep_poles_int, max_nnz
    )

    # Trim to actual nnz
    row_curr = row_curr[:nnz_curr]
    col_curr = col_curr[:nnz_curr]
    val_curr = val_curr[:nnz_curr]

    # Create L_current sparse matrix
    L_current_coo = coo_matrix(
        (val_curr, (row_curr, col_curr)), shape=(n_total, n_total))
    L_current_csc = L_current_coo.tocsc()

    # Compute streamfunction anomaly
    delta_psi = psi_current - psi_base  # δΨ

    # Flatten fields to vectors (Fortran order: lat varies fastest)
    psi_base_flat = psi_base.T.ravel('F')
    delta_psi_flat = delta_psi.T.ravel('F')

    # Compute δL = L_current - L_base
    delta_L_csc = L_current_csc - L_base_csc

    # Compute RHS terms for decomposition
    # Term 1: -δL * Ψ_base (static stability change effect on base state)
    RHS_stability = -delta_L_csc.dot(psi_base_flat)

    # Term 2: -δL * δΨ (residual/nonlinear term)
    RHS_residual = -delta_L_csc.dot(delta_psi_flat)

    # Solve L_base * δΨ_i = RHS_i for each component
    lu_base = splu(L_base_csc)

    # Solve for stability and residual components
    psi_stability_flat = lu_base.solve(RHS_stability)
    psi_residual_flat = lu_base.solve(RHS_residual)

    # Reshape back to (nlev, nlat) using module-level helper
    psi_stability = _reshape_solution(psi_stability_flat, nlat, nlev)
    psi_residual = _reshape_solution(psi_residual_flat, nlat, nlev)

    # Build result dictionary
    result = {
        'PSI_stability': psi_stability,   # Static stability component
        'PSI_residual': psi_residual,     # Residual component
    }

    return result
