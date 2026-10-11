#define MyAppName "CrowEyes Image Viewer"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Crow Science Lab"
#define MyAppExeName "CrowEyes.exe"
#ifndef MyDistDir
  #define MyDistDir "..\dist\CrowEyes"
#endif

[Setup]
AppId={{1DE942C5-2E41-4771-B02C-0E18414B5D15}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
VersionInfoVersion=2.0.0.0
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\CrowEyes
DefaultGroupName=CrowEyes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=CrowEyes_Setup_2.0.0_Windows_x64
SetupIconFile=..\assets\icons\croweyes-2.0.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕 화면 바로가기 만들기"; GroupDescription: "추가 바로가기:"; Flags: unchecked

[Files]
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\WINDOWS_SECURITY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion

[Icons]
Name: "{group}\CrowEyes Image Viewer"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\CrowEyes 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CrowEyes"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\CrowScienceLab\CrowEyes"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\CrowEyes.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "CrowEyes Image Viewer"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Applications\CrowEyes.exe\DefaultIcon"; ValueType: string; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\Applications\CrowEyes.exe\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "CrowEyes Image Viewer"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "가볍고 빠른 Windows 이미지 뷰어"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "CrowEyes"; ValueData: "Software\CrowEyes\Capabilities"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".bmp"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".dib"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".gif"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".ico"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".jfif"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".jpe"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".jpeg"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".jpg"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pbm"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pgm"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".png"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".ppm"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".tga"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".tif"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".tiff"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".webp"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".psd"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".svg"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".avif"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".heic"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".heif"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".cr2"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".cr3"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".nef"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".arw"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".dng"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".raf"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".rw2"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\CrowEyes\Capabilities\FileAssociations"; ValueType: string; ValueName: ".orf"; ValueData: "CrowEyes.Image"
Root: HKCU; Subkey: "Software\Classes\CrowEyes.Image"; ValueType: string; ValueData: "CrowEyes 이미지"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\CrowEyes.Image\DefaultIcon"; ValueType: string; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\CrowEyes.Image\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "CrowEyes 실행"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
