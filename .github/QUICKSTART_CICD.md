# GitHub Actions CI/CD 快速开始

本文档介绍如何为 KuoEliassen 项目配置和使用 GitHub Actions CI/CD 系统。

## 前置条件

1. **GitHub 账户**: 确保你有 GitHub 账户并且拥有项目的推送权限
2. **PyPI 账户**(可选): 如果需要发布到 PyPI,需要注册账户并获取 API token

## 第一次配置步骤

### 1. 推送代码到 GitHub

```bash
# 如果还没有初始化 git 仓库
git init
git add .
git commit -m "Initial commit with CI/CD configuration"

# 添加远程仓库(替换为你的仓库地址)
git remote add origin https://github.com/YOUR_USERNAME/KuoEliassen.git

# 推送到 GitHub
git push -u origin main
```

### 2. 验证 GitHub Actions

1. 访问你的 GitHub 仓库
2. 点击 "Actions" 标签页
3. 你应该看到两个工作流:
   - **Build and publish wheels**: 构建多平台 wheels
   - **Tests**: 运行测试

4. 第一次推送后,workflows 会自动运行
5. 点击工作流查看运行状态和日志

### 3. 配置 PyPI 发布(可选)

如果你想自动发布到 PyPI:

#### 3.1 获取 PyPI API Token

1. 访问 https://pypi.org/manage/account/token/
2. 登录你的 PyPI 账户
3. 创建新的 API token:
   - Token 名称: "GitHub Actions - KuoEliassen"
   - 范围: "Entire account" 或特定项目
4. **重要**: 复制生成的 token(只显示一次!)

#### 3.2 添加 Secret 到 GitHub

1. 访问你的 GitHub 仓库
2. 进入 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. 添加 secret:
   - Name: `PYPI_API_TOKEN`
   - Value: 粘贴你的 PyPI API token
5. 点击 **Add secret**

### 4. 配置 Codecov(可选)

如果你想跟踪代码覆盖率:

#### 4.1 设置 Codecov

1. 访问 https://codecov.io/
2. 使用 GitHub 账户登录
3. 添加你的 KuoEliassen 仓库
4. 获取 **Repository Upload Token**

#### 4.2 添加 Codecov Token

1. 在 GitHub 仓库的 **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**
3. 添加:
   - Name: `CODECOV_TOKEN`
   - Value: 粘贴 Codecov token
4. 点击 **Add secret**

## 日常工作流程

### 开发和测试

```bash
# 创建新分支
git checkout -b feature/new-feature

# 进行代码修改
# ...

# 提交更改
git add .
git commit -m "Add new feature"

# 推送到 GitHub
git push origin feature/new-feature
```

**自动触发**: 推送代码会自动触发测试工作流

### 创建 Pull Request

1. 在 GitHub 上创建 Pull Request
2. CI/CD 会自动运行所有测试
3. 检查测试结果(绿色✓或红色✗)
4. 如果测试失败,查看日志并修复
5. 合并 PR 到 main 分支

### 发布新版本

#### 步骤 1: 更新版本号

编辑 `pyproject.toml`:
```toml
[project]
name = "KuoEliassen"
version = "0.2.0"  # 更新版本号
```

同时更新 `src/kuoeliassen/__init__.py`:
```python
__version__ = "0.2.0"
```

#### 步骤 2: 提交更改

```bash
git add pyproject.toml src/kuoeliassen/__init__.py
git commit -m "Bump version to 0.2.0"
git push origin main
```

#### 步骤 3: 创建 Git 标签

```bash
# 创建带注释的标签
git tag -a v0.2.0 -m "Release version 0.2.0"

# 推送标签到 GitHub
git push origin v0.2.0
```

**自动触发**: 推送标签会触发 wheel 构建工作流

#### 步骤 4: 创建 GitHub Release

1. 访问 GitHub 仓库的 "Releases" 页面
2. 点击 "Create a new release"
3. 选择标签: `v0.2.0`
4. 填写 Release 标题: "Version 0.2.0"
5. 添加更新说明(changelog)
6. 点击 "Publish release"

**自动触发**: 创建 Release 会触发 PyPI 发布工作流

#### 步骤 5: 验证发布

1. 检查 GitHub Actions 页面,确保发布成功
2. 访问 PyPI 页面: https://pypi.org/project/KuoEliassen/
3. 验证新版本是否可用

## 下载构建的 Wheels

即使不发布到 PyPI,你也可以下载构建的 wheels:

1. 访问 GitHub Actions 页面
2. 选择 "Build and publish wheels" 工作流
3. 点击最近的成功运行
4. 向下滚动到 "Artifacts" 部分
5. 下载需要的 wheel 文件:
   - `wheel-cp39-manylinux_x86_64`
   - `wheel-cp310-win_amd64`
   - 等等...

6. 解压并安装:
```bash
pip install KuoEliassen-0.2.0-cp310-cp310-win_amd64.whl
```

## 手动触发 CI/CD

有时你可能需要手动触发构建:

1. 访问 GitHub Actions 页面
2. 选择工作流(Build wheels 或 Tests)
3. 点击 "Run workflow" 按钮
4. 选择分支
5. (可选)输入触发原因
6. 点击 "Run workflow"

## 查看构建日志

如果构建失败,查看日志来诊断问题:

1. 访问 GitHub Actions 页面
2. 点击失败的工作流运行(红色✗)
3. 点击失败的 job
4. 展开失败的 step 查看详细日志
5. 常见问题:
   - **Fortran 编译器**: 检查 gfortran 是否正确安装
   - **Meson 构建**: 查看 meson.build 配置
   - **测试失败**: 检查代码逻辑错误

## 支持的平台和 Python 版本

当前 CI/CD 配置支持:

**操作系统**:
- ✅ Linux (Ubuntu 22.04, manylinux_2_28)
- ✅ macOS Intel (macOS 13)
- ✅ macOS Apple Silicon (macOS 14)
- ✅ Windows (Windows Server 2022)

**Python 版本**:
- ✅ Python 3.9
- ✅ Python 3.10
- ✅ Python 3.11
- ✅ Python 3.12
- ✅ Python 3.13

**总共**: 4 平台 × 5 Python 版本 = 20 个 wheel 文件

## 常见问题

### Q: 为什么我的 wheel 构建失败?

**A**: 检查以下几点:
1. Fortran 代码是否有语法错误?
2. `meson.build` 配置是否正确?
3. 依赖项是否正确安装?
4. 查看 GitHub Actions 日志获取详细错误信息

### Q: 如何禁用某个平台的构建?

**A**: 编辑 `.github/workflows/build-wheels.yml`,在 `matrix.buildplat` 中注释掉不需要的平台:

```yaml
matrix:
  buildplat:
    - [ubuntu-22.04, manylinux_x86_64]
    # - [windows-2022, win_amd64]  # 禁用 Windows
```

### Q: 如何添加新的 Python 版本?

**A**: 编辑 `matrix.python` 列表:

```yaml
matrix:
  python: ["cp39", "cp310", "cp311", "cp312", "cp313", "cp314"]
```

### Q: PyPI 发布失败怎么办?

**A**: 检查:
1. `PYPI_API_TOKEN` secret 是否正确设置?
2. Token 是否有权限发布到该项目?
3. 版本号是否已经存在于 PyPI?(不能重复发布相同版本)

### Q: 如何跳过 CI/CD?

**A**: 在 commit 消息中添加 `[skip ci]` 或 `[ci skip]`:

```bash
git commit -m "Update README [skip ci]"
```

## 进阶配置

### 添加代码质量检查

你可以添加更多的检查工具:
- `black` - 代码格式化
- `flake8` - 代码风格检查
- `mypy` - 类型检查
- `isort` - import 排序

示例工作流步骤:
```yaml
- name: Run code quality checks
  run: |
    pip install black flake8 mypy isort
    black --check src/
    flake8 src/
    mypy src/
    isort --check-only src/
```

### 添加性能测试

```yaml
- name: Run performance benchmarks
  run: |
    pip install pytest-benchmark
    pytest tests/benchmark_test.py --benchmark-only
```

## 资源链接

- [cibuildwheel 文档](https://cibuildwheel.readthedocs.io/)
- [meson-python 文档](https://meson-python.readthedocs.io/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [PyPI 发布教程](https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

## 获取帮助

如果遇到问题:
1. 查看 [Issues](https://github.com/YOUR_USERNAME/KuoEliassen/issues)
2. 创建新的 Issue 描述问题
3. 包含相关的日志输出
