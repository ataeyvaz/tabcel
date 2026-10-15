"""Giriş noktası: python main.py [dosya.xlsx ...]"""
import sys

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from tabcel import APP_NAME, resource_dir
from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.window import Pencere


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    # Qt'nin hazır iletişim kutusu metinleri (Tamam/İptal, Evet/Hayır, dosya/renk seçici) Türkçe olsun:
    # Windows görüntü dili İngilizce olsa bile (kullanıcı arayüzü her zaman Türkçe).
    cevirmen = QTranslator(app)
    if cevirmen.load("qtbase_tr", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(cevirmen)
    ikon = resource_dir() / "tabcel.ico"
    if ikon.is_file():
        app.setWindowIcon(QIcon(str(ikon)))
    # setOrganizationName bilerek çağrılmıyor (CLAUDE.md kural 1).
    pencereler = []
    for yol in sys.argv[1:]:                       # komut satırından dosya açma
        ilk = pencereler[0] if pencereler else Pencere(CalismaKitabi())
        p = ilk.dosya_ac(yol)
        if p is not None and p not in pencereler:
            pencereler.append(p)
        if not pencereler:
            pencereler.append(ilk)
    if not pencereler:
        pencereler.append(Pencere(CalismaKitabi()))
    for p in pencereler:
        p.show()
    pencereler[0].kurtarma_denetle()               # çökme sonrası kurtarma önerisi
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
