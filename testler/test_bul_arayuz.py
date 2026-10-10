"""Faz 5 / 5b: Bul ve Değiştir penceresi + Git (ekransız)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
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
    s.ata(1, 1, Hucre("elma"))
    s.ata(2, 2, Hucre("Elma suyu"))
    s.ata(4, 1, Hucre("armut"))
    s.ata(5, 1, Hucre(None, "=SUM(B1:B3)"))
    p = Pencere(k)
    p.show()
    yield p
    p.hide()


def test_menu_eylemleri_ve_pencere(pencere):
    for ad in ("bul", "degistir", "git"):
        assert pencere.duzen_eylemleri[ad].isEnabled()
    pencere.bul_ac(False)
    b = pencere.bul_penceresi
    assert b.isVisible() and b.sekme.currentIndex() == 0 and not b.degistir_metni.isVisible()
    pencere.bul_ac(True)
    assert b.sekme.currentIndex() == 1 and b.degistir_metni.isVisible()


def test_sonrakini_bul_hucreye_gider_ve_sarar(pencere):
    pencere.bul_ac()
    b = pencere.bul_penceresi
    b.bul_metni.setText("elma")
    g = pencere.izgara()
    g.sec((1, 1))
    assert b.sonrakini_bul() and g.aktif == (2, 2)
    assert b.sonrakini_bul() and g.aktif == (1, 1)               # sardı
    b.bul_metni.setText("yok böyle")
    assert b.sonrakini_bul() is False and b.durum.text() == "Aradığınız bulunamadı."


def test_onceki_bul(pencere):
    pencere.bul_ac()
    b = pencere.bul_penceresi
    b.bul_metni.setText("elma")
    g = pencere.izgara()
    g.sec((2, 2))
    assert b.sonrakini_bul(ters=True) and g.aktif == (1, 1)


def test_secim_icinde_arama_kisiti_korur(pencere):
    pencere.bul_ac()
    b = pencere.bul_penceresi
    b.bul_metni.setText("elma")
    g = pencere.izgara()
    g.sec((1, 1), (3, 3))
    assert b.sonrakini_bul()
    assert g.aktif == (2, 2)
    assert b.sonrakini_bul() and g.aktif == (1, 1)             # kısıt sürer: seçim dışına (4,1) çıkmaz
    g.sec((5, 5))                                              # kullanıcı başka yere tıkladı: kısıt biter
    assert b.sonrakini_bul() and g.aktif == (1, 1)
    g.sec((1, 1))
    assert b.sonrakini_bul() and g.aktif == (2, 2)


def test_tumunu_bul_listesi_ve_tiklayinca_gider(pencere):
    pencere.bul_ac()
    b = pencere.bul_penceresi
    b.bul_metni.setText("elma")
    b.tumunu_bul()
    assert b.sonuclar.topLevelItemCount() == 2
    assert b.sonuclar.topLevelItem(0).text(2) == "A1"
    assert b.durum.text() == "2 hücre bulundu."
    b._sonuca_git(b.sonuclar.topLevelItem(1))
    assert pencere.izgara().aktif == (2, 2)


def test_sayfa_degistirerek_bulur(pencere):
    s2 = pencere.kitap.sayfa_ekle("Ikinci")
    s2.ata(3, 3, Hucre("özel kayıt"))
    pencere.bul_ac()
    b = pencere.bul_penceresi
    b.bul_metni.setText("özel")
    b.kapsam.setCurrentIndex(1)
    assert b.sonrakini_bul()
    assert pencere.izgara().sayfa is s2 and pencere.izgara().aktif == (3, 3)


def test_tumunu_degistir_tek_geri_al(pencere):
    pencere.bul_ac(True)
    b = pencere.bul_penceresi
    b.bul_metni.setText("elma")
    b.degistir_metni.setText("kiraz")
    b.tumunu_degistir()
    s = pencere.kitap.sayfalar[0]
    assert s.deger(1, 1) == "kiraz" and s.deger(2, 2) == "kiraz suyu"
    assert "2 hücre değiştirildi" in b.durum.text()
    pencere.izgara().geri_al()
    assert s.deger(1, 1) == "elma" and s.deger(2, 2) == "Elma suyu"


def test_degistir_etkin_hucre_eslesirse_degistirir_sonrakine_gecer(pencere):
    pencere.bul_ac(True)
    b = pencere.bul_penceresi
    b.bul_metni.setText("elma")
    b.degistir_metni.setText("kiraz")
    g = pencere.izgara()
    g.sec((1, 1))
    b.degistir()
    s = pencere.kitap.sayfalar[0]
    assert s.deger(1, 1) == "kiraz" and g.aktif == (2, 2)
    b.degistir()
    assert s.deger(2, 2) == "kiraz suyu"


def test_degerler_ve_notlar_modunda_degistir_kapali(pencere):
    pencere.bul_ac(True)
    b = pencere.bul_penceresi
    b.bakilan.setCurrentIndex(1)
    assert not b.degistir_dugmesi.isEnabled() and not b.tumunu_degistir_dugmesi.isEnabled()
    b.bakilan.setCurrentIndex(0)
    assert b.degistir_dugmesi.isEnabled()


def test_formul_icinde_degistir_turkce_metinde(pencere):
    pencere.bul_ac(True)
    b = pencere.bul_penceresi
    b.bul_metni.setText("B1")
    b.degistir_metni.setText("C1")
    b.tumunu_degistir()
    s = pencere.kitap.sayfalar[0]
    assert s.hucre(5, 1).formul == "=SUM(B1:C3)"


def test_git_adrese(pencere):
    pencere._adrese_git("C7")
    assert pencere.izgara().aktif == (7, 3)
    pencere._adrese_git("A1:B2")
    assert pencere.izgara().secim == Aralik(1, 1, 2, 2)


def test_sonrakini_bul_kisayolu_pencere_kapaliyken(pencere):
    pencere.bul_ac()
    b = pencere.bul_penceresi
    b.bul_metni.setText("armut")
    b.close()
    pencere.izgara().sec((1, 1))
    pencere.sonrakini_bul(False)
    assert pencere.izgara().aktif == (4, 1)
