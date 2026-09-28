## ADDED Requirements

### Requirement: Configurable agent profiles
系统 SHALL 支持创建、编辑、复制和停用智能体，配置名称、角色指令、模型连接、Skill、工具及工作目录；任务启动时 SHALL 固定配置快照或版本引用。

#### Scenario: Edit a profile while a task is running
- **WHEN** 用户修改正在执行任务所使用的智能体配置
- **THEN** 修改对后续任务生效，不隐式更换当前任务的模型、指令或工具权限

### Requirement: Private model capability validation
系统 SHALL 优先适配目标 Qwen3.6＋vLLM 服务的 OpenAI 兼容 Chat Completions 接口，使用可配置的实际地址和模型标识，且不得访问外部模型平台。系统 SHALL 通过接口检查区分连接、证书、认证、模型、自动工具调用、工具结果回传及流式工具调用能力；不以提供启动命令为测试前提，不支持必要能力时 SHALL 明确限制相关功能。

#### Scenario: Validate model capabilities without server startup arguments
- **WHEN** 用户提供可连接的批准内网接口和必要认证，但不能提供 vLLM 启动命令
- **THEN** 系统使用无副作用的模拟工具分别测试普通对话、自动工具选择、结果回传及流式调用，逐项显示通过、失败或未测试状态，不依据模型名称推定能力

#### Scenario: Forced tool success is not automatic tool success
- **WHEN** 指定工具调用或非流式调用成功，但自动选择或流式工具调用尚未测试
- **THEN** 系统不将后两项标记为已通过，也不从普通回答文字提取命令执行

#### Scenario: Tool calling is unavailable
- **WHEN** 模型连通但未通过工具调用能力测试
- **THEN** 系统显示能力不足且不启用依赖该能力的执行路径，不将普通模型文本当作命令或回退至外部服务

### Requirement: Bounded and validated tool execution
运行时 SHALL 仅调用已注册、全局启用、当前智能体绑定且经任务授权的工具，校验参数、调用轮次、执行时限及结果大小。

#### Scenario: Model requests an ungranted tool
- **WHEN** 模型请求未绑定或未授权的工具
- **THEN** 系统拒绝执行并记录原因，不因模型声明已获得用户同意而放行

#### Scenario: Execution limit is reached
- **WHEN** 工具循环达到预设轮次上限或执行超时
- **THEN** 系统停止后续调用，展示可理解的限制原因，保留已完成步骤和已有产物状态

### Requirement: Observable task lifecycle
系统 SHALL 展示待执行、执行中、等待确认、成功、失败、取消与中断状态以及脱敏步骤记录；第一版 SHALL 同时最多执行一个任务。

#### Scenario: Cancel a running task
- **WHEN** 用户取消正在执行的任务
- **THEN** 系统停止发起后续调用并尝试终止受控本地执行，不将部分输出标记为完整成功，也不声称已撤回送达内网服务的请求

#### Scenario: Recover from an unexpected shutdown
- **WHEN** 重启时发现上次未结束的任务
- **THEN** 系统将其标为中断，保留可用记录，不自动重放工具调用

#### Scenario: Start another task during execution
- **WHEN** 已有任务正在执行或等待确认，用户发起第二个任务
- **THEN** 系统提示先结束或取消当前任务，不启动第二个并行执行循环
