#define PY_SSIZE_T_CLEAN

#include <Python.h>
#include <numpy/arrayobject.h>

#ifndef _PyCFunction_CAST
#define _PyCFunction_CAST(func) ((PyCFunction)(void (*)(void))(func))
#endif

void vertical_gradient_c(void *field, void *p, int nlev, void *grad);
void meridional_gradient_coeff_c(void *phi, int nlat, void *dphi_array);
void meridional_gradient_2d_c(void *field, void *phi, double radius, int nlev, int nlat, void *grad);
void vertical_gradient_2d_c(void *field, void *p, int nlev, int nlat, void *grad);
void compute_rhs_components_c(void *v_mean, void *temp, void *latent_heating, void *rad_heating,
                              void *vt_eddy, void *vu_eddy, void *p, void *phi,
                              int nlev, int nlat, int keep_poles,
                              void *d_dtcond, void *d_rad, void *d_vt,
                              void *d_vu, void *d_x, void *f_friction);
void build_ke_operator_coo_c(void *temp, void *p, void *phi, int nlev, int nlat,
                             int keep_poles, void *row_idx, void *col_idx,
                             void *values, int *nnz, int max_nnz);
void compute_qgpv_balance_terms_c(void *temp, void *v_mean, void *f_friction,
                                  void *q_diabatic, void *vt_eddy, void *vu_eddy,
                                  void *p, void *phi, int nlev, int nlat,
                                  void *momentum_term, void *thermal_term);
void sor_solve_ke_c(void *temp, void *p, void *phi, void *rhs, int nlev, int nlat,
                    int nrhs, int keep_poles, double omega, double tol, int max_iter,
                    void *solutions, void *iterations, void *residuals, void *status);
void sor_solve_coo_c(void *row_coo, void *col_coo, void *val_coo, void *rhs,
                     int n, int nnz, int nrhs, double omega, double tol, int max_iter,
                     void *solutions, void *iterations, void *residuals, void *status);

static PyArrayObject *as_double_1d(PyObject *obj, const char *name) {
    PyArrayObject *arr = (PyArrayObject *)PyArray_FROM_OTF(
        obj, NPY_FLOAT64,
        NPY_ARRAY_ALIGNED | NPY_ARRAY_C_CONTIGUOUS | NPY_ARRAY_FORCECAST);
    if (arr == NULL) {
        return NULL;
    }
    if (PyArray_NDIM(arr) != 1) {
        PyErr_Format(PyExc_ValueError, "%s must be a 1D float64 array", name);
        Py_DECREF(arr);
        return NULL;
    }
    return arr;
}

static PyArrayObject *as_double_2d_fortran(PyObject *obj, const char *name) {
    PyArrayObject *arr = (PyArrayObject *)PyArray_FROM_OTF(
        obj, NPY_FLOAT64,
        NPY_ARRAY_ALIGNED | NPY_ARRAY_F_CONTIGUOUS | NPY_ARRAY_FORCECAST);
    if (arr == NULL) {
        return NULL;
    }
    if (PyArray_NDIM(arr) != 2) {
        PyErr_Format(PyExc_ValueError, "%s must be a 2D float64 Fortran-contiguous array", name);
        Py_DECREF(arr);
        return NULL;
    }
    return arr;
}

static PyArrayObject *as_double_3d_fortran(PyObject *obj, const char *name) {
    PyArrayObject *arr = (PyArrayObject *)PyArray_FROM_OTF(
        obj, NPY_FLOAT64,
        NPY_ARRAY_ALIGNED | NPY_ARRAY_F_CONTIGUOUS | NPY_ARRAY_FORCECAST);
    if (arr == NULL) {
        return NULL;
    }
    if (PyArray_NDIM(arr) != 3) {
        PyErr_Format(PyExc_ValueError, "%s must be a 3D float64 Fortran-contiguous array", name);
        Py_DECREF(arr);
        return NULL;
    }
    return arr;
}

static PyArrayObject *as_int32_1d(PyObject *obj, const char *name) {
    PyArrayObject *arr = (PyArrayObject *)PyArray_FROM_OTF(
        obj, NPY_INT32,
        NPY_ARRAY_ALIGNED | NPY_ARRAY_C_CONTIGUOUS | NPY_ARRAY_FORCECAST);
    if (arr == NULL) {
        return NULL;
    }
    if (PyArray_NDIM(arr) != 1) {
        PyErr_Format(PyExc_ValueError, "%s must be a 1D int32 array", name);
        Py_DECREF(arr);
        return NULL;
    }
    return arr;
}

static int same_2d_shape(PyArrayObject *a, PyArrayObject *b) {
    return PyArray_DIM(a, 0) == PyArray_DIM(b, 0) && PyArray_DIM(a, 1) == PyArray_DIM(b, 1);
}

static int check_2d_shape(PyArrayObject *arr, npy_intp nlev, npy_intp nlat, const char *name) {
    if (PyArray_DIM(arr, 0) != nlev || PyArray_DIM(arr, 1) != nlat) {
        PyErr_Format(PyExc_ValueError, "%s shape mismatch", name);
        return -1;
    }
    return 0;
}

static PyArrayObject *empty_double_fortran(int ndim, npy_intp *dims) {
    return (PyArrayObject *)PyArray_EMPTY(ndim, dims, NPY_FLOAT64, 1);
}

static PyObject *py_vertical_gradient(PyObject *self, PyObject *args) {
    PyObject *field_obj = NULL, *p_obj = NULL;
    PyArrayObject *field = NULL, *p = NULL, *grad = NULL;
    npy_intp dims[1];
    (void)self;

    if (!PyArg_ParseTuple(args, "OO", &field_obj, &p_obj)) {
        return NULL;
    }
    field = as_double_1d(field_obj, "field");
    p = as_double_1d(p_obj, "p");
    if (field == NULL || p == NULL) {
        goto fail;
    }
    if (PyArray_DIM(field, 0) != PyArray_DIM(p, 0)) {
        PyErr_SetString(PyExc_ValueError, "field and p length mismatch");
        goto fail;
    }
    dims[0] = PyArray_DIM(field, 0);
    grad = empty_double_fortran(1, dims);
    if (grad == NULL) {
        goto fail;
    }
    vertical_gradient_c(PyArray_DATA(field), PyArray_DATA(p), (int)dims[0], PyArray_DATA(grad));
    Py_DECREF(field);
    Py_DECREF(p);
    return (PyObject *)grad;

fail:
    Py_XDECREF(field);
    Py_XDECREF(p);
    Py_XDECREF(grad);
    return NULL;
}

static PyObject *py_meridional_gradient_coeff(PyObject *self, PyObject *args) {
    PyObject *phi_obj = NULL;
    PyArrayObject *phi = NULL, *out = NULL;
    npy_intp dims[1];
    (void)self;

    if (!PyArg_ParseTuple(args, "O", &phi_obj)) {
        return NULL;
    }
    phi = as_double_1d(phi_obj, "phi");
    if (phi == NULL) {
        return NULL;
    }
    dims[0] = PyArray_DIM(phi, 0);
    out = empty_double_fortran(1, dims);
    if (out == NULL) {
        Py_DECREF(phi);
        return NULL;
    }
    meridional_gradient_coeff_c(PyArray_DATA(phi), (int)dims[0], PyArray_DATA(out));
    Py_DECREF(phi);
    return (PyObject *)out;
}

static PyObject *py_meridional_gradient_2d(PyObject *self, PyObject *args) {
    PyObject *field_obj = NULL, *phi_obj = NULL;
    PyArrayObject *field = NULL, *phi = NULL, *grad = NULL;
    double radius;
    npy_intp dims[2];
    (void)self;

    if (!PyArg_ParseTuple(args, "OOd", &field_obj, &phi_obj, &radius)) {
        return NULL;
    }
    field = as_double_2d_fortran(field_obj, "field");
    phi = as_double_1d(phi_obj, "phi");
    if (field == NULL || phi == NULL) {
        goto fail;
    }
    if (PyArray_DIM(field, 1) != PyArray_DIM(phi, 0)) {
        PyErr_SetString(PyExc_ValueError, "field latitude dimension and phi length mismatch");
        goto fail;
    }
    dims[0] = PyArray_DIM(field, 0);
    dims[1] = PyArray_DIM(field, 1);
    grad = empty_double_fortran(2, dims);
    if (grad == NULL) {
        goto fail;
    }
    meridional_gradient_2d_c(PyArray_DATA(field), PyArray_DATA(phi), radius,
                             (int)dims[0], (int)dims[1], PyArray_DATA(grad));
    Py_DECREF(field);
    Py_DECREF(phi);
    return (PyObject *)grad;

fail:
    Py_XDECREF(field);
    Py_XDECREF(phi);
    Py_XDECREF(grad);
    return NULL;
}

static PyObject *py_vertical_gradient_2d(PyObject *self, PyObject *args) {
    PyObject *field_obj = NULL, *p_obj = NULL;
    PyArrayObject *field = NULL, *p = NULL, *grad = NULL;
    npy_intp dims[2];
    (void)self;

    if (!PyArg_ParseTuple(args, "OO", &field_obj, &p_obj)) {
        return NULL;
    }
    field = as_double_2d_fortran(field_obj, "field");
    p = as_double_1d(p_obj, "p");
    if (field == NULL || p == NULL) {
        goto fail;
    }
    if (PyArray_DIM(field, 0) != PyArray_DIM(p, 0)) {
        PyErr_SetString(PyExc_ValueError, "field level dimension and p length mismatch");
        goto fail;
    }
    dims[0] = PyArray_DIM(field, 0);
    dims[1] = PyArray_DIM(field, 1);
    grad = empty_double_fortran(2, dims);
    if (grad == NULL) {
        goto fail;
    }
    vertical_gradient_2d_c(PyArray_DATA(field), PyArray_DATA(p),
                           (int)dims[0], (int)dims[1], PyArray_DATA(grad));
    Py_DECREF(field);
    Py_DECREF(p);
    return (PyObject *)grad;

fail:
    Py_XDECREF(field);
    Py_XDECREF(p);
    Py_XDECREF(grad);
    return NULL;
}

static PyObject *py_compute_rhs_components(PyObject *self, PyObject *args) {
    PyObject *v_obj = NULL, *temp_obj = NULL, *latent_obj = NULL, *rad_obj = NULL;
    PyObject *vt_obj = NULL, *vu_obj = NULL, *p_obj = NULL, *phi_obj = NULL;
    PyArrayObject *v = NULL, *temp = NULL, *latent = NULL, *rad = NULL;
    PyArrayObject *vt = NULL, *vu = NULL, *p = NULL, *phi = NULL;
    PyArrayObject *d_dtcond = NULL, *d_rad = NULL, *d_vt = NULL, *d_vu = NULL, *d_x = NULL, *friction = NULL;
    int keep_poles;
    npy_intp dims[2], nlev, nlat;
    (void)self;

    if (!PyArg_ParseTuple(args, "OOOOOOOOi", &v_obj, &temp_obj, &latent_obj, &rad_obj,
                          &vt_obj, &vu_obj, &p_obj, &phi_obj, &keep_poles)) {
        return NULL;
    }
    v = as_double_2d_fortran(v_obj, "v_mean");
    temp = as_double_2d_fortran(temp_obj, "temp");
    latent = as_double_2d_fortran(latent_obj, "latent_heating");
    rad = as_double_2d_fortran(rad_obj, "rad_heating");
    vt = as_double_2d_fortran(vt_obj, "vt_eddy");
    vu = as_double_2d_fortran(vu_obj, "vu_eddy");
    p = as_double_1d(p_obj, "p");
    phi = as_double_1d(phi_obj, "phi");
    if (v == NULL || temp == NULL || latent == NULL || rad == NULL || vt == NULL || vu == NULL || p == NULL || phi == NULL) {
        goto fail;
    }
    nlev = PyArray_DIM(v, 0);
    nlat = PyArray_DIM(v, 1);
    if (!same_2d_shape(v, temp) || !same_2d_shape(v, latent) || !same_2d_shape(v, rad) ||
        !same_2d_shape(v, vt) || !same_2d_shape(v, vu) ||
        PyArray_DIM(p, 0) != nlev || PyArray_DIM(phi, 0) != nlat) {
        PyErr_SetString(PyExc_ValueError, "compute_rhs_components input shape mismatch");
        goto fail;
    }
    dims[0] = nlev;
    dims[1] = nlat;
    d_dtcond = empty_double_fortran(2, dims);
    d_rad = empty_double_fortran(2, dims);
    d_vt = empty_double_fortran(2, dims);
    d_vu = empty_double_fortran(2, dims);
    d_x = empty_double_fortran(2, dims);
    friction = empty_double_fortran(2, dims);
    if (d_dtcond == NULL || d_rad == NULL || d_vt == NULL || d_vu == NULL || d_x == NULL || friction == NULL) {
        goto fail;
    }
    compute_rhs_components_c(PyArray_DATA(v), PyArray_DATA(temp), PyArray_DATA(latent), PyArray_DATA(rad),
                             PyArray_DATA(vt), PyArray_DATA(vu), PyArray_DATA(p), PyArray_DATA(phi),
                             (int)nlev, (int)nlat, keep_poles,
                             PyArray_DATA(d_dtcond), PyArray_DATA(d_rad), PyArray_DATA(d_vt),
                             PyArray_DATA(d_vu), PyArray_DATA(d_x), PyArray_DATA(friction));
    Py_DECREF(v);
    Py_DECREF(temp);
    Py_DECREF(latent);
    Py_DECREF(rad);
    Py_DECREF(vt);
    Py_DECREF(vu);
    Py_DECREF(p);
    Py_DECREF(phi);
    return Py_BuildValue("NNNNNN", d_dtcond, d_rad, d_vt, d_vu, d_x, friction);

fail:
    Py_XDECREF(v);
    Py_XDECREF(temp);
    Py_XDECREF(latent);
    Py_XDECREF(rad);
    Py_XDECREF(vt);
    Py_XDECREF(vu);
    Py_XDECREF(p);
    Py_XDECREF(phi);
    Py_XDECREF(d_dtcond);
    Py_XDECREF(d_rad);
    Py_XDECREF(d_vt);
    Py_XDECREF(d_vu);
    Py_XDECREF(d_x);
    Py_XDECREF(friction);
    return NULL;
}

static PyObject *py_build_ke_operator_coo(PyObject *self, PyObject *args) {
    PyObject *temp_obj = NULL, *p_obj = NULL, *phi_obj = NULL;
    PyArrayObject *temp = NULL, *p = NULL, *phi = NULL;
    PyArrayObject *row = NULL, *col = NULL, *values = NULL;
    int keep_poles, max_nnz, nnz = 0;
    npy_intp dims[1], nlev, nlat;
    (void)self;

    if (!PyArg_ParseTuple(args, "OOOii", &temp_obj, &p_obj, &phi_obj, &keep_poles, &max_nnz)) {
        return NULL;
    }
    temp = as_double_2d_fortran(temp_obj, "temp");
    p = as_double_1d(p_obj, "p");
    phi = as_double_1d(phi_obj, "phi");
    if (temp == NULL || p == NULL || phi == NULL) {
        goto fail;
    }
    nlev = PyArray_DIM(temp, 0);
    nlat = PyArray_DIM(temp, 1);
    if (PyArray_DIM(p, 0) != nlev || PyArray_DIM(phi, 0) != nlat) {
        PyErr_SetString(PyExc_ValueError, "build_ke_operator_coo input shape mismatch");
        goto fail;
    }
    if (max_nnz <= 0) {
        PyErr_SetString(PyExc_ValueError, "max_nnz must be positive");
        goto fail;
    }
    dims[0] = max_nnz;
    row = (PyArrayObject *)PyArray_EMPTY(1, dims, NPY_INT32, 1);
    col = (PyArrayObject *)PyArray_EMPTY(1, dims, NPY_INT32, 1);
    values = empty_double_fortran(1, dims);
    if (row == NULL || col == NULL || values == NULL) {
        goto fail;
    }
    build_ke_operator_coo_c(PyArray_DATA(temp), PyArray_DATA(p), PyArray_DATA(phi),
                            (int)nlev, (int)nlat, keep_poles,
                            PyArray_DATA(row), PyArray_DATA(col), PyArray_DATA(values), &nnz, max_nnz);
    Py_DECREF(temp);
    Py_DECREF(p);
    Py_DECREF(phi);
    return Py_BuildValue("NNNi", row, col, values, nnz);

fail:
    Py_XDECREF(temp);
    Py_XDECREF(p);
    Py_XDECREF(phi);
    Py_XDECREF(row);
    Py_XDECREF(col);
    Py_XDECREF(values);
    return NULL;
}

static PyObject *py_compute_qgpv_balance_terms(PyObject *self, PyObject *args) {
    PyObject *temp_obj = NULL, *v_obj = NULL, *friction_obj = NULL, *q_obj = NULL;
    PyObject *vt_obj = NULL, *vu_obj = NULL, *p_obj = NULL, *phi_obj = NULL;
    PyArrayObject *temp = NULL, *v = NULL, *friction = NULL, *q = NULL, *vt = NULL, *vu = NULL;
    PyArrayObject *p = NULL, *phi = NULL, *momentum = NULL, *thermal = NULL;
    npy_intp dims[2], nlev, nlat;
    (void)self;

    if (!PyArg_ParseTuple(args, "OOOOOOOO", &temp_obj, &v_obj, &friction_obj, &q_obj,
                          &vt_obj, &vu_obj, &p_obj, &phi_obj)) {
        return NULL;
    }
    temp = as_double_2d_fortran(temp_obj, "temp");
    v = as_double_2d_fortran(v_obj, "v_mean");
    friction = as_double_2d_fortran(friction_obj, "f_friction");
    q = as_double_2d_fortran(q_obj, "q_diabatic");
    vt = as_double_2d_fortran(vt_obj, "vt_eddy");
    vu = as_double_2d_fortran(vu_obj, "vu_eddy");
    p = as_double_1d(p_obj, "p");
    phi = as_double_1d(phi_obj, "phi");
    if (temp == NULL || v == NULL || friction == NULL || q == NULL || vt == NULL || vu == NULL || p == NULL || phi == NULL) {
        goto fail;
    }
    nlev = PyArray_DIM(temp, 0);
    nlat = PyArray_DIM(temp, 1);
    if (check_2d_shape(v, nlev, nlat, "v_mean") != 0 ||
        check_2d_shape(friction, nlev, nlat, "f_friction") != 0 ||
        check_2d_shape(q, nlev, nlat, "q_diabatic") != 0 ||
        check_2d_shape(vt, nlev, nlat, "vt_eddy") != 0 ||
        check_2d_shape(vu, nlev, nlat, "vu_eddy") != 0 ||
        PyArray_DIM(p, 0) != nlev || PyArray_DIM(phi, 0) != nlat) {
        goto fail;
    }
    dims[0] = nlev;
    dims[1] = nlat;
    momentum = empty_double_fortran(2, dims);
    thermal = empty_double_fortran(2, dims);
    if (momentum == NULL || thermal == NULL) {
        goto fail;
    }
    compute_qgpv_balance_terms_c(PyArray_DATA(temp), PyArray_DATA(v), PyArray_DATA(friction),
                                 PyArray_DATA(q), PyArray_DATA(vt), PyArray_DATA(vu),
                                 PyArray_DATA(p), PyArray_DATA(phi), (int)nlev, (int)nlat,
                                 PyArray_DATA(momentum), PyArray_DATA(thermal));
    Py_DECREF(temp);
    Py_DECREF(v);
    Py_DECREF(friction);
    Py_DECREF(q);
    Py_DECREF(vt);
    Py_DECREF(vu);
    Py_DECREF(p);
    Py_DECREF(phi);
    return Py_BuildValue("NN", momentum, thermal);

fail:
    Py_XDECREF(temp);
    Py_XDECREF(v);
    Py_XDECREF(friction);
    Py_XDECREF(q);
    Py_XDECREF(vt);
    Py_XDECREF(vu);
    Py_XDECREF(p);
    Py_XDECREF(phi);
    Py_XDECREF(momentum);
    Py_XDECREF(thermal);
    return NULL;
}

static PyObject *py_sor_solve_ke(PyObject *self, PyObject *args) {
    PyObject *temp_obj = NULL, *p_obj = NULL, *phi_obj = NULL, *rhs_obj = NULL;
    PyArrayObject *temp = NULL, *p = NULL, *phi = NULL, *rhs = NULL;
    PyArrayObject *solutions = NULL, *iterations = NULL, *residuals = NULL, *status = NULL;
    int keep_poles, max_iter;
    double omega, tol;
    npy_intp dims3[3], dims1[1], nlev, nlat, nrhs;
    (void)self;

    if (!PyArg_ParseTuple(args, "OOOOiddi", &temp_obj, &p_obj, &phi_obj, &rhs_obj,
                          &keep_poles, &omega, &tol, &max_iter)) {
        return NULL;
    }
    temp = as_double_2d_fortran(temp_obj, "temp");
    p = as_double_1d(p_obj, "p");
    phi = as_double_1d(phi_obj, "phi");
    rhs = as_double_3d_fortran(rhs_obj, "rhs");
    if (temp == NULL || p == NULL || phi == NULL || rhs == NULL) {
        goto fail;
    }
    nlev = PyArray_DIM(temp, 0);
    nlat = PyArray_DIM(temp, 1);
    if (PyArray_DIM(p, 0) != nlev || PyArray_DIM(phi, 0) != nlat ||
        PyArray_DIM(rhs, 0) != nlev || PyArray_DIM(rhs, 1) != nlat) {
        PyErr_SetString(PyExc_ValueError, "sor_solve_ke input shape mismatch");
        goto fail;
    }
    nrhs = PyArray_DIM(rhs, 2);
    dims3[0] = nlev;
    dims3[1] = nlat;
    dims3[2] = nrhs;
    dims1[0] = nrhs;
    solutions = empty_double_fortran(3, dims3);
    iterations = (PyArrayObject *)PyArray_EMPTY(1, dims1, NPY_INT32, 1);
    residuals = empty_double_fortran(1, dims1);
    status = (PyArrayObject *)PyArray_EMPTY(1, dims1, NPY_INT32, 1);
    if (solutions == NULL || iterations == NULL || residuals == NULL || status == NULL) {
        goto fail;
    }
    sor_solve_ke_c(PyArray_DATA(temp), PyArray_DATA(p), PyArray_DATA(phi), PyArray_DATA(rhs),
                   (int)nlev, (int)nlat, (int)nrhs, keep_poles, omega, tol, max_iter,
                   PyArray_DATA(solutions), PyArray_DATA(iterations),
                   PyArray_DATA(residuals), PyArray_DATA(status));
    Py_DECREF(temp);
    Py_DECREF(p);
    Py_DECREF(phi);
    Py_DECREF(rhs);
    return Py_BuildValue("NNNN", solutions, iterations, residuals, status);

fail:
    Py_XDECREF(temp);
    Py_XDECREF(p);
    Py_XDECREF(phi);
    Py_XDECREF(rhs);
    Py_XDECREF(solutions);
    Py_XDECREF(iterations);
    Py_XDECREF(residuals);
    Py_XDECREF(status);
    return NULL;
}

static PyObject *py_sor_solve_coo(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *kwlist[] = {
        "row_coo", "col_coo", "val_coo", "rhs", "n", "nnz", "nrhs",
        "omega", "tol", "max_iter", NULL
    };
    PyObject *row_obj = NULL, *col_obj = NULL, *val_obj = NULL, *rhs_obj = NULL;
    PyArrayObject *row = NULL, *col = NULL, *val = NULL, *rhs = NULL;
    PyArrayObject *solutions = NULL, *iterations = NULL, *residuals = NULL, *status = NULL;
    int n, nnz, nrhs, max_iter;
    double omega, tol;
    npy_intp dims2[2], dims1[1];
    (void)self;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOOOiiiddi", kwlist,
                                     &row_obj, &col_obj, &val_obj, &rhs_obj,
                                     &n, &nnz, &nrhs, &omega, &tol, &max_iter)) {
        return NULL;
    }
    row = as_int32_1d(row_obj, "row_coo");
    col = as_int32_1d(col_obj, "col_coo");
    val = as_double_1d(val_obj, "val_coo");
    rhs = as_double_2d_fortran(rhs_obj, "rhs");
    if (row == NULL || col == NULL || val == NULL || rhs == NULL) {
        goto fail;
    }
    if (PyArray_DIM(row, 0) < nnz || PyArray_DIM(col, 0) < nnz || PyArray_DIM(val, 0) < nnz ||
        PyArray_DIM(rhs, 0) != n || PyArray_DIM(rhs, 1) != nrhs) {
        PyErr_SetString(PyExc_ValueError, "sor_solve_coo input shape mismatch");
        goto fail;
    }
    dims2[0] = n;
    dims2[1] = nrhs;
    dims1[0] = nrhs;
    solutions = empty_double_fortran(2, dims2);
    iterations = (PyArrayObject *)PyArray_EMPTY(1, dims1, NPY_INT32, 1);
    residuals = empty_double_fortran(1, dims1);
    status = (PyArrayObject *)PyArray_EMPTY(1, dims1, NPY_INT32, 1);
    if (solutions == NULL || iterations == NULL || residuals == NULL || status == NULL) {
        goto fail;
    }
    sor_solve_coo_c(PyArray_DATA(row), PyArray_DATA(col), PyArray_DATA(val), PyArray_DATA(rhs),
                    n, nnz, nrhs, omega, tol, max_iter,
                    PyArray_DATA(solutions), PyArray_DATA(iterations),
                    PyArray_DATA(residuals), PyArray_DATA(status));
    Py_DECREF(row);
    Py_DECREF(col);
    Py_DECREF(val);
    Py_DECREF(rhs);
    return Py_BuildValue("NNNN", solutions, iterations, residuals, status);

fail:
    Py_XDECREF(row);
    Py_XDECREF(col);
    Py_XDECREF(val);
    Py_XDECREF(rhs);
    Py_XDECREF(solutions);
    Py_XDECREF(iterations);
    Py_XDECREF(residuals);
    Py_XDECREF(status);
    return NULL;
}

static PyMethodDef module_methods[] = {
    {"vertical_gradient", py_vertical_gradient, METH_VARARGS, NULL},
    {"meridional_gradient_coeff", py_meridional_gradient_coeff, METH_VARARGS, NULL},
    {"meridional_gradient_2d", py_meridional_gradient_2d, METH_VARARGS, NULL},
    {"vertical_gradient_2d", py_vertical_gradient_2d, METH_VARARGS, NULL},
    {"compute_rhs_components", py_compute_rhs_components, METH_VARARGS, NULL},
    {"build_ke_operator_coo", py_build_ke_operator_coo, METH_VARARGS, NULL},
    {"compute_qgpv_balance_terms", py_compute_qgpv_balance_terms, METH_VARARGS, NULL},
    {"compute_QGPV_balance_terms", py_compute_qgpv_balance_terms, METH_VARARGS, NULL},
    {"sor_solve_ke", py_sor_solve_ke, METH_VARARGS, NULL},
    {"sor_solve_coo", _PyCFunction_CAST(py_sor_solve_coo), METH_VARARGS | METH_KEYWORDS, NULL},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "kuoeliassen_module",
    NULL,
    -1,
    module_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC PyInit_kuoeliassen_module(void) {
    PyObject *module;

    import_array();
    module = PyModule_Create(&moduledef);
    if (module == NULL) {
        return NULL;
    }
    return module;
}
