"""Faz 3 / 3k: biçim boyacısı — model (Qt'siz desen/yineleme) + araç çubuğu/ızgara akışı."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model.adres import Aralik
from tabcel.model.bicim_islem import BOYACI_ALAN_SINIRI, boyaci_stilleri
from tabcel.model.komutlar import bicim_komutu
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import StilYama
from tabcel.ui.window import Pencere


# ------------------------------------------------------------------ model (Qt'siz)
def _sayfa():
    return CalismaKitabi().sayfalar[0]


def _yaz(s, ar, **yama):
    bicim_komutu(s, [ar], StilYama(**yama)).yap()


def test_tek_hucre_kaynak_tek_hucre_hedef():
    s = _sayfa()
    _yaz(s, Aralik(1, 1, 1, 1), kalin=True)
    plan = boyaci_stilleri(s, Aralik(1, 1, 1, 1), Aralik(3, 3, 3, 3))
    assert plan == {(3, 3): s.stil_kimligi(1, 1)}


def test_tek_hucre_kaynak_buyuk_hedefe_yayilir():
    s = _sayfa()
    _yaz(s, Aralik(1, 1, 1, 1), italik=True)
    plan = boyaci_stilleri(s, Aralik(1, 1, 1, 1), Aralik(2, 2, 4, 3))
    assert len(plan) == 6 and set(plan.values()) == {s.stil_kimligi(1, 1)}


def test_cok_hucreli_kaynak_tek_hucreye_tum_deseni_boyar():
    s = _sayfa()
    _yaz(s, Aralik(1, 1, 1, 1), kalin=True)
    _yaz(s, Aralik(2, 2, 2, 2), italik=True)
    plan = boyaci_stilleri(s, Aralik(1, 1, 2, 2), Aralik(5, 5, 5, 5))
    assert set(plan) == {(5, 5), (5, 6), (6, 5), (6, 6)}
    assert plan[(5, 5)] == s.stil_kimligi(1, 1) and plan[(6, 6)] == s.stil_kimligi(2, 2)
    assert plan[(5, 6)] == 0 and plan[(6, 5)] == 0          # biçimsiz kaynak hücre hedefi sıfırlar


def test_desen_buyuk_hedefe_yinelenir_ve_kirpilir():
    s = _sayfa()
    _yaz(s, Aralik(1, 1, 1, 1), kalin=True)                 # 2 satırlık kaynak: kalın, düz
    plan = boyaci_stilleri(s, Aralik(1, 1, 2, 1), Aralik(10, 4, 14, 4))   # 5 satır = 2.5 yineleme
    kalin = s.stil_kimligi(1, 1)
    assert [plan[(r, 4)] for r in range(10, 15)] == [kalin, 0, kalin, 0, kalin]


def test_hedef_sayfa_sonunda_kirpilir():
    s = _sayfa()
    _yaz(s, Aralik(1, 1, 1, 1), kalin=True)
    plan = boyaci_stilleri(s, Aralik(1, 1, 3, 3), Aralik(1_048_575, 16_383, 1_048_575, 16_383))
    assert set(plan) == {(1_048_575, 16_383), (1_048_575, 16_384), (1_048_576, 16_383), (1_048_576, 16_384)}


def test_satir_stili_kaynak_hucrede_okunur():
    s = _sayfa()
    _yaz(s, Aralik(2, 1, 2, 16_384), kalin=True)            # tam satır → satır stili
    plan = boyaci_stilleri(s, Aralik(2, 5, 2, 5), Aralik(7, 7, 7, 7))
    assert plan[(7, 7)] == s.stil_kimligi(2, 5) != 0


def test_cok_buyuk_hedef_reddedilir():
    s = _sayfa()
    with pytest.raises(ValueError):
        boyaci_stilleri(s, Aralik(1, 1, 1, 1), Aralik(1, 1, 1_048_576, 2))
    assert BOYACI_ALAN_SINIRI == 200_000


# ------------------------------------------------------------------ arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 6):
        s.ata(r, 1, Hucre(float(r)))
        s.ata(r, 2, Hucre("m"))
    p = Pencere(k)
    p.show()
    return p


def _tikla(g, r, c, ikinci=None):
    vp = g.viewport()
    a = g.hucre_dikdortgeni(r, c).center()
    QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, a)
    if ikinci:
        b = g.hucre_dikdortgeni(*ikinci).center()
        QTest.mouseMove(vp, b)
        QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, b)
    else:
        QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, a)


def _stil(g, r, c):
    return g.sayfa.stil(r, c)


def test_tek_tik_bir_kez_boyar(pencere):
    g, c = pencere.izgara(), pencere.bicim_cubugu
    g.sec((1, 1))
    c.kalin.click()
    c.boyaci.click()
    assert g.boyaci_acik_mi() and c.boyaci.isChecked()
    _tikla(g, 3, 1)
    assert _stil(g, 3, 1).kalin
    assert not g.boyaci_acik_mi() and not c.boyaci.isChecked()   # tek tık: bir kez
    _tikla(g, 4, 1)
    assert not _stil(g, 4, 1).kalin                              # artık boyamaz


def test_surukleyerek_aralik_boyar_tek_geri_al(pencere):
    g, c = pencere.izgara(), pencere.bicim_cubugu
    g.sec((1, 1))
    c.kalin.click()
    c.boyaci.click()
    _tikla(g, 2, 1, ikinci=(5, 2))
    assert all(_stil(g, r, k).kalin for r in range(2, 6) for k in (1, 2))
    g.geri_al()
    assert not any(_stil(g, r, k).kalin for r in range(2, 6) for k in (1, 2))
    assert _stil(g, 1, 1).kalin                                  # kaynak durur


def test_cift_tik_kalici_esc_bitirir(pencere):
    g, c = pencere.izgara(), pencere.bicim_cubugu
    g.sec((1, 1))
    c.kalin.click()
    QTest.mouseDClick(c.boyaci, Qt.LeftButton)
    assert g.boyaci_acik_mi()
    _tikla(g, 2, 1)
    _tikla(g, 3, 1)
    assert _stil(g, 2, 1).kalin and _stil(g, 3, 1).kalin and g.boyaci_acik_mi()
    QTest.keyClick(g, Qt.Key_Escape)
    assert not g.boyaci_acik_mi() and not c.boyaci.isChecked()
    _tikla(g, 4, 1)
    assert not _stil(g, 4, 1).kalin


def test_dugmeye_yeniden_basmak_kapatir(pencere):
    g, c = pencere.izgara(), pencere.bicim_cubugu
    c.boyaci.click()
    assert g.boyaci_acik_mi()
    c.boyaci.click()
    assert not g.boyaci_acik_mi() and not c.boyaci.isChecked()


def test_coklu_secimde_alinamaz(pencere, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: QMessageBox.Ok)
    g, c = pencere.izgara(), pencere.bicim_cubugu
    g.sec((1, 1))
    QTest.mouseClick(g.viewport(), Qt.LeftButton, Qt.ControlModifier, g.hucre_dikdortgeni(3, 1).center())
    uyarilar = []
    g.uyari.connect(uyarilar.append)
    c.boyaci.click()
    assert not g.boyaci_acik_mi() and not c.boyaci.isChecked() and uyarilar


def test_kaynak_kendine_boyanirsa_komut_eklenmez(pencere):
    g, c = pencere.izgara(), pencere.bicim_cubugu
    g.sec((1, 1))
    c.kalin.click()
    onceki = len(g.yigin._geri) if hasattr(g.yigin, "_geri") else None
    c.boyaci.click()
    _tikla(g, 1, 1)
    if onceki is not None:
        assert len(g.yigin._geri) == onceki
    assert _stil(g, 1, 1).kalin


def test_sayfa_degisince_boyaci_biter(pencere):
    g, c = pencere.izgara(), pencere.bicim_cubugu
    pencere.kitap.sayfa_ekle()
    pencere.sekmeler.setCurrentIndex(0)
    c.boyaci.click()
    assert g.boyaci_acik_mi()
    pencere.sekmeler.setCurrentIndex(1)
    assert not g.boyaci_acik_mi()
