! ==============================================================================
! KuoEliassen_QGPV_Balance.f90 - QGPV balance diagnostic terms
! ==============================================================================
!
! Author:  Qianye Su
! Email:   suqianye2000@gmail.com
! Created: 2025/11/13 21:35
!
! DESCRIPTION:
!   Computes diagnostic terms for analyzing steady-state zonal-mean
!   Quasi-Geostrophic Potential Vorticity (QGPV) balance.
! ==============================================================================

! ============================================================================
! SUBROUTINE: compute_QGPV_balance_terms
! ============================================================================
!
! PURPOSE:
!   Computes the Momentum Term and Thermal Term for diagnosing steady-state
!   zonal-mean Quasi-Geostrophic Potential Vorticity (QGPV) balance.
!
! THEORETICAL BACKGROUND:
!   In steady state, the QGPV balance equation can be written as:
!
!     ∂F_total/∂y ≈ f * (∂Q_total_θ/∂p) / (∂θ/∂p)
!
!   where:
!     - LHS is the "Momentum Term"
!     - RHS is the "Thermal Term" (Diabatic Term)
!     - Residual = LHS - RHS should be ~0 in perfect balance
!
! THEORY: Z to P COORDINATE TRANSFORMATION
!   The original QGPV balance equation from Held's paper is in height (z) coordinates:
!
!     ∂F/∂y = (f/N²) * ∂Q_buoyancy/∂z         (Eq. Z)
!
!   To use this with pressure-coordinate model data, we must transform each
!   term on the RHS from z- to p-coordinates.
!
!   1. KEY RELATIONSHIPS:
!      - Hydrostatic Balance: ∂p/∂z = -ρg
!      - Chain Rule for derivatives: ∂/∂z = (∂p/∂z)(∂/∂p) = -ρg * ∂/∂p
!
!   2. TRANSFORMING N² (Static Stability):
!      - Definition in z-coords: N² = (g/θ) * ∂θ/∂z
!      - Substituting ∂/∂z: N² = (g/θ) * (-ρg * ∂θ/∂p) = - (g²ρ/θ) * ∂θ/∂p
!
!   3. TRANSFORMING Q_buoyancy (Buoyancy Forcing):
!      - The buoyancy forcing Q_buoyancy [m/s³] is related to the diabatic
!        heating rate in potential temperature, Q_θ [K/s].
!      - Buoyancy B is defined as B = (g/θ)θ.
!      - The forcing term is the material derivative: Q_buoyancy = dB/dt = (g/θ) * dθ/dt
!      - Therefore: Q_buoyancy = (g/θ) * Q_θ
!
!   4. COMBINING AND SIMPLIFYING THE RHS:
!      - Start with the RHS of Eq. Z: (f/N²) * ∂Q_buoyancy/∂z
!      - Substitute all transformed terms:
!        = [ f / (-(g²ρ/θ) * ∂θ/∂p) ] * [-ρg * ∂/∂p] * [ (g/θ) * Q_θ ]
!
!      - The two negative signs cancel out.
!      - We can rearrange and cancel terms (assuming g/θ is slowly varying):
!        = [ (f * θ) / (g²ρ * ∂θ/∂p) ] * [ ρg * (g/θ) * ∂Q_θ/∂p ]
!
!      - Canceling ρ, g², and θ from numerator and denominator leaves:
!        = ( f * ∂Q_θ/∂p ) / ( ∂θ/∂p )
!
!   This yields the final equation in pressure coordinates, which is implemented
!   in this subroutine. The 'F' and 'Q' terms are further expanded to
!   include both mean and eddy components as described below.
!
! MOMENTUM TERM (LHS):
!   F_total = F_friction - ∂[u'v']/∂y
!   
!   Momentum Term = ∂F_total/∂y = ∂F_friction/∂y - ∂²[u'v']/∂y²
!
!   Steps:
!   1. Compute F_total = F_friction - ∂[u'v'*cos²φ]/∂φ / cos²φ
!   2. Compute ∂F_total/∂y using meridional gradient
!
! THERMAL TERM (RHS):
!   Q_total_θ = (θ/T) * (Q_diabatic - ∂[v'T']/∂y)
!   
!   Thermal Term = f * (∂Q_total_θ/∂p) / (∂θ/∂p)
!
!   Steps:
!   1. Compute potential temperature θ = T * (P0/P)^(R/cp)
!   2. Compute ∂[v'T'*cosφ]/∂φ / cosφ (eddy heat flux convergence)
!   3. Compute Q_total_θ = (θ/T) * (Q_diabatic - eddy_heat_conv)
!   4. Compute ∂θ/∂p (static stability)
!   5. Compute ∂Q_total_θ/∂p
!   6. Thermal Term = f * (∂Q_total_θ/∂p) / (∂θ/∂p)
!
! INPUT PARAMETERS:
!   temp(nlev, nlat)        - Temperature [K]
!   v_mean(nlev, nlat)      - Mean meridional wind [m/s]
!   F_friction(nlev, nlat)  - Friction forcing [m/s²]
!   Q_diabatic(nlev, nlat)  - Diabatic heating rate [K/s]
!   vt_eddy(nlev, nlat)     - Eddy heat flux v'T' [K·m/s]
!   vu_eddy(nlev, nlat)     - Eddy momentum flux u'v' [m²/s²]
!   p(nlev)                 - Pressure levels [Pa]
!   phi(nlat)               - Latitude [radians]
!   nlev                    - Number of pressure levels
!   nlat                    - Number of latitude points
!
! OUTPUT PARAMETERS:
!   momentum_term(nlev, nlat) - ∂F_total/∂y [s⁻²]
!   thermal_term(nlev, nlat)  - f*(∂Q_θ/∂p)/(∂θ/∂p) [s⁻²]
!
! NOTES:
!   - This subroutine uses meridional_gradient_2d and vertical_gradient_2d
!     from KuoEliassen_gradient.f90
!   - All computations follow the ETM (Eulerian-mean) framework
!   - Follows the methodology from test_KE_Held_v2.py
! 
! References
!   Held, I. M. & Zurita-Gotor, P. (2025). Misuse of Kuo–Eliassen Equation in Studies of the
!   Climatological Mean Meridional Circulation. Journal of the Atmospheric Sciences, 82,
!   1765–1766.
!   This implementation follows the diagnostic approach used in Held's methodology and
!   takes into account the cautions discussed by Held & Zurita-Gotor (2025).
!
! ============================================================================
subroutine compute_QGPV_balance_terms(temp, v_mean, F_friction, Q_diabatic, &
                                      vt_eddy, vu_eddy, p, phi, nlev, nlat, &
                                      momentum_term, thermal_term)
    use, intrinsic :: ieee_arithmetic, only: ieee_value, ieee_quiet_nan
    implicit none
    integer, intent(in) :: nlev, nlat
    real(kind=8), intent(in) :: temp(nlev, nlat), v_mean(nlev, nlat)
    real(kind=8), intent(in) :: F_friction(nlev, nlat), Q_diabatic(nlev, nlat)
    real(kind=8), intent(in) :: vt_eddy(nlev, nlat), vu_eddy(nlev, nlat)
    real(kind=8), intent(in) :: p(nlev), phi(nlat)
    real(kind=8), intent(out) :: momentum_term(nlev, nlat), thermal_term(nlev, nlat)

    ! Physical constants
    real(kind=8), parameter :: R_gas = 287.047d0      ! J/(kg·K)
    real(kind=8), parameter :: c_p = 1004.6d0         ! J/(kg·K)
    real(kind=8), parameter :: a_earth = 6.371d6      ! m
    real(kind=8), parameter :: omega = 7.292d-5       ! rad/s
    real(kind=8), parameter :: P0 = 100000.0d0        ! Pa (reference pressure)
    real(kind=8), parameter :: eps_cos = 1.0d-6
    real(kind=8), parameter :: eps_dtheta = 1.0d-12   ! Avoid division by zero
    real(kind=8), parameter :: POLAR_THRESHOLD = 1.5533430342749532d0  ! 89 degrees in radians

    ! Local variables
    integer :: k, j
    real(kind=8) :: cos_phi, f_coriolis, cos_safe_val, kappa, nan_val
    real(kind=8), allocatable :: cos_array(:,:), cos_safe(:,:), f_array(:,:)
    real(kind=8), allocatable :: theta(:,:), dtheta_dp(:,:)
    real(kind=8), allocatable :: VT_cos(:,:), dvt_dlat(:,:), eddy_heat_conv(:,:)
    real(kind=8), allocatable :: VU_cos(:,:), dvu_dlat(:,:), eddy_mom_conv(:,:)
    real(kind=8), allocatable :: F_total(:,:), dF_total_dy(:,:)
    real(kind=8), allocatable :: Q_total_theta(:,:), dQ_theta_dp(:,:)

    ! Allocate arrays
    allocate(cos_array(nlev, nlat), cos_safe(nlev, nlat), f_array(nlev, nlat))
    allocate(theta(nlev, nlat), dtheta_dp(nlev, nlat))
    allocate(VT_cos(nlev, nlat), dvt_dlat(nlev, nlat), eddy_heat_conv(nlev, nlat))
    allocate(VU_cos(nlev, nlat), dvu_dlat(nlev, nlat), eddy_mom_conv(nlev, nlat))
    allocate(F_total(nlev, nlat), dF_total_dy(nlev, nlat))
    allocate(Q_total_theta(nlev, nlat), dQ_theta_dp(nlev, nlat))

    ! Initialize outputs
    momentum_term = 0.0d0
    thermal_term = 0.0d0

    ! Compute κ = R/cp
    kappa = R_gas / c_p
    
    ! Create NaN value using IEEE arithmetic for polar masking
    nan_val = ieee_value(nan_val, ieee_quiet_nan)

    ! ========================================================================
    ! Precompute geometric factors
    ! ========================================================================
    do j = 1, nlat
        cos_phi = cos(phi(j))
        f_coriolis = 2.0d0 * omega * sin(phi(j))
        
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
    ! PART 1: MOMENTUM TERM = ∂F_total/∂y
    ! ========================================================================
    
    ! Step 1: Compute eddy momentum flux convergence: -∂[u'v']/∂y
    ! VU_cos = u'v' * cos²(φ)
    do j = 1, nlat
        do k = 1, nlev
            VU_cos(k, j) = vu_eddy(k, j) * cos_array(k, j)**2
        end do
    end do
    
    ! Compute ∂(VU*cos²)/∂φ
    call meridional_gradient_2d(VU_cos, phi, a_earth, nlev, nlat, dvu_dlat)
    
    ! Eddy momentum flux convergence = -∂[u'v']/∂y = -∂(VU*cos²)/∂φ / cos²
    do j = 1, nlat
        do k = 1, nlev
            eddy_mom_conv(k, j) = -dvu_dlat(k, j) / (cos_safe(k, j)**2)
        end do
    end do
    
    ! Step 2: Compute F_total = F_friction + eddy_mom_conv
    ! (Note: eddy_mom_conv already has the negative sign)
    do j = 1, nlat
        do k = 1, nlev
            F_total(k, j) = F_friction(k, j) + eddy_mom_conv(k, j)
        end do
    end do
    
    ! Step 3: Compute ∂F_total/∂y
    call meridional_gradient_2d(F_total, phi, a_earth, nlev, nlat, dF_total_dy)
    
    ! Store Momentum Term
    momentum_term = dF_total_dy

    ! ========================================================================
    ! PART 2: THERMAL TERM = f * (∂Q_total_θ/∂p) / (∂θ/∂p)
    ! ========================================================================
    
    ! Step 1: Compute potential temperature θ = T * (P0/P)^κ
    do j = 1, nlat
        do k = 1, nlev
            theta(k, j) = temp(k, j) * ((P0 / p(k)) ** kappa)
        end do
    end do
    
    ! Step 2: Compute eddy heat flux convergence: -∂[v'T']/∂y
    ! VT_cos = v'T' * cos(φ)
    do j = 1, nlat
        do k = 1, nlev
            VT_cos(k, j) = vt_eddy(k, j) * cos_array(k, j)
        end do
    end do
    
    ! Compute ∂(VT*cos)/∂φ
    call meridional_gradient_2d(VT_cos, phi, a_earth, nlev, nlat, dvt_dlat)
    
    ! Eddy heat flux convergence = -∂[v'T']/∂y = -∂(VT*cos)/∂φ / cos
    do j = 1, nlat
        do k = 1, nlev
            eddy_heat_conv(k, j) = -dvt_dlat(k, j) / cos_safe(k, j)
        end do
    end do
    
    ! Step 3: Compute Q_total_θ = (θ/T) * (Q_diabatic + eddy_heat_conv)
    ! Note: eddy_heat_conv = -∂[v'T']/∂y, so we add it
    do j = 1, nlat
        do k = 1, nlev
            Q_total_theta(k, j) = (theta(k, j) / temp(k, j)) * &
                                  (Q_diabatic(k, j) + eddy_heat_conv(k, j))
        end do
    end do
    
    ! Step 4: Compute ∂θ/∂p (static stability)
    call vertical_gradient_2d(theta, p, nlev, nlat, dtheta_dp)
    
    ! Step 5: Compute ∂Q_total_θ/∂p
    call vertical_gradient_2d(Q_total_theta, p, nlev, nlat, dQ_theta_dp)
    
    ! Step 6: Thermal Term = f * (∂Q_θ/∂p) / (∂θ/∂p)
    do j = 1, nlat
        do k = 1, nlev
            ! Avoid division by zero in static stability
            if (abs(dtheta_dp(k, j)) < eps_dtheta) then
                thermal_term(k, j) = 0.0d0
            else
                thermal_term(k, j) = f_array(k, j) * dQ_theta_dp(k, j) / dtheta_dp(k, j)
            end if
        end do
    end do

    ! ========================================================================
    ! Post-processing: Set polar region terms to NaN
    ! ========================================================================
    ! Quasi-geostrophic theory breaks down near poles, so mask regions
    ! where |latitude| > 89.8 degrees
    do j = 1, nlat
        if (abs(phi(j)) > POLAR_THRESHOLD) then
            momentum_term(:, j) = nan_val
            thermal_term(:, j) = nan_val
        end if
    end do

    ! Clean up
    deallocate(cos_array, cos_safe, f_array)
    deallocate(theta, dtheta_dp)
    deallocate(VT_cos, dvt_dlat, eddy_heat_conv)
    deallocate(VU_cos, dvu_dlat, eddy_mom_conv)
    deallocate(F_total, dF_total_dy)
    deallocate(Q_total_theta, dQ_theta_dp)

end subroutine compute_QGPV_balance_terms

