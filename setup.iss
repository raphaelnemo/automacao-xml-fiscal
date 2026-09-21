#define MyAppName "OSC ERP Fiscal"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Organiza"
#define MyAppExeName "run_app.exe"
#define SourcePath "C:\Projetos\automacao_xml_homologacao\dist\run_app"

[Setup]
AppId={{8F5A3B21-C910-4A82-9B1D-6F479C1283A4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=C:\Projetos\automacao_xml_homologacao\installer_output
OutputBaseFilename=setup_osc_fiscal
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copia todos os arquivos compilados e a pasta _internal
Source: "{#SourcePath}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Garante que as pastas de persistencia existam no cliente
Name: "{app}\segredos"; Permissions: users-full
Name: "{app}\armazenamento"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full

[Icons]
; Atalho no Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Gerenciador Mestre"; Filename: "{app}\gerenciador_mestre.bat"; IconFilename: "{sys}\cmd.exe"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Atalho opcional na Area de Trabalho
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Inicia o ERP automaticamente apos finalizar a instalacao
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent