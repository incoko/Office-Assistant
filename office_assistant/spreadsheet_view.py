"""Spreadsheet UI. Imported only when Tk is available."""
import tkinter as tk
from tkinter import filedialog, ttk
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError

from .scenarios import check_spreadsheets
from .spreadsheet_presentation import present_result
from .spreadsheet_tools import HEADERS


class SpreadsheetPage(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.files = []
        self.report = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)
        ttk.Label(self, text='汇总 / 检查表格', font=('Segoe UI', 20, 'bold')).grid(sticky='w')
        ttk.Label(self, text='选择同模板 Excel，检查后查看问题和来源；不会修改原始文件。').grid(row=1, sticky='w', pady=6)
        toolbar = ttk.Frame(self)
        toolbar.grid(row=2, sticky='ew', pady=6)
        toolbar.columnconfigure(2, weight=1)
        ttk.Button(toolbar, text='选择表格', command=self.choose_files).grid(row=0, column=0)
        self.check_button = ttk.Button(toolbar, text='开始检查', command=self.run_check, state='disabled')
        self.check_button.grid(row=0, column=1, padx=8)
        self.selected = tk.StringVar(value='尚未选择文件')
        ttk.Label(toolbar, textvariable=self.selected).grid(row=0, column=2, sticky='w')
        self.counts = tk.StringVar(value='请选择文件后开始检查。')
        self.status_label = ttk.Label(self, textvariable=self.counts, wraplength=740)
        self.status_label.grid(row=3, sticky='ew', pady=6)

        summary = ttk.Frame(self)
        summary.grid(row=4, sticky='ew', pady=6)
        self.total_values = []
        for index, title in enumerate(('应完成（人次）', '已完成（人次）', '未完成（人次）')):
            summary.columnconfigure(index, weight=1)
            card = ttk.LabelFrame(summary, text=title, padding=10)
            card.grid(row=0, column=index, sticky='ew', padx=(0, 8))
            value = tk.StringVar(value='—')
            self.total_values.append(value)
            ttk.Label(card, textvariable=value, font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        self.caution = tk.StringVar(value='数值为培训人次，不是去重员工人数。')
        ttk.Label(summary, textvariable=self.caution, foreground='#805000', wraplength=740).grid(
            row=1, column=0, columnspan=3, sticky='ew', pady=(8, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=5, sticky='nsew', pady=6)
        problems = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(problems, text='问题清单')
        problems.columnconfigure(0, weight=1)
        problems.rowconfigure(0, weight=1)
        self.issue_tree = self.make_table(problems, ('序号', '问题类型', '问题说明', '来源位置'), (55, 110, 265, 450))
        self.detail = tk.Text(problems, height=5, wrap='word', state='disabled')
        self.detail.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(8, 0))
        self.issue_tree.bind('<<TreeviewSelect>>', self.show_detail)

        preview = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(preview, text='合并数据预览')
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)
        columns = ('来源文件', '来源工作表', '原始行号', *HEADERS)
        self.data_tree = self.make_table(preview, columns, (180, 100, 75, *([120] * len(HEADERS))))
        ttk.Label(self, text='当前为原型：本页提供检查和预览，尚不支持导出 Excel。', foreground='#666').grid(row=6, sticky='w')
        self.reset_results()

    @staticmethod
    def make_table(parent, titles, widths):
        columns = tuple(str(index) for index in range(len(titles)))
        tree = ttk.Treeview(parent, columns=columns, show='headings', selectmode='browse', height=7)
        for key, title, width in zip(columns, titles, widths):
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=50, stretch=False, anchor='w')
        tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(parent, orient='vertical', command=tree.yview)
        horizontal = ttk.Scrollbar(parent, orient='horizontal', command=tree.xview)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        return tree

    def set_detail(self, text):
        self.detail.configure(state='normal')
        self.detail.delete('1.0', 'end')
        self.detail.insert('1.0', text)
        self.detail.configure(state='disabled')

    def reset_results(self):
        self.report = None
        for tree in (self.issue_tree, self.data_tree):
            for item in tree.get_children():
                tree.delete(item)
        for value in self.total_values:
            value.set('—')
        self.notebook.tab(0, text='问题清单')
        self.notebook.tab(1, text='合并数据预览')
        self.caution.set('数值为培训人次，不是去重员工人数。')
        self.set_detail('检查后选择一项问题，查看完整说明和所有来源位置。')

    def set_files(self, paths):
        # Preserve selection if the user cancels the file picker.
        if not paths:
            return
        self.files = list(dict.fromkeys(paths))
        self.reset_results()
        self.selected.set(f'已选择 {len(self.files)} 个文件')
        self.counts.set('文件已选择，请点击“开始检查”。')
        self.status_label.configure(foreground='#333')
        self.check_button.configure(state='normal')
        self.set_detail('已选择文件：\n' + '\n'.join(self.files))

    def choose_files(self):
        self.set_files(filedialog.askopenfilenames(parent=self, title='选择同模板 Excel 文件', filetypes=[('Excel 工作簿', '*.xlsx')]))

    def run_check(self):
        self.reset_results()
        if not self.files:
            self.counts.set('请先选择要检查的 Excel 文件。')
            return
        self.counts.set('正在检查，请稍候……')
        self.check_button.configure(state='disabled')
        self.update_idletasks()
        try:
            self.render_result(check_spreadsheets(self.files))
        except (OSError, ValueError, KeyError, BadZipFile, ParseError) as exc:
            self.counts.set('检查未完成，请确认文件可读取且符合台账模板后重试。')
            self.status_label.configure(foreground='#a03020')
            self.set_detail(f'未显示汇总结果，以免误用上次结果。\n原因：{exc}')
        finally:
            self.check_button.configure(state='normal')

    def render_result(self, result):
        self.reset_results()
        self.report = present_result(result)
        self.counts.set(self.report.status)
        self.status_label.configure(foreground='#805000' if self.report.has_issues else '#333')
        self.caution.set(self.report.caution)
        for value, text in zip(self.total_values, self.report.totals):
            value.set(text)
        for index, problem in enumerate(self.report.problems):
            self.issue_tree.insert('', 'end', iid=str(index), values=(index + 1, problem.kind, problem.message, '；'.join(problem.sources)))
        for row in result['rows']:
            self.data_tree.insert('', 'end', values=(row.source_file, row.source_sheet, row.source_row,
                                                     *(row.values.get(header, '') for header in HEADERS)))
        self.notebook.tab(0, text=f'问题清单（{len(self.report.problems)} 组）')
        self.notebook.tab(1, text=f'合并数据预览（{self.report.row_count} 行）')
        if self.report.problems:
            self.issue_tree.selection_set('0')
            self.show_detail()
        else:
            self.set_detail(self.report.status)

    def show_detail(self, _event=None):
        selection = self.issue_tree.selection()
        if self.report and selection:
            self.set_detail(self.report.problems[int(selection[0])].detail)
