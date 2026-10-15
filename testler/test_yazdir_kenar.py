"""Yazdırma/PDF doğruluğu (2026-10-15 elle yazdırma testi): kenar boşluğu iki kez sayılmaz, grafik yazı tipleri yazıcıda büyümez.
PDF, QtPdf ile geri okunup ölçülür (gerçek çıktı)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.sayfa_yapisi import SayfaYapisi
from tabcel.ui import yazdir as yz
from tabcel.ui.grid import Izgara


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def sayfa_goruntusu(yol: str, dpi: int = 100):
    d = QPdfDocument()
    assert d.load(yol) == QPdfDocument.Error.None_
    ps = d.pagePointSize(0)
    w, h = int(ps.width() / 72 * dpi), int(ps.height() / 72 * dpi)
    ham = d.render(0, QSize(w, h))
    im = QImage(w, h, QImage.Format_RGB32)
    im.fill(QColor("white"))
    p = QPainter(im)
    p.drawImage(0, 0, ham)
    p.end()
    return im, d.pageCount(), (ps.width(), ps.height())


def icerik_kutusu(im: QImage):
    """İçeriğin (beyaz olmayan piksel) sınırları: sol, üst, sağ, alt (piksel)."""
    w, h = im.width(), im.height()
    koyu = lambda x, y: im.pixelColor(x, y).lightness() < 235          # noqa: E731
    sol = next((x for x in range(w) if any(koyu(x, y) for y in range(0, h, 2))), None)
    sag = next((x for x in range(w - 1, -1, -1) if any(koyu(x, y) for y in range(0, h, 2))), None)
    ust = next((y for y in range(h) if any(koyu(x, y) for x in range(0, w, 2))), None)
    alt = next((y for y in range(h - 1, -1, -1) if any(koyu(x, y) for x in range(0, w, 2))), None)
    return sol, ust, sag, alt


def _izgara(yapi: SayfaYapisi):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 6):
        for c in range(1, 4):
            s.ata(r, c, Hucre(f"Satır {r} Sütun {c}"))
    s.sayfa_yapisi = yapi
    return Izgara(s)


@pytest.mark.parametrize("ust,sol", [(2.54, 1.91), (1.91, 1.78), (0.5, 0.5)])
def test_icerik_kenar_boslugunda_baslar(app, tmp_path, ust, sol):
    """İçeriğin sol/üst kenarı tam olarak ayarlanan kenar boşluğundadır (önceden 2 katıydı)."""
    from dataclasses import replace
    yapi = replace(SayfaYapisi(), ust=ust, sol=sol, alt=ust, sag=sol)
    g = _izgara(yapi)
    yol = str(tmp_path / "k.pdf")
    assert yz.pdf_yaz([g], yol)
    im, sayfa_sayisi, _ = sayfa_goruntusu(yol)
    sl, us, _sg, _al = icerik_kutusu(im)
    beklenen_sol, beklenen_ust = sol / 2.54 * 100, ust / 2.54 * 100               # 100 dpi
    assert abs(sl - beklenen_sol) <= 4, (sl, beklenen_sol)
    assert abs(us - beklenen_ust) <= 8, (us, beklenen_ust)                        # ilk satır yazısı kutuda biraz aşağıda


def test_yatay_sayfada_da_dogru(app, tmp_path):
    from dataclasses import replace
    yapi = replace(SayfaYapisi(), yon="yatay", ust=1.0, sol=2.0, alt=1.0, sag=2.0)
    g = _izgara(yapi)
    yol = str(tmp_path / "y.pdf")
    assert yz.pdf_yaz([g], yol)
    im, _, (w, h) = sayfa_goruntusu(yol)
    assert w > h                                                                    # yatay
    sl, us, _, _ = icerik_kutusu(im)
    assert abs(sl - 2.0 / 2.54 * 100) <= 4 and abs(us - 1.0 / 2.54 * 100) <= 8


def test_grafik_yazi_tipleri_yazicida_buyumez(app, tmp_path):
    """Yazıcıda (1200 dpi) punto tabanlı yazı ×12 büyüyordu: eksen etiketleri sayfayı kaplıyordu."""
    from tabcel.io import xlsx_io
    kit, _ = xlsx_io.ac(os.path.join(os.path.dirname(__file__), "ornekler", "grafikli.xlsx"))
    ilk = Izgara(kit.sayfalar[0])
    yol = str(tmp_path / "g.pdf")
    assert yz.pdf_yaz([ilk], yol)
    im, _, _ = sayfa_goruntusu(yol)
    # yalnız birkaç küçük metin ve mavi sütunlar olmalı: koyu gri (büyük harf) alan sayfanın %3'ünü geçmemeli
    koyu = sum(1 for y in range(0, im.height(), 3) for x in range(0, im.width(), 3) if im.pixelColor(x, y).lightness() < 120)
    toplam = (im.height() // 3) * (im.width() // 3)
    assert koyu / toplam < 0.03, koyu / toplam


def test_grafik_yazi_tipi_piksel_boyutlu():
    from tabcel.ui.grafik_boyayici import yazi_tipi
    f = yazi_tipi(9.0)
    assert f.pixelSize() == 12 and f.pointSizeF() < 0 or f.pixelSize() == 12                # 9 pt = 12 px (96 dpi)
    assert yazi_tipi(0.2).pixelSize() >= 1
