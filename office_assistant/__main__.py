from __future__ import annotations
import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Office Assistant offline desktop prototype')
    parser.add_argument('--self-check', action='store_true', help='Run offline packaging checks and exit')
    parser.add_argument('--report', type=Path, help='Self-check report destination')
    parser.add_argument('--require-windows', action='store_true', help='Require Windows x64 in self-check')
    parser.add_argument('--show-result', action='store_true', help='Display self-check result in a dialog')
    args = parser.parse_args(argv)
    try:
        if args.self_check:
            from .paths import user_data_dir
            from .self_check import run_checks, write_report
            report = run_checks(require_windows=args.require_windows)
            path = args.report or user_data_dir() / 'logs' / 'self-check.json'
            write_report(report, path)
            message = ('Self-check passed' if report['ok'] else 'Self-check FAILED') + f'\nReport: {path}'
            if sys.stdout:
                print(message)
            if args.show_result:
                _dialog(message, error=not report['ok'])
            return 0 if report['ok'] else 1
        from .gui import run_app
        run_app()
        return 0
    except Exception as exc:
        message = f'Office Assistant could not start: {exc}'
        if sys.stderr:
            print(message, file=sys.stderr)
        if getattr(sys, 'frozen', False) and (not args.self_check or args.show_result):
            _dialog(message, error=True)
        return 1


def _dialog(message: str, error: bool) -> None:
    # Native fallback still works if bundled Tcl/Tk fails to load.
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'Office Assistant', 0x10 if error else 0x40)


if __name__ == '__main__':
    raise SystemExit(main())
