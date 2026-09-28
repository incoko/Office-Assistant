# Strict offline phase: never downloads packages or installers.
param([string]$Python = 'python', [string]$BundleDir = '', [string]$Iscc = '', [switch]$PortableOnly, [string]$ResultFile = '')
. "$PSScriptRoot\windows-common.ps1"
$Root = Split-Path $PSScriptRoot -Parent
if (-not $BundleDir) { $BundleDir = Join-Path $Root 'offline-bundle' }
Assert-BuildPython $Python
if ($ResultFile) {
    $ResultFile = [System.IO.Path]::GetFullPath($ResultFile)
    if (Test-Path $ResultFile) { throw 'Result file already exists; use a fresh path to avoid stale CI output.' }
}
$BundleDir = (Resolve-Path $BundleDir).Path
if (-not $PortableOnly) {
    if (-not $Iscc) { $Iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
    if (-not (Test-Path $Iscc -PathType Leaf)) { throw 'Install Inno Setup offline or pass -Iscc; no download will be attempted.' }
    $Iscc = (Resolve-Path $Iscc).Path
}
Invoke-Checked $Python @((Join-Path $PSScriptRoot 'bundle_manifest.py'),'verify',$BundleDir,'--requirements',(Join-Path $Root 'packaging\windows\requirements-build.txt'))
# Fresh work directory each time: no recursive deletion or stale output reuse.
$Run = Join-Path $Root ('build\windows-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Run -Force | Out-Null
$Venv = Join-Path $Run 'venv'
Invoke-Checked $Python @('-m','venv',$Venv)
$BuildPython = Join-Path $Venv 'Scripts\python.exe'
$env:PIP_NO_INDEX = '1'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
Invoke-Checked $BuildPython @('-m','pip','--isolated','--disable-pip-version-check','install','--no-index','--only-binary=:all:','--find-links',(Join-Path $BundleDir 'wheels'),'-r',(Join-Path $BundleDir 'requirements-build.txt'))
Invoke-Checked $BuildPython @('-m','pip','--isolated','--disable-pip-version-check','check')
Push-Location $Root
try {
    Invoke-Checked $BuildPython @('-m','unittest','discover','-s','tests','-v')
    $Dist = Join-Path $Run 'dist'
    Invoke-Checked $BuildPython @('-m','PyInstaller','--noconfirm','--clean','--distpath',$Dist,'--workpath',(Join-Path $Run 'pyinstaller'),'packaging\windows\OfficeAssistant.spec')
    $App = Join-Path $Dist 'OfficeAssistant'
    $Exe = Join-Path $App 'OfficeAssistant.exe'
    $Report = Join-Path $Run 'self-check.json'
    # GUI subsystem EXEs require explicit waiting; do not rely on a shell exit code.
    $Process = Start-Process -FilePath $Exe -ArgumentList @('--self-check','--require-windows','--report',('"' + $Report + '"')) -PassThru
    if (-not $Process.WaitForExit(120000)) {
        $Process.Kill()
        throw 'Frozen executable self-check exceeded 120 seconds.'
    }
    if ($Process.ExitCode -ne 0 -or -not (Test-Path $Report)) { throw 'Frozen executable self-check failed.' }
    $Result = Get-Content $Report -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $Result.ok) { throw 'Frozen executable self-check reports failure.' }
    $Version = (& $BuildPython -c 'from office_assistant import __version__; print(__version__)').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Could not read application version.' }
    if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid application version.' }
    $Release = Join-Path $Run 'release'
    New-Item -ItemType Directory -Path $Release | Out-Null
    Compress-Archive -Path $App -DestinationPath (Join-Path $Release "OfficeAssistant-$Version-windows-x64-portable.zip")
    if (-not $PortableOnly) {
        Invoke-Checked $Iscc @("/DAppVersion=$Version", "/DSourceDir=$App", "/DReleaseDir=$Release", 'packaging\windows\installer.iss')
    }
    Copy-Item $Report (Join-Path $Release 'build-self-check.json')
    Copy-Item (Join-Path $BundleDir 'manifest.json') (Join-Path $Release 'dependency-manifest.json')
    Copy-Item 'docs\WINDOWS-QUICKSTART.txt' $Release
    $PythonVersion = (& $BuildPython -c 'import platform; print(platform.python_version())').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Could not read Python version.' }
    $Provenance = @{
        app_version = $Version
        python_version = $PythonVersion
        platform = [System.Environment]::OSVersion.VersionString
        commit = $env:GITHUB_SHA
        runner_image = $env:ImageVersion
        inno_version = $(if ($PortableOnly) { $null } else { (Get-Item $Iscc).VersionInfo.FileVersion })
        acceptance = 'Build smoke test only; Windows 10 deployment and real services not validated.'
    }
    $Provenance | ConvertTo-Json | Set-Content (Join-Path $Release 'build-provenance.json') -Encoding UTF8
    $Hashes = Get-ChildItem $Release -File | Get-FileHash -Algorithm SHA256 | ForEach-Object { $_.Hash.ToLower() + '  ' + (Split-Path $_.Path -Leaf) }
    $Hashes | Set-Content (Join-Path $Release 'SHA256SUMS.txt') -Encoding ASCII
    if ($ResultFile) {
        New-Item -ItemType Directory -Path (Split-Path $ResultFile -Parent) -Force | Out-Null
        @{ release_dir = $Release; version = $Version } | ConvertTo-Json |
            Set-Content $ResultFile -Encoding UTF8
    }
    Write-Host "Build outputs: $Release"
    Write-Host 'Built successfully. Target Windows 10 standard-user installation acceptance is STILL REQUIRED.'
} finally { Pop-Location }
