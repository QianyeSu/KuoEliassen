# KuoEliassen

[![Build Wheels](https://github.com/YOUR_USERNAME/KuoEliassen/actions/workflows/build-wheels.yml/badge.svg)](https://github.com/YOUR_USERNAME/KuoEliassen/actions/workflows/build-wheels.yml)
[![Tests](https://github.com/YOUR_USERNAME/KuoEliassen/actions/workflows/test.yml/badge.svg)](https://github.com/YOUR_USERNAME/KuoEliassen/actions/workflows/test.yml)
[![PyPI version](https://badge.fury.io/py/KuoEliassen.svg)](https://badge.fury.io/py/KuoEliassen)
[![Python Version](https://img.shields.io/pypi/pyversions/KuoEliassen)](https://pypi.org/project/KuoEliassen/)

High-Performance Kuo-Eliassen Circulation Solver with Fortran Backend

## 特性

- 🚀 **高性能 Fortran 后端**: 使用 f2py 编译的 Fortran 核心代码
- 🌍 **多平台支持**: Linux, macOS (Intel & Apple Silicon), Windows
- 📦 **预编译 Wheels**: 支持 Python 3.9-3.13
- 🔧 **灵活的 API**: 支持 NumPy 数组和 xarray DataArray
- 🧪 **完整测试**: 多平台 CI/CD 自动化测试

## 安装

### 从 PyPI 安装(推荐)

```bash
pip install KuoEliassen
```

### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/KuoEliassen.git
cd KuoEliassen

# 安装依赖
pip install -r requirements.txt

# 安装开发模式
pip install -e .
```

## 快速开始

### NumPy 接口

```python
import numpy as np
from kuoeliassen import solve_ke

# 准备输入数据
v_mean = ...      # 经向风 (nz, ny, nt)
temperature = ... # 温度 (nz, ny, nt)
heating = ...     # 加热率 (nz, ny, nt)
vt_eddy = ...     # 涡旋热通量 (nz, ny, nt)
vu_eddy = ...     # 涡旋动量通量 (nz, ny, nt)
p = ...           # 气压坐标 (nz,)
phi = ...         # 纬度坐标 (ny,)

# 求解 Kuo-Eliassen 方程
result = solve_ke(
    v_mean=v_mean,
    temperature=temperature,
    heating=heating,
    vt_eddy=vt_eddy,
    vu_eddy=vu_eddy,
    p=p,
    phi=phi,
    qgpv=True
)

# 结果包含
# PSI_Q: 总加热引起的流函数
# D_vt: 热通量强迫
# D_vu: 动量通量强迫
# 等等...
```

### xarray 接口

```python
import xarray as xr
from kuoeliassen.xarray_interface import solve_ke_xarray

# 从 xarray Dataset 读取数据
ds = xr.open_dataset('atmospheric_data.nc')

# 求解(自动处理坐标)
result_ds = solve_ke_xarray(
    v_mean=ds['v'],
    temperature=ds['temp'],
    heating=ds['heating'],
    vt_eddy=ds['vt_eddy'],
    vu_eddy=ds['vu_eddy'],
    qgpv=True
)

# 结果是 xarray Dataset,可以直接绘图或保存
result_ds['PSI_Q'].plot()
```

## 文档

详细文档请参见:
- [使用指南](USAGE_GUIDE.md)
- [构建指南](BUILD_GUIDE.md)
- [CI/CD 配置说明](.github/CICD_README.md)

## 开发

### 设置开发环境

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 生成覆盖率报告
pytest tests/ --cov=kuoeliassen --cov-report=html
```

### 构建 Wheels

```bash
# 安装构建工具
pip install build

# 构建 wheel
python -m build

# Wheel 将在 dist/ 目录中
```

## CI/CD

本项目使用 GitHub Actions 进行持续集成和自动发布:

- **自动测试**: 每次 push 和 PR 都会在多平台运行测试
- **自动构建 Wheels**: 支持 Linux/macOS/Windows × Python 3.9-3.13
- **自动发布到 PyPI**: 创建 GitHub Release 时自动发布

详见 [CI/CD 配置说明](.github/CICD_README.md)

## 许可证

BSD-3-Clause License

## 致谢

感谢 Skyborn 项目提供的 CI/CD 配置参考。