; Instalador de RenombradorPDF - Inno Setup 6
; Compilar: abrir este archivo con Inno Setup y pulsar Compilar,
; o ejecutar construir.bat en la raiz del proyecto.

#define MiNombre "RenombradorPDF"
#define MiTitulo "Asistente de Renombrado de PDFs"
#define MiVersion "3.0"
#define MiAutor "Levi"
#define MiExe "RenombradorPDF-Experimental.exe"

[Setup]
AppId={{8F3C4D21-9A6E-4B7C-9E15-2D0A7C6B41F3}
AppName={#MiTitulo}
AppVersion={#MiVersion}
AppVerName={#MiTitulo} {#MiVersion}
AppPublisher={#MiAutor}
DefaultDirName={autopf}\{#MiNombre}
DefaultGroupName={#MiTitulo}
DisableProgramGroupPage=yes
OutputDir=salida
OutputBaseFilename=RenombradorPDF-{#MiVersion}-instalador
SetupIconFile=..\assets\icono.ico
UninstallDisplayIcon={app}\{#MiExe}
UninstallDisplayName={#MiTitulo} {#MiVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
; Todo el contenido generado por PyInstaller, incluida la carpeta tesseract\
Source: "..\dist\RenombradorPDF-Experimental\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; Carpetas de trabajo con permiso de escritura para cualquier usuario
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\src"; Permissions: users-modify
Name: "{app}\archivos_entrada\informe"; Permissions: users-modify
Name: "{app}\archivos_entrada\pdfs_a_renombrar"; Permissions: users-modify
Name: "{app}\archivos_salida\renombrados"; Permissions: users-modify

[Icons]
Name: "{group}\{#MiTitulo}"; Filename: "{app}\{#MiExe}"
Name: "{group}\Desinstalar {#MiTitulo}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MiTitulo}"; Filename: "{app}\{#MiExe}"; Tasks: escritorio

[Run]
Filename: "{app}\{#MiExe}"; Description: "Abrir {#MiTitulo} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Los logs se generan despues de instalar; se limpian al desinstalar
Type: filesandordirs; Name: "{app}\logs"
