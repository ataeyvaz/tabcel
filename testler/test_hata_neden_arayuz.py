"""T8 arayüz: hata açıklaması ipucu (fare bekleyince) ve durum çubuğu."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtGui import QHelpEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolTip

from tabcel.model.adres import Aralik
from tabcel.model.notlar import Not
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def p(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("abc"))
    s.ata(1, 2, Hucre(None, "=A1+1"))           # B1: #DEĞER!
    s.ata(2, 2, Hucre(None, "=B1*2"))           # B2: B1'den gelir
    s.ata(3, 2, Hucre(5.0))
    pencere = Pencere(k)
    pencere.resize(1000, 700)
    pencere.show()
    QApplication.processEvents()
    yield pencere
    pencere.degisti_mi = lambda: False
    pencere.close()


def ipucu(g, r, c):
    QToolTip.hideText()                             # Qt ipucunu gecikmeyle gizler: kapanana dek bekle (en çok 2 sn)
    for _ in range(100):
        if not QToolTip.isVisible():
            break
        QTest.qWait(20)
    ar = g.hucre_dikdortgeni(r, c)
    nokta = ar.center()
    olay = QHelpEvent(QEvent.ToolTip, nokta, g.viewport().mapToGlobal(nokta))
    QApplication.sendEvent(g.viewport(), olay)
    QApplication.processEvents()
    return QToolTip.text() if QToolTip.isVisible() else ""


def test_durum_cubugu_etkin_hucre_hatasi(p):
    g = p.izgara()
    g.sec((1, 2))
    QApplication.processEvents()
    assert p.hata_etiketi.isVisible()
    assert p.hata_etiketi.toolTip() == "#DEĞER!: A1 hücresinde sayı yerine metin var (\"abc\")."
    g.sec((2, 2))
    assert p.hata_etiketi.toolTip().startswith("#DEĞER!: B1 hücresinden geliyor (B2 → B1).")


def test_durum_cubugu_hatasiz_ve_coklu_secimde_gizli(p):
    g = p.izgara()
    g.sec((3, 2))
    assert not p.hata_etiketi.isVisible()
    g.sec((1, 2), (2, 2))                          # çok hücreli seçim: etkin hücre hatalı olsa da gösterilmez
    assert not p.hata_etiketi.isVisible()


def test_duzeltilince_aciklama_kalkar(p):
    g = p.izgara()
    g.sec((1, 2))
    assert p.hata_etiketi.isVisible()
    g.hucre_gir(1, 1, "3")                          # A1 sayı oldu: B1 artık 4
    QApplication.processEvents()
    assert g.sayfa.deger(1, 2) == 4.0
    assert not p.hata_etiketi.isVisible()           # önbellek olayla düştü
    assert p.hata_aciklamasi(g.sayfa, 1, 2) == ""


def test_ipucu_hatali_hucrede(p):
    g = p.izgara()
    assert ipucu(g, 1, 2) == "#DEĞER!: A1 hücresinde sayı yerine metin var (\"abc\")."
    assert ipucu(g, 3, 2) == ""                     # hatasız hücre


def test_notlu_hucrede_not_oncelikli(p):
    g = p.izgara()
    g.sayfa.notlar[(1, 2)] = Not("not metni", "")
    assert ipucu(g, 1, 2) == ""


def test_birlesik_hucrede_sol_ust_aciklanir(p):
    from tabcel.model.komutlar import birlesim_komutu
    g = p.izgara()
    s = g.sayfa
    s.ata(5, 1, Hucre(None, "=1/0"))
    g.yigin.calistir(birlesim_komutu(s, [Aralik(5, 1, 5, 2)], "birlestir"))
    QApplication.processEvents()
    assert ipucu(g, 5, 2) == "#BÖL/0!: Bölen sıfır ya da boş."
    g.sec((5, 1))
    assert p.hata_etiketi.isVisible()
