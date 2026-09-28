# Run ONLY on a connected, trusted Windows x64 build machine.
param([string]$Python = 'python', [string]$BundleDir = '')
. "$PSScriptRoot\windows-common.ps1"
$Root = Split-Path $PSScriptRoot -Parent
if (-not $BundleDir) { $BundleDir = Join-Path $Root 'offline-bundle' }
Assert-BuildPython $Python
if (Test-Path $BundleDir) { throw 'Bundle directory already exists. Choose a new empty location; it will not be deleted.' }
New-Item -ItemType Directory -Path $BundleDir | Out-Null
$BundleDir = (Resolve-Path $BundleDir).Path
$Wheels = Join-Path $BundleDir 'wheels'
New-Item -ItemType Directory -Path $Wheels | Out-Null
$Requirements = Join-Path $Root 'packaging\windows\requirements-build.txt'
Copy-Item $Requirements (Join-Path $BundleDir 'requirements-build.txt')
# Explicit online phase. No source distributions, no unpinned dependency resolution.
Invoke-Checked $Python @('-m','pip','--isolated','--disable-pip-version-check','download','--only-binary=:all:','--no-deps','--dest',$Wheels,'-r',$Requirements)
Invoke-Checked $Python @((Join-Path $PSScriptRoot 'bundle_manifest.py'),'create',$BundleDir)
Write-Host "Prepared $BundleDir. Transfer the WHOLE directory, source, Python 3.12 x64 offline installer and Inno Setup 6.3+ installer. Keep manifest hash separately."
Get-FileHash (Join-Path $BundleDir 'manifest.json') -Algorithm SHA256
