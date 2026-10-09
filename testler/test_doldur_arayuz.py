"""Faz 3 / 3h: doldurma arayüzde — Ctrl+D/R/Enter, tutamaç sürükleme, çift tık, geri al, birleşim koruması."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model.adres import Aralik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.model.stil import Stil
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    p = Pencere(CalismaKitabi())
    p.resize(1100, 700)
    p.show()
    p.activateWindow()
    QTest.qWaitForWindowActive(p)
    return p


def A(r1, c1, r2, c2):
    return Aralik(r1, c1, r2, c2)


def deger(g, r, c):
    h = g.sayfa.hucre(r, c)
    return None if h is None else (h.formul if h.formul is not None else h.deger)


def merkez(g, r, c):
    d = g.hucre_dikdortgeni(r, c)
    return d.center()


def tutamac(g):
    t = g._tutamac_dikdortgeni()
    assert t is not None
    return t.center()


def surukle(g, kaynak_son, hedef_hucre):
    """Tutamaçtan hedef hücreye sürükle."""
    vp = g.viewport()
    QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, tutamac(g))
    QTest.mouseMove(vp, merkez(g, *hedef_hucre))
    QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, merkez(g, *hedef_hucre))


# ------------------------------------------------------------------ Ctrl+D / Ctrl+R / Ctrl+Enter
def test_ctrl_d_ve_ctrl_r(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(5.0))
    g.sayfa.ata(1, 2, Hucre(None, "=A1*2"))
    g.sec((1, 1), (4, 2))
    QTest.keyClick(g, Qt.Key_D, Qt.ControlModifier)
    assert [deger(g, r, 1) for r in (2, 3, 4)] == [5.0, 5.0, 5.0]
    assert [deger(g, r, 2) for r in (2, 3, 4)] == ["=A2*2", "=A3*2", "=A4*2"]
    assert g.secim == A(1, 1, 4, 2)
    g.geri_al()
    assert deger(g, 2, 1) is None and deger(g, 4, 2) is None             # tek adım
    g.sec((1, 1), (1, 3))
    QTest.keyClick(g, Qt.Key_R, Qt.ControlModifier)
    assert deger(g, 1, 2) == 5.0 and deger(g, 1, 3) == 5.0


def test_ctrl_d_tek_hucre_ustten_ve_ilk_satir_bos(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre("x"))
    g.sec((2, 1))
    QTest.keyClick(g, Qt.Key_D, Qt.ControlModifier)
    assert deger(g, 2, 1) == "x"
    n = len(pencere.yigin._geri)
    g.sec((1, 1))
    QTest.keyClick(g, Qt.Key_D, Qt.ControlModifier)                      # üstte satır yok: iş yok
    assert len(pencere.yigin._geri) == n


def test_ctrl_d_bicim_gelir_ve_tam_sutun_sinirlanir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(1.0))
    g.sayfa.ata(3, 1, Hucre(9.0))
    g.sayfa.bicim_yaz({(1, 1): g.sayfa.havuz.kimlik(Stil(kalin=True))})
    g.sec((1, 1), (3, 1))
    QTest.keyClick(g, Qt.Key_D, Qt.ControlModifier)
    assert g.sayfa.stil(2, 1).kalin and g.sayfa.stil(3, 1).kalin and deger(g, 3, 1) == 1.0
    g.sec((1, 1), (1048576, 1))                                           # tüm sütun: 1M satır kopyalanmaz
    QTest.keyClick(g, Qt.Key_D, Qt.ControlModifier)
    assert g.sayfa.kullanilan_aralik()[2] == 3


def test_ctrl_d_coklu_secimde_uyarir(pencere, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: QMessageBox.Ok)
    g = pencere.izgara()
    uyarilar = []
    g.uyari.connect(uyarilar.append)
    g.sec((1, 1), (2, 1))
    g._ekler.append(g.secim)
    g._koru = True
    g.sec((4, 1), (5, 1))
    g._koru = False
    assert g.asagi_doldur() is False and uyarilar


def test_ctrl_enter_girdiyi_tum_secime_yazar(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(2.0))
    g.sec((2, 2), (4, 3))
    g.duzenle_baslat("=A1*3")
    QTest.keyClick(g._duzenleyici, Qt.Key_Return, Qt.ControlModifier)
    assert not g.duzenleniyor()
    assert deger(g, 2, 2) == "=A1*3" and deger(g, 3, 2) == "=A2*3" and deger(g, 4, 3) == "=B3*3"
    assert g.aktif == (2, 2) and g.secim == A(2, 2, 4, 3)                # seçim ve etkin hücre kalır
    g.geri_al()                                                          # tek adım
    assert all(deger(g, r, c) is None for r in (2, 3, 4) for c in (2, 3))


def test_ctrl_enter_tek_hucrede_olagan_ve_deger_sabit(pencere):
    g = pencere.izgara()
    g.sec((1, 1))
    g.duzenle_baslat("7")
    QTest.keyClick(g._duzenleyici, Qt.Key_Return, Qt.ControlModifier)
    assert deger(g, 1, 1) == 7.0
    g.sec((3, 1), (4, 1))
    g.duzenle_baslat("12.10.2026")                                       # akıllı giriş: tarih + biçim her yerde
    QTest.keyClick(g._duzenleyici, Qt.Key_Return, Qt.ControlModifier)
    assert deger(g, 3, 1) == deger(g, 4, 1) and g.sayfa.stil(4, 1).sayi_bicimi == "d.mm.yyyy"


# ------------------------------------------------------------------ tutamaç
def test_tutamac_secimin_sag_altinda_ve_coklu_secimde_yok(pencere):
    g = pencere.izgara()
    g.sec((2, 2), (3, 3))
    t = g._tutamac_dikdortgeni()
    son = g.hucre_dikdortgeni(3, 3)
    assert t is not None and abs(t.right() - (son.right() - 1)) <= 3 and abs(t.bottom() - (son.bottom() - 1)) <= 3
    g._ekler.append(Aralik(1, 1, 1, 1))
    assert g._tutamac_dikdortgeni() is None
    g._ekler.clear()
    g.sec((1, 1), (1048576, 1))
    assert g._tutamac_dikdortgeni() is None                              # tam sütun
    g.duzenle_baslat("a")
    assert g._tutamac_dikdortgeni() is None                              # düzenlerken


def test_tutamac_gorunur_ve_imlec(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    t = g._tutamac_dikdortgeni()
    img = g.viewport().grab().toImage()
    assert img.pixelColor(t.center()).name().upper() == "#217346"        # vurgu renkli kare
    g._imlec_guncelle(t.center())                                        # (ekransız ortamda fare izleme olayı gelmez)
    assert g.viewport().cursor().shape() == Qt.CrossCursor
    g._imlec_guncelle(merkez(g, 6, 6))
    assert g.viewport().cursor().shape() == Qt.ArrowCursor


def test_surukle_asagi_seri(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(1.0))
    g.sayfa.ata(2, 1, Hucre(2.0))
    g.sayfa.ata(1, 2, Hucre("Ocak"))
    g.sayfa.ata(2, 2, Hucre("Şubat"))
    g.sec((1, 1), (2, 2))
    surukle(g, (2, 2), (5, 2))
    assert [deger(g, r, 1) for r in (3, 4, 5)] == [3.0, 4.0, 5.0]
    assert [deger(g, r, 2) for r in (3, 4, 5)] == ["Mart", "Nisan", "Mayıs"]
    assert g.secim == A(1, 1, 5, 2) and g.aktif == (1, 1)
    g.geri_al()                                                          # tek adım
    assert all(deger(g, r, c) is None for r in (3, 4, 5) for c in (1, 2))


def test_surukle_yukari_sola_saga(pencere):
    g = pencere.izgara()
    g.sayfa.ata(8, 3, Hucre("Ürün 5"))
    g.sec((8, 3))
    surukle(g, (8, 3), (6, 3))
    assert [deger(g, r, 3) for r in (6, 7)] == ["Ürün 3", "Ürün 4"]
    g.sec((1, 5), (1, 6))
    g.sayfa.ata(1, 5, Hucre(10.0))
    g.sayfa.ata(1, 6, Hucre(20.0))
    surukle(g, (1, 6), (1, 8))
    assert [deger(g, 1, c) for c in (7, 8)] == [30.0, 40.0]
    g.sayfa.ata(3, 7, Hucre(30.0))
    g.sayfa.ata(3, 8, Hucre(40.0))
    g.sec((3, 7), (3, 8))
    surukle(g, (3, 8), (3, 5))                                           # sola: seri geriye devam eder
    assert [deger(g, 3, c) for c in (5, 6)] == [10.0, 20.0]
    assert g.secim == A(3, 5, 3, 8) and g.aktif == (3, 8)


def test_surukle_asagi_formul_kayar_ve_bicim(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(4.0))
    g.sayfa.ata(1, 2, Hucre(None, "=A1+1"))
    g.sayfa.bicim_yaz({(1, 2): g.sayfa.havuz.kimlik(Stil(italik=True))})
    g.sec((1, 2))
    surukle(g, (1, 2), (3, 2))
    assert deger(g, 2, 2) == "=A2+1" and deger(g, 3, 2) == "=A3+1"
    assert g.sayfa.stil(3, 2).italik


def test_surukle_kaynak_icine_degisiklik_yok(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(1.0))
    g.sayfa.ata(2, 1, Hucre(2.0))
    g.sec((1, 1), (2, 1))
    n = len(pencere.yigin._geri)
    surukle(g, (2, 1), (2, 1))
    assert len(pencere.yigin._geri) == n and g._doldur is None


def test_onizleme_cerceve_cizilir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(1.0))
    g.sec((1, 1))
    vp = g.viewport()
    QTest.mousePress(vp, Qt.LeftButton, Qt.NoModifier, tutamac(g))
    QTest.mouseMove(vp, merkez(g, 4, 1))
    assert g._doldur["hedef"] == A(2, 1, 4, 1)
    from PySide6.QtGui import QImage, QPainter
    img = QImage(vp.size(), QImage.Format_RGB32)               # paintEvent hataları yutulur: _boya'yı doğrudan çağır
    pn = QPainter(img)
    g._boya(pn, vp.rect())
    pn.end()
    QTest.mouseMove(vp, merkez(g, 1, 3))
    assert g._doldur["hedef"] == A(1, 2, 1, 3)                            # yatay eksen baskın
    QTest.mouseRelease(vp, Qt.LeftButton, Qt.NoModifier, merkez(g, 1, 3))
    assert deger(g, 1, 3) == 1.0


def test_cift_tik_komsu_veri_sonuna_doldurur(pencere):
    g = pencere.izgara()
    for r in range(1, 7):
        g.sayfa.ata(r, 1, Hucre(f"k{r}"))
    g.sayfa.ata(1, 2, Hucre(1.0))
    g.sayfa.ata(2, 2, Hucre(2.0))
    g.sec((1, 2), (2, 2))
    QTest.mouseDClick(g.viewport(), Qt.LeftButton, Qt.NoModifier, tutamac(g))
    assert [deger(g, r, 2) for r in range(3, 7)] == [3.0, 4.0, 5.0, 6.0]
    assert deger(g, 7, 2) is None and g.secim == A(1, 2, 6, 2)
    g.geri_al()
    assert deger(g, 3, 2) is None


def test_cift_tik_komsu_yoksa_bir_sey_yapmaz(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 2, Hucre(1.0))
    g.sec((1, 2))
    n = len(pencere.yigin._geri)
    QTest.mouseDClick(g.viewport(), Qt.LeftButton, Qt.NoModifier, tutamac(g))
    assert len(pencere.yigin._geri) == n


def test_birlesik_hucrelere_doldurma_reddedilir(pencere, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: QMessageBox.Ok)
    g = pencere.izgara()
    g.sayfa.birlesimleri_yaz([A(4, 1, 5, 1)], [])
    g.sayfa.ata(1, 1, Hucre("a"))
    g.sec((1, 1), (3, 1))
    QTest.keyClick(g, Qt.Key_D, Qt.ControlModifier)
    assert deger(g, 2, 1) == "a"                                          # birleşime değmeyen doldurma çalışır
    g.sec((1, 1))
    assert g.doldur(A(1, 1, 1, 1), A(2, 1, 5, 1)) is False                # birleşime değen reddedilir
    assert deger(g, 4, 1) is None


def test_doldurma_formul_motorunu_gunceller(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(1.0))
    g.sayfa.ata(2, 1, Hucre(2.0))
    g.sayfa.ata(1, 2, Hucre(None, "=SUM(A1:A10)"))
    g.sec((1, 1), (2, 1))
    surukle(g, (2, 1), (4, 1))
    assert g.sayfa.sonuc(1, 2) == 10.0                                    # 1+2+3+4
