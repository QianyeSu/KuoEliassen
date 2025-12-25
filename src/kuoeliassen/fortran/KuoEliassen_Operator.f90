! ==============================================================================
! KuoEliassen_Operator.f90 - Sparse matrix operator assembly
! ==============================================================================
!
! Author:  Qianye Su
! Email:   suqianye2000@gmail.com
! Created: 2025/11/14 17:27
!
! DESCRIPTION:
!   Assembles the sparse matrix operator (L-operator) for the Kuo-Eliassen
!   equation in coordinate (COO) sparse matrix format.
!   Data layout: (nlev, nlat) in Fortran, but matrix indexed as (lat, lev)
!   like Python implementation.
! ==============================================================================

! ============================================================================
! SUBROUTINE: build_ke_operator_coo
! ============================================================================
! PURPOSE:
!   Assembles the sparse matrix operator (L-operator) for the Kuo-Eliassen
!   equation in coordinate (COO) sparse matrix format.
!
! PHYSICS DESCRIPTION:
!   The Kuo-Eliassen equation is:
!     ∇²ψ = D (Laplacian of streamfunction = all forcing)
!
!   The L-operator discretizes the Laplacian with:
!     L_ψ = -∂²ψ/∂p² * m_dp - ∂²ψ/∂y² * m_dlat
!   where:
!     m_dp  = g*f² / (2π*R*cosφ)    [pressure-direction operator coefficient]
!     m_dlat = S²*g / (2π*R²)        [meridional-direction operator coefficient]
!     S² = -(1/ρθ) * ∂θ/∂p           [static stability in potential temperature]
!
! ALGORITHM:
!   1. Extract latitude subset (remove poles if keep_poles=0)
!   2. Precompute spacing arrays: dp1, dp2 (pressure), dlat1, dlat2 (latitude)
!   3. Compute potential temperature θ and density ρ from input temperature T
!   4. Compute vertical derivative ∂θ/∂p using centered differences
!   5. Loop over all grid points (i,j) in subset domain
!   6. For each point, compute m_dp and m_dlat coefficients
!   7. Apply finite difference stencil (5-point cross stencil for interior points)
!   8. Handle boundary conditions (3-point stencil for edge points)
!   9. Store matrix entries in COO format (row_idx, col_idx, values)
!
! INPUT PARAMETERS:
!   temp(nlev, nlat)     - Temperature [K] on (pressure level, latitude) grid
!   p(nlev)              - Pressure levels [Pa] in ascending order
!   phi(nlat)            - Latitude [radians] in ascending order
!   nlev                 - Number of pressure levels
!   nlat                 - Number of latitude points
!   keep_poles           - 0: exclude poles (3-point buffer), 1: include all
!   max_nnz              - Maximum number of non-zero entries allowed
!
! OUTPUT PARAMETERS:
!   row_idx(max_nnz)     - Row indices of non-zero entries (0-based)
!   col_idx(max_nnz)     - Column indices of non-zero entries (0-based)
!   values(max_nnz)      - Values of non-zero entries (matrix coefficients)
!   nnz                  - Actual number of non-zero entries stored
!
! INDEXING SCHEME (0-based, like Python):
!   Global matrix index: idx = j*M + i
!   where: i ∈ [0, M-1] is latitude index, j ∈ [0, N-1] is pressure index
!   This maps 2D grid (i,j) to 1D linear system
!
! STENCIL PATTERN:
!   Interior point (5-point cross):
!       val_c  at (i,j)
!       val_jp at (i,j+1)  [pressure above]
!       val_jm at (i,j-1)  [pressure below]
!       val_ip at (i+1,j)  [north latitude]
!       val_im at (i-1,j)  [south latitude]
!
!
! MATRIX STRUCTURE:
!   The matrix is sparse, size (M*N) x (M*N), where M = latitude points, N = pressure levels.
!   Indexing: row/col = j*M + i (0-based), i=lat index, j=pressure index.
!   Each interior grid point (i,j) contributes 5 non-zero entries (5-point stencil):
!     - Center: (i,j) -> val_c (diagonal)
!     - North: (i+1,j) -> val_ip
!     - South: (i-1,j) -> val_im
!     - Above (lower pressure): (i,j+1) -> val_jp
!     - Below (higher pressure): (i,j-1) -> val_jm
!   Boundary points have fewer entries (3 or 4).
!
!   Visual example for a small 3x3 grid (M=3, N=3, simplified):
!     Matrix layout (rows/cols 0-8, but only non-zeros shown):
!       0--1--2
!       |  |  |
!       3--4--5
!       |  |  |
!       6--7--8
!     Non-zero pattern (arrows indicate connections):
!       Corner (0): connects to 1 (right), 3 (down)
!       Edge (1): connects to 0 (left), 2 (right), 4 (down)
!       Interior (4): connects to 1 (up), 3 (left), 5 (right), 7 (down)
!     Actual values depend on m_dp, m_dlat, and finite differences.
! ============================================================================
subroutine build_ke_operator_coo(temp, p, phi, nlev, nlat, keep_poles, &
                                 row_idx, col_idx, values, nnz, max_nnz)
    implicit none
    integer, intent(in) :: nlev, nlat, keep_poles, max_nnz
    real(kind=8), intent(in) :: temp(nlev, nlat), p(nlev), phi(nlat)
    integer, intent(out) :: row_idx(max_nnz), col_idx(max_nnz), nnz
    real(kind=8), intent(out) :: values(max_nnz)

    ! Physical constants - EXACTLY as in Python
    real(kind=8), parameter :: g = 9.81d0
    real(kind=8), parameter :: R_gas = 287.0d0
    real(kind=8), parameter :: omega = 7.292d-5
    real(kind=8), parameter :: radius = 6.371d6
    real(kind=8), parameter :: pi = 3.141592653589793d0
    real(kind=8), parameter :: eps_cos = 1e-6
    real(kind=8), parameter :: p0 = 100000.0d0

    ! Local variables
    integer :: i, j, M, N, j_start, j_end, center
    integer :: i_lat, j_lev
    real(kind=8) :: f, cos_phi, m_dp, m_dlat, S_squared
    real(kind=8) :: rho_ij, theta_ij, dtheta_dp_ij
    real(kind=8) :: val_c, val_jp, val_jm, val_ip, val_im
    real(kind=8), allocatable :: dp1(:), dp2(:), dlat1(:), dlat2(:)
    real(kind=8), allocatable :: theta(:,:), rho(:,:), dtheta_dp(:,:)
    real(kind=8) :: dphi, cos_mid, temp_up, temp_down
    
    ! Determine latitude range
    if (keep_poles == 0) then
        j_start = 4  ! slice(3, -3) in Python
        j_end = nlat - 3
    else
        j_start = 1
        j_end = nlat
    end if
    M = j_end - j_start + 1
    N = nlev
    
    ! Allocate work arrays
    allocate(dp1(N-1), dp2(N))
    allocate(dlat1(M-1), dlat2(M))
    allocate(theta(M, N), rho(M, N), dtheta_dp(M, N))
    
    ! Compute dp1, dp2
    do j = 1, N-1
        dp1(j) = p(j+1) - p(j)
    end do
    
    dp2(1) = p(2) - p(1)
    dp2(N) = p(N) - p(N-1)
    if (N > 2) then
        do j = 2, N-1
            dp2(j) = 0.5d0 * (p(j+1) - p(j-1))
        end do
    end if
    
    ! Compute dlat1, dlat2
    do i = 1, M-1
        dphi = phi(j_start + i) - phi(j_start + i - 1)
        cos_mid = cos(phi(j_start + i - 1) + 0.5d0 * dphi)
        dlat1(i) = dphi * radius * cos_mid
    end do
    
    dlat2(1) = phi(j_start + 1) - phi(j_start)
    dlat2(M) = phi(j_end) - phi(j_end - 1)
    if (M > 2) then
        do i = 2, M-1
            dlat2(i) = 0.5d0 * (phi(j_start + i) - phi(j_start + i - 2))
        end do
    end if
    
    ! Compute theta, rho for subset
    do i = 1, M
        i_lat = j_start + i - 1
        do j = 1, N
            theta(i, j) = temp(j, i_lat) * (p0 / p(j)) ** (2.0d0/7.0d0)
            rho(i, j) = p(j) / (R_gas * temp(j, i_lat))
        end do
    end do
    
    ! Compute dtheta_dp using vertical_gradient
    do i = 1, M
        i_lat = j_start + i - 1
        ! Top
        dtheta_dp(i, 1) = (theta(i, 2) - theta(i, 1)) / (p(2) - p(1))
        ! Interior
        do j = 2, N-1
            dtheta_dp(i, j) = (theta(i, j+1) - theta(i, j-1)) / (p(j+1) - p(j-1))
        end do
        ! Bottom
        dtheta_dp(i, N) = (theta(i, N) - theta(i, N-1)) / (p(N) - p(N-1))
    end do
    
    ! Assemble L matrix - EXACTLY following Python's logic
    nnz = 0
    
    do i = 0, M-1  ! Python uses 0-based indexing
        i_lat = j_start + i
        f = 2.0d0 * omega * sin(phi(i_lat))
        cos_phi = cos(phi(i_lat))
        
        ! Safe cos
        if (abs(cos_phi) < eps_cos) then
            if (cos_phi >= 0.0d0) then
                cos_phi = eps_cos
            else
                cos_phi = eps_cos
            end if
        end if
        
        ! Python's m_dp with 2*pi factor
        m_dp = (g * f * f) / (2.0d0 * pi * radius * cos_phi)
        
        do j = 0, N-1  ! Python uses 0-based indexing
            ! S_squared
            S_squared = -(1.0d0 / (rho(i+1, j+1) * theta(i+1, j+1))) * dtheta_dp(i+1, j+1)
            
            ! Python's m_dlat with 2*pi factor
            m_dlat = S_squared * g / (2.0d0 * pi * radius * radius)
            
            center = j * M + i
            
            ! Following Python's branching logic EXACTLY
            if (i == 0) then
                if (j == 0) then
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (2.0d0/dp1(j+1)) &
                           -m_dlat * (2.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    val_jp = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1))
                    val_ip = m_dlat * (1.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j+1)*M + i, val_jp)
                    call add_entry(center, j*M + (i+1), val_ip)
                    
                else if (j == N-1) then
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (2.0d0/dp1(j)) &
                           -m_dlat * (2.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    val_jm = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j))
                    val_ip = m_dlat * (1.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j-1)*M + i, val_jm)
                    call add_entry(center, j*M + (i+1), val_ip)
                    
                else
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1) + 1.0d0/dp1(j)) &
                           -m_dlat * (2.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    val_jp = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1))
                    val_jm = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j))
                    val_ip = m_dlat * (1.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j+1)*M + i, val_jp)
                    call add_entry(center, (j-1)*M + i, val_jm)
                    call add_entry(center, j*M + (i+1), val_ip)
                end if
                
            else if (i == M-1) then
                if (j == 0) then
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (2.0d0/dp1(j+1)) &
                           -m_dlat * (2.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    val_jp = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1))
                    val_im = m_dlat * (1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j+1)*M + i, val_jp)
                    call add_entry(center, j*M + (i-1), val_im)
                    
                else if (j == N-1) then
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (2.0d0/dp1(j)) &
                           -m_dlat * (2.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    val_jm = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j))
                    val_im = m_dlat * (1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j-1)*M + i, val_jm)
                    call add_entry(center, j*M + (i-1), val_im)
                    
                else
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1) + 1.0d0/dp1(j)) &
                           -m_dlat * (2.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    val_jp = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1))
                    val_jm = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j))
                    val_im = m_dlat * (1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j+1)*M + i, val_jp)
                    call add_entry(center, (j-1)*M + i, val_jm)
                    call add_entry(center, j*M + (i-1), val_im)
                end if
                
            else
                if (j == 0) then
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (2.0d0/dp1(j+1)) &
                           -m_dlat * (1.0d0/dlat1(i+1) + 1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    val_jp = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1))
                    val_ip = m_dlat * (1.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    val_im = m_dlat * (1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j+1)*M + i, val_jp)
                    call add_entry(center, j*M + (i+1), val_ip)
                    call add_entry(center, j*M + (i-1), val_im)
                    
                else if (j == N-1) then
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (2.0d0/dp1(j)) &
                           -m_dlat * (1.0d0/dlat1(i+1) + 1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    val_jm = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j))
                    val_ip = m_dlat * (1.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    val_im = m_dlat * (1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j-1)*M + i, val_jm)
                    call add_entry(center, j*M + (i+1), val_ip)
                    call add_entry(center, j*M + (i-1), val_im)
                    
                else
                    val_c = -m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1) + 1.0d0/dp1(j)) &
                           -m_dlat * (1.0d0/dlat1(i+1) + 1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    val_jp = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j+1))
                    val_jm = m_dp * (1.0d0/dp2(j+1)) * (1.0d0/dp1(j))
                    val_ip = m_dlat * (1.0d0/dlat1(i+1)) * (1.0d0/dlat2(i+1))
                    val_im = m_dlat * (1.0d0/dlat1(i)) * (1.0d0/dlat2(i+1))
                    
                    call add_entry(center, center, val_c)
                    call add_entry(center, (j+1)*M + i, val_jp)
                    call add_entry(center, (j-1)*M + i, val_jm)
                    call add_entry(center, j*M + (i+1), val_ip)
                    call add_entry(center, j*M + (i-1), val_im)
                end if
            end if
        end do
    end do
    
    deallocate(dp1, dp2, dlat1, dlat2, theta, rho, dtheta_dp)
    
contains
    
    subroutine add_entry(row, col, val)
        integer, intent(in) :: row, col
        real(kind=8), intent(in) :: val
        
        nnz = nnz + 1
        if (nnz > max_nnz) then
            print *, "Error: Exceeded max_nnz at", nnz
            return
        end if
        row_idx(nnz) = row
        col_idx(nnz) = col
        values(nnz) = val
    end subroutine add_entry
    
end subroutine build_ke_operator_coo
