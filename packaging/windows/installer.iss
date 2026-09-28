; Compile with Inno Setup 6.3+ (Unicode). No network or user data deletion steps.
#ifndef AppVersion
  #error AppVersion must be supplied by the build script
#endif
#ifndef SourceDir
  #error SourceDir must be supplied by the build script
#endif
#ifndef ReleaseDir
  #error ReleaseDir must be supplied by the build script
#endif
[Setup]
AppId={{C590E931-87D7-46E1-9E67-4D96894C2927}
AppName=Office Assistant
AppVersion={#AppVersion}
AppPublisher=Office Assistant
DefaultDirName=D:\Program Files\Office Assistant
DefaultGroupName=Office Assistant
DisableProgramGroupPage=yes
DisableDirPage=no
UsePreviousAppDir=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#ReleaseDir}
OutputBaseFilename=OfficeAssistant-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\OfficeAssistant.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Office Assistant"; Filename: "{app}\OfficeAssistant.exe"; WorkingDir: "{app}"
Name: "{group}\Office Assistant - Self Check"; Filename: "{app}\OfficeAssistant.exe"; Parameters: "--self-check --show-result"; WorkingDir: "{app}"
Name: "{commondesktop}\Office Assistant"; Filename: "{app}\OfficeAssistant.exe"; WorkingDir: "{app}"; Tasks: desktopicon

; Deliberately no [Run], [UninstallDelete], broad ACL grants or per-user writes.
; The original user is not reliably recoverable after 'Run as administrator'.
[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
var
  Drive: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then begin
    Drive := ExtractFileDrive(WizardDirValue);
    if (Drive = '') or not DirExists(Drive + '\') then begin
      MsgBox('The selected drive does not exist. Select an available local drive.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
