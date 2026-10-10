"""Faz 5 / 5j-4: şerit pencerede — Dosya + Giriş sekmeleri, grup düzeni, daralma ölçütleri, başlık."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QToolButton

from tabcel.model.notlar import Not
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    k.sayfalar[0].ata(1, 1, Hucre(1.0))
    p = Pencere(k)
    p.show()
    return p


def test_sekmeler_dosya_ve_giris(pencere):
    sr = pencere.serit
    assert sr.sekme_adlari()[:2] == ["Dosya", "Giriş"]
    assert sr.sekme_adlari()[sr.sekmeler.currentIndex()] == "Giriş"
    assert sr.sayfa("Giriş") is pencere.bicim_cubugu


def test_giris_gruplari_sirasi(pencere):
    assert [g.ad for g in pencere.bicim_cubugu.gruplar] == [
        "Pano", "Yazı Tipi", "Hizalama", "Sayı", "Stiller", "Hücreler", "Düzenleme"]


def test_baslikta_yalniz_hizli_erisim(pencere):
    for ad in ("duzen_dugmesi", "veri_dugmesi", "gorunum_dugmesi", "kosullu_dugmesi", "dosya_dugmesi"):
        assert not hasattr(pencere, ad), ad
    assert pencere.geri_dugmesi.defaultAction() is pencere.eylemler["geri_al"]
    assert pencere.kaydet_dugmesi.toolTip().startswith("Kaydet")


# not: 1100 px'te "hiçbir grup açılır düğmeye inmez" ölçütü gerçek yazı tipi ister (ekransız Qt yazıyı kutu
# ölçer); `araclar/serit_olcum.py` bunu gerçek platformda denetler (test.md Faz 5 / 5j).


@pytest.mark.parametrize("genislik", [800, 700])
def test_dar_pencerede_gruplar_sayfa_disina_tasmaz(pencere, genislik):
    pencere.resize(genislik, 600)
    QApplication.processEvents()
    sayfa = pencere.bicim_cubugu
    for g in sayfa.gruplar:
        sag = g.mapTo(sayfa, g.rect().topRight()).x()
        assert sag <= sayfa.width() + 1, (g.ad, sag, sayfa.width())


def test_genis_pencerede_hepsi_tam(pencere):
    pencere.resize(3000, 700)
    QApplication.processEvents()
    assert all(g.durum == 0 for g in pencere.bicim_cubugu.gruplar)


def test_sirala_ve_hucreler_menuleri_katalog_eylemlerini_icerir(pencere):
    bulunan = pencere.serit.eylemler()
    for k in ("satir_ekle", "sutun_sil", "sayfa_ekle", "satir_yukseklik", "satir_gizle", "sekme_rengi",
              "hucre_bicimi", "artan", "azalan", "ozel_sirala", "filtre", "filtre_temizle", "filtre_yeniden",
              "bul", "degistir", "git", "doldur_asagi", "doldur_saga", "temizle_hepsi", "temizle_bicim",
              "temizle_icerik", "temizle_not", "otomatik_toplam", "yapistir", "kes", "kopyala"):
        assert pencere.eylemler[k] in bulunan, k
    assert any(a.text() == "Hücreleri Biçimlendir…" for a in bulunan)
    assert any(k.startswith("Koşullu") or "Veri Çubuğu" in k
               for k in (a.text() for a in bulunan))                      # koşullu biçim menüsü Stiller'de


def test_eski_menulerdeki_eylemler_dosya_dahil_seritten_erisilir(pencere):
    bulunan = set(map(id, pencere.serit.eylemler()))
    for sozluk in (pencere.duzen_eylemleri, pencere.veri_eylemleri):
        for k in ("bul", "artan", "ozel_sirala", "filtre"):
            if k in sozluk:
                assert id(sozluk[k]) in bulunan, k
    for k, a in pencere.eylemler.items():
        if k.startswith("dosya."):
            assert id(a) in bulunan, k                                   # Dosya sekmesi menüsü


def test_dugmeler_odagi_izgaradan_almaz(pencere):
    g = pencere.izgara()
    g.setFocus()
    for d in pencere.bicim_cubugu.findChildren(QToolButton):
        assert d.focusPolicy().name == "NoFocus", d.objectName() or d.toolTip()


def test_not_ve_filtre_eylem_durumu_etkin_hucreyi_izler(pencere):
    g = pencere.izgara()
    g.sec((1, 1))
    pencere._arayuzu_guncelle()
    assert not pencere.eylemler["notu_sil"].isEnabled()
    assert pencere.eylemler["yeni_not"].text() == "Yeni Not"
    g.not_yaz({(1, 1): Not("deneme", "Ata")})
    pencere._arayuzu_guncelle()
    assert pencere.eylemler["notu_sil"].isEnabled()
    assert pencere.eylemler["yeni_not"].text() == "Notu Düzenle"
    assert not pencere.eylemler["filtre"].isChecked()
    pencere.filtre_ac_kapat()
    assert pencere.eylemler["filtre"].isChecked()
    pencere.filtre_ac_kapat()
    assert not pencere.eylemler["filtre"].isChecked()


def test_giris_sekmesi_sayfa_degisince_etkin_sayfaya_gore_esitlenir(pencere):
    pencere.sayfa_ekle()
    pencere.eylemler["kilavuz"].setChecked(False)
    assert pencere.izgara().sayfa.kilavuz is False
    pencere.sekmeler.setCurrentIndex(0)
    assert pencere.eylemler["kilavuz"].isChecked()                       # ilk sayfa değişmedi
