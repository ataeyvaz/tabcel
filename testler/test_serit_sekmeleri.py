"""Faz 5 / 5j-5: Sayfa Düzeni, Formüller, Veri, Gözden Geçir, Görünüm sekmeleri."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.notlar import Not
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere

SEKMELER = ["Dosya", "Giriş", "Sayfa Düzeni", "Formüller", "Veri", "Gözden Geçir", "Görünüm"]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 5):
        s.ata(r, 1, Hucre(float(r)))
    p = Pencere(k)
    p.resize(1100, 700)
    p.show()
    return p


def yapi(p):
    return p.izgara().sayfa.sayfa_yapisi


def test_sekme_sirasi(pencere):
    assert pencere.serit.sekme_adlari() == SEKMELER


def test_eski_menulerdeki_her_eylem_seritten_erisilir(pencere):
    """Plan ölçütü: tüm eski menü eylemleri (Düzen, Veri, Görünüm, Koşullu Biçim, Dosya) şeritte."""
    bulunan = set(map(id, pencere.serit.eylemler()))
    for sozluk in (pencere.duzen_eylemleri, pencere.veri_eylemleri, pencere.gorunum_eylemleri,
                   pencere.kosullu_eylemleri):
        for k, a in sozluk.items():
            assert id(a) in bulunan, k
    assert id(pencere.kilavuz_eylemi) in bulunan
    for k, a in pencere.eylemler.items():
        if k.startswith("dosya."):
            assert id(a) in bulunan, k


def test_veri_sekmesi_var_ve_eylemleri_icerir(pencere):
    sr = pencere.serit.eylemler()
    for k in ("artan", "azalan", "ozel_sirala", "filtre", "filtre_temizle", "filtre_yeniden", "dogrulama",
              "ad_tanimla", "ad_yoneticisi", "otomatik_toplam", "yeni_not", "notu_sil", "bolme", "ust_satir",
              "ilk_sutun", "coz", "kilavuz", "yakin_100"):
        assert pencere.eylemler[k] in sr, k


@pytest.mark.parametrize("sekme", SEKMELER[2:])
@pytest.mark.parametrize("genislik", [800, 640])
def test_dar_pencerede_hicbir_sekmede_tasma_yok(pencere, sekme, genislik):
    pencere.resize(genislik, 600)
    pencere.serit.sec(sekme)
    QApplication.processEvents()
    sayfa = pencere.serit.sayfa(sekme)
    for g in sayfa.gruplar:
        assert g.mapTo(sayfa, g.rect().topRight()).x() <= sayfa.width() + 1, (sekme, g.ad)


# ------------------------------------------------------------------ Sayfa Düzeni
def test_yonlendirme_kagit_kenar_geri_alinir(pencere):
    e = pencere.eylemler
    e["yon_yatay"].trigger()
    assert yapi(pencere).yon == "yatay"
    e["kagit_A3"].trigger()
    assert yapi(pencere).kagit == "A3"
    e["kenar_dar"].trigger()
    y = yapi(pencere)
    assert (y.ust, y.alt, y.sol, y.sag) == (1.91, 1.91, 0.64, 0.64)
    e["kenar_genis"].trigger()
    assert (yapi(pencere).sol, yapi(pencere).ust) == (2.54, 2.54)
    pencere.izgara().geri_al()                                  # tek geri al adımı: geniş → dar
    assert (yapi(pencere).sol, yapi(pencere).ust) == (0.64, 1.91)
    pencere.izgara().geri_al()
    pencere.izgara().geri_al()
    pencere.izgara().geri_al()
    assert yapi(pencere).yon == "dikey" and yapi(pencere).kagit == "A4"


def test_ayni_deger_komut_olusturmaz(pencere):
    n = len(pencere.yigin._geri) if hasattr(pencere.yigin, "_geri") else None
    assert pencere.sayfa_yapisi_degistir(yon="dikey") is False         # zaten dikey
    if n is not None:
        assert len(pencere.yigin._geri) == n


def test_yazdirma_alani_belirle_ve_temizle(pencere):
    pencere.izgara().sec((2, 1), (3, 2))
    pencere.eylemler["alan_belirle"].trigger()
    assert yapi(pencere).alan == Aralik(2, 1, 3, 2)
    pencere.eylemler["alan_temizle"].trigger()
    assert yapi(pencere).alan is None


def test_olcek_ve_sigdir(pencere):
    pencere.serit.sec("Sayfa Düzeni")
    sayfa = pencere.serit.sayfa("Sayfa Düzeni")
    sayfa.olcek.setValue(150)
    sayfa.olcek.editingFinished.emit()
    assert yapi(pencere).olcek == 150
    sayfa.sigdir.click()
    assert yapi(pencere).sigdir_genislik is True
    pencere._arayuzu_guncelle()
    assert sayfa.sigdir.isChecked() and not sayfa.olcek.isEnabled()      # sığdır açıkken ölçek kapalı
    sayfa.sigdir.click()
    assert yapi(pencere).sigdir_genislik is False


def test_kilavuz_yazdir_isareti_modeli_izler(pencere):
    a = pencere.eylemler["kilavuz_yazdir"]
    assert a.isCheckable() and not a.isChecked()
    a.trigger()
    assert yapi(pencere).kilavuz is True and a.isChecked()
    pencere.izgara().geri_al()
    pencere._arayuzu_guncelle()
    assert yapi(pencere).kilavuz is False and not a.isChecked()


def test_sayfa_yapisi_sayfaya_ozel(pencere):
    pencere.eylemler["yon_yatay"].trigger()
    pencere.sayfa_ekle()
    assert yapi(pencere).yon == "dikey"                                 # yeni sayfa kendi ayarında
    pencere.serit.sec("Sayfa Düzeni")
    pencere.sekmeler.setCurrentIndex(0)
    assert yapi(pencere).yon == "yatay"


def test_gecersiz_deger_uyari_verir(pencere, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    uyarilar = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: uyarilar.append(a[2]))
    assert pencere.sayfa_yapisi_degistir(olcek=5) is False
    assert uyarilar and yapi(pencere).olcek == 100


# ------------------------------------------------------------------ Veri / Gözden Geçir / Görünüm
def test_filtre_dugmesi_isaretli_ve_siralama_calisir(pencere):
    pencere.izgara().sec((1, 1), (4, 1))
    pencere.eylemler["azalan"].trigger()
    assert [pencere.izgara().sayfa.hucre(r, 1).deger for r in range(1, 5)] == [4.0, 3.0, 2.0, 1.0]
    pencere.eylemler["filtre"].trigger()
    assert pencere.eylemler["filtre"].isChecked() and pencere.izgara().sayfa.filtre is not None
    pencere.eylemler["filtre"].trigger()
    assert not pencere.eylemler["filtre"].isChecked() and pencere.izgara().sayfa.filtre is None


def test_not_dugmeleri(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere._arayuzu_guncelle()
    assert not pencere.eylemler["notu_sil"].isEnabled()
    g.not_yaz({(2, 1): Not("x", "Ata")})
    pencere._arayuzu_guncelle()
    assert pencere.eylemler["notu_sil"].isEnabled() and pencere.eylemler["yeni_not"].text() == "Notu Düzenle"
    pencere.eylemler["notu_sil"].trigger()
    assert not g.not_var_mi((2, 1))


def test_gorunum_dondur_kilavuz_ve_yakinlastirma(pencere):
    g = pencere.izgara()
    g.sec((3, 3))
    pencere.eylemler["bolme"].trigger()
    assert g.sayfa.dondur is not None
    pencere._arayuzu_guncelle()
    assert pencere.eylemler["coz"].isEnabled()
    pencere.eylemler["coz"].trigger()
    assert g.sayfa.dondur is None
    g.yakinlastir(2.0)
    pencere.eylemler["yakin_100"].trigger()
    assert abs(g.yakinlastirma - 1.0) < 1e-9
    pencere.eylemler["kilavuz"].setChecked(False)
    assert g.sayfa.kilavuz is False


def test_formuller_sekmesi_otomatik_toplam_ve_ad_yoneticisi(pencere, monkeypatch):
    from tabcel.ui import window as w
    acilan = []
    monkeypatch.setattr(w.AdYoneticisi, "exec", lambda self: acilan.append(1))
    pencere.eylemler["ad_yoneticisi"].trigger()
    assert acilan == [1]
    g = pencere.izgara()
    g.sec((5, 1))
    pencere.eylemler["otomatik_toplam"].trigger()
    assert g.duzenleniyor()                                              # =TOPLA(A1:A4) düzenlemesi açıldı
