; Inno Setup script for Morale. packaging/build.py passes the version and paths:
;   ISCC /DAppVersion=0.2.0 /DSourceDir=dist\Morale /DIconFile=build\icons\morale.ico
;        /DLicenseFile=LICENSE /DOutputDir=dist\release /DOutputName=Morale-0.2.0-windows-x86_64-setup morale.iss

#ifndef AppVersion
  #error AppVersion must be defined
#endif

[Setup]
AppId={{6B0E3C1D-7A52-4E7B-9C1F-4D6F0A9E2B31}
AppName=Morale
AppVersion={#AppVersion}
AppVerName=Morale {#AppVersion}
AppPublisher=Morale contributors
AppPublisherURL=https://github.com/vomitselfie/Morale
AppSupportURL=https://github.com/vomitselfie/Morale/issues
DefaultDirName={autopf}\Morale
DefaultGroupName=Morale
DisableProgramGroupPage=yes
LicenseFile={#LicenseFile}
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\Morale.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Install for the current user without administrator rights by default;
; the wizard offers an all-users install.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
VersionInfoVersion={#AppVersion}
VersionInfoProductName=Morale
VersionInfoDescription=Morale embroidery studio installer

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associate"; Description: "Open .morale projects with Morale"; GroupDescription: "File types:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Morale"; Filename: "{app}\Morale.exe"
Name: "{autodesktop}\Morale"; Filename: "{app}\Morale.exe"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.morale"; ValueType: string; ValueName: ""; ValueData: "Morale.Project"; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\Morale.Project"; ValueType: string; ValueName: ""; ValueData: "Morale embroidery project"; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\Morale.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Morale.exe,0"; Tasks: associate
Root: HKA; Subkey: "Software\Classes\Morale.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Morale.exe"" ""%1"""; Tasks: associate

[Run]
Filename: "{app}\Morale.exe"; Description: "{cm:LaunchProgram,Morale}"; Flags: nowait postinstall skipifsilent
