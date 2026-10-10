"""Şerit ikonlarını (20 px ve 32 px ızgara) tek PNG'ye çizer: keskinlik denetimi (5j-2).

Kullanım: .venv\\Scripts\\python araclar/ikon_sayfasi.py [çıktı.png]
Her ikon kendi ızgarasında 1x, 1,5x ve 2x çizilir; 20 px ikonların 1x sürümü ayrıca 4x büyütülüp
piksel ızgarası incelenebilsin diye eklenir. Ekran görüntüsü incelenir (bulanık/kayık çizgi yok)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from tabcel.ui import icons


def ciz(yol: str) -> None:
    QApplication.instance() or QApplication([])
    adlar = list(icons.ICONS)
    hucre_g, hucre_y = 250, 120
    sutun = 5
    satir = (len(adlar) + sutun - 1) // sutun
    img = QImage(sutun * hucre_g, satir * hucre_y, QImage.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    yazi = QFont("Segoe UI", 7)
    for i, ad in enumerate(adlar):
        x0, y0 = (i % sutun) * hucre_g, (i // sutun) * hucre_y
        g = icons.ICONS[ad].get("grid", icons.GRID)
        x = x0 + 6
        for oran in (1.0, 1.5, 2.0):
            b = round(g * oran)
            icons.draw(p, QRectF(x, y0 + 6, b, b), ad)
            x += b + 8
        if g == icons.GRID:
            kucuk = QImage(g, g, QImage.Format_RGB32)
            kucuk.fill(Qt.white)
            q = QPainter(kucuk)
            icons.draw(q, QRectF(0, 0, g, g), ad)
            q.end()
            p.drawImage(QRectF(x0 + 160, y0 + 6, 80, 80),
                        kucuk.scaled(80, 80, Qt.IgnoreAspectRatio, Qt.FastTransformation))
        p.setPen(QColor("#666"))
        p.setFont(yazi)
        p.drawText(QRectF(x0 + 6, y0 + hucre_y - 22, hucre_g - 12, 18), Qt.AlignLeft, ad)
    p.end()
    img.save(yol)
    print(f"{len(adlar)} ikon -> {yol}")


if __name__ == "__main__":
    ciz(sys.argv[1] if len(sys.argv) > 1 else "ikon_sayfasi.png")
