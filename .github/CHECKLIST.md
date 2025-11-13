# 🚀 GitHub Actions CI/CD 部署检查清单

使用此检查清单确保 CI/CD 系统正确配置和运行。

## ✅ 第一步: 推送到 GitHub (必需)

```bash
# 1. 检查当前状态
git status

# 2. 添加所有新文件
git add .

# 3. 提交
git commit -m "Add GitHub Actions CI/CD configuration"

# 4. 推送到 GitHub (如果还没有远程仓库,先添加)
git remote add origin https://github.com/YOUR_USERNAME/KuoEliassen.git
git push -u origin main
```

**验证:**
- [ ] 代码已成功推送到 GitHub
- [ ] 可以在 GitHub 网页上看到 `.github/workflows/` 目录

---

## ✅ 第二步: 验证 CI/CD 工作流

### 2.1 检查 Actions 是否启用

1. [ ] 访问 `https://github.com/YOUR_USERNAME/KuoEliassen`
2. [ ] 点击 **"Actions"** 标签页
3. [ ] 确认你看到以下工作流:
   - [ ] "Build and publish wheels"
   - [ ] "Tests"

### 2.2 查看首次运行

首次推送代码后,GitHub Actions 会自动运行:

1. [ ] 点击 **"Tests"** 工作流
2. [ ] 查看最近的运行记录
3. [ ] 检查运行状态:
   - 🟢 绿色勾号 = 成功
   - 🔴 红色叉号 = 失败
   - 🟡 黄色圆点 = 运行中

4. [ ] 点击具体的运行查看详细日志

**预期结果:**
- 测试工作流应该在所有平台上运行
- 可能需要 10-20 分钟完成全部 12 个测试配置

### 2.3 查看构建日志(如果失败)

如果有失败的任务:

1. [ ] 点击失败的工作流运行(红色 ✗)
2. [ ] 点击失败的 job(例如 "Test on ubuntu-latest with Python 3.11")
3. [ ] 展开失败的步骤
4. [ ] 阅读错误信息
5. [ ] 根据错误修复代码

**常见问题:**
- Fortran 编译错误 → 检查 Fortran 代码语法
- 导入错误 → 检查模块路径
- 测试失败 → 检查测试逻辑

---

## ✅ 第三步: 配置 PyPI 发布 (可选但推荐)

### 3.1 注册 PyPI 账户

1. [ ] 访问 https://pypi.org/account/register/
2. [ ] 创建账户并验证邮箱
3. [ ] 登录 PyPI

### 3.2 创建 PyPI API Token

1. [ ] 访问 https://pypi.org/manage/account/token/
2. [ ] 点击 **"Add API token"**
3. [ ] 填写表单:
   - Token name: `GitHub Actions - KuoEliassen`
   - Scope: `Entire account` (首次) 或 `Project: KuoEliassen`
4. [ ] 点击 **"Add token"**
5. [ ] **立即复制 token**(只显示一次!)
   ```
   pypi-AgEIcHlwaS5vcmc...
   ```

### 3.3 添加 Token 到 GitHub

1. [ ] 访问 `https://github.com/YOUR_USERNAME/KuoEliassen/settings/secrets/actions`
2. [ ] 点击 **"New repository secret"**
3. [ ] 添加 secret:
   - Name: `PYPI_API_TOKEN`
   - Value: 粘贴刚才复制的 token
4. [ ] 点击 **"Add secret"**

**验证:**
- [ ] 在 Secrets 列表中可以看到 `PYPI_API_TOKEN`

---

## ✅ 第四步: 配置 Codecov (可选)

### 4.1 设置 Codecov 账户

1. [ ] 访问 https://codecov.io/
2. [ ] 使用 GitHub 账户登录
3. [ ] 授权 Codecov 访问你的仓库

### 4.2 添加仓库

1. [ ] 在 Codecov 仪表板点击 **"Add new repository"**
2. [ ] 搜索并选择 `KuoEliassen`
3. [ ] 点击 **"Setup repo"**
4. [ ] 复制显示的 **Repository Upload Token**

### 4.3 添加 Token 到 GitHub

1. [ ] 访问 GitHub Secrets 页面
2. [ ] 点击 **"New repository secret"**
3. [ ] 添加:
   - Name: `CODECOV_TOKEN`
   - Value: 粘贴 Codecov token
4. [ ] 点击 **"Add secret"**

**验证:**
- [ ] Secrets 中有 `CODECOV_TOKEN`
- [ ] 下次测试运行后,Codecov 会显示覆盖率报告

---

## ✅ 第五步: 更新 README 徽章

编辑 `README.md`,替换 `YOUR_USERNAME` 为你的 GitHub 用户名:

```markdown
[![Build Wheels](https://github.com/YOUR_USERNAME/KuoEliassen/actions/workflows/build-wheels.yml/badge.svg)](https://github.com/YOUR_USERNAME/KuoEliassen/actions/workflows/build-wheels.yml)
[![Tests](https://github.com/YOUR_USERNAME/KuoEliassen/actions/workflows/test.yml/badge.svg)](https://github.com/YOUR_USERNAME/KuoEliassen/actions/workflows/test.yml)
```

**提交更改:**
```bash
git add README.md
git commit -m "Update CI/CD badges with correct username"
git push
```

**验证:**
- [ ] README 中的徽章显示为绿色(通过)或红色(失败)
- [ ] 点击徽章可以跳转到 Actions 页面

---

## ✅ 第六步: 测试 Wheel 构建

### 6.1 手动触发构建

1. [ ] 访问 Actions → **"Build and publish wheels"**
2. [ ] 点击 **"Run workflow"**
3. [ ] 选择 `main` 分支
4. [ ] 输入原因: "Testing wheel builds"
5. [ ] 点击 **"Run workflow"**

### 6.2 等待构建完成

- [ ] 观察构建进度(约 30-60 分钟,因为要构建 20 个 wheels)
- [ ] 检查是否所有平台都成功

### 6.3 下载并测试 Wheel

1. [ ] 构建成功后,滚动到 **"Artifacts"** 部分
2. [ ] 下载一个 wheel,例如:
   - `wheel-cp311-win_amd64` (Windows, Python 3.11)
3. [ ] 解压并安装:
   ```bash
   pip install KuoEliassen-0.1.0-cp311-cp311-win_amd64.whl
   ```
4. [ ] 测试导入:
   ```python
   import kuoeliassen
   from kuoeliassen import solve_ke
   print("✓ Import successful!")
   ```

**验证:**
- [ ] Wheel 可以成功安装
- [ ] 模块可以正常导入
- [ ] 没有 DLL 或依赖错误

---

## ✅ 第七步: 首次发布测试

### 7.1 准备版本 0.1.0

1. [ ] 确认 `pyproject.toml` 中版本号为 `0.1.0`
2. [ ] 确认 `__init__.py` 中 `__version__ = "0.1.0"`
3. [ ] 提交所有更改:
   ```bash
   git add .
   git commit -m "Prepare for v0.1.0 release"
   git push
   ```

### 7.2 创建 Git 标签

```bash
# 创建带注释的标签
git tag -a v0.1.0 -m "Release version 0.1.0 - Initial release with CI/CD"

# 推送标签到 GitHub
git push origin v0.1.0
```

**验证:**
- [ ] GitHub 上可以看到新标签
- [ ] Wheel 构建工作流自动触发

### 7.3 创建 GitHub Release

1. [ ] 访问 `https://github.com/YOUR_USERNAME/KuoEliassen/releases`
2. [ ] 点击 **"Draft a new release"**
3. [ ] 选择标签: `v0.1.0`
4. [ ] 填写 Release 信息:
   ```
   标题: Version 0.1.0
   
   描述:
   ## 🎉 First Release
   
   ### Features
   - High-performance Kuo-Eliassen solver with Fortran backend
   - NumPy and xarray interfaces
   - Multi-platform support (Linux/macOS/Windows)
   - Python 3.9-3.13 support
   
   ### CI/CD
   - Automated wheel building for all platforms
   - Comprehensive testing on multiple configurations
   ```
5. [ ] 点击 **"Publish release"**

### 7.4 验证 PyPI 发布(如果配置了 PYPI_API_TOKEN)

1. [ ] 访问 Actions 查看 "publish" job 状态
2. [ ] 如果成功,访问 https://pypi.org/project/KuoEliassen/
3. [ ] 验证版本 0.1.0 已经发布
4. [ ] 测试从 PyPI 安装:
   ```bash
   pip install KuoEliassen
   python -c "import kuoeliassen; print(kuoeliassen.__version__)"
   ```

**验证:**
- [ ] PyPI 上可以看到新版本
- [ ] 可以使用 `pip install KuoEliassen` 安装
- [ ] 所有 wheels 都已上传(约 21 个文件)

---

## ✅ 第八步: 日常使用检查

### 8.1 提交代码

```bash
# 正常的开发流程
git add .
git commit -m "Add new feature"
git push
```

**自动触发:**
- [ ] Tests 工作流自动运行
- [ ] 所有测试在多平台上执行

### 8.2 创建 Pull Request

1. [ ] 创建新分支开发
2. [ ] 推送分支到 GitHub
3. [ ] 创建 Pull Request
4. [ ] CI/CD 自动运行测试
5. [ ] 查看测试结果再合并

**验证:**
- [ ] PR 页面显示 CI/CD 状态
- [ ] 可以点击 "Details" 查看详细日志

### 8.3 发布新版本

发布流程(例如 v0.2.0):

1. [ ] 更新版本号(pyproject.toml 和 __init__.py)
2. [ ] 提交: `git commit -m "Bump version to 0.2.0"`
3. [ ] 推送: `git push`
4. [ ] 创建标签: `git tag v0.2.0 && git push origin v0.2.0`
5. [ ] 创建 GitHub Release
6. [ ] 自动发布到 PyPI

**验证:**
- [ ] GitHub Release 已创建
- [ ] Wheels 已构建
- [ ] PyPI 已更新

---

## 📊 完整性检查表

### GitHub 配置
- [ ] `.github/workflows/build-wheels.yml` 存在
- [ ] `.github/workflows/test.yml` 存在
- [ ] `.github/CICD_README.md` 存在
- [ ] `.github/QUICKSTART_CICD.md` 存在
- [ ] `.github/SUMMARY.md` 存在

### 代码配置
- [ ] `tests/test_basic.py` 存在并包含基础测试
- [ ] `requirements.txt` 包含所有依赖
- [ ] `pyproject.toml` 版本号正确
- [ ] `__init__.py` 版本号与 pyproject.toml 一致

### GitHub Actions
- [ ] Actions 已启用
- [ ] 至少运行过一次 Tests 工作流
- [ ] 至少运行过一次 Build wheels 工作流
- [ ] 所有徽章显示正确状态

### Secrets(可选)
- [ ] `PYPI_API_TOKEN` 已配置(用于发布)
- [ ] `CODECOV_TOKEN` 已配置(用于覆盖率)

### PyPI(可选)
- [ ] PyPI 账户已创建
- [ ] 项目名称 `KuoEliassen` 可用
- [ ] API token 已创建并添加到 GitHub

---

## 🎯 成功标准

全部完成后,你应该能够:

✅ **自动化测试**
- 每次推送代码都会自动运行测试
- 测试覆盖 Linux/macOS/Windows × Python 3.9-3.12

✅ **自动化构建**
- 可以构建 20 个不同的 wheel 文件
- 支持所有主流平台和 Python 版本

✅ **自动化发布**
- 创建 GitHub Release 时自动发布到 PyPI
- 用户可以直接 `pip install KuoEliassen`

✅ **可维护性**
- CI/CD 徽章显示项目状态
- 详细的日志帮助诊断问题
- 文档完整,易于理解

---

## 🆘 遇到问题?

### 查看文档
1. `.github/CICD_README.md` - 详细技术说明
2. `.github/QUICKSTART_CICD.md` - 分步骤教程
3. `.github/SUMMARY.md` - 配置总览

### 常见问题
- **构建失败**: 查看 Actions 日志,检查 Fortran 编译
- **测试失败**: 检查代码逻辑,确保导入路径正确
- **PyPI 发布失败**: 检查 token 和版本号

### 获取帮助
- 查看 GitHub Actions 文档
- 搜索 cibuildwheel 问题
- 创建 GitHub Issue 描述问题

---

## 🎉 恭喜!

如果你完成了所有步骤,你现在拥有一个:
- ✨ 专业级的 CI/CD 流程
- 🚀 可以自动发布的 Python 包
- 🌍 支持所有主流平台
- 📦 完整的测试和构建系统

准备好开发和发布你的 KuoEliassen 项目了! 🚀
