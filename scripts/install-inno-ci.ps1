# ONLINE CI preparation only; never called by the offline build script.
# Source: https://github.com/jrsoftware/issrc/releases/expanded_assets/is-6_4_3
param([Parameter(Mandatory=$true)][string]$Destination)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Inno Setup requires Windows.' }
if (Test-Path $Destination) { throw 'Choose a fresh Inno Setup installation directory.' }
$Uri = 'https://github.com/jrsoftware/issrc/releases/download/is-6_4_3/innosetup-6.4.3.exe'
$ExpectedHash = 'f3c42116542c4cc57263c5ba6c4feabfc49fe771f2f98a79d2f7628b8762723b'
$Installer = Join-Path ([System.IO.Path]::GetTempPath()) ('inno-' + [guid]::NewGuid().ToString('N') + '.exe')
$Log = Join-Path ([System.IO.Path]::GetTempPath()) 'inno-setup-install.log'
Invoke-WebRequest -Uri $Uri -OutFile $Installer
$ActualHash = (Get-FileHash $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualHash -ne $ExpectedHash) { throw 'Inno Setup SHA256 mismatch; refusing to execute download.' }
$Process = Start-Process -FilePath $Installer -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
    ('/DIR="' + $Destination + '"'), ('/LOG="' + $Log + '"')
) -PassThru
if (-not $Process.WaitForExit(180000)) {
    $Process.Kill()
    throw 'Inno Setup installation exceeded 180 seconds.'
}
if ($Process.ExitCode -ne 0) { throw "Inno Setup installation failed: $($Process.ExitCode)" }
$Compiler = Join-Path $Destination 'ISCC.exe'
if (-not (Test-Path $Compiler -PathType Leaf)) { throw 'ISCC.exe is missing after installation.' }
Write-Host "Installed Inno Setup 6.4.3, verified SHA256 $ActualHash"
