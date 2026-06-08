module kuoeliassen_bindings_mod
    use, intrinsic :: iso_c_binding, only: c_ptr, c_f_pointer, c_int, c_double
    implicit none

contains

subroutine vertical_gradient_c(field, p, nlev, grad) bind(C, name="vertical_gradient_c")
    type(c_ptr), value, intent(in) :: field, p, grad
    integer(c_int), value, intent(in) :: nlev
    real(c_double), pointer :: field_view(:), p_view(:), grad_view(:)

    call c_f_pointer(field, field_view, [int(nlev)])
    call c_f_pointer(p, p_view, [int(nlev)])
    call c_f_pointer(grad, grad_view, [int(nlev)])
    call vertical_gradient(field_view, p_view, int(nlev), grad_view)
end subroutine vertical_gradient_c

subroutine meridional_gradient_coeff_c(phi, nlat, dphi_array) bind(C, name="meridional_gradient_coeff_c")
    type(c_ptr), value, intent(in) :: phi, dphi_array
    integer(c_int), value, intent(in) :: nlat
    real(c_double), pointer :: phi_view(:), dphi_view(:)

    call c_f_pointer(phi, phi_view, [int(nlat)])
    call c_f_pointer(dphi_array, dphi_view, [int(nlat)])
    call meridional_gradient_coeff(phi_view, int(nlat), dphi_view)
end subroutine meridional_gradient_coeff_c

subroutine meridional_gradient_2d_c(field, phi, radius, nlev, nlat, grad) bind(C, name="meridional_gradient_2d_c")
    type(c_ptr), value, intent(in) :: field, phi, grad
    real(c_double), value, intent(in) :: radius
    integer(c_int), value, intent(in) :: nlev, nlat
    real(c_double), pointer :: field_view(:, :), phi_view(:), grad_view(:, :)

    call c_f_pointer(field, field_view, [int(nlev), int(nlat)])
    call c_f_pointer(phi, phi_view, [int(nlat)])
    call c_f_pointer(grad, grad_view, [int(nlev), int(nlat)])
    call meridional_gradient_2d(field_view, phi_view, radius, int(nlev), int(nlat), grad_view)
end subroutine meridional_gradient_2d_c

subroutine vertical_gradient_2d_c(field, p, nlev, nlat, grad) bind(C, name="vertical_gradient_2d_c")
    type(c_ptr), value, intent(in) :: field, p, grad
    integer(c_int), value, intent(in) :: nlev, nlat
    real(c_double), pointer :: field_view(:, :), p_view(:), grad_view(:, :)

    call c_f_pointer(field, field_view, [int(nlev), int(nlat)])
    call c_f_pointer(p, p_view, [int(nlev)])
    call c_f_pointer(grad, grad_view, [int(nlev), int(nlat)])
    call vertical_gradient_2d(field_view, p_view, int(nlev), int(nlat), grad_view)
end subroutine vertical_gradient_2d_c

subroutine compute_rhs_components_c(v_mean, temp, latent_heating, rad_heating, vt_eddy, vu_eddy, &
                                    p, phi, nlev, nlat, keep_poles, &
                                    d_dtcond, d_rad, d_vt, d_vu, d_x, f_friction) &
                                    bind(C, name="compute_rhs_components_c")
    type(c_ptr), value, intent(in) :: v_mean, temp, latent_heating, rad_heating
    type(c_ptr), value, intent(in) :: vt_eddy, vu_eddy, p, phi
    type(c_ptr), value, intent(in) :: d_dtcond, d_rad, d_vt, d_vu, d_x, f_friction
    integer(c_int), value, intent(in) :: nlev, nlat, keep_poles
    real(c_double), pointer :: v_view(:, :), temp_view(:, :)
    real(c_double), pointer :: latent_view(:, :), rad_view(:, :)
    real(c_double), pointer :: vt_view(:, :), vu_view(:, :)
    real(c_double), pointer :: p_view(:), phi_view(:)
    real(c_double), pointer :: dtcond_view(:, :), drad_view(:, :), dvt_view(:, :)
    real(c_double), pointer :: dvu_view(:, :), dx_view(:, :), friction_view(:, :)

    call c_f_pointer(v_mean, v_view, [int(nlev), int(nlat)])
    call c_f_pointer(temp, temp_view, [int(nlev), int(nlat)])
    call c_f_pointer(latent_heating, latent_view, [int(nlev), int(nlat)])
    call c_f_pointer(rad_heating, rad_view, [int(nlev), int(nlat)])
    call c_f_pointer(vt_eddy, vt_view, [int(nlev), int(nlat)])
    call c_f_pointer(vu_eddy, vu_view, [int(nlev), int(nlat)])
    call c_f_pointer(p, p_view, [int(nlev)])
    call c_f_pointer(phi, phi_view, [int(nlat)])
    call c_f_pointer(d_dtcond, dtcond_view, [int(nlev), int(nlat)])
    call c_f_pointer(d_rad, drad_view, [int(nlev), int(nlat)])
    call c_f_pointer(d_vt, dvt_view, [int(nlev), int(nlat)])
    call c_f_pointer(d_vu, dvu_view, [int(nlev), int(nlat)])
    call c_f_pointer(d_x, dx_view, [int(nlev), int(nlat)])
    call c_f_pointer(f_friction, friction_view, [int(nlev), int(nlat)])

    call compute_rhs_components(v_view, temp_view, latent_view, rad_view, vt_view, vu_view, &
                                p_view, phi_view, int(nlev), int(nlat), int(keep_poles), &
                                dtcond_view, drad_view, dvt_view, dvu_view, dx_view, friction_view)
end subroutine compute_rhs_components_c

subroutine build_ke_operator_coo_c(temp, p, phi, nlev, nlat, keep_poles, &
                                   row_idx, col_idx, values, nnz, max_nnz) &
                                   bind(C, name="build_ke_operator_coo_c")
    type(c_ptr), value, intent(in) :: temp, p, phi, row_idx, col_idx, values
    integer(c_int), value, intent(in) :: nlev, nlat, keep_poles, max_nnz
    integer(c_int), intent(out) :: nnz
    real(c_double), pointer :: temp_view(:, :), p_view(:), phi_view(:), values_view(:)
    integer(c_int), pointer :: row_view(:), col_view(:)

    call c_f_pointer(temp, temp_view, [int(nlev), int(nlat)])
    call c_f_pointer(p, p_view, [int(nlev)])
    call c_f_pointer(phi, phi_view, [int(nlat)])
    call c_f_pointer(row_idx, row_view, [int(max_nnz)])
    call c_f_pointer(col_idx, col_view, [int(max_nnz)])
    call c_f_pointer(values, values_view, [int(max_nnz)])

    call build_ke_operator_coo(temp_view, p_view, phi_view, int(nlev), int(nlat), int(keep_poles), &
                               row_view, col_view, values_view, nnz, int(max_nnz))
end subroutine build_ke_operator_coo_c

subroutine compute_qgpv_balance_terms_c(temp, v_mean, f_friction, q_diabatic, vt_eddy, vu_eddy, &
                                        p, phi, nlev, nlat, momentum_term, thermal_term) &
                                        bind(C, name="compute_qgpv_balance_terms_c")
    type(c_ptr), value, intent(in) :: temp, v_mean, f_friction, q_diabatic, vt_eddy, vu_eddy
    type(c_ptr), value, intent(in) :: p, phi, momentum_term, thermal_term
    integer(c_int), value, intent(in) :: nlev, nlat
    real(c_double), pointer :: temp_view(:, :), v_view(:, :), friction_view(:, :)
    real(c_double), pointer :: q_view(:, :), vt_view(:, :), vu_view(:, :)
    real(c_double), pointer :: p_view(:), phi_view(:), momentum_view(:, :), thermal_view(:, :)

    call c_f_pointer(temp, temp_view, [int(nlev), int(nlat)])
    call c_f_pointer(v_mean, v_view, [int(nlev), int(nlat)])
    call c_f_pointer(f_friction, friction_view, [int(nlev), int(nlat)])
    call c_f_pointer(q_diabatic, q_view, [int(nlev), int(nlat)])
    call c_f_pointer(vt_eddy, vt_view, [int(nlev), int(nlat)])
    call c_f_pointer(vu_eddy, vu_view, [int(nlev), int(nlat)])
    call c_f_pointer(p, p_view, [int(nlev)])
    call c_f_pointer(phi, phi_view, [int(nlat)])
    call c_f_pointer(momentum_term, momentum_view, [int(nlev), int(nlat)])
    call c_f_pointer(thermal_term, thermal_view, [int(nlev), int(nlat)])

    call compute_QGPV_balance_terms(temp_view, v_view, friction_view, q_view, vt_view, vu_view, &
                                    p_view, phi_view, int(nlev), int(nlat), momentum_view, thermal_view)
end subroutine compute_qgpv_balance_terms_c

subroutine sor_solve_ke_c(temp, p, phi, rhs, nlev, nlat, nrhs, keep_poles, &
                          omega, tol, max_iter, solutions, iterations, residuals, status) &
                          bind(C, name="sor_solve_ke_c")
    type(c_ptr), value, intent(in) :: temp, p, phi, rhs, solutions, iterations, residuals, status
    integer(c_int), value, intent(in) :: nlev, nlat, nrhs, keep_poles, max_iter
    real(c_double), value, intent(in) :: omega, tol
    real(c_double), pointer :: temp_view(:, :), p_view(:), phi_view(:), rhs_view(:, :, :)
    real(c_double), pointer :: solution_view(:, :, :), residual_view(:)
    integer(c_int), pointer :: iteration_view(:), status_view(:)

    call c_f_pointer(temp, temp_view, [int(nlev), int(nlat)])
    call c_f_pointer(p, p_view, [int(nlev)])
    call c_f_pointer(phi, phi_view, [int(nlat)])
    call c_f_pointer(rhs, rhs_view, [int(nlev), int(nlat), int(nrhs)])
    call c_f_pointer(solutions, solution_view, [int(nlev), int(nlat), int(nrhs)])
    call c_f_pointer(iterations, iteration_view, [int(nrhs)])
    call c_f_pointer(residuals, residual_view, [int(nrhs)])
    call c_f_pointer(status, status_view, [int(nrhs)])

    call sor_solve_ke(temp_view, p_view, phi_view, rhs_view, int(nlev), int(nlat), int(nrhs), &
                      int(keep_poles), omega, tol, int(max_iter), &
                      solution_view, iteration_view, residual_view, status_view)
end subroutine sor_solve_ke_c

subroutine sor_solve_coo_c(row_coo, col_coo, val_coo, rhs, n, nnz, nrhs, &
                           omega, tol, max_iter, solutions, iterations, residuals, status) &
                           bind(C, name="sor_solve_coo_c")
    type(c_ptr), value, intent(in) :: row_coo, col_coo, val_coo, rhs
    type(c_ptr), value, intent(in) :: solutions, iterations, residuals, status
    integer(c_int), value, intent(in) :: n, nnz, nrhs, max_iter
    real(c_double), value, intent(in) :: omega, tol
    integer(c_int), pointer :: row_view(:), col_view(:), iteration_view(:), status_view(:)
    real(c_double), pointer :: val_view(:), rhs_view(:, :), solution_view(:, :), residual_view(:)

    call c_f_pointer(row_coo, row_view, [int(nnz)])
    call c_f_pointer(col_coo, col_view, [int(nnz)])
    call c_f_pointer(val_coo, val_view, [int(nnz)])
    call c_f_pointer(rhs, rhs_view, [int(n), int(nrhs)])
    call c_f_pointer(solutions, solution_view, [int(n), int(nrhs)])
    call c_f_pointer(iterations, iteration_view, [int(nrhs)])
    call c_f_pointer(residuals, residual_view, [int(nrhs)])
    call c_f_pointer(status, status_view, [int(nrhs)])

    call sor_solve_coo(row_view, col_view, val_view, rhs_view, int(n), int(nnz), int(nrhs), &
                       omega, tol, int(max_iter), solution_view, iteration_view, residual_view, status_view)
end subroutine sor_solve_coo_c

end module kuoeliassen_bindings_mod
