; Tabcel kurulum paketi (Inno Setup 6)
; Derleme:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" kurulum\tabcel.iss
; Önce PyInstaller paketi hazırlanmalı:  .venv\Scripts\python.exe -m PyInstaller tabcel.spec --noconfirm
; Kullanıcı verisi (%APPDATA%\Tabcel: son dosyalar, kurtarma kopyaları) kaldırmada SİLİNMEZ.

#define AppName "Tabcel"
#define AppVersion "0.1"
#define AppPublisher "Eagle Office"
#define AppContact "mailto:ataeyvaz@gmail.com"
#define AppExe "Tabcel.exe"

[Setup]
AppId={{B3F1C2D4-5A6E-4F70-8B19-2C7D9E0A4F33}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppSupportURL={#AppContact}
AppContact={#AppContact}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Tabcel-{#AppVersion}-kurulum
SetupIconFile=..\tabcel.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstünde kısayol oluştur"; GroupDescription: "Ek kısayollar:"
Name: "xlsxassoc"; Description: "Excel çalışma kitaplarını (.xlsx) {#AppName} ile açmak için ilişkilendir"; \
    GroupDescription: "Dosya türleri:"; Flags: unchecked
Name: "csvassoc"; Description: "CSV dosyalarını (.csv) {#AppName} ile açmak için ilişkilendir"; \
    GroupDescription: "Dosya türleri:"; Flags: unchecked

[InstallDelete]
; eski sürümden kalanlar: temiz kurulum
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\Tabcel\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\Tabcel\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} Kaldır"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; "Birlikte aç" listesinde görünsün
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; \
    ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; \
    ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".xlsx"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; \
    ValueType: string; ValueName: ".csv"; ValueData: ""
; İsteğe bağlı: .xlsx dosyalarını doğrudan Tabcel açsın (varsayılan program seçimi Windows'ta kullanıcıdadır;
; burada "Birlikte aç" önerisi olarak eklenir)
Root: HKA; Subkey: "Software\Classes\.xlsx\OpenWithProgids"; ValueType: string; \
    ValueName: "Tabcel.Kitap"; ValueData: ""; Tasks: xlsxassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.csv\OpenWithProgids"; ValueType: string; \
    ValueName: "Tabcel.Kitap"; ValueData: ""; Tasks: csvassoc; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Tabcel.Kitap"; ValueType: string; ValueName: ""; \
    ValueData: "Çalışma Kitabı ({#AppName})"; Tasks: xlsxassoc csvassoc; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Tabcel.Kitap\DefaultIcon"; ValueType: string; ValueName: ""; \
    ValueData: "{app}\{#AppExe},0"; Tasks: xlsxassoc csvassoc
Root: HKA; Subkey: "Software\Classes\Tabcel.Kitap\shell\open\command"; ValueType: string; ValueName: ""; \
    ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: xlsxassoc csvassoc

[Run]
Filename: "{app}\{#AppExe}"; Description: "{#AppName}'i şimdi çalıştır"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
