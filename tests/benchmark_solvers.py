import time
import tracemalloc
import numpy as np
import xarray as xr
import os
from kuoeliassen import solve_ke


def benchmark():
    print("="*60)
    print("KuoEliassen Solver Benchmark: LU vs SOR")
    print("="*60)

    # 1. Load Data
    data_path = os.path.join("examples", "example_data.nc")
    print(f"Loading data from: {data_path}")

    try:
        ds = xr.open_dataset(data_path).sel(latitude=slice(-89.9, 89.9))
    except FileNotFoundError:
        print(f"Error: File not found at {data_path}")
        # Create dummy data for testing if file missing
        print("Generating synthetic data instead...")
        nlev, nlat = 30, 180
        p = np.linspace(100, 100000, nlev)
        lat = np.linspace(-89.9, 89.9, nlat)
        v = np.zeros((nlev, nlat))
        temp = np.ones((nlev, nlat)) * 250.0
        vt = np.zeros((nlev, nlat))
        vu = np.zeros((nlev, nlat))
        heating = np.ones((nlev, nlat)) * 1e-4
    else:
        # Prepare data as per user's method
        v = ds['v'].fillna(0.0).values
        temp = ds['temperature'].fillna(200.0).values
        vt = ds['vt_eddy'].fillna(0.0).values
        vu = ds['vu_eddy'].fillna(0.0).values
        p = ds['pressure'].values
        lat = ds['latitude'].values
        if 'diabatic_heating' in ds:
            heating = ds['diabatic_heating'].fillna(0.0).values
        else:
            heating = np.zeros_like(temp)

    print(f"Grid Dimensions: {len(p)} levels x {len(lat)} latitudes")
    print("-" * 60)

    # 2. Benchmark LU Solver
    print("Running LU Solver (Direct)...")
    tracemalloc.start()
    t0 = time.perf_counter()

    # Run solver
    res_lu = solve_ke(v, temp, vt, vu, p, lat, heating=heating, solver='lu')

    t_lu = time.perf_counter() - t0
    _, peak_lu = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    psi_lu = res_lu['PSI']
    print(f"  Time:        {t_lu:.6f} s")
    print(f"  Peak Memory: {peak_lu / 1024**2:.2f} MB")

    # 3. Benchmark SOR Solver
    print("\nRunning SOR Solver (Iterative, omega=1.8)...")
    tracemalloc.start()
    t0 = time.perf_counter()

    # Run solver
    res_sor = solve_ke(v, temp, vt, vu, p, lat, heating=heating,
                       solver='sor', omega=1.8, tol=1e-8, max_iter=50000)

    t_sor = time.perf_counter() - t0
    _, peak_sor = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    psi_sor = res_sor['PSI']
    print(f"  Time:        {t_sor:.6f} s")
    print(f"  Peak Memory: {peak_sor / 1024**2:.2f} MB")

    # 4. Comparison
    print("-" * 60)
    print("Comparison Results:")

    # Accuracy
    abs_diff = np.abs(psi_lu - psi_sor)
    max_diff = np.max(abs_diff)
    mean_psi = np.mean(np.abs(psi_lu))
    rel_diff = max_diff / (np.max(np.abs(psi_lu)) + 1e-20)

    print(f"  Max Absolute Diff: {max_diff:.4e} kg/s")
    print(f"  Max Relative Diff: {rel_diff:.4e}")

    # Speedup
    if t_sor < t_lu:
        speedup = t_lu / t_sor
        print(f"  Speed: SOR is {speedup:.2f}x FASTER than LU")
    else:
        slowdown = t_sor / t_lu
        print(f"  Speed: SOR is {slowdown:.2f}x SLOWER than LU")

    # Memory
    mem_ratio = peak_lu / peak_sor if peak_sor > 0 else 0
    print(f"  Memory: LU used {mem_ratio:.2f}x more memory than SOR")

    print("="*60)


if __name__ == "__main__":
    benchmark()
