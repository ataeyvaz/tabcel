"""Giriş noktası: python main.py [dosya.xlsx ...]"""
import sys

from PySide6.QtWidgets import QApplication

from tabcel import APP_NAME
from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.window import Pencere


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
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
