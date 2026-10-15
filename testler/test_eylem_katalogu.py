"""Faz 5 / 5j-3: eylem kataloğu — her komut tek QAction; eski sözlükler aynı nesneleri gösterir."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere


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
    p.show()
    return p


def test_eski_sozlukler_katalogla_ayni_nesneler(pencere):
    e = pencere.eylemler
    for sozluk in (pencere.duzen_eylemleri, pencere.veri_eylemleri, pencere.gorunum_eylemleri):
        for k, a in sozluk.items():
            assert e[k] is a, k
    assert e["kilavuz"] is pencere.kilavuz_eylemi
    for k, a in pencere.kosullu_eylemleri.items():
        assert e["kosullu." + k] is a, k


def test_dosya_menusu_eylemleri_katalogda(pencere):
    dosya = {k for k in pencere.eylemler if k.startswith("dosya.")}
    assert dosya == {"dosya." + a for a in ("yeni", "ac", "kaydet", "farkli_kaydet", "sayfa_yapisi", "onizleme",
                                            "yazdir", "pdf_etkin", "pdf_tum", "cikis",
                                            "bulut_ac_google", "bulut_kaydet_google",         # Faz 7a (klasör yoksa gizli)
                                            "bulut_ac_onedrive", "bulut_kaydet_onedrive",
                                            "parola",                                        # Faz 8b
                                            "sablondan_yeni",                                # Faz 10d
                                            "kitaptan_sablon")}                              # Faz 11
    menu = pencere.dosya_menusu
    assert all(pencere.eylemler[k] in menu.actions() for k in dosya)


def test_seritteki_her_eylem_katalogda(pencere):
    katalog = set(map(id, pencere.eylemler.values()))
    bulunan = pencere.serit.eylemler()
    assert bulunan
    for a in bulunan:
        assert id(a) in katalog or a in pencere.bicim_cubugu.kenar_eylemleri.values()             or a in pencere.bicim_cubugu.birlestir_eylemleri.values(), a.text()


def test_eylemler_kisayol_tasimaz(pencere):
    """Aynı tuş eylemde ve QShortcut'ta olursa Qt 'belirsiz kısayol' verir: katalogda hiç kısayol yok."""
    for k, a in pencere.eylemler.items():
        assert a.shortcut().isEmpty(), k


def test_eylemler_etkin_sayfanin_izgarasina_calisir(pencere):
    g = pencere.izgara()
    g.sec((1, 1), (4, 1))
    pencere.eylemler["temizle_icerik"].trigger()
    assert all(pencere.izgara().sayfa.hucre(r, 1) is None for r in range(1, 5))
    pencere.eylemler["geri_al"].trigger()
    assert pencere.izgara().sayfa.hucre(2, 1) is not None
    pencere.eylemler["yinele"].trigger()
    assert pencere.izgara().sayfa.hucre(2, 1) is None


def test_satir_sutun_ve_sayfa_eylemleri(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.eylemler["satir_ekle"].trigger()
    assert g.sayfa.hucre(2, 1) is None and g.sayfa.hucre(3, 1).deger == 2.0     # 2. satırın üstüne boş satır
    pencere.eylemler["satir_sil"].trigger()
    assert g.sayfa.hucre(2, 1).deger == 2.0
    n = len(pencere.kitap.sayfalar)
    pencere.eylemler["sayfa_ekle"].trigger()
    assert len(pencere.kitap.sayfalar) == n + 1


def test_pano_ve_doldur_eylemleri(pencere):
    g = pencere.izgara()
    g.sec((1, 1), (1, 1))
    pencere.eylemler["kopyala"].trigger()
    g.sec((6, 1))
    pencere.eylemler["yapistir"].trigger()
    assert g.sayfa.hucre(6, 1).deger == 1.0
    g.sec((1, 1), (4, 1))
    pencere.eylemler["doldur_asagi"].trigger()
    assert all(g.sayfa.hucre(r, 1).deger == 1.0 for r in range(1, 5))


def test_kilavuz_eylemi_isaretli_ve_sayfaya_yazar(pencere):
    a = pencere.eylemler["kilavuz"]
    assert a.isCheckable() and a.isChecked()
    a.setChecked(False)
    assert pencere.izgara().sayfa.kilavuz is False
    a.setChecked(True)
    assert pencere.izgara().sayfa.kilavuz is True


def test_not_ve_siralama_eylemleri(pencere):
    g = pencere.izgara()
    g.sec((1, 1), (4, 1))
    pencere.eylemler["azalan"].trigger()
    assert [g.sayfa.hucre(r, 1).deger for r in range(1, 5)] == [4.0, 3.0, 2.0, 1.0]


def test_geri_yinele_dugmeleri_eylemi_kullanir(pencere):
    assert pencere.geri_dugmesi.defaultAction() is pencere.eylemler["geri_al"]
    assert pencere.yinele_dugmesi.defaultAction() is pencere.eylemler["yinele"]
    assert all(isinstance(a, QAction) for a in pencere.eylemler.values())
