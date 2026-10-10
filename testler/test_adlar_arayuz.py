"""Faz 5 / 5d: tanımlı ad arayüzü — Ad Kutusu, Ad Tanımla, Ad Yöneticisi, Git, otomatik tamamlama (ekransız)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from tabcel.formul import ceviri, isaretleme
from tabcel.model import deger as D
from tabcel.model.ad import TanimliAd, ad_anahtari
from tabcel.model.adres import Aralik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.ad_penceresi import AdTanimlaPenceresi, AdYoneticisi, GitPenceresi
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
    s.ata(1, 1, Hucre(10.0))
    s.ata(2, 1, Hucre(20.0))
    s.ata(3, 1, Hucre(30.0))
    p = Pencere(k)
    p.show()
    yield p
    p.hide()


@pytest.fixture
def iletiler(monkeypatch):
    liste = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: liste.append(a[2]))
    return liste


def ad_kutusundan(pencere, metin):
    pencere.ad_kutusu.setText(metin)
    pencere.ad_kutusu.returnPressed.emit()


def test_ad_kutusu_secimi_adlandirir_ve_geri_alinir(pencere):
    g = pencere.izgara()
    g.sec((1, 1), (3, 1))
    ad_kutusundan(pencere, "Fiyat")
    t = pencere.kitap.ad_bul("Fiyat")
    assert t is not None and t.kapsam is None and t.formul == "=[1]!$A$1:$A$3"
    assert pencere.ad_kutusu.text() == "Fiyat"                   # seçim tam adın aralığı: ad görünür
    g.sec((2, 2))
    assert pencere.ad_kutusu.text() == "B2"
    pencere.yigin.geri_al()
    assert pencere.kitap.ad_bul("Fiyat") is None


def test_ad_kutusu_ada_gider(pencere):
    pencere.izgara().sec((1, 1), (3, 1))
    ad_kutusundan(pencere, "Fiyat")
    pencere.izgara().sec((5, 5))
    ad_kutusundan(pencere, "fiyat")                              # büyük/küçük harf duyarsız
    assert pencere.izgara().secim == Aralik(1, 1, 3, 1)


def test_ad_kutusu_baska_sayfadaki_ada_gider(pencere):
    k = pencere.kitap
    s2 = k.sayfa_ekle("Veri")
    pencere.sekmeler.setCurrentIndex(1)
    pencere.izgara().sec((2, 2), (4, 3))
    ad_kutusundan(pencere, "Bolge")
    pencere.sekmeler.setCurrentIndex(0)
    ad_kutusundan(pencere, "Bolge")
    assert pencere.izgara().sayfa is s2 and pencere.izgara().secim == Aralik(2, 2, 4, 3)


def test_ad_kutusu_gecersiz_ad_uyarir(pencere, iletiler):
    for kotu in ("A1:", "1abc", "toplam 1", "R1C1"):
        ad_kutusundan(pencere, kotu)
    assert pencere.kitap.adlar == {}
    assert iletiler and all("geçerli değil" in m for m in iletiler)


def test_git_mevcut_olmayan_ad_tanimlamaz(pencere, iletiler):
    pencere._adrese_git("Yok")
    assert pencere.kitap.adlar == {} and iletiler == ["Başvuru geçerli değil."]


def test_sabit_ad_aralik_degil_uyarir(pencere, iletiler):
    pencere.kitap.ad_yaz(TanimliAd("KDV", "=0.18"))
    pencere._adrese_git("KDV")
    assert iletiler == ["Bu ad bir hücre aralığına başvurmuyor."]


def test_git_penceresi_adlari_listeler(pencere, monkeypatch):
    pencere.kitap.ad_yaz(TanimliAd("Fiyat", "=[1]!$A$1:$A$3"))
    pencere.kitap.ad_yaz(TanimliAd("Gizli", "=1", gizli=True))
    gorulen = {}

    def exec_(self):
        gorulen["adlar"] = [self.liste.item(i).text() for i in range(self.liste.count())]
        self.liste.setCurrentRow(0)
        return QDialog.Accepted
    monkeypatch.setattr(GitPenceresi, "exec", exec_)
    pencere.git_ac()
    assert gorulen["adlar"] == ["Fiyat"]
    assert pencere.izgara().secim == Aralik(1, 1, 3, 1)


def test_tamamlayici_adlari_gunceller(pencere):
    pencere.kitap.ad_yaz(TanimliAd("Fiyat", "=[1]!$A$1"))
    pencere.kitap.ad_yaz(TanimliAd("Oran", "=0.18"))
    assert pencere._ad_model.stringList() == ["Fiyat", "Oran"]
    pencere.kitap.ad_yaz(None, ad_anahtari(None, "Oran"))
    assert pencere._ad_model.stringList() == ["Fiyat"]


def test_ad_tanimla_penceresi_secimden(pencere):
    g = pencere.izgara()
    g.sec((1, 1), (3, 1))
    pen = AdTanimlaPenceresi(pencere.kitap, g.sayfa, g.secim, None, pencere)
    assert pen.basvurur_kutusu.text() == "=Sayfa1!$A$1:$A$3"
    pen.ad_kutusu.setText("Fiyat")
    pen.aciklama_kutusu.setText("birim fiyatlar")
    pen.accept()
    assert pen.tanim == TanimliAd("Fiyat", "=[1]!$A$1:$A$3", None, "birim fiyatlar")


def test_ad_tanimla_penceresi_hatalar(pencere):
    g = pencere.izgara()
    pen = AdTanimlaPenceresi(pencere.kitap, g.sayfa, g.secim, None, pencere)
    pen.ad_kutusu.setText("A1")
    pen.accept()
    assert pen.tanim is None and "geçerli değil" in pen.ileti.text()
    pen.ad_kutusu.setText("Veri")
    pen.basvurur_kutusu.setText("=TOPLA(")
    pen.accept()
    assert pen.tanim is None and "Başvurur" in pen.ileti.text()
    pen.basvurur_kutusu.setText("=1")
    pen.accept()
    assert pen.tanim is not None
    pencere.kitap.ad_yaz(pen.tanim)
    pen2 = AdTanimlaPenceresi(pencere.kitap, g.sayfa, g.secim, None, pencere)
    pen2.ad_kutusu.setText("VERİ")             # Türkçe: İ → i
    pen2.basvurur_kutusu.setText("=2")
    pen2.accept()
    assert pen2.tanim is None and "zaten var" in pen2.ileti.text()


def test_ad_tanimla_turkce_formul_ve_sayfaya_baglama(pencere):
    g = pencere.izgara()
    pen = AdTanimlaPenceresi(pencere.kitap, g.sayfa, g.secim, None, pencere)
    pen.ad_kutusu.setText("Kdv")
    pen.basvurur_kutusu.setText("=0,18")
    pen.accept()
    assert pen.tanim.formul == "=0.18"
    pen3 = AdTanimlaPenceresi(pencere.kitap, g.sayfa, g.secim, None, pencere)
    pen3.ad_kutusu.setText("Hucre")
    pen3.basvurur_kutusu.setText("=B2")                         # sayfasız → etkin sayfaya bağlanır
    pen3.accept()
    assert pen3.tanim.formul == "=[1]!B2"


def test_ad_tanimla_pencere_komutu_ve_duzenleme(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((1, 1), (3, 1))

    def tamam(self):
        self.ad_kutusu.setText("Fiyat")
        self.accept()
        return QDialog.Accepted
    monkeypatch.setattr(AdTanimlaPenceresi, "exec", tamam)
    assert pencere.ad_tanimla_ac()
    assert pencere.kitap.ad_bul("Fiyat") is not None
    pencere.izgara().sayfa.ata(4, 1, ceviri.hucre_girdisi("=TOPLA(Fiyat)", pencere.kitap))
    assert pencere.izgara().sayfa.sonuc(4, 1) == 60.0

    def yeniden_adlandir(self):
        assert self.ad_kutusu.text() == "Fiyat" and not self.kapsam_kutusu.isEnabled()
        self.ad_kutusu.setText("Liste")
        self.accept()
        return QDialog.Accepted
    monkeypatch.setattr(AdTanimlaPenceresi, "exec", yeniden_adlandir)
    assert pencere.ad_tanimla_ac(pencere.kitap.ad_bul("Fiyat"))
    assert pencere.kitap.ad_bul("Fiyat") is None and pencere.kitap.ad_bul("Liste") is not None
    assert pencere.izgara().sayfa.hucre(4, 1).formul == "=SUM(Liste)"
    pencere.yigin.geri_al()
    assert pencere.izgara().sayfa.hucre(4, 1).formul == "=SUM(Fiyat)"
    assert pencere.izgara().sayfa.sonuc(4, 1) == 60.0


def test_ad_yoneticisi_listeler_ve_siler(pencere):
    k = pencere.kitap
    k.ad_yaz(TanimliAd("Fiyat", "=[1]!$A$1:$A$3", None, "birim"))
    k.ad_yaz(TanimliAd("KDV", "=0.18"))
    k.ad_yaz(TanimliAd("Yerel", "=[1]!$A$1", k.sayfalar[0].kimlik))
    k.ad_yaz(TanimliAd("Gizli", "=1", gizli=True))
    y = AdYoneticisi(pencere)
    satirlar = [[y.tablo.item(i, j).text() for j in range(5)] for i in range(y.tablo.rowCount())]
    assert [r[0] for r in satirlar] == ["Fiyat", "KDV", "Yerel"]            # gizli yok
    fiyat, kdv, yerel = satirlar
    assert fiyat[1] == "{…}" and fiyat[2] == "=Sayfa1!$A$1:$A$3" and fiyat[3] == "Çalışma Kitabı" and fiyat[4] == "birim"
    assert kdv[1] == "0,18" and kdv[2] == "=0,18"
    assert yerel[1] == "10" and yerel[3] == "Sayfa1"
    y.tablo.selectRow(1)
    y.sil()
    assert k.ad_bul("KDV") is None and y.tablo.rowCount() == 2
    pencere.yigin.geri_al()
    assert k.ad_bul("KDV") is not None


def test_ad_yoneticisi_kisayolu_acar(pencere, monkeypatch):
    acildi = []
    monkeypatch.setattr(AdYoneticisi, "exec", lambda self: acildi.append(1))
    pencere.veri_eylemleri["ad_yoneticisi"].trigger()
    assert acildi == [1]


def test_formul_oneri_listesi_tanimli_adlari_icerir():
    assert isaretleme.oneriler("Fi", tanimli_adlar=["Fiyat", "Oran"])[-1] == "Fiyat"
    assert "Oran" not in isaretleme.oneriler("Fi", tanimli_adlar=["Fiyat", "Oran"])
    assert isaretleme.oneriler("TOPL", tanimli_adlar=["TOPLA"]).count("TOPLA") == 1   # gölgeleme yok
    assert isaretleme.oneriler("Fi") == isaretleme.oneriler("Fi", tanimli_adlar=())


def test_duzenleyici_ad_onerisi_kabul_parantez_eklemez(pencere):
    k = pencere.kitap
    k.ad_yaz(TanimliAd("FiyatListesi", "=[1]!$A$1:$A$3"))
    g = pencere.izgara()
    g.sec((5, 5))
    g.duzenle_baslat("=Fiyat")
    e = g._duzenleyici
    e.setText("=Fiy")
    e.setText("=Fiyat")                                          # textChanged → öneri listesi
    assert e.oneri_acik()
    e.oneri_kabul()
    assert e.text() == "=FiyatListesi"
    e.setText("=TOPL")
    assert e.oneri_acik()
    e.oneri_kabul()
    assert e.text().endswith("(")
    g._duzenleme_bitti(False, 0, 0)


def test_ad_formulde_otomatik_cozulur_ve_ad_silinince_hata(pencere):
    k = pencere.kitap
    g = pencere.izgara()
    pencere.izgara().sec((1, 1), (3, 1))
    ad_kutusundan(pencere, "Fiyat")
    g.sec((5, 5))
    assert g.hucre_gir(5, 5, "=TOPLA(Fiyat)")
    assert g.sayfa.sonuc(5, 5) == 60.0
    pencere.ad_sil(k.ad_bul("Fiyat"))
    assert g.sayfa.sonuc(5, 5) == D.AD
