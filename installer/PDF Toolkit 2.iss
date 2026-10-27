; Installateur de PDF Toolkit 2 (Inno Setup 6).
;
; Construction (depuis le dossier du projet) :
;   $env:CONSTRUCTION = "dossier"; python -m PyInstaller --clean --noconfirm "PDF Toolkit 2.spec"
;   ISCC "installer\PDF Toolkit 2.iss"
; Résultat : dist\PDF-Toolkit-2-Installation-<version>.exe
;
; - La version est lue dans l'exécutable (informations de version écrites par la recette PyInstaller).
; - Installation pour l'utilisateur seul, sans droits d'administrateur (au choix : pour tous les utilisateurs).
; - Option : ajouter PDF Toolkit 2 au menu « Ouvrir avec » des fichiers PDF (sans changer le lecteur par défaut).
; - Désinstallation par Paramètres → Applications, ou par le menu Démarrer.

#define AppName "PDF Toolkit 2"
#define AppExe "PDF Toolkit 2.exe"
#define AppDir "..\dist\PDF Toolkit 2"
#define AppVersion GetStringFileInfo(AppDir + "\" + AppExe, "ProductVersion")
#define AppPublisher "Yannick Buchet"
#define AppUrl "https://github.com/yannickbuchet-ctrl/pdf-toolkit-2"

[Setup]
; Identifiant permanent de l'application : ne jamais le changer (mises à jour et désinstallation).
AppId={{FCEB06FB-5DF8-411F-BB23-72CD881AF940}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}
AppCopyright=© 2026 {#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Installation de {#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\LICENSE
SetupIconFile=..\PDF Toolkit 2.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir=..\dist
OutputBaseFilename=PDF-Toolkit-2-Installation-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
ChangesAssociations=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "ouvriravec"; Description: "Proposer {#AppName} dans le menu « Ouvrir avec » des fichiers PDF"; GroupDescription: "Fichiers PDF :"

[Files]
Source: "{#AppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; « Ouvrir avec » : l'application se déclare pour les PDF, sans devenir le lecteur par défaut. Retiré à la
; désinstallation.
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey; Tasks: ouvriravec
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Tasks: ouvriravec
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: ouvriravec
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithList\{#AppExe}"; ValueType: none; Flags: uninsdeletekey; Tasks: ouvriravec

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
