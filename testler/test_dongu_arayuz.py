"""Döngüsel başvuru uyarısı arayüzde (6e): durum çubuğu etiketi + yeni döngüde tek uyarı."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import window
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    uyarilar = []
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: uyarilar.append(a[2]))
    Izgara._pano_durumu = None
    p = Pencere(CalismaKitabi())
    p.uyarilar = uyarilar
    p.show()
    return p


def gir(g, r, c, metin):
    g.hucre_gir(r, c, metin)


def test_dongu_yoksa_etiket_gizli(pencere):
    g = pencere.izgara()
    gir(g, 1, 1, "=1+1")
    assert not pencere.dongu_etiketi.isVisible() and pencere.uyarilar == []


def test_dongu_olusunca_etiket_ve_tek_uyari(pencere):
    g = pencere.izgara()
    gir(g, 1, 1, "=B1+1")
    assert pencere.uyarilar == []
    gir(g, 1, 2, "=A1+1")                           # döngü kapandı
    assert len(pencere.uyarilar) == 1 and "döngüsel" in pencere.uyarilar[0]
    assert pencere.dongu_etiketi.isVisible()
    assert pencere.dongu_etiketi.text() == "Döngüsel Başvurular: A1"
    gir(g, 3, 3, "=1")                              # alakasız giriş: yeniden uyarı yok
    assert len(pencere.uyarilar) == 1


def test_dongu_cozulunce_etiket_kalkar(pencere):
    g = pencere.izgara()
    gir(g, 1, 1, "=B1+1")
    gir(g, 1, 2, "=A1+1")
    gir(g, 1, 2, "5")
    assert not pencere.dongu_etiketi.isVisible()


def test_kendine_basvuru_ve_geri_al_uyarmaz(pencere):
    g = pencere.izgara()
    gir(g, 2, 2, "=B2")
    assert len(pencere.uyarilar) == 1 and pencere.dongu_etiketi.text() == "Döngüsel Başvurular: B2"
    g.geri_al()
    assert not pencere.dongu_etiketi.isVisible()
    g.yinele()                                      # yinelemede döngü geri gelir: uyarı yok, etiket var
    assert len(pencere.uyarilar) == 1 and pencere.dongu_etiketi.isVisible()


def test_baska_sayfadaki_dongu_adressiz_etiket(pencere):
    g1 = pencere.izgara()
    gir(g1, 1, 1, "=A1")
    pencere.sayfa_ekle()                            # yeni sayfa seçilir; döngü ilk sayfada
    assert pencere.dongu_etiketi.isVisible() and pencere.dongu_etiketi.text() == "Döngüsel Başvurular"
    pencere.sekmeler.setCurrentIndex(0)
    assert pencere.dongu_etiketi.text() == "Döngüsel Başvurular: A1"
