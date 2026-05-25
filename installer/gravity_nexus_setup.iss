; ============================================================================
;  Gravity Nexus — Inno Setup Installer Script
;  Inno Setup 6.x required  (https://jrsoftware.org/isinfo.php)
;
;  Prerequisite: build the Nuitka onefile executable first:
;      python build_nuitka.py
;  which produces:  dist\main.exe
;
;  To compile this script:
;      iscc installer\gravity_nexus_setup.iss
;  Output:  installer\Output\GravityNexus_Setup_0.1.0.exe
; ============================================================================

; VERSION — keep this in sync with app/_version.py (__version__)
#define AppName        "Gravity Nexus"
#define AppVersion     "0.1.0"
#define AppPublisher   "GravityNexus"
#define AppURL         "https://github.com/GravityGuild/gravity_nexus"
#define AppExeName     "GravityNexus.exe"
#define AppDescription "Gravity Nexus Tool"
#define AppId          "{{A3F2C1B4-7E9D-4F0A-BE5C-82D6F4103A91}"

; Paths relative to this .iss file (which lives in installer\)
#define RootDir        ".."
#define DistDir        "..\dist"
#define ResourceDir    "..\resources"
#define AssetsIconDir  "..\app\assets\icons"

; ── [Setup] ──────────────────────────────────────────────────────────────────

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
AppComments={#AppDescription}

; Default install location — respects 32-bit vs 64-bit automatically
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes

; Output
OutputDir={#RootDir}\installer\Output
OutputBaseFilename=GravityNexus_Setup_{#AppVersion}
SetupIconFile={#AssetsIconDir}\full_logo.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Windows version guard — Windows 10 (build 17763) minimum
MinVersion=10.0.17763

; Privileges — install per-machine (requires elevation)
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Look & feel
WizardStyle=modern
WizardSizePercent=120
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=yes

; Uninstaller
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
CreateUninstallRegKey=yes

; Optionally offer to run the app after install
[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "Launch {#AppName}"; \
    Flags: nowait postinstall

; ── [Languages] ──────────────────────────────────────────────────────────────

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ── [Tasks] ──────────────────────────────────────────────────────────────────

[Tasks]
Name: "desktopicon";    Description: "Create a &desktop shortcut";           GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startupicon";   Description: "Launch {#AppName} when Windows starts"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

; ── [Files] ──────────────────────────────────────────────────────────────────

[Files]
; Main executable (Nuitka onefile — already self-contained)
Source: "{#DistDir}\main.exe"; \
    DestDir: "{app}"; \
    DestName: "{#AppExeName}"; \
    Flags: ignoreversion

; Application icon files (used by shortcuts and the uninstaller)
Source: "{#AssetsIconDir}\full_logo.ico";  DestDir: "{app}\icons"; Flags: ignoreversion
Source: "{#AssetsIconDir}\only_logo.ico";  DestDir: "{app}\icons"; Flags: ignoreversion

; ── [Icons] ──────────────────────────────────────────────────────────────────

[Icons]
; Start Menu
Name: "{group}\{#AppName}"; \
    Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\icons\full_logo.ico"; \
    Comment: "{#AppDescription}"

Name: "{group}\Uninstall {#AppName}"; \
    Filename: "{uninstallexe}"

; Desktop shortcut (optional task)
Name: "{autodesktop}\{#AppName}"; \
    Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\icons\full_logo.ico"; \
    Comment: "{#AppDescription}"; \
    Tasks: desktopicon

; Startup shortcut (optional task)
Name: "{autostartup}\{#AppName}"; \
    Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\icons\full_logo.ico"; \
    Comment: "{#AppDescription}"; \
    Tasks: startupicon

; ── [Registry] ───────────────────────────────────────────────────────────────

[Registry]
; Register the App User Model ID so the taskbar groups correctly with the
; running process (must match set_app_user_model_id in main.py)
Root: HKLM; \
    Subkey: "Software\Classes\AppUserModelId\com.gravitynexus.app"; \
    ValueType: string; ValueName: "DisplayName"; ValueData: "{#AppName}"; \
    Flags: uninsdeletekey

Root: HKLM; \
    Subkey: "Software\Classes\AppUserModelId\com.gravitynexus.app"; \
    ValueType: string; ValueName: "IconUri"; \
    ValueData: "{app}\icons\full_logo.ico"; \
    Flags: uninsdeletevalue

; ── [UninstallDelete] ────────────────────────────────────────────────────────

[UninstallDelete]
; Remove the icons sub-folder left after the main exe is deleted
Type: filesandordirs; Name: "{app}\icons"

; ── [Code] ───────────────────────────────────────────────────────────────────

[Code]
// ---------------------------------------------------------------------------
//  KillRunningInstance — gracefully stop any running copy before upgrading
// ---------------------------------------------------------------------------
function FindAndStopProcess(const ExeName: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('taskkill', '/F /IM "' + ExeName + '"', '', SW_HIDE,
          ewWaitUntilTerminated, ResultCode) then
    Result := (ResultCode = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  FindAndStopProcess('{#AppExeName}');
  // Give the process a moment to fully exit
  Sleep(800);
end;

