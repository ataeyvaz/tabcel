"""İşaretleme modu (K7) arayüzde: formül yazarken tıklama/sürükleme/ok başvuru ekler, onaylamaz;
F4; odak kaybı onaylamaz; formül çubuğu aynı modu paylaşır (ekransız)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QFocusEvent
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
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: None)
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 6):
        s.ata(r, 1, Hucre(float(r)))
        s.ata(r, 2, Hucre(float(r * 10)))
    p = Pencere(k)
    p.show()
    p.activateWindow()
    return p


def yaz(g, metin):
    QTest.keyClicks(g, metin[0])
    QTest.keyClicks(g.focusWidget(), metin[1:])


def merkez(g, r, c):
    return g.hucre_dikdortgeni(r, c).center()


def tikla(g, r, c, mod=Qt.NoModifier):
    QTest.mouseClick(g.viewport(), Qt.LeftButton, mod, merkez(g, r, c))


def test_tiklama_basvuru_ekler_onaylamaz(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=TOPLA(")
    tikla(g, 2, 1)
    assert g.duzenleniyor()
    assert g._duzenleyici.text() == "=TOPLA(A2"
    tikla(g, 4, 2)                                   # ikinci tıklama aynı işareti değiştirir
    assert g._duzenleyici.text() == "=TOPLA(B4"
    assert g.sayfa.hucre(1, 4) is None               # henüz yazılmadı


def test_surukleme_aralik_ekler(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=TOPLA(")
    QTest.mousePress(g.viewport(), Qt.LeftButton, Qt.NoModifier, merkez(g, 1, 1))
    QTest.mouseMove(g.viewport(), merkez(g, 3, 2))
    QTest.mouseRelease(g.viewport(), Qt.LeftButton, Qt.NoModifier, merkez(g, 3, 2))
    assert g._duzenleyici.text() == "=TOPLA(A1:B3"
    QTest.keyClicks(g._duzenleyici, ")")
    QTest.keyClick(g._duzenleyici, Qt.Key_Return)
    assert g.sayfa.hucre(1, 4).formul == "=SUM(A1:B3)"
    assert g.sayfa.deger(1, 4) == 66.0


def test_yazinca_isaret_donar_sonraki_tiklama_yeni_parca(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=")
    tikla(g, 1, 1)
    QTest.keyClicks(g._duzenleyici, "+")
    tikla(g, 2, 1)
    assert g._duzenleyici.text() == "=A1+A2"


def test_formul_olmayan_metinde_tiklama_onaylar(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "abc")
    tikla(g, 3, 3)
    assert not g.duzenleniyor() and g.sayfa.deger(1, 4) == "abc"


def test_basvuru_konumu_degilse_tiklama_onaylar(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=A1")
    tikla(g, 3, 3)
    assert not g.duzenleniyor() and g.sayfa.hucre(1, 4).formul == "=A1"


def test_ok_tuslari_isaret_hucresini_gezdirir_gir_modunda(pencere):
    g = pencere.izgara()
    g.sec((3, 4))
    yaz(g, "=")
    e = g._duzenleyici
    QTest.keyClick(e, Qt.Key_Up)
    assert e.text() == "=D2"
    QTest.keyClick(e, Qt.Key_Left)
    assert e.text() == "=C2"
    QTest.keyClick(e, Qt.Key_Down, Qt.ShiftModifier)
    assert e.text() == "=C2:C3"
    assert g.duzenleniyor()


def test_duzenle_modunda_oklar_imlec_gezdirir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(3, 4, Hucre(None, "=A1+"))
    g.sec((3, 4))
    QTest.keyClick(g, Qt.Key_F2)
    e = g._duzenleyici
    assert not e.yazma_modu
    QTest.keyClick(e, Qt.Key_Left)
    assert e.text() == "=A1+" and e.cursorPosition() == 3
    assert g.duzenleniyor()


def test_f2_gir_duzenle_gecisi(pencere):
    g = pencere.izgara()
    g.sec((3, 4))
    yaz(g, "=A1+")
    e = g._duzenleyici
    assert e.yazma_modu
    QTest.keyClick(e, Qt.Key_F2)
    assert not e.yazma_modu
    QTest.keyClick(e, Qt.Key_F2)
    assert e.yazma_modu


def test_f4_dongusu_duzenleyicide(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=A1")
    e = g._duzenleyici
    QTest.keyClick(e, Qt.Key_F4)
    assert e.text() == "=$A$1"
    QTest.keyClick(e, Qt.Key_F4)
    assert e.text() == "=A$1"


def test_pencere_disi_odak_kaybi_onaylamaz(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=A1+1")
    e = g._duzenleyici
    QApplication.sendEvent(e, QFocusEvent(QEvent.FocusOut, Qt.ActiveWindowFocusReason))
    assert g.duzenleniyor() and g.sayfa.hucre(1, 4) is None
    QApplication.sendEvent(e, QFocusEvent(QEvent.FocusOut, Qt.TabFocusReason))   # uygulama içi: onaylar
    assert not g.duzenleniyor()


def test_renkli_vurgu_basvuru_listesi(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=A1+B2")
    g.grab()                                         # çizim hata vermeden çalışır
    from tabcel.formul import isaretleme
    assert len(isaretleme.renkli_basvurular(g._duzenleyici.text())) == 2


def test_formul_cubugu_ayni_modu_paylasir(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    pencere.formul.setFocus()
    pencere.formul.setText("=TOPLA(")
    pencere.formul.setCursorPosition(7)
    pencere.formul.textEdited.emit("=TOPLA(")
    tikla(g, 2, 1)
    assert pencere.formul.text() == "=TOPLA(A2"
    assert g.sayfa.hucre(1, 4) is None
    tikla(g, 3, 2)
    assert pencere.formul.text() == "=TOPLA(B3"
    pencere.formul.setCursorPosition(len(pencere.formul.text()))
    QTest.keyClicks(pencere.formul, ")")
    QTest.keyClick(pencere.formul, Qt.Key_Return)
    assert g.sayfa.hucre(1, 4).formul == "=SUM(B3)"


def test_formul_cubugu_f4(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    pencere.formul.setFocus()
    pencere.formul.setText("=A1")
    pencere.formul.setCursorPosition(3)
    QTest.keyClick(pencere.formul, Qt.Key_F4)
    assert pencere.formul.text() == "=$A$1"


# ---------------------------------------------------------------- Otomatik Toplam (Alt+=)
def alt_esittir(g):
    QTest.keyClick(g, Qt.Key_Equal, Qt.AltModifier)


def test_otomatik_toplam_ustteki_blogu_toplar(pencere):
    g = pencere.izgara()
    g.sec((6, 1))
    alt_esittir(g)
    assert g.duzenleniyor() and g._duzenleyici.text() == "=TOPLA(A1:A5)"
    QTest.keyClick(g._duzenleyici, Qt.Key_Return)
    assert g.sayfa.hucre(6, 1).formul == "=SUM(A1:A5)" and g.sayfa.deger(6, 1) == 15.0


def test_otomatik_toplam_bitisik_blokta_durur(pencere):
    g = pencere.izgara()
    g.sayfa.ata(3, 1, Hucre("baslik"))               # A3 metin: blok A4:A5
    g.sec((6, 1))
    alt_esittir(g)
    assert g._duzenleyici.text() == "=TOPLA(A4:A5)"


def test_otomatik_toplam_ustte_yoksa_soldakini_toplar(pencere):
    g = pencere.izgara()
    g.sec((2, 3))                                    # C2: solunda A2, B2 sayı
    alt_esittir(g)
    assert g._duzenleyici.text() == "=TOPLA(A2:B2)"


def test_otomatik_toplam_veri_yoksa_bos_imlec_icinde(pencere):
    g = pencere.izgara()
    g.sec((9, 9))
    alt_esittir(g)
    e = g._duzenleyici
    assert e.text() == "=TOPLA()" and e.cursorPosition() == 7


# ---------------------------------------------------------------- otomatik tamamlama
def test_oneri_listesi_acilir_tab_kabul_eder(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=topl")
    e = g._duzenleyici
    assert e.oneri_acik() and e._liste.item(0).text() == "TOPLA"
    QTest.keyClick(e, Qt.Key_Tab)
    assert e.text() == "=TOPLA(" and not e.oneri_acik() and g.duzenleniyor()
    QTest.keyClicks(e, "A1:A3)")
    QTest.keyClick(e, Qt.Key_Return)
    assert g.sayfa.hucre(1, 4).formul == "=SUM(A1:A3)"


def test_oneri_asagi_ok_secimi_degistirir_esc_listeyi_kapatir(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=topl")
    e = g._duzenleyici
    QTest.keyClick(e, Qt.Key_Down)
    QTest.keyClick(e, Qt.Key_Tab)
    assert e.text() == "=TOPLA.ÇARPIM("
    e.setText("=topl")
    e.setCursorPosition(5)
    assert e.oneri_acik()
    QTest.keyClick(e, Qt.Key_Escape)
    assert not e.oneri_acik() and g.duzenleniyor()       # Esc önce listeyi kapatır, düzenlemeyi değil


def test_oneri_tam_ad_yazilinca_kapanir_basvuruda_acilmaz(pencere):
    g = pencere.izgara()
    g.sec((1, 4))
    yaz(g, "=A1")
    assert not g._duzenleyici.oneri_acik()
