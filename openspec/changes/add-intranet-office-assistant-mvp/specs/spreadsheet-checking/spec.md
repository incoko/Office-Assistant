## ADDED Requirements

### Requirement: Fixed template merge with provenance
表格助手 SHALL 支持 `DEMO-TASK-1.0` 固定 `.xlsx` 模板，仅合并“事项台账”数据行，保留所有输入记录并附加来源文件、工作表和行号，不自动去重或修改源数据。

#### Scenario: Merge both sample branches
- **WHEN** 用户选择 `samples/02-表格汇总/演示东网点.xlsx` 和 `演示西网点.xlsx`
- **THEN** 输出保留6行台账记录，跳过“使用说明”工作表，每行均可追溯到输入位置

### Requirement: Deterministic validation and problem localization
系统 SHALL 使用确定性程序检查九列必填、跨文件编号唯一、合法日期、非负整数人数及加和关系、允许状态与完成状态一致性；问题 SHALL 显示实际值、规则及位置。

#### Scenario: Detect the four planted problems
- **WHEN** 对两份网点样例执行校验
- **THEN** 报告东网点D3缺负责人、东网点A4与西网点A3的DEMO-003重复、西网点E4日期无效、西网点G4:I4人数不平，并将重复问题定位到两行

### Requirement: Distinguish raw totals from valid business results
系统 SHALL 将人数合计标为培训人次而非去重员工数；存在重复或校验错误时 SHALL 不将原始合计标记为已核验业务结果。

#### Scenario: Display totals for invalid sample inputs
- **WHEN** 展示两份样例的原始汇总
- **THEN** 应完成55、已完成41、未完成15均由程序计算，并注明待核验及现存错误，不修正为模型推测的数字

### Requirement: Safe workbook processing and export
系统 SHALL 不执行宏、外部链接或公式；对不支持模板、公式必填值和损坏文件 SHALL 明确拒绝相应处理。用户确认后 SHALL 新建包含合并数据和问题清单的 Excel 结果文件。

#### Scenario: Formula or incompatible template is supplied
- **WHEN** 输入必填单元格含公式或缺少要求的表头
- **THEN** 系统定位问题并请求值化数据或正确模板，不执行公式、不读取外部链接、不静默猜测列映射

#### Scenario: Export a checked workbook
- **WHEN** 用户确认结果及输出目录
- **THEN** 系统输出合并表和问题清单，原输入文件内容保持不变，来自材料的文本不被导出为可执行公式
