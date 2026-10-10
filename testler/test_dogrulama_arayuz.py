"""Faz 5 / 5g: veri doğrulama arayüzü (pencere, giriş denetimi, açılır liste, giriş iletisi) — ekransız."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.dogrulama import Dogrulama
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.dogrulama_penceresi import DogrulamaPenceresi
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
    for i, v in enumerate(("Elma", "Armut", "Kiraz"), start=1):
        s.ata(i, 5, Hucre(v))
    p = Pencere(k)
    p.resize(900, 500)
    p.show()
    app.processEvents()
    yield p
    p.hide()


def tus(g, anahtar, mod=Qt.NoModifier):
    g.keyPressEvent(QKeyEvent(QEvent.KeyPress, anahtar, mod))


def kural(**kw):
    return Dogrulama((), **kw)


def test_menu_acik(pencere):
    assert pencere.veri_eylemleri["dogrulama"].isEnabled()


def test_pencereden_uygula_geri_al_temizle(pencere):
    g = pencere.izgara()
    g.sec((2, 2), (4, 3))
    assert pencere.dogrulama_ac(kural(tur="tam_sayi", islec="arasinda", formul1="=1", formul2="=10"))
    dv = g.sayfa.dogrulamalar[0]
    assert dv.araliklar == (Aralik(2, 2, 4, 3),)
    assert g.sayfa.dogrulama(4, 3) is dv
    g.geri_al()
    assert g.sayfa.dogrulamalar == []
    g.yinele()
    assert pencere.dogrulama_ac("temizle")
    assert g.sayfa.dogrulamalar == []
    assert not pencere.dogrulama_ac("temizle")                          # zaten yok


def test_etkisiz_kural_kaldirir(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1"))
    assert pencere.dogrulama_ac(kural(tur="her_deger"))                 # herhangi bir değer + ileti yok = kaldır
    assert g.sayfa.dogrulamalar == []


def test_karisik_secimde_soru(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1"))
    g.sec((2, 2), (3, 2))                                               # biri kurallı, biri kuralsız
    sorular = []
    monkeypatch.setattr(pencere, "_dogrulama_karisik_onayi", lambda: sorular.append(1) or False)
    assert not pencere.dogrulama_ac(kural(tur="ondalik", formul1="=1"))
    assert sorular == [1] and g.sayfa.dogrulamalar[0].tur == "tam_sayi"
    monkeypatch.setattr(pencere, "_dogrulama_karisik_onayi", lambda: True)
    assert pencere.dogrulama_ac(kural(tur="ondalik", formul1="=1"))
    assert [d.tur for d in g.sayfa.dogrulamalar] == ["ondalik"]
    assert g.sayfa.dogrulamalar[0].araliklar == (Aralik(2, 2, 3, 2),)


def test_ayni_kuralla_tamamen_kapli_secimde_soru_yok(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((2, 2), (3, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1"))
    monkeypatch.setattr(pencere, "_dogrulama_karisik_onayi", lambda: pytest.fail("sorulmamalı"))
    assert pencere.dogrulama_ac(kural(tur="ondalik", formul1="=1"))


def test_geri_yonlu_secimde_goreli_formul_capaya_kayar(pencere):
    g = pencere.izgara()
    g.sec((5, 2), (3, 2))                                               # etkin B5, seçim B3:B5 (çapa B3)
    pencere.dogrulama_ac(kural(tur="tam_sayi", islec="kucuk_esit", formul1="=A5"))
    assert g.sayfa.dogrulamalar[0].formul1 == "=A3"
    assert g.sayfa.dogrulamalar[0].capa() == (3, 2)


def test_gecersiz_giris_durdur_tekrar_ve_iptal(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", islec="arasinda", formul1="=1", formul2="=10"))
    sorular = []
    g.dogrulama_soru = lambda dv: sorular.append(dv.hata[1]) or "tekrar"
    assert g.hucre_gir(2, 2, "50") is False                              # düzenleme açık kalır
    assert g.sayfa.hucre(2, 2) is None and sorular == ["durdur"]
    g.dogrulama_soru = lambda dv: "iptal"
    assert g.hucre_gir(2, 2, "50") is True and g.sayfa.hucre(2, 2) is None
    assert g.hucre_gir(2, 2, "5") is True and g.sayfa.deger(2, 2) == 5.0   # geçerli: soru yok (lambda iptal verirdi)


def test_uyari_stili_devam_yazar(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1", islec="buyuk", hata=(True, "uyari", "", "")))
    g.dogrulama_soru = lambda dv: "devam"
    assert g.hucre_gir(2, 2, "-4") is True and g.sayfa.deger(2, 2) == -4.0


def test_hata_uyarisi_kapaliysa_sessizce_izin(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1", islec="buyuk", hata=(False, "durdur", "", "")))
    g.dogrulama_soru = lambda dv: pytest.fail("sorulmamalı")
    assert g.hucre_gir(2, 2, "-4") is True and g.sayfa.deger(2, 2) == -4.0


def test_formul_girisi_ve_silme_denetlenmez(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1", islec="buyuk"))
    g.dogrulama_soru = lambda dv: pytest.fail("sorulmamalı")
    assert g.hucre_gir(2, 2, "=-5*2") is True and g.sayfa.deger(2, 2) == -10.0
    g.sec((2, 2))
    tus(g, Qt.Key_Delete)
    assert g.sayfa.hucre(2, 2) is None


def test_yapistirma_denetlenmez_kopya_notu(pencere, app):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1", islec="buyuk"))
    g.dogrulama_soru = lambda dv: pytest.fail("sorulmamalı")
    g.sec((1, 5))
    g.kopyala()                                                          # "Elma"
    g.sec((2, 2))
    g.yapistir()
    assert g.sayfa.deger(2, 2) == "Elma"


def test_bos_girdi_bos_yoksay(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1", islec="buyuk", bos_yoksay=False))
    asilar = []
    g.dogrulama_soru = lambda dv: asilar.append(1) or "iptal"
    g.hucre_gir(2, 2, "")
    assert asilar == [1]


def test_acilir_liste_ogeleri_ve_secim(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    assert g.acilir_liste_ogeleri() is None
    pencere.dogrulama_ac(kural(tur="liste", formul1="=$E$1:$E$4"))
    assert g.acilir_liste_ogeleri() == ["Elma", "Armut", "Kiraz", ""]       # boş hücre boş satır
    assert g.acilir_liste_sec("Armut") and g.sayfa.deger(2, 2) == "Armut"
    g.dogrulama_soru = lambda dv: "iptal"
    g.acilir_liste_sec("Muz")                                              # listede yok: kural yine denetler
    assert g.sayfa.deger(2, 2) == "Armut"
    g.geri_al()
    assert g.sayfa.hucre(2, 2) is None


def test_acilir_liste_kapali_ya_da_baska_tur(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="liste", formul1='"a,b"', acilir_liste=False))
    assert g.acilir_liste_ogeleri() is None and g._acilir_dugme_dikdortgeni() is None
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1"))
    assert g.acilir_liste_ogeleri() is None


def test_dugme_dikdortgeni_tiklama_ve_alt_asagi(pencere, app):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="liste", formul1='"Evet,Hayır"'))
    d = g._acilir_dugme_dikdortgeni()
    ar = g.hucre_dikdortgeni(2, 2)
    assert d is not None and d.left() == ar.right() + 1                   # hücrenin sağ kenarının dışında
    QTest.mouseClick(g.viewport(), Qt.LeftButton, Qt.NoModifier, d.center())
    assert g._liste_acik is not None and g._liste_acik.count() == 2 and g.aktif == (2, 2)
    g._liste_acik.close()
    g._liste_acik = None
    tus(g, Qt.Key_Down, Qt.AltModifier)
    assert g._liste_acik is not None
    g._liste_acik.close()
    g.sec((3, 2))
    assert g._acilir_dugme_dikdortgeni() is None                          # yalnız etkin hücrede
    img = g.viewport().grab().toImage()
    assert img is not None


def test_giris_iletisi_gosterilir_ve_kapanir(pencere, app):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1", giris=(True, "Yaş", "1 ile 120 arası <gir>")))
    g.sec((3, 2))
    g.sec((2, 2))
    assert g._giris_etiketi is not None and g._giris_etiketi.isVisible()
    assert "Yaş" in g._giris_etiketi.text() and "&lt;gir&gt;" in g._giris_etiketi.text()
    g.sec((3, 3))
    assert not g._giris_etiketi.isVisible()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1", giris=(True, "", "")))     # boş ileti gösterilmez
    g.sec((3, 3))
    g.sec((2, 2))
    assert not g._giris_etiketi.isVisible()


def test_tumunu_temizle_kurali_da_kaldirir(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    pencere.dogrulama_ac(kural(tur="tam_sayi", formul1="=1"))
    g.tumunu_temizle()
    assert g.sayfa.dogrulamalar == []
    g.geri_al()
    assert len(g.sayfa.dogrulamalar) == 1


# ------------------------------------------------------------------------------- pencere alanları
def yeni_pencere(app, kitap=None, mevcut=None):
    return DogrulamaPenceresi(kitap or CalismaKitabi(), mevcut)


def test_pencere_liste_ve_sayi_donusumu(app):
    p = yeni_pencere(app)
    p.izin.setCurrentIndex(p.izin.findData("liste"))
    p.alan1.setText("Evet; Hayır;İyi")
    assert p.dogrulama_olustur().formul1 == '"Evet,Hayır,İyi"'
    p.alan1.setText("=$E$1:$E$5")
    assert p.dogrulama_olustur().formul1 == "=$E$1:$E$5"
    p.alan1.setText("a,b")
    with pytest.raises(ValueError):
        p.dogrulama_olustur()
    p.izin.setCurrentIndex(p.izin.findData("ondalik"))
    p.veri.setCurrentIndex(p.veri.findData("arasinda"))
    p.alan1.setText("2,5")
    p.alan2.setText("=B1*2")
    dv = p.dogrulama_olustur()
    assert (dv.formul1, dv.formul2, dv.islec) == ("=2.5", "=B1*2", "arasinda")
    p.alan2.setText("")
    with pytest.raises(ValueError):
        p.dogrulama_olustur()
    p.alan2.setText("metin")
    with pytest.raises(ValueError):
        p.dogrulama_olustur()


def test_pencere_ozel_ve_formul_hatasi_ve_tarih(app):
    p = yeni_pencere(app)
    p.izin.setCurrentIndex(p.izin.findData("ozel"))
    p.alan1.setText("TOPLA(A1:A3)>5")
    assert p.dogrulama_olustur().formul1 == "=SUM(A1:A3)>5"
    p.alan1.setText("=TOPLA(")
    with pytest.raises(ValueError):
        p.dogrulama_olustur()
    p.izin.setCurrentIndex(p.izin.findData("tarih"))
    p.veri.setCurrentIndex(p.veri.findData("buyuk_esit"))
    p.alan1.setText("1.1.2026")
    assert p.dogrulama_olustur().formul1 == "=46023"


def test_pencere_yukle_ve_yeniden_olustur(app):
    mevcut = Dogrulama((Aralik(1, 1, 1, 1),), tur="ondalik", islec="arasinda_degil", formul1="=1.5", formul2="=$A$1",
                       bos_yoksay=False, giris=(True, "B", "İ"), hata=(True, "bilgi", "H", "E"))
    p = yeni_pencere(app, mevcut=mevcut)
    assert (p.alan1.text(), p.alan2.text()) == ("1,5", "=$A$1")
    yeni = p.dogrulama_olustur()
    assert yeni.araliklar == () and yeni.formul1 == "=1.5" and yeni.formul2 == "=$A$1"
    assert (yeni.tur, yeni.islec, yeni.bos_yoksay, yeni.giris, yeni.hata) == (
        "ondalik", "arasinda_degil", False, (True, "B", "İ"), (True, "bilgi", "H", "E"))
    liste = yeni_pencere(app, mevcut=Dogrulama((Aralik(1, 1, 1, 1),), tur="liste", formul1='"x,y"'))
    assert liste.alan1.text() == "x;y"


def test_pencere_duzen_alanlari(app):
    p = yeni_pencere(app)
    p.show()
    p.izin.setCurrentIndex(p.izin.findData("her_deger"))
    assert not p.alan1.isEnabled()
    p.izin.setCurrentIndex(p.izin.findData("tam_sayi"))
    assert p.alan2.isVisible() and p.etiket1.text() == "En Az:"
    p.veri.setCurrentIndex(p.veri.findData("buyuk"))
    assert not p.alan2.isVisible() and p.etiket1.text() == "Değer:"
    p.izin.setCurrentIndex(p.izin.findData("liste"))
    assert p.acilir.isEnabled() and p.etiket1.text() == "Kaynak:" and not p.veri.isEnabled()
    p.close()
