# Windows x64 离线打包链

## 状态与范围

构建源：Python/Tk 原型。选用 **PyInstaller onedir + Inno Setup 6.3+**。
所有运行依赖（Python、Tcl/Tk、标准库）进入程序目录；同事电脑不安装 Python。
这是打包链实现，不代表已生成或验收 Windows 安装包。macOS 不能用本链直接生成 Windows EXE。
当前没有代码签名、生产模型接入或完整业务功能；只发布为模拟材料测试版。

固定构建基线：**CPython 3.12 x64**，PyInstaller 6.11.1 及传递依赖见
`packaging/windows/requirements-build.txt`。这些是选定基线，不宣称是最新版本。
使用可信来源的完整 CPython 安装器（包括 Tcl/Tk、pip、venv），不是嵌入式 Python 分发包。
准备机与断网构建机使用相同的 Python 补丁版本；在交付记录中保存 Python 和 Inno 的准确版本。
8GB 是使用者电脑总内存目标，不是本链已经测得的应用占用保证。

## 1. 联网准备（Windows x64）

准备机需已有 Python 3.12 x64 和 Tk，可使用组织认可的依赖镜像。
下载并保留官方 Python 和 Inno Setup 完整安装器，通过发布者签名和独立可信校验值验证，
不要将浏览器页面或在线引导下载器当作离线安装器。这两个工具仅构建人员使用。

从项目根目录用 Windows PowerShell 5.1+ 执行：

```powershell
# Python 必须指向构建机的 3.12 x64 解释器；路径含空格也可。
.\scripts\prepare-windows-offline.ps1 -Python 'C:\Python312\python.exe'
```

此步骤**需要联网**，下载所有固定版本 wheel 到 `offline-bundle\wheels`，不下载源码包、
不运行构建安装脚本。生成 `requirements-build.txt` 和完整文件 SHA256 清单 `manifest.json`。
如果准备失败，保留失败目录用于排查，用 `-BundleDir` 指定一个新目录重试，不自动删除原目录。

复制到内网构建机：
- 项目源代码（含 `samples`、`docs`、`packaging`、`scripts` 和 `tests`）；
- 整个 `offline-bundle`，包括 manifest；
- 上述 Python 与 Inno 离线安装器及其可信校验记录。

manifest 用于防止丢失/意外改动，**不是数字签名**；通过独立渠道保存准备脚本打印的
manifest SHA256，传入时核对。不要依赖可与文件一起被改写的校验表来证明发布者身份。

## 2. 断网构建（Windows x64，有桌面会话）

先离线安装构建工具。Python 勾选 Tcl/Tk、pip；Inno 需6.3或以上6.x版本。
不需要在办公使用者电脑安装构建工具。

```powershell
.\scripts\build-windows.ps1 -Python 'C:\Python312\python.exe' `
  -BundleDir '.\offline-bundle' `
  -Iscc 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
```

若仅验证程序目录：加 `-PortableOnly`，不需要 Inno 编译器。
脚本不会修改 PowerShell 执行策略；如果脚本被阻止，由维护人员按本单位流程授权执行。
不需要对应用用户开放脚本执行权限。

构建过程：
1. 检查 Windows、Python版本、x64架构、Tk 窗口初始化。
2. 校验 offline-bundle 哈希、文件集合以及 requirements 与当前源码一致。
3. 在唯一工作目录创建 venv，使用 `pip --no-index --find-links` 安装，执行 `pip check`。
4. 运行单元测试，PyInstaller 收集 Tk 与样例生成 onedir 应用。
5. 执行冻结程序 `--self-check --require-windows`，失败即停止，不编译安装器。
6. 生成便携ZIP和管理员安装EXE，再生成产物SHA256清单。

任何外部命令非零退出均中止；工作目录唯一，不会重用旧EXE冒充本次构建。
脚本无在线降级安装路径。构建机离线验证仍需实际断网运行，而不仅检查脚本参数。

输出在脚本打印的 `build\windows-<唯一编号>\release\`：

```text
OfficeAssistant-0.1.0-windows-x64-setup.exe
OfficeAssistant-0.1.0-windows-x64-portable.zip
build-self-check.json
dependency-manifest.json
WINDOWS-QUICKSTART.txt
SHA256SUMS.txt
```

程序目录是一个整体，不可只复制 OfficeAssistant.exe 而丢弃 `_internal`。
版本由 `office_assistant/__init__.py` 读取。当前无发布签名、构建产物未自动上传外部服务。
构建自检报告可能含构建机用户数据目录；分发前检查个人路径信息，不含业务正文或密钥。

## 3. 安装行为

- 管理员安装到 `D:\Program Files\Office Assistant`（无D盘时明确另选存在的本地盘）。
- 安装程序创建开始菜单入口、可选桌面快捷方式和卸载入口。
- 应用 EXE 不要求 UAC 提权；安装完成不自动启动，避免以管理员身份产生用户配置。
- 每个实际使用者首次运行时在 `%LOCALAPPDATA%\Office Assistant` 创建自己的目录。
- 不安装 Windows 服务/驱动、不修改防火墙、不安装系统级 Python、不写入实际用户的配置。
- 卸载只处理安装器登记的程序文件；没有递归清除用户数据或输出目录的卸载指令。
- 自定义D盘目录实际ACL需验证；不通过授予 Everyone 写权限解决问题。

安装后自检（普通用户 PowerShell）：

```powershell
$p = Start-Process 'D:\Program Files\Office Assistant\OfficeAssistant.exe' `
  -ArgumentList '--self-check','--require-windows','--show-result' -Wait -PassThru
$p.ExitCode
Get-Content "$env:LOCALAPPDATA\Office Assistant\logs\self-check.json" -Raw
```

也可以从开始菜单“Office Assistant - Self Check”运行。自检失败退出1，全部检查通过退出0。
仅检查平台、目录读写、样例读取和GUI页面初始化；不发出模型/MCP或其他网络请求。
自检界面使用临时状态，不读取/重写实际用户 state.json。

## 4. 现场验收（未完成，不能用静态检查替代）

- [ ] Windows 10 x64、8GB、无Python环境下离线安装。
- [ ] 默认D盘路径含空格；D盘不存在时给出明确提示并能另选目录。
- [ ] 标准用户运行，无UAC提示，配置不写安装目录。
- [ ] 自检通过，六个界面可打开；从非安装目录启动仍可读取打包资源。
- [ ] 实际交互、样例表格/制度/草稿结果及错误提示检查。
- [ ] 记录空闲、文档处理、检索时的内存和响应时间。
- [ ] 卸载后用户数据及导出文件保留；重新安装不清空任务记录。
- [ ] 升级前备份用户状态，验证迁移与回退（本版没有自动迁移承诺）。
- [ ] 断网构建、断网运行，无未授权外联。

真实 vLLM、SSE MCP 和安全验收仍是独立的后续工作。
