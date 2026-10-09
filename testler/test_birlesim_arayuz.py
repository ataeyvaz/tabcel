"""Faz 3 / 3f: birleşik hücreler arayüzde — seçim, gezinme, çizim, düğme, uyarı, geri al."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model.adres import Aralik
from tabcel.model.komutlar import birlesim_komutu
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import theme
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(2, 2, Hucre("Başlık"))
    s.ata(5, 1, Hucre("alt"))
    p = Pencere(k)
    p.resize(1100, 700)
    p.show()
    return p


def A(r1, c1, r2, c2):
    return Aralik(r1, c1, r2, c2)


def birlestir(p, ar, tur="birlestir"):
    g = p.izgara()
    g.sec((ar.ilk_satir, ar.ilk_sutun), (ar.son_satir, ar.son_sutun))
    assert g.birlestir(tur, onayli=True)


def piksel(g, x, y):
    return QColor(g.viewport().grab().toImage().pixel(x, y)).name()


def test_tiklama_birlesimi_secer_etkin_sol_ust(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(2, 2, 3, 4))
    g.sec((5, 5))
    g.sec((3, 4))                                         # kapsanan hücreye tıklama
    assert g.aktif == (2, 2) and g.secim == A(2, 2, 3, 4)
    assert pencere.ad_kutusu.text() == "B2"


def test_secim_birlesimi_kesiyorsa_genisler(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(3, 3, 4, 4))
    g.sec((1, 1), (3, 3))                                 # birleşimin köşesine kadar
    assert g.secim == A(1, 1, 4, 4)
    g.sec((6, 6), (4, 4))                                 # ters yönde
    assert g.secim == A(3, 3, 6, 6)
    g.sec((1, 1), (2, 2))                                 # değmeyen seçim aynen kalır
    assert g.secim == A(1, 1, 2, 2)


def test_ok_tuslari_birlesimi_tek_hucre_gibi_gezer(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(3, 3, 4, 4))
    g.sec((3, 3))
    QTest.keyClick(g, Qt.Key_Down)
    assert g.aktif == (5, 3)                              # birleşimin altına
    QTest.keyClick(g, Qt.Key_Up)
    assert g.aktif == (3, 3) and g.secim == A(3, 3, 4, 4)  # tekrar birleşime
    QTest.keyClick(g, Qt.Key_Right)
    assert g.aktif == (3, 5)
    QTest.keyClick(g, Qt.Key_Left)
    assert g.aktif == (3, 3)
    g.sec((1, 3))
    QTest.keyClick(g, Qt.Key_Down)
    QTest.keyClick(g, Qt.Key_Down)
    assert g.aktif == (3, 3)                              # üstten girince sol üst
    g.sec((4, 2))
    QTest.keyClick(g, Qt.Key_Right)                       # alt satırdan yan girince de birleşim
    assert g.aktif == (3, 3)


def test_shift_ok_birlesimi_atlamaz_kapsar(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(3, 3, 4, 4))
    g.sec((3, 2))
    QTest.keyClick(g, Qt.Key_Right, Qt.ShiftModifier)
    assert g.secim == A(3, 2, 4, 3 + 1)                   # birleşimin tamamı dahil
    QTest.keyClick(g, Qt.Key_Right, Qt.ShiftModifier)
    assert g.secim == A(3, 2, 4, 5)


def test_enter_birlesimden_cikar(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(3, 3, 4, 3))
    g.sec((3, 3))
    QTest.keyClick(g, Qt.Key_Return)
    assert g.aktif == (5, 3)


def test_cizim_ic_cizgiler_gorunmez(pencere):
    g = pencere.izgara()
    g.sec((8, 8))
    birlestir(pencere, A(2, 2, 3, 3))
    QTest.qWait(10)
    r2 = g.hucre_dikdortgeni(2, 2)
    assert r2.width() == g._gen(2) + g._gen(3) and r2.height() == g._yuk(2) + g._yuk(3)
    g.sec((8, 8))
    zemin = QColor(theme.SURFACE).name()
    ic_x = r2.x() + g._gen(2) - 1                          # eski sütun sınırı çizgisi
    ic_y = r2.y() + 3
    assert piksel(g, ic_x, ic_y) == zemin                  # birleşimin içinden çizgi geçmiyor
    ic_y2 = r2.y() + g._yuk(2) - 1
    assert piksel(g, r2.x() + 3, ic_y2) == zemin
    # dış sağ ve alt çizgiler duruyor
    assert piksel(g, r2.x() + r2.width() - 1, r2.y() + 3) == QColor(theme.GRID_LINE).name()
    assert piksel(g, r2.x() + 3, r2.y() + r2.height() - 1) == QColor(theme.GRID_LINE).name()


def test_metin_birlesimde_ortalanir(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(2, 2, 3, 6), "ortala")
    g.sec((9, 9))
    dik = g.hucre_dikdortgeni(2, 2)
    img = g.viewport().grab().toImage()
    koyu_x = [x for x in range(dik.x() + 2, dik.x() + dik.width() - 2)
              for y in range(dik.y() + 2, dik.y() + dik.height() - 2)
              if QColor(img.pixel(x, y)).lightness() < 120]
    assert koyu_x, "metin çizilmedi"
    orta = (min(koyu_x) + max(koyu_x)) / 2
    assert abs(orta - (dik.x() + dik.width() / 2)) < 6


def test_dolgu_birlesimin_tamamini_boyar(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(2, 2, 4, 3))
    g.sec((2, 2))
    pencere.bicim_cubugu.dolgu.sec(QColor("#ffff00"))
    g.sec((9, 9))
    dik = g.hucre_dikdortgeni(2, 2)
    for dx, dy in ((3, 3), (dik.width() - 4, dik.height() - 4), (g._gen(2) + 2, g._yuk(2) + 2)):
        assert piksel(g, dik.x() + dx, dik.y() + dy) == "#ffff00"


def test_cizim_birlesim_kismen_gorunurken(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(2, 2, 3, 3))
    g.horizontalScrollBar().setValue(2)                    # B sütunu ekran dışında
    g.verticalScrollBar().setValue(1)
    QTest.qWait(10)
    g.viewport().grab()                                    # çökmeden çizilir
    assert g.hucre_dikdortgeni(2, 2) is None or g.hucre_dikdortgeni(2, 2).x() < g._baslik_g()


def test_duzenleme_birlesim_alaninda(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(6, 2, 7, 4))
    g.sec((6, 2))
    QTest.keyClick(g, Qt.Key_F2)
    assert g.duzenleniyor()
    dik = g.hucre_dikdortgeni(6, 2)
    assert g._duzenleyici.geometry().width() >= dik.width() - 4
    QTest.keyClick(g._duzenleyici, Qt.Key_Escape)


def test_cubuk_dugmesi_ve_menu(pencere):
    g = pencere.izgara()
    c = pencere.bicim_cubugu
    g.sec((7, 1), (8, 3))
    c.birlestir.click()                                     # Birleştir ve Ortala
    assert g.sayfa.birlesim(8, 3) == A(7, 1, 8, 3) and g.sayfa.stil(7, 1).yatay == "orta"
    assert c.birlestir.isChecked()
    c.birlestir.click()                                     # aynı seçimde tekrar: çözer
    assert g.sayfa.birlesimler == [] and not c.birlestir.isChecked()
    assert set(c.birlestir_eylemleri) == {"ortala", "birlestir", "satirlar", "coz"}
    g.sec((7, 1), (8, 3))
    c.birlestir_eylemleri["satirlar"].trigger()
    assert g.sayfa.birlesimler == [A(7, 1, 7, 3), A(8, 1, 8, 3)]
    g.sec((7, 1), (8, 3))
    c.birlestir_eylemleri["coz"].trigger()
    assert g.sayfa.birlesimler == []
    g.geri_al()
    assert len(g.sayfa.birlesimler) == 2


def test_veri_kaybi_uyarisi(pencere, monkeypatch):
    g = pencere.izgara()
    sorular = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a: sorular.append(a[2]) or QMessageBox.Cancel)
    g.sec((2, 2), (3, 2))
    g.sayfa.ata(3, 2, Hucre("x"))
    assert g.birlestir("birlestir") is False                # iptal: değişmez
    assert g.sayfa.birlesimler == [] and g.sayfa.hucre(3, 2) == Hucre("x")
    assert len(sorular) == 1 and "sol üstteki" in sorular[0]
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: QMessageBox.Ok)
    assert g.birlestir("birlestir") is True
    assert g.sayfa.hucre(3, 2) is None and g.sayfa.hucre(2, 2) == Hucre("Başlık")
    g.geri_al()
    assert g.sayfa.hucre(3, 2) == Hucre("x")


def test_uyari_gerektirmeyen_birlestirme_sormaz(pencere, monkeypatch):
    g = pencere.izgara()
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: pytest.fail("sorulmamalıydı"))
    g.sec((8, 1), (9, 2))                                   # boş
    assert g.birlestir("birlestir")


def test_coklu_secim_birlestirmez(pencere, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: QMessageBox.Ok)   # pencere uyarısı modal
    g = pencere.izgara()
    uyarilar = []
    g.uyari.connect(uyarilar.append)
    g.sec((1, 1), (1, 2))
    g._ekler.append(g.secim)
    g._koru = True                                          # Ctrl ile ekleme durumu
    g.sec((4, 4), (4, 5))
    g._koru = False
    assert g.birlestir("birlestir", onayli=True) is False
    assert uyarilar and g.sayfa.birlesimler == []


def test_satir_ekle_sil_birlesim_gorunur_kalir(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(3, 2, 4, 3))
    g.sec((1, 1))
    g.satirlari_ekle()
    assert g.sayfa.birlesimler == [A(4, 2, 5, 3)]
    g.viewport().grab()
    g.geri_al()
    assert g.sayfa.birlesimler == [A(3, 2, 4, 3)]


def test_formul_birlesik_hucreyi_okur(pencere):
    g = pencere.izgara()
    s = g.sayfa
    s.ata(2, 2, Hucre(7.0))
    s.ata(10, 1, Hucre(None, "=B2*2"))
    birlestir(pencere, A(2, 2, 3, 3))
    assert s.sonuc(10, 1) == 14.0                           # sol üst değeri okunur
    s.ata(10, 2, Hucre(None, "=C3+1"))
    assert s.sonuc(10, 2) == 1.0                            # kapsanan hücre boş


def test_gizli_sutunlu_birlesim_boyutu(pencere):
    g = pencere.izgara()
    birlestir(pencere, A(2, 2, 2, 4))
    g.sayfa.gizli_sutun.add(3)
    dik = g.hucre_dikdortgeni(2, 2)
    assert dik.width() == g._gen(2) + g._gen(4)
