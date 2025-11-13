# GitHub Actions CI/CD 配置说明

本项目使用 GitHub Actions 自动构建和发布多平台 Python wheels。

## 工作流概述

### 1. `build-wheels.yml` - Wheel 构建和发布

**触发条件:**
- 推送到 `main` 或 `dev` 分支
- 创建 Pull Request
- 创建带 `v*` 前缀的标签(如 `v0.1.0`)
- GitHub Release 发布
- 手动触发

**支持平台:**
- **Linux:** x86_64 (manylinux_2_28)
- **macOS:** x86_64 (Intel) 和 arm64 (Apple Silicon)
- **Windows:** x64

**支持 Python 版本:**
- Python 3.9, 3.10, 3.11, 3.12, 3.13

**构建流程:**
1. 使用 `cibuildwheel` 为每个平台和 Python 版本构建 wheel
2. 自动安装所需的 Fortran 编译器(gfortran)
3. 上传构建的 wheels 作为 artifacts
4. 构建源代码分发包(sdist)
5. 在 Release 时自动发布到 PyPI

### 2. `test.yml` - 多平台测试

**触发条件:**
- 推送到 `main` 或 `dev` 分支
- 创建 Pull Request
- 手动触发

**测试矩阵:**
- 操作系统: Ubuntu, macOS, Windows
- Python 版本: 3.9, 3.10, 3.11, 3.12

**测试流程:**
1. 在每个平台上安装 Fortran 编译器
2. 从源码构建并安装包
3. 运行测试套件
4. 生成代码覆盖率报告
5. 上传覆盖率到 Codecov(仅 Ubuntu + Python 3.11)

## 使用指南

### 本地开发构建

```bash
# 安装构建依赖
pip install build meson ninja

# 构建 wheel
python -m build

# 安装开发模式
pip install -e .
```

### 发布新版本

1. **更新版本号**
   编辑 `pyproject.toml` 中的 `version` 字段:
   ```toml
   [project]
   version = "0.2.0"
   ```

2. **创建 Git 标签**
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. **GitHub 自动构建**
   - GitHub Actions 会自动触发 wheel 构建
   - 所有平台的 wheels 会作为 artifacts 上传

4. **创建 GitHub Release**
   - 在 GitHub 上创建新的 Release
   - 关联 tag `v0.2.0`
   - 自动触发 PyPI 发布

5. **自动发布到 PyPI**
   - 需要在 GitHub Secrets 中设置 `PYPI_API_TOKEN`
   - Wheels 和 sdist 自动上传到 PyPI

### 配置 PyPI 发布

1. **获取 PyPI API Token**
   - 访问 https://pypi.org/manage/account/token/
   - 创建新的 API token
   - 命名为 "GitHub Actions - KuoEliassen"

2. **添加到 GitHub Secrets**
   - 访问项目的 Settings → Secrets and variables → Actions
   - 创建新 secret:
     - Name: `PYPI_API_TOKEN`
     - Value: 粘贴 PyPI token

### 配置 Codecov(可选)

1. **获取 Codecov Token**
   - 访问 https://codecov.io/
   - 关联 GitHub 账号
   - 添加仓库并获取 token

2. **添加到 GitHub Secrets**
   - 创建新 secret:
     - Name: `CODECOV_TOKEN`
     - Value: 粘贴 Codecov token

## 工作流详解

### Fortran 编译器配置

**Linux (manylinux):**
```yaml
dnf install -y gcc-gfortran
```

**macOS:**
```yaml
brew install gcc
export FC=gfortran-13
```

**Windows (msys2):**
```yaml
choco install msys2
pacman -Sy mingw-w64-x86_64-gcc-fortran
```

### Wheel 修复

- **Windows:** 使用 `delvewheel` 修复 DLL 依赖
- **macOS:** 设置 `MACOSX_DEPLOYMENT_TARGET` 确保兼容性
- **Linux:** 使用 `manylinux_2_28` 镜像保证兼容性

### 测试命令

构建的 wheels 会通过以下命令测试:
```python
import kuoeliassen
from kuoeliassen import solve_ke
from kuoeliassen.xarray_interface import solve_ke_xarray
print('Import test passed')
```

## 手动触发构建

可以在 GitHub Actions 页面手动触发工作流:
1. 进入 Actions 标签页
2. 选择 "Build and publish wheels"
3. 点击 "Run workflow"
4. 选择分支并输入原因
5. 点击 "Run workflow"

## 下载构建的 Wheels

构建完成后,可以从 Actions 页面下载 artifacts:
1. 进入 Actions 标签页
2. 选择具体的 workflow run
3. 向下滚动到 "Artifacts" 部分
4. 下载所需的 wheel 文件

## 故障排查

### 构建失败

1. **Fortran 编译器问题**
   - 检查编译器是否正确安装
   - 查看工作流日志中的编译器版本

2. **Meson 构建失败**
   - 确保 `meson.build` 文件正确配置
   - 检查 Fortran 源文件路径

3. **测试失败**
   - 检查导入路径是否正确
   - 验证 Fortran 模块是否正确编译

### Windows 特定问题

- 确保 gfortran 在 PATH 中
- 可能需要手动设置 `FC=gfortran CC=gcc`

### macOS 特定问题

- Apple Silicon (M1/M2) 需要 `MACOSX_DEPLOYMENT_TARGET=14.0`
- Intel Mac 使用 `MACOSX_DEPLOYMENT_TARGET=13.0`

## 参考资源

- [cibuildwheel 文档](https://cibuildwheel.readthedocs.io/)
- [meson-python 文档](https://meson-python.readthedocs.io/)
- [PyPI 发布指南](https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
