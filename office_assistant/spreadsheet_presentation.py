"""Human-readable spreadsheet results, independent of Tk for unit testing."""
from dataclasses import dataclass

from .spreadsheet_tools import NUMBER_FIELDS

ISSUE_LABELS = {
    'required': '必填项缺失', 'date': '日期无效', 'sum': '人数不平',
    'status': '状态异常', 'number': '人数格式错误', 'duplicate': '编号重复',
}


@dataclass(frozen=True)
class ProblemView:
    kind: str
    message: str
    sources: tuple[str, ...]

    @property
    def detail(self) -> str:
        return f'{self.kind}\n{self.message}\n\n来源位置：\n' + '\n'.join(self.sources)


@dataclass(frozen=True)
class SpreadsheetReport:
    row_count: int
    problems: tuple[ProblemView, ...]
    totals: tuple[str, ...]
    status: str
    caution: str
    has_issues: bool


def present_result(result: dict) -> SpreadsheetReport:
    problems = []
    for issue in result['issues']:
        sources = tuple(
            f"{loc['file']} · {loc['sheet']} · 第 {loc['row']} 行 · {', '.join(loc['cells'])}"
            for loc in issue.get('locations', [])
        ) or (issue.get('source', '来源未提供'),)
        problems.append(ProblemView(ISSUE_LABELS.get(issue['type'], '其他问题'), issue['message'], sources))
    count = len(result['rows'])
    if not count:
        status = '没有可检查的数据：所选表格仅含表头或空白行。'
    elif problems:
        status = f'检查完成：共 {count} 行，发现 {len(problems)} 组问题，请核对原表。'
    else:
        status = f'检查完成：共 {count} 行，当前规则未发现问题。仍需人工复核。'
    totals = tuple('—' if not count or result['raw_totals'].get(name) is None
                   else str(result['raw_totals'][name]) for name in NUMBER_FIELDS)
    caution = '待核验原始合计（培训人次，非去重员工人数）；不作为最终业务结果。'
    if any(value == '—' for value in totals) and count:
        caution += ' “—”表示该列存在无法计算的数值。'
    return SpreadsheetReport(count, tuple(problems), totals, status, caution, bool(problems))
