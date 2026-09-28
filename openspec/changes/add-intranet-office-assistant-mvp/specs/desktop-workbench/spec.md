## ADDED Requirements

### Requirement: Unified task workbench
系统 SHALL 提供通用任务对话、智能体选择和文稿整理、表格检查、制度查询三个快捷入口；快捷入口 SHALL 使用与自定义智能体相同的任务运行时。

#### Scenario: Start a preset task without technical configuration
- **WHEN** 用户已导入有效预配置并选择文稿整理入口
- **THEN** 系统展示材料输入与任务操作，不要求编辑 JSON 或安装开发工具，并在统一任务列表展示执行进度和结果

### Requirement: Basic and advanced configuration experiences
系统 SHALL 同时支持使用预置助手和在高级设置中管理模型、智能体及扩展，并明确界面模式不是组织级管理员权限。

#### Scenario: Customize without changing a preset
- **WHEN** 用户在高级设置复制预置助手并修改名称与角色指令
- **THEN** 新助手可在工作台选择，原预置助手保持不变，运行时安全策略不因进入高级设置而放宽

### Requirement: Offline deployment and manual updates
客户端 SHALL 在确认的 Windows 10 x64、8GB 内存目标环境中通过管理员运行的离线安装程序安装到 `D:\Program Files\Office Assistant\`，完成启动和预置资源加载，不依赖已安装开发环境或外网下载；客户端日常运行 SHALL 允许普通用户启动且不要求管理员权限；用户数据 SHALL 存放在当前用户可写目录；更新 SHALL 通过离线安装包进行。

#### Scenario: Administrator installs and a standard user runs the client
- **WHEN** 管理员在 Windows 10 x64、8GB 内存电脑上运行离线安装程序并安装到 `D:\Program Files\Office Assistant\`，随后普通用户启动应用
- **THEN** 安装能够完成，用户数据目录可写，客户端可由普通用户启动并使用本地界面；运行时不因安装程序的管理员权限而获得额外文件、网络或工具执行权限

#### Scenario: Install on a clean disconnected workstation
- **WHEN** 目标电脑未安装开发工具且外网不可达，用户按已确认的权限安装应用
- **THEN** 应用能够启动、打开本地界面并使用预置资源，仅模型任务需要连接已配置的内网服务

#### Scenario: Missing model configuration
- **WHEN** 用户首次启动且尚无可用内网模型配置
- **THEN** 系统允许查看本地界面与高级设置，清楚提示模型功能未就绪，不请求公共模型服务

### Requirement: Local task history and artifact access
系统 SHALL 本地保存任务状态和产物信息，提供预览、打开产物位置及清理任务记录的入口，清理与卸载不得删除用户源文件或显式导出的产物。

#### Scenario: Restart and inspect a completed task
- **WHEN** 用户重启客户端并打开已完成任务
- **THEN** 系统显示本地结果与产物位置，产物已被外部移走时明确提示文件不存在

#### Scenario: Clear history without deleting user files
- **WHEN** 用户确认清理任务记录
- **THEN** 系统清除选定的本地任务记录及应用管理的关联临时数据，保留用户源文件和显式导出的产物
