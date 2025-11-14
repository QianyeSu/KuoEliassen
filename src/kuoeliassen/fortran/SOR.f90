! sor.f90 - Successive Over-Relaxation solver for the Kuo-Eliassen system
!
! This file provides a Fortran implementation of a Gauss-Seidel based
! Successive Over-Relaxation (SOR) solver that operates directly on the
! sparse operator assembled for the Kuo-Eliassen equation. The solver is
! designed to handle multiple right-hand sides (RHS) in a single call and
! performs all heavy numerical work inside Fortran so that Python only
! orchestrates high-level control flow.

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
    real(kind=8), allocatable :: rhs_vec(:), sol_vec(:), old_vec(:), work_vec(:)

    solutions = 0.0d0
    iterations = 0
    residuals = 0.0d0
    status = 1

    if (nrhs <= 0) then
        status = 0
        return
    end if

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

    if (nnz <= 0) then
        status = -2
        deallocate(row_idx, col_idx, values)
        return
    end if

    allocate(row_ptr(n_total + 1), col_ind(nnz), csr_values(nnz))
    call coo_to_csr(n_total, nnz, row_idx, col_idx, values, row_ptr, col_ind, csr_values)
    deallocate(row_idx, col_idx, values)

    allocate(rhs_vec(n_total), sol_vec(n_total), old_vec(n_total), work_vec(n_total))

    omega_local = omega
    if (omega_local <= 0.0d0 .or. omega_local >= 2.0d0) omega_local = 1.0d0
    tol_local = max(tol, 1.0d-12)

    do comp = 1, nrhs
        call pack_rhs_slice(rhs(:,:,comp), nlev, nlat, j_start, j_end, rhs_vec, has_rhs)
        if (.not. has_rhs) then
            sol_vec = 0.0d0
            iterations(comp) = 0
            residuals(comp) = 0.0d0
            status(comp) = 0
        else
            call sor_linear_solver(n_total, row_ptr, col_ind, csr_values, rhs_vec, &
                                   omega_local, tol_local, max_iter, sol_vec, old_vec, work_vec, &
                                   iterations(comp), residuals(comp), status(comp))
        end if
        call scatter_solution(sol_vec, solutions(:,:,comp), nlev, nlat, j_start, j_end)
    end do

    deallocate(row_ptr, col_ind, csr_values)
    deallocate(rhs_vec, sol_vec, old_vec, work_vec)
    return

contains

    subroutine pack_rhs_slice(field, nlev_local, nlat_local, js, je, vec, has_data)
        implicit none
        integer, intent(in) :: nlev_local, nlat_local, js, je
        real(kind=8), intent(in) :: field(nlev_local, nlat_local)
        real(kind=8), intent(out) :: vec(nlev_local * (je - js + 1))
        logical, intent(out) :: has_data
        integer :: lev, lat, idx
        real(kind=8) :: val

        vec = 0.0d0
        has_data = .false.
        idx = 0
        do lev = 1, nlev_local
            do lat = js, je
                idx = idx + 1
                val = field(lev, lat)
                if (val /= val) val = 0.0d0  ! Replace NaNs with zero forcing
                vec(idx) = val
                if (.not. has_data) then
                    if (abs(val) > 0.0d0) has_data = .true.
                end if
            end do
        end do
    end subroutine pack_rhs_slice

    subroutine scatter_solution(vec, field, nlev_local, nlat_local, js, je)
        implicit none
        integer, intent(in) :: nlev_local, nlat_local, js, je
        real(kind=8), intent(in) :: vec(nlev_local * (je - js + 1))
        real(kind=8), intent(inout) :: field(nlev_local, nlat_local)
        integer :: lev, lat, idx

        idx = 0
        do lev = 1, nlev_local
            do lat = js, je
                idx = idx + 1
                field(lev, lat) = vec(idx)
            end do
        end do
    end subroutine scatter_solution

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

    subroutine sor_linear_solver(npoints, row_ptr_local, col_ind_local, val_local, b_vec, &
                                 omega_local, tol_local, max_iter_local, x_vec, prev_vec, resid_vec, &
                                 iter_out, rel_res_out, status_out)
        implicit none
        integer, intent(in) :: npoints, max_iter_local
        integer, intent(in) :: row_ptr_local(npoints + 1), col_ind_local(:)
        real(kind=8), intent(in) :: val_local(:), b_vec(npoints)
        real(kind=8), intent(in) :: omega_local, tol_local
        real(kind=8), intent(inout) :: x_vec(npoints), prev_vec(npoints), resid_vec(npoints)
        integer, intent(out) :: iter_out, status_out
        real(kind=8), intent(out) :: rel_res_out

        integer :: iter, row, idx
        real(kind=8) :: diag, sum_ax, diag_eps, omega_safe, tol_safe
        real(kind=8) :: b_norm, rel_res
        integer :: col, check_every
        logical :: rhs_is_zero

        diag_eps = 1.0d-12
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
        prev_vec = 0.0d0
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
            prev_vec = x_vec
            do row = 1, npoints
                diag = 0.0d0
                sum_ax = 0.0d0
                do idx = row_ptr_local(row), row_ptr_local(row + 1) - 1
                    col = col_ind_local(idx)
                    if (col < 1 .or. col > npoints) cycle
                    if (col == row) then
                        diag = val_local(idx)
                    else if (col < row) then
                        sum_ax = sum_ax + val_local(idx) * x_vec(col)
                    else
                        sum_ax = sum_ax + val_local(idx) * prev_vec(col)
                    end if
                end do
                if (abs(diag) < diag_eps) then
                    if (diag >= 0.0d0) then
                        diag = diag_eps
                    else
                        diag = -diag_eps
                    end if
                end if
                x_vec(row) = (1.0d0 - omega_safe) * prev_vec(row) + &
                             (omega_safe / diag) * (b_vec(row) - sum_ax)
            end do

            if (mod(iter, check_every) == 0 .or. iter == max_iter_local) then
                call csr_matvec(npoints, row_ptr_local, col_ind_local, val_local, x_vec, resid_vec)
                do row = 1, npoints
                    resid_vec(row) = b_vec(row) - resid_vec(row)
                end do
                rel_res = 0.0d0
                do row = 1, npoints
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
    end subroutine sor_linear_solver

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
