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
    v_mean: np.ndarray,
    temperature: np.ndarray,
    vt_eddy: np.ndarray,
    vu_eddy: np.ndarray,
    pressure: np.ndarray,
    latitude: np.ndarray,
    latent_heating: np.ndarray = None,
    rad_heating: np.ndarray = None,
    dtv_heating: np.ndarray = None,
    components: bool = True,
    qgpv: bool = False
) -> Dict[str, np.ndarray]:
    """
    Solve the Kuo-Eliassen equation for meridional circulation.

    Parameters
    ----------
    v_mean : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Mean meridional wind [m/s]
    temperature : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Temperature field [K]
    vt_eddy : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Eddy heat flux v'T' [K·m/s]
    vu_eddy : ndarray, shape (nlev, nlat) or (ntime, nlev, nlat)
        Eddy momentum flux u'v' [m²/s²]
    pressure : ndarray, shape (nlev,)
        Pressure levels [Pa]
    latitude : ndarray, shape (nlat,)
        Latitude [degrees]
    latent_heating : ndarray, optional
        Latent heating rate [K/s]
    rad_heating : ndarray, optional
        Radiative heating rate [K/s]
    dtv_heating : ndarray, optional
        Vertical diffusion heating [K/s]
    components : bool, default=True
        Return individual PSI components
    qgpv : bool, default=False
        Return QGPV balance diagnostics

    Returns
    -------
    result : dict
        - 'PSI': Total streamfunction [kg/s]
        - 'D': Total forcing
        - 'PSI_latent', 'PSI_rad', 'PSI_dtv_heating': Heating components (if components=True)
        - 'PSI_dtv', 'PSI_vt', 'PSI_vu', 'PSI_x': Dynamical components (if components=True)
        - 'momentum_term', 'thermal_term', 'residual': QGPV diagnostics (if qgpv=True)

    Examples
    --------
    # Simple mode
    result = solve_ke(v, T, vt, vu, p, lat, latent_heating=Q)

    if is_3d:
        # 3D mode: (ntime, nlev, nlat)
        ntime, nlev, nlat = v_mean.shape
        expected_shape_3d = (ntime, nlev, nlat)
        expected_shape_2d = (nlev, nlat)

        # Validate 3D arrays
        arrays_to_check_3d = {
            'temperature': temperature,
            'vt_eddy': vt_eddy,
            'vu_eddy': vu_eddy
        }

        for name, arr in arrays_to_check_3d.items():
            if arr.shape != expected_shape_3d:
                raise ValueError(
                    f"{name} shape {arr.shape} != {expected_shape_3d}")

        # Check heating inputs
        has_decomposed_heating = (rad_heating is not None) and (
            latent_heating is not None)
        has_dtv_heating = (dtv_heating is not None)

        if has_decomposed_heating:
            if rad_heating.shape != expected_shape_3d:
                raise ValueError(
                    f"rad_heating shape {rad_heating.shape} != {expected_shape_3d}")
            if latent_heating.shape != expected_shape_3d:
                raise ValueError(
                    f"latent_heating shape {latent_heating.shape} != {expected_shape_3d}")
            if has_dtv_heating and dtv_heating.shape != expected_shape_3d:
                raise ValueError(
                    f"dtv_heating shape {dtv_heating.shape} != {expected_shape_3d}")
        elif heating is not None:
            if heating.shape != expected_shape_3d:
                raise ValueError(
                    f"heating shape {heating.shape} != {expected_shape_3d}")
        else:
            raise ValueError(
                "Either 'heating' or both 'rad_heating' and 'latent_heating' must be provided")

        # Solve for each time step
        results_list = []
        for t in range(ntime):
            v_2d = v_mean[t, :, :]
            T_2d = temperature[t, :, :]
            vt_2d = vt_eddy[t, :, :]
            vu_2d = vu_eddy[t, :, :]

            if has_decomposed_heating:
                rad_2d = rad_heating[t, :, :]
                latent_2d = latent_heating[t, :, :]
                dtv_2d = dtv_heating[t, :, :] if has_dtv_heating else None
                result_t = solve_ke(
                    v_2d, T_2d, vt_2d, vu_2d, pressure, latitude,
                    rad_heating=rad_2d, latent_heating=latent_2d, dtv_heating=dtv_2d,
                    return_components=return_components,
                    return_qgpv_balance=return_qgpv_balance
                )
            else:
                heating_2d = heating[t, :, :]
                result_t = solve_ke(
                    v_2d, T_2d, vt_2d, vu_2d, pressure, latitude,
                    heating=heating_2d,
                    return_components=return_components,
                    return_qgpv_balance=return_qgpv_balance
                )
            results_list.append(result_t)

        # Stack results along time dimension
        result_3d = {}
        for key in results_list[0].keys():
            result_3d[key] = np.stack([r[key] for r in results_list], axis=0)

        return result_3d

    else:
        # 2D mode: (nlev, nlat)
        nlev, nlat = v_mean.shape
        expected_shape = (nlev, nlat)

        arrays_to_check = {
            'temperature': temperature,
            'vt_eddy': vt_eddy,
            'vu_eddy': vu_eddy
        }

        for name, arr in arrays_to_check.items():
            if arr.shape != expected_shape:
                raise ValueError(
                    f"{name} shape {arr.shape} != {expected_shape}")

        if pressure.shape != (nlev,):
            raise ValueError(f"pressure shape {pressure.shape} != ({nlev},)")
        if latitude.shape != (nlat,):
            raise ValueError(f"latitude shape {latitude.shape} != ({nlat},)")

        # Check heating decomposition mode
        has_decomposed_heating = (rad_heating is not None) and (
            latent_heating is not None)
        has_dtv_heating = (dtv_heating is not None)

        if has_decomposed_heating:
            # Mode 2/3: Decomposed heating
            if rad_heating.shape != expected_shape:
                raise ValueError(
                    f"rad_heating shape {rad_heating.shape} != {expected_shape}")
            if latent_heating.shape != expected_shape:
                raise ValueError(
                    f"latent_heating shape {latent_heating.shape} != {expected_shape}")
            if has_dtv_heating and dtv_heating.shape != expected_shape:
                raise ValueError(
                    f"dtv_heating shape {dtv_heating.shape} != {expected_shape}")
        elif heating is not None:
            # Mode 1: Single total heating
            if heating.shape != expected_shape:
                raise ValueError(
                    f"heating shape {heating.shape} != {expected_shape}")
            rad_heating = np.zeros_like(heating)
            latent_heating = heating.copy()
        else:
            raise ValueError(
                "Either 'heating' or both 'rad_heating' and 'latent_heating' must be provided")

    # Convert latitude to radians
    phi = np.deg2rad(latitude)

    # Handle DTV heating (vertical diffusion)
    if has_dtv_heating:
        # Add DTV to total heating for Fortran computation
        total_latent_heating = latent_heating + dtv_heating
    else:
        total_latent_heating = latent_heating
        # For separate component calculation
        dtv_heating = np.zeros_like(latent_heating)

    # Ensure Fortran-contiguous arrays with float32 for Python interface
    # Using tuple unpacking for memory efficiency (avoids dictionary overhead)
    v_mean_f, temp_f, latent_heating_f, rad_heating_f, vt_eddy_f, vu_eddy_f, p_f, phi_f = (
        np.asfortranarray(arr, dtype=np.float32) for arr in
        (v_mean, temperature, total_latent_heating,
         rad_heating, vt_eddy, vu_eddy, pressure, phi)
    )

    # Always keep all data points (keep_poles=True, which is 1 in Fortran)
    keep_poles_int = 1

    # Compute RHS components using Fortran (f2py will convert float32 to float64 internally)
    # RHS components:
    #   D_dtcond: Latent heating + DTV heating (if provided)
    #   D_rad: Radiative heating
    #   D_dtv: Temperature advection by mean meridional circulation (v̄·∇T)
    #   D_vt: Eddy heat flux convergence
    #   D_vu: Eddy momentum flux convergence
    #   D_x: Friction term = -f * dF/dp
    #   F_friction: Friction force X = d(u'v'*cos²)/dφ / cos² - v̄*f [m/s²]
    D_dtcond, D_rad, D_dtv, D_vt, D_vu, D_x, F_friction = KuoEliassen_module.compute_rhs_components(
        v_mean_f, temp_f, latent_heating_f, vt_eddy_f, vu_eddy_f, p_f, phi_f, keep_poles_int
    )

    # Compute radiative heating component separately if decomposed
    if has_decomposed_heating:
        D_rad_separate, _, _, _, _, _, _ = KuoEliassen_module.compute_rhs_components(
            v_mean_f, temp_f, rad_heating_f, vt_eddy_f, vu_eddy_f, p_f, phi_f, keep_poles_int
        )
    else:
        D_rad_separate = np.zeros_like(D_dtcond)

    # Compute DTV heating component separately if provided
    if has_dtv_heating:
        dtv_heating_f = np.asfortranarray(dtv_heating, dtype=np.float32)
        D_dtv_heating, _, _, _, _, _, _ = KuoEliassen_module.compute_rhs_components(
            v_mean_f, temp_f, dtv_heating_f, vt_eddy_f, vu_eddy_f, p_f, phi_f, keep_poles_int
        )
    else:
        D_dtv_heating = np.zeros_like(D_dtcond)

    # Total RHS
    if has_decomposed_heating:
        D_total = D_dtcond + D_rad_separate + D_dtv + D_vt + D_vu + D_x
    else:
        D_total = D_dtcond + D_rad + D_dtv + D_vt + D_vu + D_x

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
    if has_decomposed_heating and has_dtv_heating:
        # Full decomposed mode: latent, radiative, and DTV heating
        rhs_list = [D_dtcond, D_rad_separate,
                    D_dtv_heating, D_dtv, D_vt, D_vu, D_x, D_total]
    elif has_decomposed_heating:
        # Decomposed mode without DTV: latent and radiative
        rhs_list = [D_dtcond, D_rad_separate, D_dtv, D_vt, D_vu, D_x, D_total]
    else:
        # Single heating mode: keep compatibility (D_rad is not used)
        rhs_list = [D_dtcond, D_dtv, D_vt, D_vu, D_x, D_total]

    rhs_vectors = []

    for rhs in rhs_list:
        rhs_flat = rhs[:, j_start:j_end].T.ravel('F')
        rhs_vectors.append(rhs_flat)

    rhs_matrix = np.column_stack(rhs_vectors)

    # Solve using LU decomposition (efficient for multiple RHS)
    lu = splu(L_csc)
    psi_solutions = np.array([lu.solve(rhs_matrix[:, i])
                             for i in range(rhs_matrix.shape[1])]).T

    # Build result dictionary
    result = {}

    if return_components:
        if has_decomposed_heating and has_dtv_heating:
            # Full decomposed heating mode (with DTV)
            result['PSI_latent'] = _reshape_solution(
                psi_solutions[:, 0], nlat_used, nlev)
            result['PSI_rad'] = _reshape_solution(
                psi_solutions[:, 1], nlat_used, nlev)
            result['PSI_dtv_heating'] = _reshape_solution(
                psi_solutions[:, 2], nlat_used, nlev)
            result['PSI_dtv'] = _reshape_solution(
                psi_solutions[:, 3], nlat_used, nlev)
            result['PSI_vt'] = _reshape_solution(
                psi_solutions[:, 4], nlat_used, nlev)
            result['PSI_vu'] = _reshape_solution(
                psi_solutions[:, 5], nlat_used, nlev)
            result['PSI_x'] = _reshape_solution(
                psi_solutions[:, 6], nlat_used, nlev)
        elif has_decomposed_heating:
            # Decomposed heating mode (no DTV)
            result['PSI_latent'] = _reshape_solution(
                psi_solutions[:, 0], nlat_used, nlev)
            result['PSI_rad'] = _reshape_solution(
                psi_solutions[:, 1], nlat_used, nlev)
            result['PSI_dtv'] = _reshape_solution(
                psi_solutions[:, 2], nlat_used, nlev)
            result['PSI_vt'] = _reshape_solution(
                psi_solutions[:, 3], nlat_used, nlev)
            result['PSI_vu'] = _reshape_solution(
                psi_solutions[:, 4], nlat_used, nlev)
            result['PSI_x'] = _reshape_solution(
                psi_solutions[:, 5], nlat_used, nlev)
        else:
            # Single heating mode (backward compatible)
            result['PSI_heating'] = _reshape_solution(
                psi_solutions[:, 0], nlat_used, nlev)
            result['PSI_dtv'] = _reshape_solution(
                psi_solutions[:, 1], nlat_used, nlev)
            result['PSI_vt'] = _reshape_solution(
                psi_solutions[:, 2], nlat_used, nlev)
            result['PSI_vu'] = _reshape_solution(
                psi_solutions[:, 3], nlat_used, nlev)
            result['PSI_x'] = _reshape_solution(
                psi_solutions[:, 4], nlat_used, nlev)

    result['PSI'] = _reshape_solution(
        psi_solutions[:, -1], nlat_used, nlev)  # Total is always last
    result['D'] = D_total

    # Compute QGPV balance terms if requested
    if return_qgpv_balance:
        # Use F_friction already computed from RHS components
        # F_friction = d(u'v'*cos²φ)/dφ / cos²φ - v*f [m/s²]

        # Determine which heating to use for QGPV calculation
        if has_decomposed_heating:
            # Use combined heating for QGPV balance
            if has_dtv_heating:
                Q_total = latent_heating + rad_heating + dtv_heating
            else:
                Q_total = latent_heating + rad_heating
        else:
            Q_total = heating

        Q_total_f = np.asfortranarray(Q_total, dtype=np.float32)
        F_friction_f = np.asfortranarray(F_friction, dtype=np.float32)

        # Call Fortran subroutine to compute QGPV balance terms
        momentum_term, thermal_term = KuoEliassen_module.compute_qgpv_balance_terms(
            temp_f, v_mean_f, F_friction_f, Q_total_f,
            vt_eddy_f, vu_eddy_f, p_f, phi_f
        )

        # Store results
        result['momentum_term'] = momentum_term  # ∂F_total/∂y [s⁻²]
        result['thermal_term'] = thermal_term    # f*(∂Q_θ/∂p)/(∂θ/∂p) [s⁻²]
        result['residual'] = momentum_term - thermal_term  # Residual [s⁻²]

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
    result_base = solve_ke(v_mean, T_mean, vt_mean, vu_mean, p, lat, heating=Q_mean)
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
