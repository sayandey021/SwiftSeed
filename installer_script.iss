; SwiftSeed Installer Script for Inno Setup
; This creates a professional Windows installer

#define MyAppName "SwiftSeed"
#define MyAppVersion "2.0.2"
#define MyAppPublisher "SwiftSeed Team"
#define MyAppURL "https://github.com/sayandey021/SwiftSeed"
#define MyAppExeName "SwiftSeed.exe"

[Setup]
; App Information
AppId={{SwiftSeed-B7E5-4F2A-9D1C-8A3E4B6F9C2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation Directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output Configuration
OutputDir=installer
OutputBaseFilename=SwiftSeed_Setup_{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes

; Visual Style
WizardStyle=modern
SetupIconFile=src\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoDescription=SwiftSeed Torrent Client Installer
VersionInfoProductName=SwiftSeed
VersionInfoCompany=SwiftSeed Team
VersionInfoVersion={#MyAppVersion}

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "startmenuicon"; Description: "Create Start Menu shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Include the entire SwiftSeed folder from dist
Source: "dist\SwiftSeed\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.torrent"; ValueType: string; ValueName: ""; ValueData: "SwiftSeed.Torrent"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\SwiftSeed.Torrent"; ValueType: string; ValueName: ""; ValueData: "Torrent File"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SwiftSeed.Torrent\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\file.ico"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\SwiftSeed.Torrent\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // You can add custom initialization code here
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Any post-installation tasks can go here
  end;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
  AppProcessName: String;
  ErrorCode: Integer;
begin
  Result := True;
  AppProcessName := '{#MyAppExeName}';
  
  // Use tasklist to check if SwiftSeed is running
  Exec('cmd.exe', '/c tasklist /FI "IMAGENAME eq ' + AppProcessName + '" 2>NUL | find /I /N "' + AppProcessName + '">NUL', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  // If ResultCode = 0, the process was found (running)
  if ResultCode = 0 then
  begin
    if MsgBox('SwiftSeed is currently running. It must be closed to continue uninstallation.' + #13#10#13#10 + 
              'Click Yes to automatically close SwiftSeed and continue.' + #13#10 +
              'Click No to cancel the uninstallation.', mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Force close the app using taskkill
      Exec('taskkill.exe', '/F /IM "' + AppProcessName + '" /T', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
      
      // Wait for the process to fully terminate
      Sleep(2000);
      
      // Verify it's actually closed
      Exec('cmd.exe', '/c tasklist /FI "IMAGENAME eq ' + AppProcessName + '" 2>NUL | find /I /N "' + AppProcessName + '">NUL', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      
      if ResultCode = 0 then
      begin
        // Still running after taskkill - force retry
        MsgBox('Failed to close SwiftSeed automatically. Please close it manually and try again.', mbError, MB_OK);
        Result := False;
      end
      else
      begin
        Result := True;
      end;
    end
    else
    begin
      Result := False; // User chose not to close the app
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Double-check the app is not running before file deletion
    Exec('cmd.exe', '/c tasklist /FI "IMAGENAME eq {#MyAppExeName}" 2>NUL | find /I /N "{#MyAppExeName}">NUL', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    if ResultCode = 0 then
    begin
      // App is still running, force kill one more time
      Exec('taskkill.exe', '/F /IM "{#MyAppExeName}" /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(1000);
    end;
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: dirifempty; Name: "{app}"
