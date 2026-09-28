## ADDED Requirements

### Requirement: Deny by default network access
系统 SHALL 仅向部署策略批准的内网模型和 MCP 等必要端点发起请求，校验协议、主机、端口和解析地址，并约束重定向、代理和认证端点；普通配置导入、扩展和模型输出不得扩大允许范围。

#### Scenario: An endpoint redirects to an unapproved host
- **WHEN** 获准服务响应重定向到外网或未批准内网地址
- **THEN** 系统拒绝跟随，不向该目标发送任务内容或凭据，并显示策略拒绝原因

#### Scenario: Policy is absent or resolution changes
- **WHEN** 部署策略缺失，或已配置主机解析到批准范围外的地址
- **THEN** 系统阻止相关连接，不仅凭配置时检查结果放行

### Requirement: Explicit intranet HTTP exception and SSE endpoint validation
系统 SHALL 默认优先 HTTPS，仅允许独立部署策略对特定内网 HTTP 主机、端口及必要路径显式配置例外；普通服务配置不得建立或扩大例外。SSE 初始连接及服务返回的动态消息提交地址 SHALL 分别经过完整目标与路径校验。

#### Scenario: Connect to an explicitly approved HTTP SSE service
- **WHEN** SSE 配置使用 HTTP，且初始连接和实际消息提交目标均符合部署策略批准的范围
- **THEN** 系统允许按配置连接和发现工具，不强制现有服务先迁移到 HTTPS，也不放行范围外目标

#### Scenario: Server advertises an unapproved message endpoint
- **WHEN** 获准 SSE 服务返回外网或未经批准的内网主机、端口或路径作为消息提交端点
- **THEN** 系统拒绝向该端点提交消息或凭据，即使初始 /sse 连接已成功

#### Scenario: Importing HTTP configuration does not create an exception
- **WHEN** 用户导入 HTTP MCP 地址但部署策略没有对应例外
- **THEN** 系统保留配置并提示策略拒绝，不通过导入动作自动允许该连接

### Requirement: No hidden external communications
客户端 SHALL 不包含外部遥测、崩溃上传、在线更新、运行时外网依赖下载和远程界面资源加载。

#### Scenario: Operate with monitored network access
- **WHEN** 在网络监测下执行首次启动、三个样例任务、错误处理和更新检查相关交互
- **THEN** 不产生应用发起的外网连接尝试，所需内网请求全部属于批准目标

### Requirement: Explicit authorized intranet data flow
系统 SHALL 在任务发送材料前展示所用内网服务及数据用途，取得对应任务范围授权，并仅发送执行所需内容；内网连接不代表数据始终留在本机。

#### Scenario: User declines model processing
- **WHEN** 用户拒绝向配置的内网模型发送本任务所需材料
- **THEN** 系统不发送材料且不执行依赖该发送的步骤，明确说明任务未继续

### Requirement: Scoped file access and non destructive output
系统 SHALL 将读取限制为用户授权文件、目录及显式导入知识资料，规范化实际路径并阻止目录穿越或链接绕过；写入 SHALL 仅在用户批准的输出目录中新建文件。

#### Scenario: A document requests reading another directory
- **WHEN** 文件或模型指令请求访问授权范围外文件，包括通过路径穿越或链接间接访问
- **THEN** 系统拒绝读取，不将文档指令视为新增授权

#### Scenario: Output name already exists
- **WHEN** 用户确认导出但目标文件名已经存在
- **THEN** 系统采用新名称或要求另选位置，不覆盖源文件或已有文件

### Requirement: Restricted executable and remote tools
系统 SHALL 仅执行经过交付验证的预置本地工具，禁止任意导入脚本、任意命令、桌面控制和业务提交；第一版远程工具 SHALL 限于获准的只读或无业务副作用的测试工具。

#### Scenario: Imported skill includes an executable script
- **WHEN** 用户导入包含脚本的 Skill 并启用该技能
- **THEN** 脚本不自动获得执行权，系统标明不支持的执行依赖，模型不能绕过限制运行它

#### Scenario: MCP exposes a business write operation
- **WHEN** 工具发现返回发送邮件、修改业务数据或交易类工具
- **THEN** 该工具在第一版不得启用或执行，不能通过普通确认对话框解除限制

### Requirement: Credential isolation and untrusted content handling
系统 SHALL 使用操作系统安全存储保存凭据，配置仅保存引用；日志和配置导出不得包含密钥或完整材料正文，模型与工具返回内容 SHALL 按不可信数据展示。

#### Scenario: Export configuration or diagnose authentication failure
- **WHEN** 用户导出配置或查看认证失败日志
- **THEN** 输出不包含密钥、认证头或任务材料正文，受控执行工具亦不继承不必要的服务凭据

#### Scenario: A response contains active content
- **WHEN** 模型或工具返回脚本、外部图片链接或要求改变权限的指令
- **THEN** 界面不执行脚本或自动加载外部资源，运行时不据此修改权限
