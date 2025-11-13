# KuoEliassen 构建指南

## 环境准备

### 使用 skyborn_dev 环境

```powershell
# 激活 conda 环境
conda activate skyborn_dev

# 确认编译器可用
gcc --version
gfortran --version
python --version
```

### 安装构建依赖

```powershell
pip install meson ninja numpy scipy xarray
```

## 方法 1: 使用 pip 构建(推荐)

这种方法最简单,自动调用 meson:

```powershell
cd F:\KuoEliassen

# 开发模式安装(可编辑)
pip install -e . -v

# 或者生产模式安装
pip install . -v
```

构建产物:
- 编译的 `.pyd` 文件会自动安装到 Python site-packages
- 使用 `-e` 时,`.pyd` 文件在 `build/` 目录

## 方法 2: 使用 Meson 手动构建

如果需要更多控制,可以直接使用 meson:

### 步骤 1: 配置构建目录

```powershell
cd F:\KuoEliassen

# 配置构建(release 模式)
meson setup builddir --buildtype=release

# 或者 debug 模式(用于调试)
meson setup builddir --buildtype=debug

# 查看配置选项
meson configure builddir
```

### 步骤 2: 编译

```powershell
# 使用 meson 编译
meson compile -C builddir

# 或者直接使用 ninja
ninja -C builddir

# 并行编译(使用 4 个核心)
ninja -C builddir -j4
```

### 步骤 3: 查看编译产物

```powershell
# 编译后的文件在这里
dir builddir\src\kuoeliassen\*.pyd
```

输出类似:
```
ke_fortran.cp311-win_amd64.pyd
```

### 步骤 4: 安装(可选)

```powershell
# 安装到 Python site-packages
meson install -C builddir

# 或者指定安装目录
meson install -C builddir --destdir="安装目录"
```

## 方法 3: 开发模式(In-place 构建)

在源代码目录直接编译,方便测试:

```powershell
cd F:\KuoEliassen

# 配置
meson setup builddir --prefix=$PWD/install

# 编译
ninja -C builddir

# 手动复制 .pyd 到源代码目录
copy builddir\src\kuoeliassen\ke_fortran.*.pyd src\kuoeliassen\

# 测试
python -c "import sys; sys.path.insert(0, 'src'); import kuoeliassen; print(kuoeliassen.__version__)"
```

## 编译选项说明

### 优化级别

```powershell
# Release (O3 优化)
meson setup builddir --buildtype=release

# Debug (无优化,调试符号)
meson setup builddir --buildtype=debug

# Debug 优化(O2 + 调试符号)
meson setup builddir --buildtype=debugoptimized
```

### 特定编译器

```powershell
# 指定 gfortran 版本
FC=gfortran-12 meson setup builddir

# 指定 gcc 版本
CC=gcc-12 FC=gfortran-12 meson setup builddir
```

### OpenMP 控制

```powershell
# 禁用 OpenMP
meson setup builddir -Dopenmp=disabled

# 强制使用 OpenMP
meson setup builddir -Dopenmp=enabled
```

## 清理构建

```powershell
# 删除构建目录
rm -r builddir

# 清理 pip 构建缓存
pip cache purge
rm -r build/ dist/ *.egg-info/
```

## 验证编译结果

### 测试 Fortran 模块

```python
import sys
sys.path.insert(0, r'F:\KuoEliassen\src')

# 导入 Fortran 模块
from kuoeliassen import ke_fortran

# 查看可用函数
print(dir(ke_fortran))
# 应该输出: ['build_ke_operator_coo', 'compute_rhs_components', ...]

# 测试简单调用
import numpy as np
field = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
p = np.array([100000., 85000., 70000., 50000., 30000.])
grad = ke_fortran.vertical_gradient(field, p)
print(f"Gradient: {grad}")
```

### 测试完整求解器

```python
from kuoeliassen import solve_ke
from kuoeliassen.core import FORTRAN_AVAILABLE

print(f"Fortran 可用: {FORTRAN_AVAILABLE}")

if FORTRAN_AVAILABLE:
    # 生成测试数据
    nlev, nlat = 20, 32
    temp = 250 + 30 * np.random.rand(nlev, nlat)
    u = 10 * np.random.randn(nlev, nlat)
    v = 2 * np.random.randn(nlev, nlat)
    heating = 1e-5 * np.random.randn(nlev, nlat)
    p = np.linspace(100000, 10000, nlev)
    lat = np.linspace(-60, 60, nlat)
    
    # 求解
    result = solve_ke(temp, u, v, heating, p, lat)
    print(f"PSI shape: {result['PSI'].shape}")
    print(f"PSI range: [{result['PSI'].min():.2e}, {result['PSI'].max():.2e}]")
```

## 编译参数说明

根据 Skyborn 项目优化后的参数:

### Fortran 参数
- `-O3`: 最高优化级别
- `-fPIC`: 位置无关代码(动态库必需)
- `-fno-second-underscore`: 符号命名规范
- `-funroll-loops`: 循环展开
- `-finline-functions`: 内联函数
- `-ftree-vectorize`: 向量化优化
- `-ffree-line-length-none`: 无行长度限制
- `-fno-common`: 变量处理方式
- `-std=legacy`: Fortran 遗留标准(兼容老代码)
- `-fopenmp`: OpenMP 并行(如果可用)

### 平台特定优化
- **Apple Silicon**: `-march=armv8-a -mtune=apple-m1`
- **Windows/Linux**: `-march=x86-64 -mtune=generic`

**注意**: 不再使用 `-march=native`,保证二进制可移植性

### 移除的参数
- ❌ `-march=native`: 会绑定到特定 CPU,不可移植
- ❌ `-ffinite-math-only`: 不支持 NaN/Inf,我们的数据可能有缺测值

## 故障排除

### 问题 1: 找不到 gfortran

```powershell
# 检查环境
where gfortran

# 如果没找到,确认 skyborn_dev 环境激活
conda activate skyborn_dev
conda list | Select-String gcc
```

### 问题 2: fortranobject.c 未找到

```python
# 查找 fortranobject.c 位置
python -c "import numpy.f2py; print(numpy.f2py.get_include())"
python -c "import numpy, os; print(os.path.join(numpy.__path__[0], 'f2py', 'src', 'fortranobject.c'))"
```

### 问题 3: f2py 版本不兼容

```powershell
# 查看 numpy 和 f2py 版本
python -c "import numpy; print(numpy.__version__)"
python -m numpy.f2py --help

# 如果有问题,更新 numpy
pip install --upgrade numpy
```

### 问题 4: OpenMP 链接错误

```powershell
# Windows MSYS2 环境可能需要
# 在 skyborn_dev 中应该已经配置好了
conda list | Select-String openmp
```

### 问题 5: 编译时符号未定义

这通常是 fortranobject.c 未正确添加,检查 meson 输出:

```
...
Found fortranobject.c: C:\...\fortranobject.c
Added fortranobject.c to build
...
```

## 性能验证

编译完成后,运行性能测试:

```powershell
cd F:\KuoEliassen
python examples/benchmark.py
```

预期输出:
```
Testing Small (20×32):
  Mean time: 0.150 ± 0.010 s
  
Testing CMIP6-like (39×128):
  Mean time: 0.800 ± 0.050 s
```

## 与原始 Python 代码对比

```python
# 使用原始 solve_KE_equation.py
import sys
sys.path.insert(0, r'I:\KuoEliassen')
from solve_KE_equation import solve_KE_equation

# 使用新的 Fortran 版本
sys.path.insert(0, r'F:\KuoEliassen\src')
from kuoeliassen import solve_ke

# 准备相同的测试数据
# ... (数据准备)

# 对比时间和结果
import time

start = time.time()
result_py = solve_KE_equation(...)
time_py = time.time() - start

start = time.time()
result_fortran = solve_ke(...)
time_fortran = time.time() - start

print(f"Python 时间: {time_py:.3f}s")
print(f"Fortran 时间: {time_fortran:.3f}s")
print(f"加速比: {time_py/time_fortran:.1f}×")

# 检查数值一致性
diff = np.abs(result_py['PSI'] - result_fortran['PSI'])
print(f"最大差异: {diff.max():.2e}")
print(f"相对误差: {(diff/np.abs(result_py['PSI']).max()).max():.2e}")
```

---

**推荐流程**: `pip install -e . -v` → 验证 → 使用
