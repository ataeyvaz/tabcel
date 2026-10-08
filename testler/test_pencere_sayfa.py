"""K6: sayfa işlemleri geri alınabilir; arayüz model olaylarıyla eşitlenir."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

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
    for r in range(1, 6):
        k.sayfalar[0].ata(r, 1, Hucre(float(r)))
    p = Pencere(k)
    p.show()
    return p


def sekme_adlari(p):
    return [p.sekmeler.tabText(i) for i in range(p.sekmeler.count())]


def evet(monkeypatch):
    from tabcel.ui import window
    monkeypatch.setattr(window.QMessageBox, "question", lambda *a: window.QMessageBox.Yes)


def test_sayfa_ekle_geri_al_yinele(pencere):
    pencere.sayfa_ekle()
    assert sekme_adlari(pencere) == ["Sayfa1", "Sayfa2"] and pencere.sekmeler.currentIndex() == 1
    pencere.izgara().geri_al()
    assert sekme_adlari(pencere) == ["Sayfa1"] and pencere.izgara().sayfa.ad == "Sayfa1"
    pencere.izgara().yinele()
    assert sekme_adlari(pencere) == ["Sayfa1", "Sayfa2"] and pencere.sekmeler.currentIndex() == 1


def test_sayfa_sil_geri_al_gecmis_silinmez_izgara_korunur(pencere, monkeypatch):
    evet(monkeypatch)
    g1 = pencere.izgara()
    g1.hucre_gir(10, 1, "once")                          # silmeden ÖNCEKİ düzenleme
    pencere.sayfa_ekle()
    g2 = pencere.izgara()
    g2.sec((5, 3))
    g2.hucre_gir(5, 3, "ikinci sayfa verisi")
    g2.sec((7, 2))
    pencere.sayfa_sil(1)
    assert sekme_adlari(pencere) == ["Sayfa1"]
    assert pencere.yigin.geri_alinabilir()               # geçmiş temizlenmedi
    g1.geri_al()                                         # silmeyi geri al
    assert sekme_adlari(pencere) == ["Sayfa1", "Sayfa2"]
    assert pencere.izgara() is g2                        # aynı ızgara nesnesi geri geldi
    assert g2.aktif == (7, 2)                            # seçim korunmuş
    assert pencere.kitap.sayfalar[1].deger(5, 3) == "ikinci sayfa verisi"
    assert pencere.sekmeler.currentIndex() == 1          # geri gelen sayfa seçilir
    g2.geri_al()                                         # önceki düzenleme de geri alınabilir
    assert pencere.kitap.sayfalar[1].deger(5, 3) is None


def test_ortadaki_sayfa_silinince_komsu_secilir(pencere, monkeypatch):
    evet(monkeypatch)
    pencere.sayfa_ekle()
    pencere.sayfa_ekle()
    pencere.sekmeler.setCurrentIndex(1)
    pencere.sayfa_sil(1)
    assert sekme_adlari(pencere) == ["Sayfa1", "Sayfa3"]
    assert pencere.sekmeler.currentIndex() == 1 and pencere.izgara().sayfa.ad == "Sayfa3"


def test_son_sayfa_silinince_onceki_secilir(pencere, monkeypatch):
    evet(monkeypatch)
    pencere.sayfa_ekle()
    pencere.sayfa_sil(1)
    assert sekme_adlari(pencere) == ["Sayfa1"] and pencere.izgara().sayfa.ad == "Sayfa1"


def test_son_sayfa_silinemez(pencere, monkeypatch):
    from tabcel.ui import window
    bilgi = []
    monkeypatch.setattr(window.QMessageBox, "information", lambda *a: bilgi.append(1))
    pencere.sayfa_sil(0)
    assert bilgi and sekme_adlari(pencere) == ["Sayfa1"] and not pencere.yigin.geri_alinabilir()


def test_yeniden_adlandirma_geri_alinir(pencere):
    pencere.sayfa_yeniden_adlandir(0, "Bütçe")
    assert sekme_adlari(pencere) == ["Bütçe"]
    pencere.izgara().geri_al()
    assert sekme_adlari(pencere) == ["Sayfa1"] and pencere.kitap.sayfalar[0].ad == "Sayfa1"
    pencere.izgara().yinele()
    assert sekme_adlari(pencere) == ["Bütçe"]


def test_ayni_adla_yeniden_adlandirma_gecmise_girmez(pencere):
    pencere.sayfa_yeniden_adlandir(0, "Sayfa1")
    assert not pencere.yigin.geri_alinabilir()


def test_sekme_tasima_geri_alinir(pencere):
    pencere.sayfa_ekle()
    a, b = pencere.kitap.sayfalar
    pencere.sekmeler.moveTab(0, 1)
    assert pencere.kitap.sayfalar == [b, a] and sekme_adlari(pencere) == ["Sayfa2", "Sayfa1"]
    pencere.izgara().geri_al()
    assert pencere.kitap.sayfalar == [a, b] and sekme_adlari(pencere) == ["Sayfa1", "Sayfa2"]
    assert pencere.izgara().sayfa is b                   # seçili sayfa değişmedi


def test_model_dogrudan_degisirse_arayuz_olaylarla_eslesir(pencere):
    yeni = pencere.kitap.sayfa_ekle("Dışarıdan")        # komut kullanılmadan
    assert sekme_adlari(pencere) == ["Sayfa1", "Dışarıdan"]
    assert pencere.izgara().sayfa is yeni
    pencere.kitap.yeniden_adlandir(yeni, "Yeni Ad")
    assert sekme_adlari(pencere) == ["Sayfa1", "Yeni Ad"]
    pencere.kitap.sayfa_tasi(yeni, 0)
    assert sekme_adlari(pencere) == ["Yeni Ad", "Sayfa1"] and pencere.izgara().sayfa is yeni


def test_baska_sayfadaki_degisikligi_geri_alinca_o_sayfaya_gecilir(pencere):
    pencere.sayfa_ekle()
    g2 = pencere.izgara()
    g2.hucre_gir(3, 3, "x")                              # 2. sayfada düzenleme
    pencere.sekmeler.setCurrentIndex(0)                  # 1. sayfaya dön
    assert pencere.izgara().sayfa.ad == "Sayfa1"
    pencere.izgara().geri_al()                           # 2. sayfadaki düzenlemeyi geri alır
    assert pencere.kitap.sayfalar[1].deger(3, 3) is None
    assert pencere.izgara().sayfa.ad == "Sayfa2"         # Excel gibi o sayfaya geçti


def test_ayni_sayfadaki_geri_al_sekme_degistirmez(pencere):
    g = pencere.izgara()
    g.hucre_gir(3, 3, "x")
    g.geri_al()
    assert pencere.izgara() is g and pencere.sekmeler.currentIndex() == 0


def test_sayfa_silme_kopya_isaretini_temizler(pencere, monkeypatch):
    evet(monkeypatch)
    pencere.sayfa_ekle()
    pencere.izgara().sec((1, 1))
    pencere.izgara().kes()
    assert Izgara._pano_durumu is not None
    pencere.sayfa_sil(1)
    assert Izgara._pano_durumu is None


def test_gecersiz_ad_geri_al_yigina_girmez(pencere, monkeypatch):
    from tabcel.ui import window
    uyarilar = []
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: uyarilar.append(a[2]))
    pencere.sayfa_yeniden_adlandir(0, "a/b")
    assert uyarilar and not pencere.yigin.geri_alinabilir()
    assert sekme_adlari(pencere) == ["Sayfa1"]


def test_sekme_rengi_esitlemede_korunur(pencere):
    pencere.sekme_rengi_ata(0, "#ff0000")
    pencere.sayfa_ekle()
    pencere.sayfa_yeniden_adlandir(1, "Başka")           # sekmeler yeniden kuruluyor
    assert pencere.sekmeler.tabData(0) == "#ff0000"


def test_silinen_sayfa_olaylari_arayuzu_bozmaz(pencere, monkeypatch):
    evet(monkeypatch)
    pencere.sayfa_ekle()
    silinen = pencere.kitap.sayfalar[1]
    pencere.sayfa_sil(1)
    silinen.ata(1, 1, Hucre("hayalet"))                  # kitaptan çıkmış sayfaya yazım: olay yok, hata yok
    assert sekme_adlari(pencere) == ["Sayfa1"]


def test_birden_cok_sayfa_islemi_art_arda_tutarli(pencere, monkeypatch):
    evet(monkeypatch)
    for _ in range(3):
        pencere.sayfa_ekle()
    pencere.sayfa_yeniden_adlandir(2, "Ortası")
    pencere.sayfa_sil(1)
    assert sekme_adlari(pencere) == ["Sayfa1", "Ortası", "Sayfa4"]
    for _ in range(5):
        pencere.izgara().geri_al()
    assert sekme_adlari(pencere) == ["Sayfa1"]
    for _ in range(5):
        pencere.izgara().yinele()
    assert sekme_adlari(pencere) == ["Sayfa1", "Ortası", "Sayfa4"]
