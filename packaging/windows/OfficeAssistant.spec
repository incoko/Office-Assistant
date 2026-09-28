# Run from scripts/build-windows.ps1. PyInstaller supplies SPECPATH.
from pathlib import Path
import sys

if sys.platform != 'win32':
    raise SystemExit('Windows binaries must be built on Windows.')
root = Path(SPECPATH).resolve().parents[1]
a = Analysis(
    [str(root / 'packaging/windows/launcher.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'samples'), 'samples'),
           (str(root / 'docs/WINDOWS-QUICKSTART.txt'), 'docs')],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='OfficeAssistant', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    uac_admin=False, uac_uiaccess=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='OfficeAssistant')
