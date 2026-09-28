## ADDED Requirements

### Requirement: Template based weekly reports and meeting minutes
文稿助手 SHALL 支持粘贴文字、文本文件及 `.docx` 材料，按预置周报或会议纪要结构生成可预览和修改的草稿，并经用户确认导出 `.docx`。

#### Scenario: Draft the sample weekly report
- **WHEN** 用户提供 `samples/01-文稿整理/原始工作记录.txt` 并选择周报模板及2026-09-14至2026-09-18周期
- **THEN** 草稿包含走访、讲义更新及报名表收集等有依据事项，展示完成事项、问题、计划和待确认信息，并可导出 Word

### Requirement: Preserve factual uncertainty and temporal scope
文稿助手 SHALL 不编造数字、完成率、负责人、日期或决定，并区分建议、已决定事项和会后进展；材料缺失或冲突 SHALL 明确标注。

#### Scenario: Missing owners and unconfirmed training
- **WHEN** 使用样例记录生成周报
- **THEN** 12人仅表述为报名人数，整改汇总截止日为2026-09-25且负责人待补充，培训日期与场地不被编造为已确定

#### Scenario: Draft minutes for the specified meeting only
- **WHEN** 用户指定根据2026-09-16会议生成纪要
- **THEN** 系统不把9月18日报名表已收齐写成会议已知事实，也不把下周培训建议写成已作出的决定

### Requirement: Draft review and unsupported input feedback
输出 SHALL 标记为待人工复核草稿，模拟材料生成结果 SHALL 保留虚构提示；不支持或损坏的材料 SHALL 显示可操作错误，不自动提交或发送文稿。

#### Scenario: An unsupported recording is supplied
- **WHEN** 用户提交录音、扫描件或无法解析的文档作为整理材料
- **THEN** 系统说明第一版支持范围并要求提供文字材料，不调用外部转写或 OCR 服务
