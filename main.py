"""Giriş noktası: python main.py [dosya.xlsx]"""
import sys

from PySide6.QtWidgets import QApplication

from tabcel import APP_NAME
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    # setOrganizationName bilerek çağrılmıyor (CLAUDE.md kural 1).
    kitap = CalismaKitabi()
    sayfa = kitap.sayfalar[0]
    # Geçici örnek veri (dosya açma gelince kalkacak)
    for i, ad in enumerate(("Ürün", "Adet", "Fiyat"), start=1):
        sayfa.ata(1, i, Hucre(ad))
    for r in range(2, 12):
        sayfa.ata(r, 1, Hucre(f"Kalem {r - 1}"))
        sayfa.ata(r, 2, Hucre(float(r * 3)))
        sayfa.ata(r, 3, Hucre(r * 1.25))
    win = Pencere(kitap)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
