! ke_rhs.f90 - Right-hand-side computation for Kuo-Eliassen equation

! ============================================================================
! SUBROUTINE: compute_rhs_components
! ============================================================================
!
! PURPOSE:
!   Computes all 6 right-hand-side (RHS) components (D terms) of the 
!   Kuo-Eliassen (KE) equation in diabatic forcing form.
!
! KUNO-ELIASSEN EQUATION BACKGROUND:
!   The KE equation describes the response of the zonal-mean meridional 
!   mass streamfunction (ψ) to diabatic heating and eddy fluxes. The equation
!   can be written as:
!
!     L(ψ) = D
!
!   where L is a linear Laplacian operator (with static stability weighting)
!   and D is the sum of diabatic forcing terms, eddy momentum flux terms, and eddy heat flux terms.
!
! FULL Kuo-Eliassen Equation:
!
!       f² g   ∂²ψ        S² g    ∂  [   1    ∂ψ   ]
!     ───────────────── + ────── ─────────────────────
!     2π a cosφ ∂p²      2π a   ∂φ  [a cosφ   ∂φ   ]
!
!      R   [  1  ∂Q̄      ∂  {  1    ∂(v'T' cosφ) } ]
!   = ─── [ ─── ──── - ─────────────────────────────  ]
!      p   [  a  ∂φ     ∂φ  [a cosφ    ∂φ      ] ]
!
!        f [   1   ∂²(u'v' cos²φ)       ∂X̄ ]
!     + ── [ ──────────────────────── - ── ]
!       1  [ a cos²φ   ∂p ∂φ            ∂p ]
!
!   LaTeX version:
!   f^2\,\frac{g}{2\pi a\cos\phi}\,\frac{\partial^2\psi}{\partial p^2}
!   + S^2\,\frac{g}{2\pi a}\,\frac{\partial}{\partial\phi}
!     \left[\frac{1}{a\cos\phi}\frac{\partial\psi}{\partial\phi}\right]
!   = \frac{R}{p}\left(\frac{1}{a}\frac{\partial\overline{Q}}{\partial\phi}
!     - \frac{\partial}{\partial\phi}
!       \left[\frac{1}{a\cos\phi}\frac{\partial(\overline{v'T'}\cos\phi)}{\partial\phi}\right]
!     \right)
!     + f\left(\frac{1}{a\cos^2\phi}\frac{\partial^2(\overline{u'v'}\cos^2\phi)}{\partial p\,\partial\phi}
!     - \frac{\partial\overline{X}}{\partial p}\right).
!
!   where:
!     ψ   - zonal-mean meridional mass streamfunction [kg/s]
!     f   - Coriolis parameter [1/s]
!     a   - Earth's radius [m]
!     φ   - latitude [rad]
!     p   - pressure [Pa]
!     S²  = -(1/ρθ) ∂θ/∂p  - static stability [1/s²]
!     Q̄   - diabatic heating rate [K/s]
!     R   - gas constant [J/(kg·K)]
!     v̄'T̄'  - eddy heat flux (meridional wind eddy × temperature eddy) [K·m/s]
!     ūv̄'  - eddy momentum flux (zonal wind eddy × meridional wind eddy) [m²/s²]
!     X̄   - zonal friction term [m/s²]
!     ρ   - air density [kg/m³]
!     θ   - potential temperature [K]
!     ū, v̄ - zonal and meridional mean winds [m/s]
!     Overbars denote zonal means, primes denote deviations
!
! MATHEMATICAL FORM OF RHS COMPONENTS:
!   The full KE equation RHS is:
!
!     D = D_dtcond + D_rad + D_vt + D_vu + D_x
!
!   where each component represents:
!
!     D_dtcond = (R/p) * ∂Q_latent/∂φ
!       - Response to latent heating from condensation
!       - Q_latent: latent heating rate [K/s]
!       - Units: [K/s]
!
!     D_rad = (R/p) * ∂Q_rad/∂φ
!       - Response to radiative heating
!       - Q_rad: radiative heating rate [K/s]
!       - Units: [K/s]
!
!     D_vt = (R/p) * (-∂²(v'T'*cosφ)/∂φ²) / cosφ
!       - Response to eddy heat flux
!       - v'T': meridional wind eddy × temperature eddy [K·m/s]
!       - First compute: VT_cos = v'T' * cos(φ)
!       - Then: ∂VT_cos/∂φ (first meridional gradient)
!       - Finally: ∂/∂φ[∂VT_cos/∂φ / cos(φ)] (second gradient with division)
!       - Units: [K/s]
!
!     D_vu = f * ∂²(u'v'*cos²φ) / (∂φ∂p) / cos²φ
!       - Response to eddy momentum flux
!       - u'v': zonal wind eddy × meridional wind eddy [m²/s²]
!       - First compute: VU_cos = u'v' * cos²(φ)
!       - Then: ∂VU_cos/∂φ (meridional gradient)
!       - Then: ∂/∂p[∂VU_cos/∂φ] (vertical gradient)
!       - Finally: divide by cos²(φ) and multiply by f
!       - Units: [K/s]
!
!     D_x = f * (-∂X/∂p)
!       - Response to mean flow and zonal friction term
!       - X̄ = (1/cos²φ) * ∂(ū'v'*cos²φ)/∂φ - v̄*f
!       - First compute meridional gradient of (u'v'*cos²φ)
!       - Then: X = ∂(u'v'*cos²φ)/∂φ / cos²(φ) - v̄*f
!       - Finally: ∂X/∂p (vertical gradient) and multiply by -f
!       - Units: [K/s]
!
! COMPUTATION ALGORITHM:
!   1. Extract latitude subset (remove poles if keep_poles=0)
!   2. Precompute geometric factors: cos(φ), Coriolis parameter f, cos_safe
!   3. For each RHS component:
!      a) Construct intermediate fields (multiply by geometric factors)
!      b) Compute meridional gradients using central differences
!      c) Compute vertical gradients using centered differences
!      d) Apply scaling factors (R/p, f, etc.)
!      e) Store result in output array
!
! INPUT PARAMETERS:
!   temp(nlev, nlat)     - Temperature [K] on (pressure, latitude) grid
!   u_wind(nlev, nlat)   - u'v' eddy momentum flux or u-wind [m²/s²]
!   v_wind(nlev, nlat)   - v'T' eddy heat flux or v-wind [K·m/s]
!   heating(nlev, nlat)  - Total diabatic heating Q [K/s]
!   p(nlev)              - Pressure levels [Pa] in ascending order
!   phi(nlat)            - Latitude [radians] in ascending order
!   nlev                 - Number of pressure levels
!   nlat                 - Number of latitude points
!   keep_poles           - 0: exclude poles, 1: include all latitudes
!
! OUTPUT PARAMETERS:
!   D_dtcond(nlev, nlat) - Condensation heating forcing component [K/s]
!   D_rad(nlev, nlat)    - Radiative heating forcing component [K/s]
!   D_vt(nlev, nlat)     - Eddy heat flux convergence component [K/s]
!   D_vu(nlev, nlat)     - Eddy momentum flux convergence component [K/s]
!   D_x(nlev, nlat)      - Mean flow and friction component [K/s]
!   F_friction(nlev, nlat) - Friction force term X = d(u'v'*cos²)/dφ / cos² - v̄*f [m/s²]
!
! PHYSICAL CONSTANTS:
!   R_gas = 287.0 J/(kg·K)   - Specific gas constant for dry air
!   omega = 7.292e-5 rad/s   - Earth's rotation rate
!   a_earth = 6.371e6 m      - Earth's radius
!   eps_cos = 1.0e-6         - Minimum cosine value (avoid poles singularity)
!
! NOTES:
!   - All arrays use (nlev, nlat) layout (Fortran column-major)
!   - Gradient computation uses centered differences in interior,
!     forward/backward differences at boundaries
!   - Pole treatment: keep_poles=0 excludes 3 latitudes at each pole
!   - Implementation follows Python solve_KE_equation.py exactly
!
! ============================================================================
subroutine compute_rhs_components(v_mean, temp, latent_heating, rad_heating, vt_eddy, vu_eddy, &
                                  p, phi, nlev, nlat, keep_poles, &
                                  D_dtcond, D_rad, D_vt, D_vu, D_x, F_friction)
    implicit none
    integer, intent(in) :: nlev, nlat, keep_poles
    real(kind=8), intent(in) :: v_mean(nlev, nlat), temp(nlev, nlat)
    real(kind=8), intent(in) :: latent_heating(nlev, nlat), rad_heating(nlev, nlat)
    real(kind=8), intent(in) :: vt_eddy(nlev, nlat)
    real(kind=8), intent(in) :: vu_eddy(nlev, nlat)
    real(kind=8), intent(in) :: p(nlev), phi(nlat)
    real(kind=8), intent(out) :: D_dtcond(nlev, nlat), D_rad(nlev, nlat)
    real(kind=8), intent(out) :: D_vt(nlev, nlat)
    real(kind=8), intent(out) :: D_vu(nlev, nlat), D_x(nlev, nlat)
    real(kind=8), intent(out) :: F_friction(nlev, nlat)

    ! Physical constants
    real(kind=8), parameter :: R_gas = 287.0d0
    real(kind=8), parameter :: a_earth = 6.371d6
    real(kind=8), parameter :: omega = 7.292d-5
    real(kind=8), parameter :: eps_cos = 1.0d-6

    ! Local variables
    integer :: k, j, j_idx
    real(kind=8) :: cos_phi, f_coriolis, cos_safe_val
    real(kind=8), allocatable :: dQ_dphi(:,:), cos_array(:,:), cos_safe(:,:)
    real(kind=8), allocatable :: f_array(:,:), VT_cos(:,:), VU_cos(:,:)
    real(kind=8), allocatable :: dvt_dlat(:,:), dvt_dlat_over_cos(:,:), dd_vt_lat(:,:)
    real(kind=8), allocatable :: dvu_dlat(:,:), dd_vu_p(:,:)
    real(kind=8), allocatable :: X(:,:), dX_dp(:,:)

    ! Allocate work arrays (nlev, nlat)
    allocate(dQ_dphi(nlev, nlat))
    allocate(cos_array(nlev, nlat), cos_safe(nlev, nlat), f_array(nlev, nlat))
    allocate(VT_cos(nlev, nlat), VU_cos(nlev, nlat))
    allocate(dvt_dlat(nlev, nlat), dvt_dlat_over_cos(nlev, nlat), dd_vt_lat(nlev, nlat))
    allocate(dvu_dlat(nlev, nlat), dd_vu_p(nlev, nlat))
    allocate(X(nlev, nlat), dX_dp(nlev, nlat))

    ! Initialize outputs to zero
    D_dtcond = 0.0d0
    D_rad = 0.0d0
    D_vt = 0.0d0
    D_vu = 0.0d0
    D_x = 0.0d0
    F_friction = 0.0d0

    ! ========================================================================
    ! Compute geometric arrays: cos(φ) and f
    ! ========================================================================
    do j = 1, nlat
        cos_phi = cos(phi(j))
        f_coriolis = 2.0d0 * omega * sin(phi(j))
        
        ! Safe cos for division (avoid singularity at poles)
        if (abs(cos_phi) < eps_cos) then
            cos_safe_val = sign(eps_cos, cos_phi)
        else
            cos_safe_val = cos_phi
        end if
        
        do k = 1, nlev
            cos_array(k, j) = cos_phi
            cos_safe(k, j) = cos_safe_val
            f_array(k, j) = f_coriolis
        end do
    end do

    ! ========================================================================
    ! Component 1-2: Heating terms (D_dtcond, D_rad)
    ! D = (R/p) * dQ/dφ
    ! ========================================================================
    
    ! D_dtcond: latent heating component
    call meridional_gradient_2d(latent_heating, phi, a_earth, nlev, nlat, dQ_dphi)
    do j = 1, nlat
        do k = 1, nlev
            D_dtcond(k, j) = (R_gas / p(k)) * dQ_dphi(k, j)
        end do
    end do
    
    ! D_rad: radiative heating component
    call meridional_gradient_2d(rad_heating, phi, a_earth, nlev, nlat, dQ_dphi)
    do j = 1, nlat
        do k = 1, nlev
            D_rad(k, j) = (R_gas / p(k)) * dQ_dphi(k, j)
        end do
    end do

    ! ========================================================================
    ! Component 4: Eddy heat flux term (D_vt)
    ! D_vt = (R/p) * (-d²(v'T'*cos)/dφ²) / cos
    ! Python: VT_cos = VT_np * cos_array
    !         dvt_dlat = meridional_gradient(VT_cos, ...)
    !         dd_vt_lat = meridional_gradient(dvt_dlat / cos_safe, ...)
    !         D_vt = (R/p) * (-dd_vt_lat)
    ! ========================================================================
    
    ! VT_cos = vt_eddy * cos(φ)
    do j = 1, nlat
        do k = 1, nlev
            VT_cos(k, j) = vt_eddy(k, j) * cos_array(k, j)
        end do
    end do
    
    ! First derivative: d(VT*cos)/dφ
    call meridional_gradient_2d(VT_cos, phi, a_earth, nlev, nlat, dvt_dlat)
    
    ! Divide by cos: dvt_dlat / cos
    do j = 1, nlat
        do k = 1, nlev
            dvt_dlat_over_cos(k, j) = dvt_dlat(k, j) / cos_safe(k, j)
        end do
    end do
    
    ! Second derivative: d²/dφ²
    call meridional_gradient_2d(dvt_dlat_over_cos, phi, a_earth, nlev, nlat, dd_vt_lat)
    
    ! D_vt = (R/p) * (-dd_vt_lat)
    do j = 1, nlat
        do k = 1, nlev
            D_vt(k, j) = -(R_gas / p(k)) * dd_vt_lat(k, j)
        end do
    end do

    ! ========================================================================
    ! Component 5: Eddy momentum flux term (D_vu)
    ! D_vu = f * d²(u'v'*cos²)/dφdp / cos²
    ! Python: VU_cos = VU_np * (cos_array**2)
    !         dvu_dlat = meridional_gradient(VU_cos, ...)
    !         dd_vu_p = vertical_gradient(dvu_dlat, p) / (cos_safe**2)
    !         D_vu = f_array * dd_vu_p
    ! ========================================================================
    
    ! VU_cos = vu_eddy * cos²(φ)
    do j = 1, nlat
        do k = 1, nlev
            VU_cos(k, j) = vu_eddy(k, j) * cos_array(k, j)**2
        end do
    end do
    
    ! First derivative: d(VU*cos²)/dφ
    call meridional_gradient_2d(VU_cos, phi, a_earth, nlev, nlat, dvu_dlat)
    
    ! Second derivative: d/dp
    call vertical_gradient_2d(dvu_dlat, p, nlev, nlat, dd_vu_p)
    
    ! Divide by cos² and multiply by f
    do j = 1, nlat
        do k = 1, nlev
            D_vu(k, j) = f_array(k, j) * dd_vu_p(k, j) / (cos_safe(k, j)**2)
        end do
    end do

    ! ========================================================================
    ! Component 6: Mean flow term (D_x)
    ! D_x = f * (-dX/dp)
    ! where X = d(u'v'*cos²)/dφ / cos² - v * f
    ! Python: X = dvu_dlat / (cos_safe**2) - V_np * f_array
    !         dX_dp = vertical_gradient(X, p)
    !         D_x = f_array * (-dX_dp)
    ! ========================================================================
    
    ! X = dvu_dlat / cos² - v_mean * f
    do j = 1, nlat
        do k = 1, nlev
            X(k, j) = dvu_dlat(k, j) / (cos_safe(k, j)**2) - &
                      v_mean(k, j) * f_array(k, j)
        end do
    end do
    
    ! Store F_friction (this is X, the friction force term)
    F_friction = X
    
    ! dX/dp
    call vertical_gradient_2d(X, p, nlev, nlat, dX_dp)
    
    ! D_x = f * (-dX/dp)
    do j = 1, nlat
        do k = 1, nlev
            D_x(k, j) = -f_array(k, j) * dX_dp(k, j)
        end do
    end do

    ! Clean up
    deallocate(dQ_dphi, cos_array, cos_safe, f_array)
    deallocate(VT_cos, VU_cos, dvt_dlat, dvt_dlat_over_cos, dd_vt_lat)
    deallocate(dvu_dlat, dd_vu_p, X, dX_dp)


end subroutine compute_rhs_components
