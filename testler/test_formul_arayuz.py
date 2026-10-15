"""Formül motorunun arayüze bağlanması: yazınca hesaplanır, düzenlerken Türkçe görünür,
hatalı formülde düzenleme açık kalır (ekransız)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import window
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: None)
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 4):
        s.ata(r, 1, Hucre(float(r)))
    p = Pencere(k)
    p.show()
    return p


def yaz_onayla(g, metin):
    QTest.keyClicks(g, metin[0])
    QTest.keyClicks(g.focusWidget(), metin[1:])
    QTest.keyClick(g.focusWidget(), Qt.Key_Return)


def test_formul_yazinca_hesaplanir(pencere):
    g = pencere.izgara()
    g.sec((1, 2))
    yaz_onayla(g, "=TOPLA(A1:A3;2,5)")
    s = g.sayfa
    assert s.hucre(1, 2).formul == "=SUM(A1:A3,2.5)"
    assert s.deger(1, 2) == 8.5
    g.sec((1, 2))
    assert pencere.formul.text() == "=TOPLA(A1:A3;2,5)"


def test_bagimli_hucre_guncellenir_ve_geri_al(pencere):
    g = pencere.izgara()
    g.sec((1, 2))
    yaz_onayla(g, "=A1*10")
    g.sec((1, 1))
    yaz_onayla(g, "7")
    assert g.sayfa.deger(1, 2) == 70.0
    g.geri_al()
    assert g.sayfa.deger(1, 2) == 10.0


def test_f2_turkce_gosterir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(5, 5, Hucre(None, "=IF(A1>0,TRUE,1.5)"))
    g.sec((5, 5))
    QTest.keyClick(g, Qt.Key_F2)
    assert g.focusWidget().text() == "=EĞER(A1>0;DOĞRU;1,5)"


def test_hatali_formul_duzenleme_acik_kalir(pencere):
    g = pencere.izgara()
    uyarilar = []
    g.uyari.connect(uyarilar.append)
    g.sec((2, 2))
    yaz_onayla(g, "=TOPLA(A1")
    assert uyarilar and "sorun" in uyarilar[0]
    assert g.duzenleniyor()
    assert g.focusWidget().text() == "=TOPLA(A1"
    assert g.sayfa.hucre(2, 2) is None
    QTest.keyClicks(g.focusWidget(), ")")
    QTest.keyClick(g.focusWidget(), Qt.Key_Return)
    assert not g.duzenleniyor() and g.sayfa.deger(2, 2) == 1.0


def test_formul_cubugundan_hatali(pencere):
    g = pencere.izgara()
    g.sec((3, 3))
    pencere.formul.setText("=1+")
    pencere.formul.onayla.emit("=1+")
    assert g.aktif == (3, 3) and g.sayfa.hucre(3, 3) is None


def test_baska_sayfa_formulu(pencere):
    s2 = pencere.kitap.sayfa_ekle("Gelir Gider")
    s2.ata(1, 1, Hucre(4.0))
    g = pencere.izgara()
    g.sec((4, 1))
    yaz_onayla(g, "='Gelir Gider'!A1*2")
    assert g.sayfa.deger(4, 1) == 8.0
    pencere.kitap.yeniden_adlandir(s2, "Gelir")
    g.sec((4, 1))
    assert pencere.formul.text() == "=Gelir!A1*2"


def test_hata_sonucu_turkce_cizilir(pencere):
    g = pencere.izgara()
    g.sec((6, 1))
    yaz_onayla(g, "=1/0")
    from tabcel.ui.grid import goster
    assert goster(g.sayfa.deger(6, 1)) == "#SAYI/0!"
