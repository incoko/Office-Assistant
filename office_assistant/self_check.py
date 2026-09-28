"""Offline packaging smoke check, not model/MCP or product acceptance."""
from __future__ import annotations
import json
import platform
import struct
import sys
import tempfile
from pathlib import Path
from typing import Callable

from . import __version__
from .paths import ensure_user_dirs, resource_dir, user_data_dir


def run_checks(data_root: Path | None = None, resources: Path | None = None,
               require_windows: bool = False, check_gui: bool = True) -> dict:
    checks = []

    def check(name: str, action: Callable[[], str]) -> None:
        try:
            checks.append({'name': name, 'status': 'passed', 'detail': action()})
        except Exception as exc:
            checks.append({'name': name, 'status': 'failed', 'detail': str(exc)})

    def environment() -> str:
        if require_windows and (sys.platform != 'win32' or struct.calcsize('P') != 8
                                or platform.machine().upper() not in ('AMD64', 'X86_64')):
            raise RuntimeError('Windows x64 is required for target acceptance.')
        return f'{platform.system()} {platform.release()} / {platform.machine()}; Python {platform.python_version()}'

    root = data_root if data_root is not None else user_data_dir()
    assets = resources if resources is not None else resource_dir()
    def storage() -> str:
        # Never open JsonStore on real user state or change existing tasks/configuration.
        for name, directory in ensure_user_dirs(root).items():
            with tempfile.TemporaryFile(dir=directory) as probe:
                probe.write(b'office-assistant-probe')
                probe.seek(0)
                if probe.read() != b'office-assistant-probe':
                    raise RuntimeError(f'User data directory is not writable: {name}')
        return str(root)

    def samples() -> str:
        from .document_tools import read_docx_text
        from .scenarios import check_spreadsheets
        sample_root = assets / 'samples'
        text = read_docx_text(sample_root / '03-制度查询/模拟培训归档制度.docx')
        if '虚构' not in text:
            raise RuntimeError('Packaged Word sample is missing its test-only marker.')
        result = check_spreadsheets([str(sample_root / '02-表格汇总' / name)
                                    for name in ('演示东网点.xlsx', '演示西网点.xlsx')])
        if len(result['rows']) != 6 or len(result['issues']) != 4:
            raise RuntimeError('Packaged spreadsheet sample check failed.')
        if result['raw_totals'] != {'应完成人数': 55, '已完成人数': 41, '未完成人数': 15}:
            raise RuntimeError('Packaged spreadsheet totals mismatch.')
        return 'Word and Excel test fixtures readable; 6 rows, 4 issues, totals 55/41/15.'

    def gui() -> str:
        from .gui import OfficeAssistantApp
        from .store import JsonStore
        # Startup uses isolated state, so a smoke test never rewrites a real user database.
        with tempfile.TemporaryDirectory(prefix='ui-check-', dir=root / 'cache') as folder:
            app = OfficeAssistantApp(JsonStore(Path(folder)))
            try:
                app.withdraw()
                for page in (app.show_home, app.show_chat, app.show_drafting,
                             app.show_spreadsheet, app.show_policy, app.show_settings):
                    page()
                    app.update_idletasks()
            finally:
                app.destroy()
        return 'Tk runtime and all six application pages initialized (no interactive acceptance).'

    check('environment', environment)
    check('user-data-writable', storage)
    check('bundled-samples', samples)
    if check_gui:
        check('tk-and-workbench', gui)
    else:
        checks.append({'name': 'tk-and-workbench', 'status': 'skipped', 'detail': 'Explicit test-only skip.'})
    return {'version': __version__, 'frozen': bool(getattr(sys, 'frozen', False)),
            'ok': all(x['status'] == 'passed' for x in checks), 'checks': checks,
            'scope': 'Offline packaging smoke check only; no vLLM/MCP network requests.'}


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
