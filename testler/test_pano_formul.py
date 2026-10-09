"""Pano ve formül (6c): kopyalayınca başvurular kayar, kes-yapıştır taşır, dışarıdan gelen Türkçe
formül saklanan biçime çevrilir (ekransız)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication

from tabcel.model import pano
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import window
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: None)
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 4):
        s.ata(r, 1, Hucre(float(r)))
    p = Pencere(k)
    p.show()
    return p


def test_formul_kopyalayinca_basvuru_kayar_ve_hesaplanir(pencere):
    g = pencere.izgara()
    s = g.sayfa
    s.toplu_yaz({(1, 2): Hucre(None, "=A1*10")})
    g.sec((1, 2))
    g.kopyala()
    g.sec((2, 2), (3, 2))
    g.yapistir()
    assert s.hucre(2, 2).formul == "=A2*10" and s.hucre(3, 2).formul == "=A3*10"
    assert [s.deger(r, 2) for r in (1, 2, 3)] == [10.0, 20.0, 30.0]
    g.geri_al()
    assert s.hucre(2, 2) is None


def test_mutlak_basvuru_kaymaz(pencere):
    g = pencere.izgara()
    s = g.sayfa
    s.toplu_yaz({(1, 2): Hucre(None, "=$A$1+A1")})
    g.sec((1, 2)); g.kopyala()
    g.sec((3, 3)); g.yapistir()
    assert s.hucre(3, 3).formul == "=$A$1+B3"


def test_kes_yapistir_formulu_tasir_basvuranlar_kayar(pencere):
    g = pencere.izgara()
    s = g.sayfa
    s.toplu_yaz({(1, 3): Hucre(None, "=A1+A2"), (5, 5): Hucre(None, "=A1*2")})
    g.sec((1, 1), (2, 1))
    g.kes()
    g.sec((1, 7))
    g.yapistir()
    assert s.deger(1, 7) == 1.0 and s.deger(1, 1) is None
    assert s.hucre(1, 3).formul == "=G1+G2"            # taşınan bölgeye işaret eden formül kaydı
    assert s.hucre(5, 5).formul == "=G1*2"
    assert s.deger(1, 3) == 3.0 and s.deger(5, 5) == 2.0
    g.geri_al()                                         # tek adım
    assert s.hucre(1, 3).formul == "=A1+A2" and s.deger(1, 1) == 1.0 and s.deger(1, 7) is None


def test_kes_yapistir_tasinan_formulun_kendi_basvurusu_kaymaz(pencere):
    g = pencere.izgara()
    s = g.sayfa
    s.toplu_yaz({(1, 3): Hucre(None, "=A1+A2")})
    g.sec((1, 3)); g.kes()
    g.sec((6, 6)); g.yapistir()
    assert s.hucre(6, 6).formul == "=A1+A2" and s.deger(6, 6) == 3.0


def test_disaridan_turkce_formul_kanonik_saklanir(pencere):
    g = pencere.izgara()
    s = g.sayfa
    md = QMimeData()
    md.setText("=TOPLA(A1:A3;2,5)\t=YOKBOYLEBIR(\r\n")
    QApplication.clipboard().setMimeData(md)
    g.sec((1, 4))
    g.yapistir()
    assert s.hucre(1, 4).formul == "=SUM(A1:A3,2.5)" and s.deger(1, 4) == 8.5
    h = s.hucre(1, 5)                                   # hatalı formül düz metin kalır
    assert h.formul is None and h.deger == "=YOKBOYLEBIR("


def test_baska_oturumdan_gelen_formul_ingilizceden_cevrilir(pencere):
    g = pencere.izgara()
    s = g.sayfa
    s.toplu_yaz({(1, 2): Hucre(None, "=SUM(A1:A3)")})
    g.sec((1, 2)); g.kopyala()
    md = QApplication.clipboard().mimeData()
    # aynı veriyi başka oturumdan gelmiş gibi yeniden paketle
    v = pano.PanoVerisi.json_oku(bytes(md.data(g.MIME_HUCRELER)).decode("utf-8"))
    assert v.en_formul[(0, 0)] == "=SUM(A1:A3)"
    v.oturum = "baska"
    v.hucreler[(0, 0)] = Hucre(None, "=[99]!ZZ9")       # kimlik bu oturumda anlamsız
    md2 = QMimeData()
    md2.setData(g.MIME_HUCRELER, v.json_yaz().encode("utf-8"))
    QApplication.clipboard().setMimeData(md2)
    g.sec((1, 6)); g.yapistir()
    assert s.hucre(1, 6).formul == "=SUM(E1:E3)"        # B1 → F1: 4 sütun kayar
