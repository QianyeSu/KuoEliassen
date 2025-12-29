! ==============================================================================
! SOR.f90 - Successive Over-Relaxation solver for the Kuo-Eliassen system
! ==============================================================================
!
! Author:  Qianye Su
! Email:   suqianye2000@gmail.com
! Created: 2025/12/25 23:09
!
! DESCRIPTION:
!   Fortran implementation of a Gauss-Seidel based Successive Over-Relaxation
!   (SOR) solver that operates directly on the sparse operator assembled for
!   the Kuo-Eliassen equation. The solver handles multiple right-hand sides
!   (RHS) in a single call and performs all heavy numerical work inside
!   Fortran so that Python only orchestrates high-level control flow.
! ==============================================================================

! ============================================================================
! ALGORITHM: Successive Over-Relaxation (SOR)
! ============================================================================
! PURPOSE:
!   Solves the linear system Ax = b for the Kuo-Eliassen equation using the
!   SOR iterative method. This is much more memory-efficient than direct
!   solvers (LU) for very large grids, though potentially slower for small ones.
!
! VISUALIZATION OF SOLVER STEP (Gauss-Seidel / SOR):
!   For a grid point (i,j), the discrete equation is:
!     A_c*x_{i,j} + A_n*x_{i,j+1} + A_s*x_{i,j-1} + A_e*x_{i+1,j} + A_w*x_{i-1,j} = b_{i,j}
!
!   1. Compute Residual (r):
!      r = b_{i,j} - (Sum of neighbor contributions + A_c*x_{i,j}^{old})
!
!   2. Update Solution (x):
!      x_{i,j}^{new} = x_{i,j}^{old} + (ω / A_c) * r
!
!   Visual Stencil Update:
!           (i,j+1)
!              |
!      (i-1,j)-(i,j)-(i+1,j)    ---> Update x(i,j) using these 4 neighbors
!              |
!           (i,j-1)
!
! OPTIMAL OMEGA (Relaxation Factor):
!   The convergence rate is highly sensitive to the relaxation factor ω.
!   - Range: 1.0 <= ω < 2.0
!   - ω = 1.0: Gauss-Seidel method (slow convergence).
!   - ω -> 2.0: Potentially fastest, but risks instability/divergence.
!
!   Empirical Results for Kuo-Eliassen (MIROC6 Data):
!     ω = 1.00  -> ~8600 iterations
!     ω = 1.50  -> ~2875 iterations
!     ω = 1.80  -> ~950 iterations
!     ω = 1.90  -> ~600 iterations (Optimal)
!     ω = 1.95  -> Diverges (>100k iterations)
!
!   Recommended Range: 1.85 - 1.90
! ============================================================================

subroutine sor_solve_ke(temp, p, phi, rhs, nlev, nlat, nrhs, keep_poles, &
                        omega, tol, max_iter, solutions, iterations, residuals, status)
    implicit none
    integer, intent(in) :: nlev, nlat, nrhs, keep_poles, max_iter
    real(kind=8), intent(in) :: temp(nlev, nlat)
    real(kind=8), intent(in) :: p(nlev)
    real(kind=8), intent(in) :: phi(nlat)
    real(kind=8), intent(in) :: rhs(nlev, nlat, nrhs)
    real(kind=8), intent(in) :: omega, tol
    real(kind=8), intent(out) :: solutions(nlev, nlat, nrhs)
    integer, intent(out) :: iterations(nrhs), status(nrhs)
    real(kind=8), intent(out) :: residuals(nrhs)

    interface
        subroutine build_ke_operator_coo(temp, p, phi, nlev, nlat, keep_poles, &
                                         row_idx, col_idx, values, nnz, max_nnz)
            implicit none
            integer, intent(in) :: nlev, nlat, keep_poles, max_nnz
            real(kind=8), intent(in) :: temp(nlev, nlat)
            real(kind=8), intent(in) :: p(nlev)
            real(kind=8), intent(in) :: phi(nlat)
            integer, intent(out) :: row_idx(max_nnz)
            integer, intent(out) :: col_idx(max_nnz)
            real(kind=8), intent(out) :: values(max_nnz)
            integer, intent(out) :: nnz
        end subroutine build_ke_operator_coo
    end interface

    integer :: j_start, j_end, m_lat, n_total
    integer :: max_nnz_local, nnz
    integer :: comp
    real(kind=8) :: omega_local, tol_local
    logical :: has_rhs

    integer, allocatable :: row_idx(:), col_idx(:)
    real(kind=8), allocatable :: values(:)
    integer, allocatable :: row_ptr(:), col_ind(:)
    real(kind=8), allocatable :: csr_values(:)
    real(kind=8), allocatable :: rhs_vec(:), sol_vec(:), work_vec(:)
    real(kind=8), allocatable :: diag_inv(:)
    
    ! real(kind=8) :: t_start, t_build, t_convert, t_precalc, t_solve_start, t_solve_end

    solutions = 0.0d0
    iterations = 0
    residuals = 0.0d0
    status = 1

    if (nrhs <= 0) then
        status = 0
        return
    end if
    
    ! call cpu_time(t_start)

    ! Determine latitude range used by the operator builder
    if (keep_poles == 0) then
        j_start = 4
        j_end = nlat - 3
    else
        j_start = 1
        j_end = nlat
    end if
    m_lat = j_end - j_start + 1

    if (m_lat <= 0) then
        status = -1
        return
    end if

    n_total = nlev * m_lat
    max_nnz_local = max(1, 5 * n_total)

    allocate(row_idx(max_nnz_local), col_idx(max_nnz_local), values(max_nnz_local))
    call build_ke_operator_coo(temp, p, phi, nlev, nlat, keep_poles, &
                               row_idx, col_idx, values, nnz, max_nnz_local)
                               
    ! call cpu_time(t_build)

    if (nnz <= 0) then
        status = -2
        deallocate(row_idx, col_idx, values)
        return
    end if

    allocate(row_ptr(n_total + 1), col_ind(nnz), csr_values(nnz))
    call coo_to_csr(n_total, nnz, row_idx, col_idx, values, row_ptr, col_ind, csr_values)
    deallocate(row_idx, col_idx, values)
    
    ! call cpu_time(t_convert)

    ! Pre-calculate inverse diagonal for SOR acceleration
    allocate(diag_inv(n_total))
    call extract_inverse_diagonal(n_total, row_ptr, col_ind, csr_values, diag_inv)
    
    ! call cpu_time(t_precalc)

    allocate(rhs_vec(n_total), sol_vec(n_total), work_vec(n_total))

    omega_local = omega
    if (omega_local <= 0.0d0 .or. omega_local >= 2.0d0) omega_local = 1.0d0
    tol_local = max(tol, 1.0d-12)
    
    ! call cpu_time(t_solve_start)

    do comp = 1, nrhs
        call pack_rhs_slice(rhs(:,:,comp), nlev, nlat, j_start, j_end, rhs_vec, has_rhs)
        if (.not. has_rhs) then
            sol_vec = 0.0d0
            iterations(comp) = 0
            residuals(comp) = 0.0d0
            status(comp) = 0
        else
            call sor_linear_solver_optimized(n_total, row_ptr, col_ind, csr_values, diag_inv, rhs_vec, &
                                   omega_local, tol_local, max_iter, sol_vec, work_vec, &
                                   iterations(comp), residuals(comp), status(comp))
        end if
        call scatter_solution(sol_vec, solutions(:,:,comp), nlev, nlat, j_start, j_end)
    end do
    
    ! call cpu_time(t_solve_end)
    
    ! Print internal timing diagnostics (can be removed later)
    ! print *, "SOR Internal Timing (sec):"
    ! print *, "  Build Operator: ", t_build - t_start
    ! print *, "  COO->CSR:       ", t_convert - t_build
    ! print *, "  Precalc Diag:   ", t_precalc - t_convert
    ! print *, "  Solve Loop:     ", t_solve_end - t_solve_start
    ! print *, "  Total Fortran:  ", t_solve_end - t_start

    deallocate(row_ptr, col_ind, csr_values, diag_inv)
    deallocate(rhs_vec, sol_vec, work_vec)
    return

contains

    ! ============================================================================
    ! SUBROUTINE: extract_inverse_diagonal
    ! ============================================================================
    ! PURPOSE:
    !   Pre-calculates the inverse of the diagonal elements (1/A_ii) of the sparse
    !   matrix. This optimization speeds up the SOR iteration by replacing division
    !   with multiplication inside the inner loop.
    !
    ! INPUTS:
    !   npoints     - Total number of grid points (rows in matrix)
    !   row_ptr     - CSR row pointers
    !   col_ind     - CSR column indices
    !   values      - CSR values
    !
    ! OUTPUTS:
    !   diag_inv    - Array containing 1.0 / A_ii for each row i
    ! ============================================================================
    subroutine extract_inverse_diagonal(npoints, row_ptr, col_ind, values, diag_inv)
        implicit none
        integer, intent(in) :: npoints
        integer, intent(in) :: row_ptr(npoints + 1), col_ind(:)
        real(kind=8), intent(in) :: values(:)
        real(kind=8), intent(out) :: diag_inv(npoints)
        
        integer :: row, idx
        real(kind=8) :: val, diag_eps
        
        diag_eps = 1.0d-150
        diag_inv = 0.0d0 ! Default if no diagonal found (should not happen for well-posed KE)

        do row = 1, npoints
            do idx = row_ptr(row), row_ptr(row + 1) - 1
                if (col_ind(idx) == row) then
                    val = values(idx)
                    if (abs(val) < diag_eps) then
                        if (val >= 0.0d0) then
                            val = diag_eps
                        else
                            val = -diag_eps
                        end if
                    end if
                    diag_inv(row) = 1.0d0 / val
                    exit ! Found diagonal, move to next row
                end if
            end do
        end do
    end subroutine extract_inverse_diagonal

    ! ============================================================================
    ! SUBROUTINE: pack_rhs_slice
    ! ============================================================================
    ! PURPOSE:
    !   Converts a 2D field (nlev, nlat) into a 1D vector for the linear solver.
    !   Also handles NaN values by replacing them with 0.0 (zero forcing).
    !
    ! MAPPING:
    !   2D (lev, lat) -> 1D index: idx = (lev-1)*m_lat + (lat-js+1)
    !   This matches the row ordering of the sparse matrix operator.
    !
    ! INPUTS:
    !   field       - 2D input field (e.g., one component of RHS)
    !   js, je      - Start and end latitude indices to process
    !
    ! OUTPUTS:
    !   vec         - Flattened 1D vector
    !   has_data    - Flag indicating if the vector contains non-zero values
    ! ============================================================================
    subroutine pack_rhs_slice(field, nlev_local, nlat_local, js, je, vec, has_data)
        implicit none
        integer, intent(in) :: nlev_local, nlat_local, js, je
        real(kind=8), intent(in) :: field(nlev_local, nlat_local)
        real(kind=8), intent(out) :: vec(nlev_local * (je - js + 1))
        logical, intent(out) :: has_data
        integer :: lev, lat, idx, m_lat
        real(kind=8) :: val

        vec = 0.0d0
        has_data = .false.
        m_lat = je - js + 1
        
        ! Match matrix indexing: center = j_lev * M + i_lat (0-based)
        ! So lat varies fastest within each pressure level
        do lev = 1, nlev_local
            do lat = js, je
                ! idx is 1-based, formula: (lev-1)*m_lat + (lat-js+1)
                idx = (lev - 1) * m_lat + (lat - js + 1)
                val = field(lev, lat)
                if (val /= val) val = 0.0d0  ! Replace NaNs with zero forcing
                vec(idx) = val
                if (.not. has_data) then
                    if (abs(val) > 0.0d0) has_data = .true.
                end if
            end do
        end do
    end subroutine pack_rhs_slice

    ! ============================================================================
    ! SUBROUTINE: scatter_solution
    ! ============================================================================
    ! PURPOSE:
    !   Maps the 1D solution vector back into the full 2D output array.
    !   This is the inverse operation of pack_rhs_slice.
    !
    ! INPUTS:
    !   vec         - 1D solution vector from the solver
    !   js, je      - Latitude range corresponding to the vector
    !
    ! OUTPUTS:
    !   field       - 2D output array (updated in-place)
    ! ============================================================================
    subroutine scatter_solution(vec, field, nlev_local, nlat_local, js, je)
        implicit none
        integer, intent(in) :: nlev_local, nlat_local, js, je
        real(kind=8), intent(in) :: vec(nlev_local * (je - js + 1))
        real(kind=8), intent(inout) :: field(nlev_local, nlat_local)
        integer :: lev, lat, idx, m_lat

        m_lat = je - js + 1
        ! Match matrix indexing: center = j_lev * M + i_lat (0-based)
        do lev = 1, nlev_local
            do lat = js, je
                idx = (lev - 1) * m_lat + (lat - js + 1)
                field(lev, lat) = vec(idx)
            end do
        end do
    end subroutine scatter_solution

    ! ============================================================================
    ! SUBROUTINE: coo_to_csr
    ! ============================================================================
    ! PURPOSE:
    !   Converts a sparse matrix from Coordinate (COO) format to Compressed Sparse
    !   Row (CSR) format. CSR is much more efficient for matrix-vector multiplication
    !   and row-wise iteration required by SOR.
    !
    ! INPUTS (COO):
    !   row_id, col_id, val_in  - Arrays of row indices, col indices, and values
    !
    ! OUTPUTS (CSR):
    !   row_ptr_out - Array of indices where each row starts in col_ind/val
    !   col_ind_out - Column indices for non-zero values
    !   val_out     - Non-zero values
    ! ============================================================================
    subroutine coo_to_csr(npoints, nnz_local, row_id, col_id, val_in, row_ptr_out, col_ind_out, val_out)
        implicit none
        integer, intent(in) :: npoints, nnz_local
        integer, intent(in) :: row_id(nnz_local), col_id(nnz_local)
        real(kind=8), intent(in) :: val_in(nnz_local)
        integer, intent(out) :: row_ptr_out(npoints + 1), col_ind_out(nnz_local)
        real(kind=8), intent(out) :: val_out(nnz_local)
        integer :: i, row
        integer, allocatable :: row_counts(:)
        integer :: pos

        allocate(row_counts(npoints))
        row_counts = 0
        do i = 1, nnz_local
            row = row_id(i) + 1
            if (row < 1 .or. row > npoints) cycle
            row_counts(row) = row_counts(row) + 1
        end do

        row_ptr_out(1) = 1
        do i = 1, npoints
            row_ptr_out(i + 1) = row_ptr_out(i) + row_counts(i)
        end do

        row_counts = row_ptr_out(1:npoints)
        do i = 1, nnz_local
            row = row_id(i) + 1
            if (row < 1 .or. row > npoints) cycle
            pos = row_counts(row)
            col_ind_out(pos) = col_id(i) + 1
            val_out(pos) = val_in(i)
            row_counts(row) = row_counts(row) + 1
        end do
        deallocate(row_counts)
    end subroutine coo_to_csr

    ! ============================================================================
    ! SUBROUTINE: sor_linear_solver_optimized
    ! ============================================================================
    ! PURPOSE:
    !   The core computational kernel. Solves Ax = b using the SOR method.
    !   Optimized for performance by using pre-calculated inverse diagonals and
    !   a branchless inner loop.
    !
    ! ALGORITHM DETAILS:
    !   Iterates: x_new = x_old + omega * D^{-1} * (b - A * x_current)
    !   where x_current uses the most recent values available (Gauss-Seidel property).
    !
    ! INPUTS:
    !   npoints     - System size
    !   row_ptr...  - CSR matrix arrays
    !   diag_inv    - Pre-calculated 1/A_ii
    !   b_vec       - Right-hand side vector
    !   omega...    - Solver parameters
    !
    ! OUTPUTS:
    !   x_vec       - Solution vector
    !   iter_out    - Number of iterations performed
    !   rel_res_out - Final relative residual
    !   status_out  - 0: Converged, 1: Max iterations reached
    ! ============================================================================
    subroutine sor_linear_solver_optimized(npoints, row_ptr_local, col_ind_local, val_local, diag_inv, b_vec, &
                                 omega_local, tol_local, max_iter_local, x_vec, resid_vec, &
                                 iter_out, rel_res_out, status_out)
        implicit none
        integer, intent(in) :: npoints, max_iter_local
        integer, intent(in) :: row_ptr_local(npoints + 1), col_ind_local(:)
        real(kind=8), intent(in) :: val_local(:), diag_inv(:), b_vec(npoints)
        real(kind=8), intent(in) :: omega_local, tol_local
        real(kind=8), intent(inout) :: x_vec(npoints), resid_vec(npoints)
        integer, intent(out) :: iter_out, status_out
        real(kind=8), intent(out) :: rel_res_out

        integer :: iter, row, idx
        real(kind=8) :: sum_ax, omega_safe, tol_safe
        real(kind=8) :: b_norm, rel_res, residual_val
        integer :: col, check_every
        logical :: rhs_is_zero

        omega_safe = min(max(omega_local, 0.1d0), 1.95d0)
        tol_safe = max(tol_local, 1.0d-12)
        iter_out = 0
        rel_res_out = 0.0d0

        rhs_is_zero = .true.
        do row = 1, npoints
            if (abs(b_vec(row)) > 0.0d0) then
                rhs_is_zero = .false.
                exit
            end if
        end do

        x_vec = 0.0d0
        status_out = 1

        if (rhs_is_zero) then
            status_out = 0
            rel_res_out = 0.0d0
            return
        end if

        b_norm = 0.0d0
        do row = 1, npoints
            b_norm = b_norm + b_vec(row) * b_vec(row)
        end do
        b_norm = sqrt(max(b_norm, 1.0d-24))

        check_every = 25
        do iter = 1, max(1, max_iter_local)
            do row = 1, npoints
                sum_ax = 0.0d0
                ! Compute (Ax)_i using current x values (Gauss-Seidel style)
                ! This loop includes the diagonal term A_ii * x_i
                do idx = row_ptr_local(row), row_ptr_local(row + 1) - 1
                    col = col_ind_local(idx)
                    sum_ax = sum_ax + val_local(idx) * x_vec(col)
                end do
                
                ! Residual r_i = b_i - (Ax)_i
                residual_val = b_vec(row) - sum_ax
                
                ! SOR update: x_i_new = x_i_old + (omega / A_ii) * r_i
                x_vec(row) = x_vec(row) + omega_safe * diag_inv(row) * residual_val
            end do

            if (mod(iter, check_every) == 0 .or. iter == max_iter_local) then
                call csr_matvec(npoints, row_ptr_local, col_ind_local, val_local, x_vec, resid_vec)
                rel_res = 0.0d0
                do row = 1, npoints
                    resid_vec(row) = b_vec(row) - resid_vec(row)
                    rel_res = rel_res + resid_vec(row) * resid_vec(row)
                end do
                rel_res = sqrt(rel_res) / b_norm
                rel_res_out = rel_res
                if (rel_res <= tol_safe) then
                    status_out = 0
                    iter_out = iter
                    return
                end if
            end if
        end do

        iter_out = max_iter_local
        rel_res_out = rel_res
    end subroutine sor_linear_solver_optimized

    ! ============================================================================
    ! SUBROUTINE: csr_matvec
    ! ============================================================================
    ! PURPOSE:
    !   Performs sparse matrix-vector multiplication: y = A * x
    !   Used to compute the true residual for convergence checking.
    !
    ! INPUTS:
    !   CSR matrix arrays (row_ptr, col_ind, val)
    !   x_vec - Input vector
    !
    ! OUTPUTS:
    !   y_vec - Output vector (A * x)
    ! ============================================================================
    subroutine csr_matvec(npoints, row_ptr_local, col_ind_local, val_local, x_vec, y_vec)
        implicit none
        integer, intent(in) :: npoints
        integer, intent(in) :: row_ptr_local(npoints + 1), col_ind_local(:)
        real(kind=8), intent(in) :: val_local(:), x_vec(npoints)
        real(kind=8), intent(out) :: y_vec(npoints)
        integer :: row, idx, col

        do row = 1, npoints
            y_vec(row) = 0.0d0
            do idx = row_ptr_local(row), row_ptr_local(row + 1) - 1
                col = col_ind_local(idx)
                if (col < 1 .or. col > npoints) cycle
                y_vec(row) = y_vec(row) + val_local(idx) * x_vec(col)
            end do
        end do
    end subroutine csr_matvec

end subroutine sor_solve_ke


! ============================================================================
! SUBROUTINE: sor_solve_coo
! ============================================================================
! PURPOSE:
!   Direct SOR solver that accepts a pre-built sparse matrix in COO format.
!   This avoids redundant matrix construction when Python has already built it.
!
! INPUTS:
!   row_coo(nnz)    - Row indices (1-based, Fortran indexing)
!   col_coo(nnz)    - Column indices (1-based, Fortran indexing)
!   val_coo(nnz)    - Non-zero values
!   rhs(n, nrhs)    - Right-hand side vectors
!   n               - Matrix dimension
!   nnz             - Number of non-zeros
!   nrhs            - Number of RHS vectors
!   omega           - SOR relaxation factor (1.0-2.0, optimal ~1.8)
!   tol             - Convergence tolerance
!   max_iter        - Maximum iterations
!
! OUTPUTS:
!   solutions(n, nrhs) - Solution vectors
!   iterations(nrhs)   - Iteration count for each RHS
!   residuals(nrhs)    - Final residual for each RHS
!   status(nrhs)       - 0=converged, 1=max_iter reached
! ============================================================================
subroutine sor_solve_coo(row_coo, col_coo, val_coo, rhs, n, nnz, nrhs, &
                         omega, tol, max_iter, solutions, iterations, residuals, status)
    implicit none
    integer, intent(in) :: n, nnz, nrhs, max_iter
    integer, intent(in) :: row_coo(nnz), col_coo(nnz)
    real(kind=8), intent(in) :: val_coo(nnz)
    real(kind=8), intent(in) :: rhs(n, nrhs)
    real(kind=8), intent(in) :: omega, tol
    real(kind=8), intent(out) :: solutions(n, nrhs)
    integer, intent(out) :: iterations(nrhs), status(nrhs)
    real(kind=8), intent(out) :: residuals(nrhs)

    ! Local variables
    integer, allocatable :: row_ptr(:), col_ind(:)
    real(kind=8), allocatable :: csr_values(:), diag_inv(:)
    real(kind=8), allocatable :: rhs_vec(:), sol_vec(:), work_vec(:)
    real(kind=8) :: omega_local, tol_local
    integer :: i, comp
    logical :: has_nonzero

    ! Validate omega
    omega_local = omega
    if (omega_local <= 0.0d0 .or. omega_local >= 2.0d0) omega_local = 1.5d0
    tol_local = max(tol, 1.0d-14)

    ! Allocate CSR arrays
    allocate(row_ptr(n + 1), col_ind(nnz), csr_values(nnz))
    allocate(diag_inv(n))
    
    ! Allocate workspace for parallel execution
    ! We need separate workspace for each thread/RHS
    ! But since we can't easily use OpenMP inside a subroutine without changing interface significantly
    ! or relying on automatic arrays which might overflow stack, we'll use allocatable arrays inside the loop
    ! or rely on the compiler to handle private variables if we use OpenMP.
    
    ! For now, let's keep it serial but optimize memory allocation pattern.
    ! Actually, to support OpenMP, we should allocate these inside the parallel region or make them private.
    
    ! Convert COO to CSR
    call coo_to_csr_local(row_coo, col_coo, val_coo, n, nnz, row_ptr, col_ind, csr_values)

    ! Pre-calculate inverse diagonal
    call extract_diag_inv_local(n, row_ptr, col_ind, csr_values, diag_inv)

    ! Solve for each RHS - Parallelized with OpenMP
    !$OMP PARALLEL DO PRIVATE(comp, i, has_nonzero, rhs_vec, sol_vec, work_vec) &
    !$OMP SHARED(nrhs, n, rhs, solutions, iterations, residuals, status, row_ptr, col_ind, csr_values, diag_inv, omega_local, tol_local, max_iter)
    do comp = 1, nrhs
        ! Allocate thread-private arrays
        allocate(rhs_vec(n), sol_vec(n), work_vec(n))
        
        ! Copy RHS and check for non-zero
        has_nonzero = .false.
        do i = 1, n
            rhs_vec(i) = rhs(i, comp)
            ! Handle NaN: treat as zero forcing
            if (rhs_vec(i) /= rhs_vec(i)) then
                rhs_vec(i) = 0.0d0
            else if (abs(rhs_vec(i)) > 1.0d-200) then
                has_nonzero = .true.
            end if
        end do

        if (.not. has_nonzero) then
            ! Zero RHS -> zero solution
            solutions(:, comp) = 0.0d0
            iterations(comp) = 0
            residuals(comp) = 0.0d0
            status(comp) = 0
        else
            ! Initialize solution to zero
            sol_vec = 0.0d0
            
            ! Call optimized SOR solver
            call sor_kernel(n, row_ptr, col_ind, csr_values, diag_inv, rhs_vec, &
                           omega_local, tol_local, max_iter, sol_vec, work_vec, &
                           iterations(comp), residuals(comp), status(comp))
            
            solutions(:, comp) = sol_vec
        end if
        
        deallocate(rhs_vec, sol_vec, work_vec)
    end do
    !$OMP END PARALLEL DO

    deallocate(row_ptr, col_ind, csr_values, diag_inv)
    ! deallocate(rhs_vec, sol_vec, work_vec) ! Removed as they are now thread-local

contains

    ! ========================================================================
    ! SUBROUTINE: coo_to_csr_local
    ! ========================================================================
    ! PURPOSE:
    !   Convert sparse matrix from COO (Coordinate) format to CSR (Compressed
    !   Sparse Row) format. CSR is more efficient for row-wise operations like
    !   SOR iteration.
    !
    ! COO FORMAT (input):
    !   - Stores each non-zero as (row, col, value) triplet
    !   - Memory: 3 arrays of length nnz
    !   - Random access pattern
    !
    ! CSR FORMAT (output):
    !   - row_ptr(i): start index in col/val arrays for row i
    !   - col_ind: column indices of non-zeros
    !   - csr_values: corresponding values
    !   - Enables fast row-wise matrix-vector products
    !
    ! INPUTS:
    !   row_in(nz)  - Row indices in COO format (1-based)
    !   col_in(nz)  - Column indices in COO format (1-based)
    !   val_in(nz)  - Non-zero values
    !   np          - Number of rows/columns (matrix dimension)
    !   nz          - Number of non-zeros
    !
    ! OUTPUTS:
    !   rp(np+1)    - Row pointer array (CSR format)
    !   ci(nz)      - Column indices (CSR format)
    !   cv(nz)      - Non-zero values (CSR format)
    !
    ! ALGORITHM:
    !   1. Count non-zeros per row
    !   2. Build cumulative row pointer array
    !   3. Distribute COO triplets into CSR structure
    ! ========================================================================
    subroutine coo_to_csr_local(row_in, col_in, val_in, np, nz, rp, ci, cv)
        implicit none
        integer, intent(in) :: np, nz
        integer, intent(in) :: row_in(nz), col_in(nz)
        real(kind=8), intent(in) :: val_in(nz)
        integer, intent(out) :: rp(np + 1), ci(nz)
        real(kind=8), intent(out) :: cv(nz)
        
        integer :: i, row, pos
        integer, allocatable :: count(:)
        
        allocate(count(np))
        count = 0
        
        ! Count elements per row (input is 0-based, convert to 1-based)
        do i = 1, nz
            row = row_in(i) + 1   ! Convert 0-based to 1-based
            ! Check both row and column bounds to ensure safe access in solver
            if (row >= 1 .and. row <= np .and. &
                col_in(i) >= 0 .and. col_in(i) < np) then
                count(row) = count(row) + 1
            end if
        end do
        
        ! Build row pointers
        rp(1) = 1
        do i = 1, np
            rp(i + 1) = rp(i) + count(i)
        end do
        
        ! Reset count for filling
        count = 0
        
        ! Fill CSR arrays (convert indices from 0-based to 1-based)
        do i = 1, nz
            row = row_in(i) + 1   ! Convert 0-based to 1-based
            if (row >= 1 .and. row <= np .and. &
                col_in(i) >= 0 .and. col_in(i) < np) then
                pos = rp(row) + count(row)
                ci(pos) = col_in(i) + 1   ! Convert 0-based to 1-based
                cv(pos) = val_in(i)
                count(row) = count(row) + 1
            end if
        end do
        
        deallocate(count)
    end subroutine coo_to_csr_local

    ! ========================================================================
    ! SUBROUTINE: extract_diag_inv_local
    ! ========================================================================
    ! PURPOSE:
    !   Extract diagonal elements from CSR matrix and compute their inverses.
    !   Pre-computing diagonal inverses (1/A_ii) improves SOR iteration
    !   efficiency by avoiding repeated division operations.
    !
    ! WHY PRE-COMPUTE?
    !   SOR update: x_new = (b - sum(A_ij*x_j)) / A_ii
    !   Instead of:  x_new = ... / diag[i]           (slow, repeated division)
    !   We do:       x_new = ... * diag_inv[i]       (fast, multiplication)
    !
    ! NUMERICAL SAFETY:
    !   - If diagonal element is too small (< 1e-12), replace with epsilon
    !   - Prevents division by zero / numerical overflow
    !   - Maintains sign to avoid flipping solution direction
    !
    ! INPUTS:
    !   np       - Matrix dimension
    !   rp(np+1) - CSR row pointer array
    !   ci(:)    - CSR column indices
    !   cv(:)    - CSR non-zero values
    !
    ! OUTPUTS:
    !   dinv(np) - Inverse of diagonal elements (1/A_ii)
    !
    ! EXAMPLE:
    !   Matrix A = [2  1]   → diag = [2, 3]
    !              [0  3]
    !   Output: dinv = [0.5, 0.333...]
    ! ========================================================================
    subroutine extract_diag_inv_local(np, rp, ci, cv, dinv)
        implicit none
        integer, intent(in) :: np
        integer, intent(in) :: rp(np + 1), ci(:)
        real(kind=8), intent(in) :: cv(:)
        real(kind=8), intent(out) :: dinv(np)
        
        integer :: row, idx
        real(kind=8) :: diag_val
        real(kind=8), parameter :: DIAG_EPS = 1.0d-200
        
        do row = 1, np
            diag_val = 0.0d0
            do idx = rp(row), rp(row + 1) - 1
                if (ci(idx) == row) then
                    diag_val = cv(idx)
                    exit
                end if
            end do
            if (abs(diag_val) < DIAG_EPS) diag_val = sign(DIAG_EPS, diag_val + DIAG_EPS)
            dinv(row) = 1.0d0 / diag_val
        end do
    end subroutine extract_diag_inv_local

    ! ========================================================================
    ! SUBROUTINE: sor_kernel
    ! ========================================================================
    ! PURPOSE:
    !   Core SOR (Successive Over-Relaxation) iterative solver.
    !   Solves linear system A*x = b using relaxed Gauss-Seidel iteration.
    !
    ! SOR ITERATION FORMULA:
    !   For each row i:
    !     x_new[i] = (b[i] - sum(A[i,j]*x[j], j≠i)) / A[i,i]  (Gauss-Seidel)
    !     x[i] = x[i] + ω * (x_new[i] - x[i])                  (Relaxation)
    !
    ! RELAXATION PARAMETER ω:
    !   - ω = 1.0: Pure Gauss-Seidel
    !   - ω > 1.0: Over-relaxation (accelerates convergence)
    !   - ω < 1.0: Under-relaxation (improves stability)
    !   - Optimal ω ≈ 1.8 for Kuo-Eliassen equation
    !
    ! CONVERGENCE CHECK:
    !   - Residual: r = b - A*x
    !   - Relative norm: ||r|| / ||b|| < tolerance
    !   - Check every 50 iterations to balance accuracy and speed
    !
    ! INPUTS:
    !   np          - System dimension
    !   rp(np+1)    - CSR row pointers
    !   ci(:)       - CSR column indices  
    !   cv(:)       - CSR non-zero values
    !   dinv(np)    - Pre-computed diagonal inverses (1/A_ii)
    !   b(np)       - Right-hand side vector
    !   w           - Relaxation parameter (omega)
    !   tl          - Convergence tolerance
    !   maxit       - Maximum iterations
    !
    ! IN/OUT:
    !   x(np)       - Solution vector (initialized to 0, updated in-place)
    !
    ! OUTPUTS:
    !   work(np)    - Work array for residual computation
    !   res         - Final relative residual norm
    !   iter        - Actual iteration count
    !   stat        - 0: converged, 1: max_iter reached without convergence
    !
    ! ALGORITHM:
    !   1. Normalize RHS (compute ||b|| for relative residual)
    !   2. Repeat SOR sweep until convergence:
    !      a. For each row: compute new x[i] using latest x values
    !      b. Apply relaxation: x[i] += ω*(x_new[i] - x[i])
    !   3. Check convergence every 50 iterations
    !   4. Return when ||b - A*x|| / ||b|| < tolerance
    ! ========================================================================
    subroutine sor_kernel(np, rp, ci, cv, dinv, b, w, tl, maxit, x, work, iter, res, stat)
        implicit none
        integer, intent(in) :: np, maxit
        integer, intent(in) :: rp(np + 1), ci(:)
        real(kind=8), intent(in) :: cv(:), dinv(np), b(np), w, tl
        real(kind=8), intent(inout) :: x(np)
        real(kind=8), intent(out) :: work(np), res
        integer, intent(out) :: iter, stat
        
        integer :: it, row, idx, col
        real(kind=8) :: sigma, bnorm, rnorm, residual_val
        real(kind=8), allocatable :: wdinv(:)
        integer, parameter :: CHECK_INTERVAL = 50
        
        ! Precompute w * dinv for faster updates
        allocate(wdinv(np))
        wdinv = w * dinv

        ! Compute ||b||
        bnorm = 0.0d0
        do row = 1, np
            bnorm = bnorm + b(row) * b(row)
        end do
        bnorm = sqrt(bnorm)
        if (bnorm < 1.0d-200) bnorm = 1.0d0
        
        stat = 1  ! Assume not converged
        
        do it = 1, maxit
            ! SOR sweep
            do row = 1, np
                sigma = 0.0d0
                ! Sum all A_ij * x_j (including diagonal)
                ! We assume column indices are valid (checked during CSR conversion)
                do idx = rp(row), rp(row + 1) - 1
                    col = ci(idx)
                    sigma = sigma + cv(idx) * x(col)
                end do
                
                ! Residual r_i = b_i - (Ax)_i
                residual_val = b(row) - sigma
                
                ! Update: x_new = x_old + (w/A_ii) * r_i
                x(row) = x(row) + wdinv(row) * residual_val
            end do
            
            ! Check convergence periodically
            if (mod(it, CHECK_INTERVAL) == 0 .or. it == maxit) then
                ! Compute residual r = b - A*x
                rnorm = 0.0d0
                do row = 1, np
                    sigma = 0.0d0
                    do idx = rp(row), rp(row + 1) - 1
                        col = ci(idx)
                        sigma = sigma + cv(idx) * x(col)
                    end do
                    work(row) = b(row) - sigma
                    rnorm = rnorm + work(row) * work(row)
                end do
                rnorm = sqrt(rnorm)
                res = rnorm / bnorm
                
                if (res < tl) then
                    stat = 0
                    iter = it
                    deallocate(wdinv)
                    return
                end if
            end if
        end do
        
        deallocate(wdinv)
        iter = maxit
    end subroutine sor_kernel

end subroutine sor_solve_coo
