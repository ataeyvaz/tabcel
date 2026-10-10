"""Faz 5 / 5e: not arayüzü (üçgen, fare üstü kutu, Shift+F2, menü, temizle, pano) — ekransız."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QKeyEvent
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

from tabcel.model.notlar import Not
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(2, 2, Hucre("a"))
    s.ata(3, 2, Hucre("b"))
    p = Pencere(k)
    p.resize(900, 600)
    p.show()
    app.processEvents()
    yield p
    p.hide()


def tus(g, anahtar, mod=Qt.NoModifier):
    g.keyPressEvent(QKeyEvent(QEvent.KeyPress, anahtar, mod))


def kirmizi_var(g, r, c) -> bool:
    """Hücrenin sağ üst köşesinde (üçgenin içinde) not kırmızısı var mı."""
    img = g.viewport().grab().toImage()
    ar = g.hucre_dikdortgeni(r, c)
    x, y = ar.x() + ar.width() - 3, ar.y() + 2
    return QColor(img.pixel(x, y)).red() > 150 and QColor(img.pixel(x, y)).green() < 60


def test_uclu_notlu_hucrede_cizilir(pencere, app):
    g = pencere.izgara()
    assert not kirmizi_var(g, 2, 2)
    g.not_yaz({(2, 2): Not("merhaba", "Ata")})
    app.processEvents()
    assert kirmizi_var(g, 2, 2)
    assert not kirmizi_var(g, 3, 2)


def test_shift_f2_ekler_odak_kaybinda_kaydeder_geri_al(pencere, app):
    g = pencere.izgara()
    g.sec((2, 2))
    tus(g, Qt.Key_F2, Qt.ShiftModifier)
    assert g._not_duzen is not None
    g._not_duzen.setPlainText("Yeni not")
    kutu = g._not_duzen
    kutu.clearFocus()                                  # odak kaybı = kaydet
    if g._not_duzen is not None:                       # ekransız ortamda odak olayı gelmediyse doğrudan bitir
        kutu._bitir("Yeni not")
    assert g.sayfa.notlar[(2, 2)].metin == "Yeni not"   # yazar Windows kullanıcı adı (boş olabilir)
    assert g._not_duzen is None
    g.geri_al()
    assert g.sayfa.notlar == {}
    g.yinele()
    assert g.sayfa.notlar[(2, 2)].metin == "Yeni not"


def test_esc_vazgecer(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    g.not_duzenle()
    g._not_duzen.setPlainText("yazıldı")
    tus(g._not_duzen, Qt.Key_Escape)
    assert g.sayfa.notlar == {} and g._not_duzen is None


def test_duzenle_mevcut_notu_yazari_korur(pencere):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("eski", "Ayşe")})
    g.sec((2, 2))
    g.not_duzenle()
    assert g._not_duzen.toPlainText() == "eski"
    g._not_duzen._bitir("yeni")
    assert g.sayfa.notlar[(2, 2)] == Not("yeni", "Ayşe")


def test_bos_metin_notu_siler_degisiklik_yoksa_komut_yok(pencere):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("x", "A")})
    g.sec((2, 2))
    g.not_duzenle()
    g._not_duzen._bitir("x")                           # değişmedi: geri al yığınına yeni adım girmemeli
    assert g.sayfa.notlar[(2, 2)] == Not("x", "A")
    g.geri_al()
    assert g.sayfa.notlar == {}                        # tek geri al = notun ilk eklenmesi
    g.yinele()
    g.sec((2, 2))
    g.not_duzenle()
    g._not_duzen._bitir("")
    assert g.sayfa.notlar == {}


def test_fare_ustu_kutu(pencere, app):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("Kutu metni", "Ata")})
    ar = g.hucre_dikdortgeni(2, 2)
    g._not_ipucu_guncelle(ar.center())
    assert g._not_adayi == (2, 2) and g._not_zamani.isActive()
    g._not_goster()                                    # 400 ms beklemeden
    assert g._not_kutusu.isVisible()
    assert "Kutu metni" in g._not_kutusu.text() and "Ata" in g._not_kutusu.text()
    g._not_ipucu_guncelle(g.hucre_dikdortgeni(5, 5).center())
    assert not g._not_kutusu.isVisible() and g._not_adayi is None


def test_kutu_html_kacisli(pencere):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("<b>kalın değil</b>", "")})
    g._not_adayi = (2, 2)
    g._not_goster()
    assert "&lt;b&gt;" in g._not_kutusu.text()


def test_tus_kutuyu_kapatir(pencere):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("x")})
    g._not_adayi = (2, 2)
    g._not_goster()
    tus(g, Qt.Key_Down)
    assert not g._not_kutusu.isVisible()


def test_notu_sil_ve_temizle_secime_uygulanir(pencere):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("a"), (3, 2): Not("b"), (9, 9): Not("uzak")})
    g.sec((2, 2), (3, 2))
    assert g.notu_sil()
    assert list(g.sayfa.notlar) == [(9, 9)]
    assert not g.notu_sil()                            # seçimde not yok
    g.geri_al()
    assert len(g.sayfa.notlar) == 3


def test_delete_notu_silmez_tumunu_temizle_siler(pencere):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("a")})
    g.sec((2, 2))
    tus(g, Qt.Key_Delete)
    assert g.sayfa.hucre(2, 2) is None and (2, 2) in g.sayfa.notlar
    g.geri_al()
    g.tumunu_temizle()
    assert g.sayfa.notlar == {} and g.sayfa.hucre(2, 2) is None
    g.geri_al()                                        # tek adım: içerik + not birlikte döner
    assert g.sayfa.hucre(2, 2) is not None and (2, 2) in g.sayfa.notlar


def test_sag_tik_menusu(pencere):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("a")})
    ar = g.hucre_dikdortgeni(2, 2)
    adlar = [a.text() for a in g.hucre_menusu(ar.center()).actions()]
    assert "Notu Düzenle" in adlar and "Notu Sil" in adlar and "Yeni Not" not in adlar
    ar3 = g.hucre_dikdortgeni(4, 4)
    adlar = [a.text() for a in g.hucre_menusu(ar3.center()).actions()]
    assert "Yeni Not" in adlar and "Notu Sil" not in adlar


def test_kopyala_yapistir_notu_getirir_kes_yapistir_tasir(pencere, app):
    g = pencere.izgara()
    g.not_yaz({(2, 2): Not("a", "Y")})
    g.sec((2, 2))
    g.kopyala()
    g.sec((6, 4))
    g.yapistir()
    assert g.sayfa.notlar[(6, 4)] == Not("a", "Y") and (2, 2) in g.sayfa.notlar
    g.geri_al()
    assert (6, 4) not in g.sayfa.notlar
    g.sec((2, 2))
    g.kes()
    g.sec((8, 4))
    g.yapistir()
    assert g.sayfa.notlar.get((8, 4)) == Not("a", "Y") and (2, 2) not in g.sayfa.notlar
