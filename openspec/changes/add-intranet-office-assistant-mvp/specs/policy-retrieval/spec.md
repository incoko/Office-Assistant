## ADDED Requirements

### Requirement: Local bounded document collection
制度助手 SHALL 支持显式导入小规模 `.docx`、文本型 PDF 和文本资料，维护本地索引、文件身份、内容指纹及已提供的版本信息；不支持扫描文档时 SHALL 明确提示。

#### Scenario: Import equivalent sample documents
- **WHEN** 用户导入模拟制度的 Word 和 Markdown 等价版本
- **THEN** 系统识别或提示可能重复，并要求选择或标记等价来源，不把它们当作两份独立制度效力证据

#### Scenario: Version metadata is missing
- **WHEN** 用户导入没有明确版本或生效日期的文件
- **THEN** 系统标记版本或日期未知，不从文件修改时间推断制度效力

### Requirement: Grounded answers with verifiable citations
制度助手 SHALL 基于已导入资料回答，展示原文片段、文件名、已有版本以及章节或其他可定位位置，并支持打开本地来源；引用 SHALL 对应实际来源内容。

#### Scenario: Ask about archiving materials and deadlines
- **WHEN** 用户对模拟培训归档制度提问所需材料及归档时限
- **THEN** 回答引用第五、六条，说明材料清单和培训结束后3个工作日内提交的虚构规定，展示DEMO-1.0及仅供测试提示

### Requirement: Abstain when evidence is absent or ambiguous
制度助手 SHALL 对未检索到依据、超出范围及冲突内容明确提示，不使用模型常识补写规定，不擅自判定版本效力。

#### Scenario: Ask about reimbursement or customer records
- **WHEN** 用户询问模拟制度中的培训报销金额或客户交易记录保存期限
- **THEN** 系统明确没有找到适用规定或超出文档范围，不编造金额、期限或真实银行规则

#### Scenario: Ask for a calendar deadline without a calendar
- **WHEN** 用户问周五培训结束后具体哪天应提交，但未提供适用工作日日历
- **THEN** 系统引用第六、十条解释3个工作日期限并请求日历，不直接推定某一日期

#### Scenario: Sources conflict
- **WHEN** 导入的两个版本对同一事项表述冲突且无明确效力信息
- **THEN** 系统并列展示相关版本与原文，提示人工确认，不自动选择最新文件修改时间作为有效依据

### Requirement: Document removal updates retrieval scope
系统 SHALL 在用户移除已导入文档后将其从后续检索范围和活动索引中排除，保留历史回答时 SHALL 说明来源已移除。

#### Scenario: Query after removing a source
- **WHEN** 用户移除唯一支持某答案的制度并重新提问
- **THEN** 新任务不继续以该资料作为依据，历史引用不伪装成当前仍可用来源
