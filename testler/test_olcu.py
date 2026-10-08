from tabcel.model.olcu import (
    genislik_sinirla, karakter_px, punto_px, px_karakter, px_punto, yukseklik_sinirla,
)
from tabcel.model.sayfa import Sayfa


def test_excel_varsayilanlari():
    assert karakter_px(8.43) == 64
    assert punto_px(15) == 20
    assert px_karakter(64) == 8.43
    assert px_punto(20) == 15.0
    assert karakter_px(8.43) == Sayfa.VARSAYILAN_SUTUN_GENISLIGI
    assert punto_px(15) == Sayfa.VARSAYILAN_SATIR_YUKSEKLIGI


def test_gidis_donus():
    for kar in (1, 5.5, 8.43, 20, 100):
        assert abs(px_karakter(karakter_px(kar)) - kar) < 0.1
    for pt in (6, 12.75, 15, 30):
        assert abs(px_punto(punto_px(pt)) - pt) < 0.5


def test_sinirlar():
    assert genislik_sinirla(-5) == 3 and genislik_sinirla(99999) == 1790
    assert yukseklik_sinirla(0) == 3 and yukseklik_sinirla(99999) == 545
    assert genislik_sinirla(64.4) == 64
