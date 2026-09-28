# GitHub Actions Windows 构建

当前工作流：`.github/workflows/windows-build.yml`，名称 **Windows Build**。
使用 GitHub 提供的 `windows-2022` x64 Runner，手动触发，不因 push 或 PR 自动启动。
目标客户端仍为 Windows 10 x64；云端 Windows Server 构建不替代办公电脑现场验收。

## 1. 提交到仓库

本地 `samples/` 是专门编写的虚构测试材料，单元测试、PyInstaller 和程序自检均依赖它。
它现在不再被 `.gitignore` 忽略。不要在此目录中添加真实内部制度、客户信息或密钥。
`offline-bundle/`、`build/` 等构建生成目录仍然保持忽略。

检查 `git status` 和待提交内容后，将本次修改提交并推送到远程默认分支（当前为 main）。
首次配置需要把 workflow 文件一起推到默认分支；仅把文件留在本地不会启动云端构建。
本方案不要求提供模型、MCP 或个人 GitHub Token，也没有调用内网服务的步骤。

## 2. 手动运行

在仓库 `incoko/Office-Assistant` 中：

1. 打开 **Actions**，如果尚未启用则按仓库策略启用。
2. 选择 **Windows Build**。
3. 选择 **Run workflow**，分支选择 `main`，确认运行。
4. 打开本次运行查看各步骤日志；等待 **Upload installer and portable application** 成功。
5. 在运行详情底部 **Artifacts** 中下载 `OfficeAssistant-windows-x64-<运行编号>-<尝试编号>`。

本工作流的成功产物保留7天（还受仓库/组织上限约束），失败诊断保留3天。
不自动创建 GitHub Release，不上传离线依赖或整个工作区；无需 write 权限。
若账号构建额度或组织策略不允许 Windows Runner，应先在 GitHub 确认相应设置，
不要随意创建 token、关闭安全检查或在日志里粘贴凭据。

## 3. 云端步骤

- 拉取源代码，不持久保存 git 凭据。
- 配置 Python 3.12 x64。
- 在线准备固定版本 wheel 和完整性清单。
- 从 Inno Setup 官方 release 获取固定6.4.3安装器，校验写死的SHA256后安装。
- 复用 `build-windows.ps1`：创建隔离环境、无索引安装、单元测试、PyInstaller打包、
  冻结程序自检、Inno编译安装包、生成SHA256和版本/提交来源记录。
- 只在成功后上传当前构建产物。失败时上传有限日志与自检报告，不上传半成品安装包。

GitHub Runner 本身可以联网；这里的“离线”指交付软件无需在线安装依赖，
及复用脚本的依赖安装阶段使用 `--no-index`，不是证明云端主机处于物理断网状态。
当前没有进行代码签名。

## 4. 下载后的内容

解压 GitHub artifact 外层 ZIP，预计包含：

```text
OfficeAssistant-0.1.0-windows-x64-setup.exe
OfficeAssistant-0.1.0-windows-x64-portable.zip
SHA256SUMS.txt
build-self-check.json
build-provenance.json
dependency-manifest.json
WINDOWS-QUICKSTART.txt
```

版本取自 `office_assistant/__init__.py`。安装版用 `setup.exe`；便携版需整体解压，
不能只复制 EXE 而丢弃 `_internal`。按单位允许的方式将产物转入内网，管理员安装后，
由普通用户启动应用和自检。见 `docs/windows-offline-build.md` 的现场验收清单。

云端自检验证 Tk、用户目录、打包样例和页面初始化，**不是 vLLM/MCP 已连通证明**。

## 5. 出错时

- 未出现 Windows Build / Run workflow：检查 workflow 是否已推送到远程默认分支、
  Actions 是否启用，以及账号是否有运行权限。
- 缺少 `samples`：确认9个虚构材料文件已随提交推送，而不仅移除了忽略规则。
- 依赖下载或 Inno 下载失败：查看对应准备步骤，确认是网络、文件校验还是包版本错误。
  校验失败不能跳过验证去执行下载内容。
- 测试或自检失败：查看 Tests/build 日志及 `windows-build-diagnostics-...`。
- 编译安装器失败：查看编译器的具体错误和本次源码提交。
- 上传失败或未生成安装包：不要把日志中的中间文件当作发布产物。

反馈错误时提供步骤名称及相关日志即可，隐藏账号凭据和真实内网配置。
本地 YAML/静态检查不等于云端流程已运行成功；首次运行结果仍待验证。
