# Office Assistant

Windows 10 x64 目标环境的内网办公助手 MVP。当前仓库实现的是**可离线开发的本地纵向切片**：Tkinter 工作台、本地 JSON 配置/任务存储、模拟模型、模拟 MCP、内网 URL 策略和三个样例处理器。

## 当前运行

```bash
python -m office_assistant
```

当前界面使用模拟服务，不会访问外网。真实 Qwen3.6/vLLM 和 SSE MCP 连接必须在单位内网部署测试阶段配置。

## 测试

```bash
python -m unittest discover -s tests -v
```

## 数据目录

安装目录和用户数据目录分离。开发机默认使用 `~/.office-assistant/`；Windows 目标环境使用 `%LOCALAPPDATA%\\Office Assistant\\`。正式安装目录目标为 `D:\\Program Files\\Office Assistant\\`。

## 当前限制

- 首批 Excel 处理只支持 `DEMO-TASK-1.0` 样例模板；不执行宏、公式或外部链接。
- 文稿整理当前先输出本地草稿；不自动发送、提交或覆盖原文件。
- 制度检索当前使用本地文本/Word 内容；引用仍需人工复核。
- `SseMcpClient` 已提供连接、动态消息端点检查、JSON-RPC 和 `tools/list`/`tools/call` 适配，但真实 SSE 服务联调待现场部署。
- Windows 离线打包链已加入 `scripts/`、`packaging/windows/` 和 `docs/windows-offline-build.md`；当前 macOS 开发环境不能生成 Windows EXE，必须在 Windows 10 x64 构建机执行。
- 真实 Windows 安装包尚未生成和现场验收；不要把脚本存在等同于安装包已经可交付。

> 当前开发容器若 Python 未编译 `_tkinter`，后端测试仍可运行；启动 GUI 时会给出明确提示。Windows 目标机需使用包含 Tk 的 Python 运行时，现场安装验证再确认这一点。

## Windows 离线打包

打包链使用 **CPython 3.12 x64 + PyInstaller onedir + Inno Setup 6.3+**。
先在可信联网 Windows 构建机执行 `scripts/prepare-windows-offline.ps1` 准备固定 wheel，
再把整个 `offline-bundle` 和源码带到断网 Windows 构建机，执行 `scripts/build-windows.ps1`。

```powershell
.\scripts\build-windows.ps1 -Python 'C:\Python312\python.exe' `
  -BundleDir '.\offline-bundle' `
  -Iscc 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
```

安装器目标为 `D:\Program Files\Office Assistant\`，日常运行使用普通用户，
配置和任务记录写入 `%LOCALAPPDATA%\Office Assistant\`。详细流程和现场验收清单见
`docs/windows-offline-build.md`。
