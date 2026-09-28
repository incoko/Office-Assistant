## ADDED Requirements

### Requirement: Local skill import and inspection
系统 SHALL 支持从本地目录导入含 `SKILL.md` 的受支持技能，展示名称、说明、内容、来源及版本或指纹，校验目录内引用并检查依赖，不自动下载外部组件。

#### Scenario: Import a supported instruction only skill
- **WHEN** 用户导入有效的纯指令 Skill，并将其启用后绑定到自定义助手
- **THEN** 后续任务能够使用该技能指令，原技能副本和指纹可查看，安全权限保持不变

#### Scenario: Import an invalid or unsupported skill
- **WHEN** 技能缺少必要文件、引用越出目录或依赖未支持的运行环境
- **THEN** 系统报告明确原因并禁止相应不可用能力，不静默联网安装或执行脚本

### Requirement: Approved intranet MCP connection
系统 SHALL 优先兼容现有旧式 HTTP＋SSE 内网 MCP，提供服务地址与必要认证配置、连接测试、自动工具发现、超时提示和按工具启停；具体协议与认证兼容范围 SHALL 通过测试记录。第一版不要求现有服务迁移到 Streamable HTTP。

#### Scenario: Configure an existing SSE service without a tool inventory
- **WHEN** 用户在智能体中配置获准的 SSE MCP 服务，提供必要连接信息但没有手工工具清单
- **THEN** 系统完成连接与初始化后自动获取并展示工具定义，不要求用户补交工具清单，也不把新增工具视为已获执行授权

#### Scenario: Connect to an approved test service
- **WHEN** 用户为兼容且获准的内网测试 MCP 补齐必要配置并测试连接
- **THEN** 系统发现并展示工具，新增工具默认禁用；经启用、绑定与授权后可在任务中调用安全测试工具

#### Scenario: Service is unavailable or incompatible
- **WHEN** MCP 服务超时、认证失败或协议不兼容
- **THEN** 系统区分错误并提示处理方式，不自动切换外部服务，也不使纯本地工具失效

### Requirement: Dynamic service independent tool discovery
系统 SHALL 在智能体配置 MCP 服务后自动通过 `tools/list` 获取工具名称、描述和输入模式，处理分页并支持手动刷新及重连刷新；不得根据 `pg-mcp` 或其他服务名称硬编码工具清单或业务逻辑。授权后的工具 SHALL 映射给模型，并由运行时校验后通过 `tools/call` 调用。

#### Scenario: Discover previously unknown tools
- **WHEN** 已配置服务返回应用中未预置的、使用受支持输入模式的工具定义
- **THEN** 系统展示完整发现结果，符合权限要求并启用后的工具可参与模型调用，不要求改应用代码以登记具体工具名

#### Scenario: Service returns an empty or failed discovery result
- **WHEN** 已初始化服务返回空工具列表或工具发现失败
- **THEN** 系统分别提示无可用工具或发现失败，不伪造工具、不绕过授权，也不声称工具执行已经可用

### Requirement: Tool permissions do not silently expand
系统 SHALL 以全局启用、智能体绑定和任务授权共同决定可用工具；工具列表或参数模式变化 SHALL 使受影响授权需要重新确认。

#### Scenario: A connected server adds or changes a tool
- **WHEN** 服务重新发现时出现新增工具或已授权工具的模式变化
- **THEN** 新增或变更工具不沿用旧授权自动执行，用户可查看变化并重新确认符合第一版范围的工具

### Requirement: Existing MCP configuration import
系统 SHALL 支持以表单配置 MCP，并兼容 `mcpServers.<服务名>.transport.type` 和 `transport.url` 的配置导入；第一版 SHALL 支持 `type` 为 `sse`。配置内容只声明连接，不授予网络例外或工具执行权；缺少认证字段不得作为服务无须认证的验证结论。

#### Scenario: Import the provided SSE configuration shape
- **WHEN** 用户导入包含 `mcpServers.pg-mcp.transport` 且指定 `type: sse` 和有效服务 URL 的配置
- **THEN** 系统识别服务名、传输与地址，检查网络策略并在必要时提示补齐认证，连接可用后自动发现工具，不要求输入工具定义

### Requirement: Portable configuration without secrets or grants
系统 SHALL 支持版本化配置导出、导入前预览与兼容校验；配置包不得包含密钥、任务内容、文档正文、可直接生效的本机目录授权或扩大网络边界的策略。

#### Scenario: Import configuration on another computer
- **WHEN** 同事导入维护人员提供的兼容配置包
- **THEN** 系统显示将新增或修改的配置，确认后导入，提示补齐凭据和目录，并默认禁用新增工具直至完成本机确认

#### Scenario: Configuration format is unsupported
- **WHEN** 导入包版本不受支持或校验失败
- **THEN** 系统拒绝导入并保持当前配置不变
