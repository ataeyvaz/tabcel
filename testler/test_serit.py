"""Faz 5 / 5j-1: şerit bileşenleri — daralma planı (Qt'siz) ve widget davranışı."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QToolButton

from tabcel.ui import icons
from tabcel.ui.serit import Serit, SeritGrubu, SeritSayfasi, daralma_plani


# ------------------------------------------------------------------ daralma_plani
def test_hepsi_sigarsa_durum_0():
    assert daralma_plani([[100, 60, 30], [80, None, 30]], [5, 5], 500) == [0, 0]


def test_dusuk_oncelik_once_kuculur():
    g = [[100, 60, 30], [100, 60, 30], [100, 60, 30]]
    assert daralma_plani(g, [9, 2, 5], 260) == [0, 1, 0]          # 100+60+100 = 260


def test_esit_oncelikte_sagdaki_once():
    g = [[100, 60, 30]] * 3
    assert daralma_plani(g, [5, 5, 5], 260) == [0, 0, 1]


def test_durum_1_olanlar_once_sonra_2():
    g = [[100, None, 30], [100, 60, 30]]
    # aşama 1: yalnız durum 1'i olan (sağdaki) 1'e iner = 160; sığmıyor -> aşama 2: en düşük öncelikli (soldaki) 2'ye
    assert daralma_plani(g, [1, 9], 150) == [2, 1]
    assert daralma_plani(g, [1, 9], 170) == [0, 1]


def test_asamali_once_hepsi_durum_1_sonra_2():
    g = [[100, 60, 30], [100, 60, 30]]
    assert daralma_plani(g, [5, 5], 135) == [1, 1]                # 60+60 = 120 sığar (sağdaki önce 1: 160; sonra soldaki: 120)
    assert daralma_plani(g, [5, 5], 100) == [1, 2]                # durum 1'ler yetmedi: sağdaki 2 -> 60+30 = 90


def test_gruplar_arasi_oncelik_durum_1_asamasinda():
    g = [[100, 60, 30]] * 3
    assert daralma_plani(g, [9, 1, 5], 260) == [0, 1, 0]


def test_hic_sigmazsa_hepsi_2():
    g = [[100, 60, 30], [100, 60, 30]]
    assert daralma_plani(g, [5, 5], 10) == [2, 2]


def test_bos_liste():
    assert daralma_plani([], [], 100) == []


# ------------------------------------------------------------------ widget
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def _grup(app, ad, n_kucuk=2, oncelik=5, ikon="bold"):
    g = SeritGrubu(ad, oncelik, ikon)
    e = [QAction(icons.icon("bold"), f"{ad} Eylem {i}") for i in range(n_kucuk)]   # ikonsuz düğme yazısız durumda da yazı gösterir
    g.kucukler(e)
    g._eylemler = e                                  # eylemleri canlı tut
    return g


def test_grup_olcusu_uc_durum(app):
    g = _grup(app, "Pano", 3)
    w = g.genislikler()
    assert w[0] > w[1] and w[2] is not None            # yazılı > yazısız küçük; durum 2 var
    assert g.durum == 0


def test_yazili_kucuk_yoksa_durum_1_yok(app):
    g = SeritGrubu("Sayı", 5, "bold")
    e = QAction("Tek")
    g.buyuk(e)
    assert g.genislikler()[1] is None
    g.durum_ayarla(1)
    assert g.durum == 2                                 # 1 istenince 2'ye atlar


def test_durum_1_kucuk_dugmeler_yazisiz(app):
    from PySide6.QtCore import Qt
    g = _grup(app, "G", 2)
    g.durum_ayarla(1)
    assert all(d.toolButtonStyle() == Qt.ToolButtonIconOnly for d in g._kucuk)
    g.durum_ayarla(0)
    assert all(d.toolButtonStyle() == Qt.ToolButtonTextBesideIcon for d in g._kucuk)


def test_durum_2_icerigi_acilirda_tasir_ve_geri_getirir(app):
    s = SeritSayfasi()
    g = s.grup_ekle(_grup(app, "G", 2))
    s.resize(600, 92)
    s.show()
    g.durum_ayarla(2)
    assert g._ozet.isVisible() and not g._icerik.isVisible()
    g._ozet.click()
    assert g._acilir is not None and g._icerik.parent() is g._acilir
    g._acilir.hide()                                    # Popup kapanır -> içerik geri döner
    assert g._acilir is None and g._icerik.parent() is g
    assert not g._icerik.isVisible()                    # hâlâ durum 2: gizli
    g.durum_ayarla(0)
    assert g._icerik.isVisible() and not g._ozet.isVisible()


def test_sayfa_dar_olunca_dusuk_oncelikli_kuculur(app):
    s = SeritSayfasi()
    a = s.grup_ekle(_grup(app, "A", 3, oncelik=9))
    b = s.grup_ekle(_grup(app, "B", 3, oncelik=1))
    s.resize(2000, 92)
    s.show()
    assert (a.durum, b.durum) == (0, 0)
    toplam0 = sum(g.genislikler()[0] for g in (a, b))
    s.resize(toplam0 - 20, 92)
    assert a.durum == 0 and b.durum >= 1
    s.resize(2000, 92)
    assert (a.durum, b.durum) == (0, 0)


def test_sayfada_gruplar_sirali_ayiricili(app):
    s = SeritSayfasi()
    a = s.grup_ekle(_grup(app, "A"))
    b = s.grup_ekle(_grup(app, "B"))
    c = s.grup_ekle(_grup(app, "C"), konum=1)
    assert [g.ad for g in s.gruplar] == ["A", "C", "B"]
    d = s._d
    sira = [d.itemAt(i).widget() for i in range(d.count()) if d.itemAt(i).widget() is not None]
    assert sira[0] is a and sira[2] is c and sira[4] is b                 # g, ayırıcı, g, ayırıcı, g
    assert len(s._ayirac) == 2


def test_dugmeler_odak_almaz_ve_eylemi_kullanir(app):
    from PySide6.QtCore import Qt
    g = SeritGrubu("G", 5)
    e = QAction("Yap")
    d = g.buyuk(e)
    assert d.focusPolicy() == Qt.NoFocus and d.defaultAction() is e


def test_serit_sekmeler_ve_guncelle(app):
    sr = Serit()
    cagri = []

    class S(SeritSayfasi):
        def guncelle(self):
            cagri.append(self)
    a, b = S(), S()
    sr.sekme_ekle("Giriş", a)
    sr.sekme_ekle("Veri", b)
    sr.show()
    assert sr.sekme_adlari() == ["Giriş", "Veri"]
    cagri.clear()
    sr.sec("Veri")
    assert cagri == [b]                                  # yalnız görünen sayfa eşitlenir
    sr.guncelle()
    assert cagri == [b, b]


def test_dosya_sekmesi_menu_acar_secimi_degistirmez(app):
    sr = Serit()
    sr.sekme_ekle("Giriş", SeritSayfasi())
    sr.sekme_ekle("Veri", SeritSayfasi())
    m = QMenu()
    m.addAction("Yeni")
    sr.dosya_sekmesi_ekle(m)
    sr.sec("Veri")
    acilan = []
    sr._dosya_menusunu_ac = lambda: acilan.append(1)
    sr.sec("Dosya")
    assert acilan == [1]
    assert sr.sekme_adlari()[sr.sekmeler.currentIndex()] == "Veri"
    assert sr.yigin.currentIndex() == sr.sekme_adlari().index("Veri")


def test_daraltma(app):
    sr = Serit()
    sr.sekme_ekle("Giriş", SeritSayfasi())
    sr.show()
    assert not sr.daraltilmis() and sr.yigin.isVisible()
    sr.daralt(True)
    assert sr.daraltilmis() and not sr.yigin.isVisible()
    sr._sekme_tiklandi(0)                                # daraltılmışken tık: açılır sayfa
    assert sr._yigin_acik is not None and sr.yigin.isVisible()
    sr.daralt(False)
    assert not sr.daraltilmis() and sr.yigin.isVisible() and sr.yigin.parent() is sr
    assert sr._yigin_acik is None


def test_eylemler_menuler_dahil_toplanir(app):
    sr = Serit()
    s = SeritSayfasi()
    g = SeritGrubu("G", 5)
    e1 = QAction("Doğrudan")
    m = QMenu()
    e2 = m.addAction("Menüde")
    alt = m.addMenu("Alt")
    e3 = alt.addAction("Alt menüde")
    g.buyuk(e1)
    g.buyuk(menu=m, metin="Menü")
    s.grup_ekle(g)
    sr.sekme_ekle("Giriş", s)
    dm = QMenu()
    e4 = dm.addAction("Yeni")
    sr.dosya_sekmesi_ekle(dm)
    bulunan = sr.eylemler()
    for e in (e1, e2, e3, e4):
        assert e in bulunan
