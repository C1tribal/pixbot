; Pixbot installer (Inno Setup 6) - builds dist\Pixbot-Installer.exe from dist\Pixbot.exe
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=1.1.0 installer\pixbot.iss
; Installs for the current user only (no admin rights needed).

#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif

[Setup]
AppId={{6F3B2C1A-8E4D-4B7A-9C2E-5D1F0A9B7C31}
AppName=Pixbot
AppVersion={#AppVersion}
AppVerName=Pixbot {#AppVersion}
AppPublisher=C1tribal
AppPublisherURL=https://github.com/C1tribal/pixbot
AppSupportURL=https://github.com/C1tribal/pixbot/issues
DefaultDirName={localappdata}\Programs\Pixbot
DisableDirPage=auto
DefaultGroupName=Pixbot
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Pixbot-Installer
SetupIconFile=..\pixbot.ico
UninstallDisplayIcon={app}\Pixbot.exe
UninstallDisplayName=Pixbot
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=force
RestartApplications=no
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Put a Pixbot icon on my desktop"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start Pixbot when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\Pixbot.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Pixbot"; Filename: "{app}\Pixbot.exe"; Comment: "Your little desktop robot"
Name: "{autodesktop}\Pixbot"; Filename: "{app}\Pixbot.exe"; Comment: "Your little desktop robot"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Pixbot"; ValueData: """{app}\Pixbot.exe"" ""--pet"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Pixbot.exe"; Description: "Open Pixbot now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; close Pixbot and remove the start-with-Windows entry (if it was turned on in the app)
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM Pixbot.exe"; Flags: runhidden; RunOnceId: "ClosePixbot"
Filename: "{sys}\reg.exe"; Parameters: "delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v Pixbot /f"; Flags: runhidden; RunOnceId: "RemoveStartup"

[UninstallDelete]
; Pixbot's own settings folder
Type: filesandordirs; Name: "{userappdata}\Pixbot"
