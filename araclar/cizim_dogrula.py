"""Artımlı çizimin (piksel kaydırma + kısmi boyama) sıfırdan çizimle aynı pikselleri verdiğini doğrular.

GERÇEK PENCERE gerekir (ekran görüntüsü alır; ekransız/offscreen ortamda çalışmaz, çalışırken
pencere ekranda görünür, farenin/pencerenin üstüne başka şey gelmemeli):

    .venv\\Scripts\\python araclar\\cizim_dogrula.py

Gerçek ekran görüntüsü (QScreen.grabWindow) ile widget.grab() (tam çizim) karşılaştırılır; çıkış
kodu 0 = fark yok, 1 = fark var (farklı karelerin PNG'leri geçici klasöre kaydedilir).
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")
from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tabcel.model.sayfa import CalismaKitabi, Hucre  # noqa: E402
from tabcel.ui.window import Pencere  # noqa: E402

TOLERANS = 1          # bilinen: seçili alan kısmen ekran dışındayken 1 piksellik köşe artefaktı

app = QApplication([])
k = CalismaKitabi()
s = k.sayfalar[0]
for r in range(1, 400):
    for c in range(1, 12):
        s.ata(r, c, Hucre(f"Satır {r} uzun metin" if c == 1 else float(r * c) + 0.25))
s.ata(30, 3, Hucre("bu metin sağa taşıyor ve komşuları kapatıyor"))
p = Pencere(k)
p.resize(900, 560)
p.move(50, 50)
p.show()
p.raise_()
p.activateWindow()
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)
g = p.izgara()
vp = g.viewport()
vs = g.verticalScrollBar()
ekran = QGuiApplication.primaryScreen()
SP = tempfile.gettempdir() + os.sep


def karsilastir(ad):
    for _ in range(6):
        app.processEvents()
        time.sleep(0.03)
    gercek = ekran.grabWindow(p.winId()).toImage()
    taze = p.grab().toImage()
    if gercek.size() != taze.size():
        taze = taze.scaled(gercek.size())
    sol_ust = vp.mapTo(p, QPoint(0, 0))          # yalnızca ızgara viewport'u karşılaştırılır
    fark, toplam = 0, 0
    kutu = [10 ** 9, 10 ** 9, -1, -1]
    ornek = None
    for y in range(vp.height()):
        for x in range(vp.width()):
            a = gercek.pixel(sol_ust.x() + x, sol_ust.y() + y)
            b = taze.pixel(sol_ust.x() + x, sol_ust.y() + y)
            toplam += 1
            if a != b:
                fark += 1
                kutu = [min(kutu[0], x), min(kutu[1], y), max(kutu[2], x), max(kutu[3], y)]
                if ornek is None:
                    ornek = (x, y, hex(a & 0xffffff), hex(b & 0xffffff))
    print(f"{ad:<46} farklı piksel: {fark} / {toplam}" +
          (f"  kutu={kutu} ilk fark (x,y,gerçek,taze)={ornek}" if fark else ""))
    if fark:
        taze.save(SP + "fark_taze.png")
        gercek.save(SP + "fark_gercek.png")
    return fark


sonuc = [karsilastir("başlangıç")]
for i in range(1, 8):
    vs.setValue(i)
    app.processEvents()
sonuc.append(karsilastir("7 satır aşağı kaydırma (artımlı)"))
for i in range(6, -1, -1):
    vs.setValue(i)
    app.processEvents()
sonuc.append(karsilastir("7 satır yukarı kaydırma (artımlı)"))
vs.setValue(25)
app.processEvents()
vs.setValue(28)
app.processEvents()
sonuc.append(karsilastir("taşan metin satırına kaydırma"))
g.sec((30, 2), (33, 4))
sonuc.append(karsilastir("çok hücreli seçim (kısmi boyama)"))
vs.setValue(31)
app.processEvents()
vs.setValue(30)
app.processEvents()
sonuc.append(karsilastir("seçili alanla kaydırma"))
g.sec((32, 6))
sonuc.append(karsilastir("seçimi taşıma (eski/yeni bölge)"))
QTest.mouseClick(vp, Qt.LeftButton, Qt.ControlModifier, g.hucre_dikdortgeni(34, 7).center())
sonuc.append(karsilastir("Ctrl+tık çoklu seçim"))
g.sec((31, 1), (31, 3))
g.kopyala()
sonuc.append(karsilastir("kopyalama çerçevesi"))
g._sutun_sec(2, False)
sonuc.append(karsilastir("sütun seçimi"))
for i in range(30, 36):
    vs.setValue(i)
    app.processEvents()
    sonuc.append(karsilastir(f"  sütun seçili, kaydırma değeri {i}"))
toplam_fark = sum(sonuc)
print(f"TOPLAM FARK: {toplam_fark} piksel (tolerans {TOLERANS})")
sys.exit(0 if toplam_fark <= TOLERANS else 1)
