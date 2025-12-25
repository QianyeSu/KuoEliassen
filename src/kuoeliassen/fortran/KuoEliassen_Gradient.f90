! ==============================================================================
! KuoEliassen_Gradient.f90 - Gradient computation subroutines
! ==============================================================================
!
! Author:  Qianye Su
! Email:   suqianye2000@gmail.com
! Created: 2025/11/13 0:05
!
! DESCRIPTION:
!   These subroutines compute spatial derivatives used in the Kuo-Eliassen
!   equation solver. They support both 1D and 2D field operations with
!   proper boundary condition handling.
! ==============================================================================

! ============================================================================
! SUBROUTINE: vertical_gradient
! ============================================================================
!
! PURPOSE:
!   Computes the vertical gradient (derivative with respect to pressure)
!   of a 1D atmospheric field using centered finite differences.
!
! MATHEMATICAL DESCRIPTION:
!   For a field F(p) on pressure levels, compute ∂F/∂p using:
!
!     ∂F/∂p|_k ≈ (F_{k+1} - F_{k-1}) / (p_{k+1} - p_{k-1})    [interior]
!     ∂F/∂p|_1 ≈ (F_2 - F_1) / (p_2 - p_1)                     [top - forward]
!     ∂F/∂p|_N ≈ (F_N - F_{N-1}) / (p_N - p_{N-1})             [bottom - backward]
!
!   Pressure typically increases with depth (ascending order): p_1 < p_2 < ... < p_N
!
! ALGORITHM:
!   1. Top level (k=1): Forward difference
!   2. Interior levels (2 ≤ k ≤ N-1): Central difference
!   3. Bottom level (k=N): Backward difference
!
! INPUT PARAMETERS:
!   field(nlev)  - 1D field values at pressure levels [arbitrary units]
!   p(nlev)      - Pressure levels [Pa], ascending order
!   nlev         - Number of pressure levels
!
! OUTPUT PARAMETERS:
!   grad(nlev)   - Vertical gradient ∂field/∂p [units/(Pa)]
!
! PRECISION:
!   - Central difference: O(Δp²) truncation error
!   - Forward/backward difference: O(Δp) truncation error
!
! NOTES:
!   - Assumes uniform or near-uniform pressure spacing
!   - No handling of missing/NaN values
!
! ============================================================================
subroutine vertical_gradient(field, p, nlev, grad)
    implicit none
    integer, intent(in) :: nlev
    real(kind=8), intent(in) :: field(nlev), p(nlev)
    real(kind=8), intent(out) :: grad(nlev)
    
    integer :: k
    real(kind=8) :: dp_down, dp_up
    
    ! Forward difference at top (k=1)
    dp_down = p(2) - p(1)
    grad(1) = (field(2) - field(1)) / dp_down
    
    ! Centered difference in interior
    do k = 2, nlev - 1
        dp_up = p(k) - p(k-1)
        dp_down = p(k+1) - p(k)
        grad(k) = (field(k+1) - field(k-1)) / (dp_up + dp_down)
    end do
    
    ! Backward difference at bottom (k=nlev)
    dp_up = p(nlev) - p(nlev-1)
    grad(nlev) = (field(nlev) - field(nlev-1)) / dp_up
    
end subroutine vertical_gradient


! ============================================================================
! SUBROUTINE: meridional_gradient_coeff
! ============================================================================
!
! PURPOSE:
!   Computes the spacing (difference) array for latitude coordinates,
!   equivalent to NumPy's np.diff function. This is a preprocessing step
!   for finite difference calculations in the meridional direction.
!
! MATHEMATICAL DESCRIPTION:
!   Given latitude array φ = [φ₁, φ₂, ..., φₙ], compute:
!
!     dphi[i] = φ_{i+1} - φ_i    for i = 1 to (nlat-1)
!     dphi[nlat] = dphi[nlat-1]  [copy last value]
!
!   This is equivalent to: dphi = np.diff(phi, append=phi[-1])
!
! USAGE:
!   These spacing values are used in:
!   - Meridional gradient calculations (∂/∂φ)
!   - Metric factor computations (distance = Δφ × radius)
!   - Finite difference stencil construction
!
! INPUT PARAMETERS:
!   phi(nlat)    - Latitude coordinates [radians]
!                  Usually: φ ∈ [-π/2, π/2] in ascending order
!   nlat         - Number of latitude points
!
! OUTPUT PARAMETERS:
!   dphi_array(nlat) - Latitude spacing [radians]
!                      dphi_array[i] = phi[i+1] - phi[i]
!
! ALGORITHM:
!   1. For i = 1 to (nlat-1): compute differences
!   2. For i = nlat: copy last difference value (boundary condition)
!
! NOTES:
!   - Output length equals input length (for compatibility with broadcasting)
!   - Last element is repeated (one-sided difference at boundary)
!   - Typically used before meridional_gradient_2d computation
!
! ============================================================================
subroutine meridional_gradient_coeff(phi, nlat, dphi_array)
    implicit none
    integer, intent(in) :: nlat
    real(kind=8), intent(in) :: phi(nlat)
    real(kind=8), intent(out) :: dphi_array(nlat)
    
    integer :: j
    
    ! Spacing array: dphi_array(i) = phi(i+1) - phi(i), similar to np.diff
    do j = 1, nlat - 1
        dphi_array(j) = phi(j+1) - phi(j)
    end do
    dphi_array(nlat) = dphi_array(nlat-1)  ! Copy last
    
end subroutine meridional_gradient_coeff


! ============================================================================
! SUBROUTINE: meridional_gradient_2d
! ============================================================================
!
! PURPOSE:
!   Computes the meridional gradient (∂/∂y or ∂/∂φ) of a 2D atmospheric field
!   on a latitude-pressure grid. This is a fundamental operation in the
!   Kuo-Eliassen equation solver.
!
! MATHEMATICAL DESCRIPTION:
!   For a 2D field F(φ, p), compute ∂F/∂y where y = a·φ·cos(latitude):
!
!     ∂F/∂φ = dF/d(latitude)  [pure meridional gradient]
!     dy = Δφ × radius × cos(φ)
!     ∂F/∂y = ∂F/∂φ / dy
!
!   Using centered differences:
!
!     ∂F/∂φ|_i ≈ (F_{i+1} - F_{i-1}) / (φ_{i+1} - φ_{i-1})   [interior]
!     ∂F/∂φ|_1 ≈ (F_2 - F_1) / (φ_2 - φ_1)                   [south pole - forward]
!     ∂F/∂φ|_N ≈ (F_N - F_{N-1}) / (φ_N - φ_{N-1})           [north pole - backward]
!
! ALGORITHM:
!   1. For each latitude point i and pressure level j:
!      - If i = 1 (south pole): forward difference
!      - If i = nlat (north pole): backward difference
!      - Otherwise (interior): central difference
!   2. Divide by meridional distance: Δy = (Δφ_forward + Δφ_backward) × radius
!   3. Handle metric terms (cos factors already included in distance calculation)
!
! INPUT PARAMETERS:
!   field(nlev, nlat)  - 2D atmospheric field [arbitrary units]
!                        Shape: (number of pressure levels, number of latitudes)
!   phi(nlat)          - Latitude coordinates [radians]
!   radius             - Earth's radius [meters], typically 6.371e6 m
!   nlev               - Number of pressure levels
!   nlat               - Number of latitude points
!
! OUTPUT PARAMETERS:
!   grad(nlev, nlat)   - Meridional gradient ∂field/∂y [units/meter]
!
! APPLICATIONS IN KE EQUATION:
!   - Heating gradient: ∂Q/∂φ (D_dtcond component)
!   - Eddy heat flux: ∂(v'T')/∂φ (D_vt component)
!   - Eddy momentum flux: ∂(u'v')/∂φ (D_vu component)
!
! PRECISION:
!   - Central difference: O(Δφ²) truncation error
!   - Forward/backward: O(Δφ) truncation error
!
! NOTES:
!   - Output shape matches input shape
!   - Pole handling ensures smooth behavior near singularities
!   - Metric factors (cosine weighting) should be applied to field before gradient
!
! ============================================================================
subroutine meridional_gradient_2d(field, phi, radius, nlev, nlat, grad)
    implicit none
    integer, intent(in) :: nlev, nlat
    real(kind=8), intent(in) :: field(nlev, nlat), phi(nlat), radius
    real(kind=8), intent(out) :: grad(nlev, nlat)

    integer :: k, j
    real(kind=8) :: dphi_forward, dphi_backward, dy

    ! Compute gradients for all points using centered/forward/backward differences
    do j = 1, nlat
        do k = 1, nlev
            if (j == 1) then
                ! Forward difference at south pole
                dphi_forward = phi(2) - phi(1)
                dy = dphi_forward * radius
                grad(k, j) = (field(k, 2) - field(k, 1)) / dy
            else if (j == nlat) then
                ! Backward difference at north pole
                dphi_backward = phi(nlat) - phi(nlat-1)
                dy = dphi_backward * radius
                grad(k, j) = (field(k, nlat) - field(k, nlat-1)) / dy
            else
                ! Central difference in interior
                dphi_forward = phi(j+1) - phi(j)
                dphi_backward = phi(j) - phi(j-1)
                dy = (dphi_forward + dphi_backward) * radius
                grad(k, j) = (field(k, j+1) - field(k, j-1)) / dy
            end if
        end do
    end do

end subroutine meridional_gradient_2d


! ============================================================================
! SUBROUTINE: vertical_gradient_2d
! ============================================================================
!
! PURPOSE:
!   Computes the vertical gradient (∂/∂p) of a 2D atmospheric field on a
!   latitude-pressure grid. This is a wrapper that applies the 1D vertical_gradient
!   subroutine to each latitude column independently.
!
! MATHEMATICAL DESCRIPTION:
!   For a 2D field F(p, φ), compute ∂F/∂p at each latitude:
!
!     For each latitude j:
!       ∂F(p,φ_j)/∂p = vertical_gradient(F(:,j), p, nlev)
!
!   Using the same centered difference scheme as vertical_gradient:
!
!     ∂F/∂p|_k ≈ (F_{k+1} - F_{k-1}) / (p_{k+1} - p_{k-1})    [interior]
!     ∂F/∂p|_1 ≈ (F_2 - F_1) / (p_2 - p_1)                     [top]
!     ∂F/∂p|_N ≈ (F_N - F_{N-1}) / (p_N - p_{N-1})             [bottom]
!
! ALGORITHM:
!   1. For each latitude column j = 1 to nlat:
!      a) Extract 1D column: field_1d = field(:, j)
!      b) Call vertical_gradient(field_1d, p, nlev, grad_1d)
!      c) Store result: grad(:, j) = grad_1d
!   2. All columns processed independently
!
! INPUT PARAMETERS:
!   field(nlev, nlat)  - 2D atmospheric field [arbitrary units]
!                        Shape: (number of pressure levels, number of latitudes)
!   p(nlev)            - Pressure levels [Pa], ascending order
!   nlev               - Number of pressure levels
!   nlat               - Number of latitude points
!
! OUTPUT PARAMETERS:
!   grad(nlev, nlat)   - Vertical gradient ∂field/∂p [units/(Pa)]
!                        Same shape as input field
!
! APPLICATIONS IN KE EQUATION:
!   - Static stability: ∂θ/∂p (for L-operator computation)
!   - Eddy vertical flux convergence: ∂(∂u'v'∂φ)/∂p (D_vu component)
!   - Mean flow term: ∂X/∂p (D_x component)
!
! PRECISION:
!   - Inherits from vertical_gradient subroutine
!   - Central difference: O(Δp²)
!   - Forward/backward: O(Δp)
!
! IMPLEMENTATION NOTES:
!   - This is a 2D wrapper around the 1D vertical_gradient routine
!   - Each latitude column is processed independently
!   - This design avoids code duplication and maintains consistency
!   - Output shape exactly matches input shape (nlev, nlat)
!
! ============================================================================
subroutine vertical_gradient_2d(field, p, nlev, nlat, grad)
    implicit none
    integer, intent(in) :: nlev, nlat
    real(kind=8), intent(in) :: field(nlev, nlat), p(nlev)
    real(kind=8), intent(out) :: grad(nlev, nlat)

    integer :: j
    
    ! Apply 1D vertical gradient to each latitude column
    do j = 1, nlat
        call vertical_gradient(field(:, j), p, nlev, grad(:, j))
    end do

end subroutine vertical_gradient_2d
