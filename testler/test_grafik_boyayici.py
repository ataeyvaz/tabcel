"""Faz 6 / 6d (ilk parça): çizim listesinin QPainter ile oynatılması (ekransız; piksel örnekleri)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from tabcel.model.grafik import Grafik
from tabcel.model.grafik_cizim import PALET, Dikdortgen, Dilim, Isaret
from tabcel.model.grafik_verisi import GrafikVerisi, SeriVerisi
from tabcel.ui.grafik_boyayici import grafik_ciz, olcer_yap

W, H = 480, 288


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def veri(*degerler):
    return GrafikVerisi(tuple(SeriVerisi(f"S{i}", tuple(d), [str(k + 1) for k in range(len(d))], None, None)
                              for i, d in enumerate(degerler)))


def render(v, **kw):
    img = QImage(W, H, QImage.Format_RGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    liste = grafik_ciz(p, v, Grafik(**kw), (W, H))
    p.end()
    return img, liste


def renk(img, x, y):
    return img.pixelColor(int(x), int(y)).name().upper()


def test_cubuklar_listedeki_renkte_boyanir(app):
    img, liste = render(veri([10, 20, 30]), tur="sutun", gosterge=None)
    cubuklar = [o for o in liste if isinstance(o, Dikdortgen) and o.dolgu == PALET[0]]
    assert len(cubuklar) == 3
    for c in cubuklar:
        assert renk(img, c.x + c.w / 2, c.y + c.h / 2) == PALET[0]


def test_pasta_dilimleri_ve_halka_deligi(app):
    img, liste = render(veri([1, 1, 2]), tur="halka", gosterge=None)
    d = [o for o in liste if isinstance(o, Dilim)]
    cx, cy, r = d[0].cx, d[0].cy, d[0].r_dis
    assert renk(img, cx, cy) == "#FFFFFF"                                        # halkanın deliği boş
    # 12 yönünden saat yönünde ilk dilim (90°): sağ üst çeyrek, ortalama yarıçapta
    assert renk(img, cx + r * 0.75 * 0.7, cy - r * 0.75 * 0.7) == PALET[0]
    assert renk(img, cx + r * 0.75 * 0.7, cy + r * 0.75 * 0.7) == PALET[1]      # ikinci dilim: sağ alt
    assert renk(img, cx - r * 0.75, cy) == PALET[2]                              # üçüncü (180°): sol yarı


def test_isaret_ve_cizgi(app):
    img, liste = render(GrafikVerisi((SeriVerisi("A", (1.0, 5.0, 3.0), ["a", "b", "c"], None, None),)),
                        tur="cizgi", gosterge=None)
    i = [o for o in liste if isinstance(o, Isaret)]
    assert len(i) == 3
    assert renk(img, i[1].x, i[1].y) == PALET[0]


def test_bos_grafik_cizilir_hata_vermez(app):
    img, liste = render(GrafikVerisi(()), tur="sutun", baslik="Boş")
    assert img.pixelColor(2, 2).name().upper() != "#000000"


def test_kirik_cizgi_bosluk_kopar(app):
    v = GrafikVerisi((SeriVerisi("A", (5.0, None, None, 5.0), ["a", "b", "c", "d"], None, None),))
    img, liste = render(v, tur="cizgi", gosterge=None)
    x, y, w, h = liste.grafik_alani
    # iki noktanın ortası boşluk: orada çizgi rengi yok
    yy = [o for o in liste if isinstance(o, Isaret)][0].y
    assert renk(img, x + w / 2, yy) != PALET[0]


def test_olcer_yakinlastirmayla_buyur(app):
    o = olcer_yap()
    a, b = o("Merhaba", 9), o("Merhaba", 18)
    assert b[0] > a[0] * 1.8 and b[1] > a[1] * 1.8
