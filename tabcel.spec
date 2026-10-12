# Tabcel — PyInstaller paketi (klasör/onedir biçiminde; PySide6 LGPLv3 uyumu için onefile KULLANILMAZ, bkz. surec.md Lisans uyum notu)
# Derleme:  .venv\Scripts\python.exe -m PyInstaller tabcel.spec --noconfirm
# Çıktı: dist\Tabcel\Tabcel.exe (+ _internal). Kurulum paketi: kurulum\tabcel.iss (Inno Setup).
# PyInstaller yalnız derleme aracıdır (GPL + paketleme istisnası); pakete girmez, requirements.txt'te yok.

from pathlib import Path

project = Path(SPECPATH)

datas = [
    (str(project / "tabcel" / "yardim.md"), "tabcel"),     # resource_dir() / "tabcel" / "yardim.md"
    (str(project / "tabcel" / "veri" / "resmi_tatiller.json"), "tabcel/veri"),   # model/tatiller.py
    (str(project / "tabcel" / "sablonlar"), "tabcel/sablonlar"),                  # sablon/yukleyici.py (yerleşik şablon tanımları)
    (str(project / "tabcel.ico"), "."),
]

hiddenimports = ["comtypes", "comtypes.client", "PIL", "openpyxl", "et_xmlfile", "xlrd", "olefile",
                 "msoffcrypto", "msoffcrypto.format.ooxml"]

# Kullanılmayan büyük bileşenler (grafikler QPainter ile; QtCharts GPL olduğu için hiç kullanılmaz)
excludes = ["tkinter", "matplotlib", "numpy", "scipy", "pandas", "torch", "sympy", "networkx",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtWebEngineCore", "PySide6.QtCharts",
            "PySide6.QtDataVisualization", "PySide6.QtMultimedia", "PySide6.QtNetwork", "PySide6.QtPdf",
            "PySide6.QtOpenGL", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtBluetooth", "PySide6.QtSensors"]

analysis = Analysis(
    [str(project / "main.py")],
    pathex=[str(project)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=excludes,
    noarchive=False,
)

# Qt eklentileri ve DLL'lerinden kullanılmayanlar; arayüz Qt çevirilerini yüklemiyor
UNUSED_QT = ("opengl32sw.dll", "qtvirtualkeyboardplugin", "qt6virtualkeyboard", "qt6quick", "qt6qml",
             "qt6pdf", "qpdf.dll", "qt6network", "qtnetwork.pyd", "plugins/networkinformation", "plugins/tls",
             "qdirect2d.dll", "qt6opengl.dll")


def _keep(entry):
    name = entry[0].replace("\\", "/").lower()
    if "pyside6/" not in name:
        return True
    if "pyside6/translations/" in name:
        return name.endswith(("qtbase_tr.qm", "qt_tr.qm"))
    return not any(part in name for part in UNUSED_QT)


analysis.binaries = [entry for entry in analysis.binaries if _keep(entry)]
analysis.datas = [entry for entry in analysis.datas if _keep(entry)]

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Tabcel",
    icon=str(project / "tabcel.ico"),
    console=False,
    disable_windowed_traceback=False,
    version=None,
)

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="Tabcel",
)
