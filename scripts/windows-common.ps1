Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable failed with exit code $LASTEXITCODE" }
}
function Assert-BuildPython {
    param([string]$Python)
    if ($env:OS -ne 'Windows_NT') { throw 'Run this script on Windows x64, not macOS/Linux.' }
    Invoke-Checked $Python @('-c', 'import sys,struct,platform,tkinter; assert sys.version_info[:2]==(3,12), "Requires Python 3.12"; assert struct.calcsize("P")==8 and platform.machine().upper() in ("AMD64","X86_64"), "Requires native x64 Python"; t=tkinter.Tk(); t.withdraw(); t.update(); t.destroy(); print(sys.version)')
}
