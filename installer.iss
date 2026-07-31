#define MyAppName "KeyUp Voice"
#define MyAppVersion "1.4.1"
#define MyAppPublisher "LexGilden"
#define MyAppExeName "KeyUpVoice.exe"

[Setup]
AppId={{D58B9CEC-4FCF-47BC-BC18-2E660C399069}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Local voice input for Windows 11
VersionInfoCopyright=© 2026 LexGilden
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer-output
OutputBaseFilename=KeyUp-Voice-Setup-{#MyAppVersion}
SetupIconFile=keyup-voice.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
AppMutex=Local\KeyUpVoiceInput,Local\GolosVoiceInput
MinVersion=10.0.22000
ShowLanguageDialog=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
english.DesktopIcon=Create a desktop shortcut
russian.DesktopIcon=Создать ярлык на рабочем столе
english.ShortcutsGroup=Shortcuts:
russian.ShortcutsGroup=Ярлыки:
english.Autostart=Start KeyUp Voice when signing in to Windows
russian.Autostart=Запускать KeyUp Voice при входе в Windows
english.AdditionalGroup=Additional options:
russian.AdditionalGroup=Дополнительно:
english.UninstallShortcut=Uninstall KeyUp Voice
russian.UninstallShortcut=Удалить KeyUp Voice
english.RunApplication=Start KeyUp Voice and load components
russian.RunApplication=Запустить KeyUp Voice и загрузить компоненты
english.AppRunning=KeyUp Voice is currently running.%n%nClose the application from its system tray icon, then start uninstall again.
russian.AppRunning=KeyUp Voice сейчас запущен.%n%nЗакройте приложение через значок в системном трее, а затем снова запустите удаление.

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:ShortcutsGroup}"; Flags: checkedonce
Name: "autostart"; Description: "{cm:Autostart}"; GroupDescription: "{cm:AdditionalGroup}"; Flags: unchecked

[Files]
Source: "dist\KeyUpVoice\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\KeyUp Voice"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallShortcut}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\KeyUp Voice"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Golos"; Flags: deletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KeyUp Voice"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart
Root: HKCU; Subkey: "Software\LexGilden\KeyUp Voice"; ValueType: string; ValueName: "InterfaceLanguage"; ValueData: "en"; Flags: uninsdeletekeyifempty; Languages: english
Root: HKCU; Subkey: "Software\LexGilden\KeyUp Voice"; ValueType: string; ValueName: "InterfaceLanguage"; ValueData: "ru"; Flags: uninsdeletekeyifempty; Languages: russian

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:RunApplication}"; Flags: nowait postinstall skipifsilent

[InstallDelete]
Type: files; Name: "{app}\Golos.exe"
Type: files; Name: "{autodesktop}\Golos.lnk"
Type: filesandordirs; Name: "{userprograms}\Golos"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeUninstall(): Boolean;
begin
  if CheckForMutexes('Local\KeyUpVoiceInput,Local\GolosVoiceInput') then
  begin
    MsgBox(
      CustomMessage('AppRunning'),
      mbError,
      MB_OK
    );
    Result := False;
  end
  else
    Result := True;
end;
