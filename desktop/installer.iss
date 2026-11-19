; Windows installer for the desktop app (Inno Setup 6, free and open source).
;
; Build the app first (desktop/auditor.spec), then:
;   iscc desktop\installer.iss /DAppVersion=0.8.0
; Output: build\desktop\installer\MultiAgentAuditor-Setup-<version>.exe
;
; Installs for the current user only (no admin prompt) into
; %LOCALAPPDATA%\Programs\Multi-Agent Code Auditor. Uninstalling keeps the
; user's audit history in %LOCALAPPDATA%\MultiAgentAuditor.

#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#define AppName "Multi-Agent Code Auditor"
#define AppExe "MultiAgentAuditor.exe"

[Setup]
; Fixed id: lets a newer version upgrade an installed one. Never change it.
AppId={{B666234D-D58B-45B5-B396-A1666E39F621}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=urumb
AppPublisherURL=https://github.com/urumb/multi-agent-code-auditor
AppSupportURL=https://github.com/urumb/multi-agent-code-auditor/issues
AppUpdatesURL=https://github.com/urumb/multi-agent-code-auditor/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
LicenseFile=..\LICENSE
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir=..\build\desktop\installer
OutputBaseFilename=MultiAgentAuditor-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Close a running copy before upgrading or uninstalling.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\build\desktop\dist\MultiAgentAuditor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
