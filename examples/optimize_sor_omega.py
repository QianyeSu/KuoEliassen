"""
SOR Relaxation Factor (Omega) Optimization Script
Find the optimal Omega parameter for the Kuo-Eliassen equation solver
to minimize the number of iterations.
"""
import time
import numpy as np
import xarray as xr
import kuoeliassen.kuoeliassen_module as km
from kuoeliassen import solve_ke


def optimize_omega():
    print("=" * 80)
    print("KuoEliassen SOR Omega Parameter Search")
    print("=" * 80)

    # Load example data
    data = xr.open_dataset("example_data.nc").sel(latitude=slice(-89.9, 89.9))

    # Extract variables and apply reasonable fill values
    V = data['v'].fillna(0.0).values  # Wind can be 0
    T = data['temperature'].fillna(200.0).values  # Temperature minimum ~200K
    heating = data['diabatic_heating'].fillna(0.0).values  # Heating can be 0
    vt_eddy = data['vt_eddy'].fillna(0.0).values  # Eddy flux can be 0
    vu_eddy = data['vu_eddy'].fillna(0.0).values  # Eddy flux can be 0
    plev = data['pressure'].values
    latitude = data['latitude'].values

    # Compute RHS
    result = solve_ke(v=V, temperature=T, heating=heating, vt_eddy=vt_eddy,
                      vu_eddy=vu_eddy, pressure=plev, latitude=latitude)
    D_total = result["D"]

    # Prepare SOR input
    lat_rad = np.deg2rad(latitude).astype(np.float64)
    T_f = np.asfortranarray(T, dtype=np.float64)
    p_f = np.ascontiguousarray(plev, dtype=np.float64)
    rhs_sor = np.asfortranarray(D_total[:, :, np.newaxis], dtype=np.float64)
    keep_poles = 1
    tol = 1e-10
    max_iter = 100000

    # Search for optimal Omega
    print(f"\n{'Omega':<8} | {'Iterations':<12} | {'Time (s)':<10}")
    print("-" * 40)

    omegas_to_test = np.concatenate([
        np.linspace(1.0, 1.6, 7),
        np.linspace(1.65, 1.95, 7)
    ])

    results = []
    for omega in omegas_to_test:
        t0 = time.perf_counter()
        solutions, iterations, residuals, status = km.sor_solve_ke(
            T_f, p_f, lat_rad, rhs_sor, keep_poles, omega, tol, max_iter
        )
        t_cost = time.perf_counter() - t0
        iters = iterations[0]
        print(f"{omega:<8.2f} | {iters:<12} | {t_cost:<10.4f}")
        results.append((omega, iters, t_cost))

    # Summary
    best_res = min(results, key=lambda x: x[1])
    print("-" * 40)
    print(f"\nOptimal Omega: {best_res[0]:.2f}")
    print(f"Minimum iterations: {best_res[1]}")
    print(f"Time cost: {best_res[2]:.4f} s")

    # Visualization
    print("\n[Iteration Trend]")
    max_iter_plot = max(r[1] for r in results)
    for omega, iters, _ in results:
        bar_len = int((iters / max_iter_plot) * 40)
        print(f"{omega:.2f} | {'#' * bar_len} ({iters})")


if __name__ == "__main__":
    optimize_omega()
