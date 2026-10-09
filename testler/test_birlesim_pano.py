"""Faz 3 / 3f: birleşik hücreler panoda — kopyala/yapıştır göreli taşır, kes-yapıştır (HucreTasi) taşır."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model import pano
from tabcel.model.adres import Aralik
from tabcel.model.komutlar import GeriAlYigini, HucreTasi, birlesim_komutu
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere


def A(r1, c1, r2, c2):
    return Aralik(r1, c1, r2, c2)


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def kitap():
    return CalismaKitabi()


# ------------------------------------------------------------------ Qt'siz model
def test_pano_verisi_tam_kapsanan_birlesimi_alir(kitap):
    s = kitap.sayfalar[0]
    s.birlesimleri_yaz([A(2, 2, 3, 4), A(6, 1, 7, 1)], [])
    v = pano.pano_verisi_al(s, A(2, 2, 4, 5))
    assert v.birlesimler == [(0, 0, 2, 3)]                 # yalnız tamamı içeride olan
    v2 = pano.PanoVerisi.json_oku(v.json_yaz())
    assert v2.birlesimler == [(0, 0, 2, 3)]
    assert pano.PanoVerisi.json_oku('{"s":1,"c":1,"h":[]}').birlesimler == []     # eski JSON


def test_pano_araligi_bos_birlesimi_kirpmaz(kitap):
    s = kitap.sayfalar[0]
    s.ata(1, 1, Hucre("x"))
    s.birlesimleri_yaz([A(3, 3, 5, 5)], [])
    ar = pano.pano_araligi(s, A(1, 1, 10, 10))
    assert (ar.son_satir, ar.son_sutun) == (5, 5)


def test_yapistirma_birlesimleri_yinelemede_cogalir(kitap):
    s = kitap.sayfalar[0]
    s.birlesimleri_yaz([A(1, 1, 1, 2)], [])
    v = pano.pano_verisi_al(s, A(1, 1, 1, 2))
    assert pano.yapistirma_birlesimleri(v, 4, 4, None) == [A(4, 4, 4, 5)]
    assert pano.yapistirma_birlesimleri(v, 4, 4, A(4, 4, 6, 7)) == [
        A(4, 4, 4, 5), A(4, 6, 4, 7), A(5, 4, 5, 5), A(5, 6, 5, 7), A(6, 4, 6, 5), A(6, 6, 6, 7)]
    assert pano.yapistirma_birlesimleri(pano.PanoVerisi(1, 1), 1, 1, None) == []


def test_birlesim_kismen_kesiyor(kitap):
    s = kitap.sayfalar[0]
    s.birlesimleri_yaz([A(2, 2, 3, 3)], [])
    assert pano.birlesim_kismen_kesiyor(s, A(3, 3, 5, 5))
    assert not pano.birlesim_kismen_kesiyor(s, A(1, 1, 4, 4))
    assert not pano.birlesim_kismen_kesiyor(s, A(6, 6, 7, 7))


def test_hucre_tasi_birlesimi_tasir_ve_geri_alir(kitap):
    s = kitap.sayfalar[0]
    y = GeriAlYigini()
    s.ata(1, 1, Hucre("b"))
    y.calistir(birlesim_komutu(s, [A(1, 1, 2, 2)], "birlestir"))
    y.calistir(HucreTasi(s, (1, 1, 2, 2), s, (5, 4)))
    assert s.birlesimler == [A(5, 4, 6, 5)] and s.hucre(5, 4) == Hucre("b")
    y.geri_al()
    assert s.birlesimler == [A(1, 1, 2, 2)] and s.hucre(1, 1) == Hucre("b")
    y.yinele()
    assert s.birlesimler == [A(5, 4, 6, 5)]


def test_hucre_tasi_ust_uste_binen_alan(kitap):
    s = kitap.sayfalar[0]
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(s, [A(1, 1, 1, 2)], "birlestir"))
    y.calistir(HucreTasi(s, (1, 1, 2, 2), s, (2, 2)))        # kısmen kendi üstüne
    assert s.birlesimler == [A(2, 2, 2, 3)]
    y.geri_al()
    assert s.birlesimler == [A(1, 1, 1, 2)]


def test_hucre_tasi_hedefteki_eski_birlesim_kalkar(kitap):
    s = kitap.sayfalar[0]
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(s, [A(5, 5, 6, 6)], "birlestir"))
    s.ata(1, 1, Hucre("k"))
    y.calistir(HucreTasi(s, (1, 1, 1, 1), s, (5, 5)))         # tek hücre, hedefte birleşim var
    assert s.birlesimler == []
    y.geri_al()
    assert s.birlesimler == [A(5, 5, 6, 6)] and s.hucre(1, 1) == Hucre("k")


def test_hucre_tasi_sayfalar_arasi(kitap):
    s1 = kitap.sayfalar[0]
    s2 = kitap.sayfa_ekle()
    y = GeriAlYigini()
    y.calistir(birlesim_komutu(s1, [A(2, 2, 2, 4)], "birlestir"))
    y.calistir(HucreTasi(s1, (2, 2, 2, 4), s2, (1, 1)))
    assert s1.birlesimler == [] and s2.birlesimler == [A(1, 1, 1, 3)]
    y.geri_al()
    assert s1.birlesimler == [A(2, 2, 2, 4)] and s2.birlesimler == []


# ------------------------------------------------------------------ arayüz
@pytest.fixture
def pencere(app):
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    p = Pencere(k)
    p.resize(1000, 600)
    p.show()
    return p


def test_kopyala_yapistir_birlesimi_tasir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre("Ba"))
    g.sec((1, 1), (1, 3))
    g.birlestir("ortala", onayli=True)
    g.kopyala()
    g.sec((4, 2))
    g.yapistir()
    assert A(4, 2, 4, 4) in g.sayfa.birlesimler and A(1, 1, 1, 3) in g.sayfa.birlesimler
    assert g.sayfa.hucre(4, 2) == Hucre("Ba") and g.sayfa.stil(4, 2).yatay == "orta"
    g.geri_al()
    assert g.sayfa.birlesimler == [A(1, 1, 1, 3)] and g.sayfa.hucre(4, 2) is None


def test_yapistirma_eski_birlesimi_kaldirir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre(5.0))
    g.sec((6, 1), (7, 2))
    g.birlestir("birlestir", onayli=True)
    g.sec((1, 1))
    g.kopyala()
    g.sec((6, 1), (7, 2))                                     # birleşimin tamamına tek hücre yapıştır
    g.yapistir()
    assert g.sayfa.birlesimler == []
    g.geri_al()
    assert g.sayfa.birlesimler == [A(6, 1, 7, 2)]


def test_yapistirma_birlesimi_kismen_keserse_reddedilir(pencere, monkeypatch):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: QMessageBox.Ok)
    g = pencere.izgara()
    g.sec((3, 3), (4, 4))
    g.birlestir("birlestir", onayli=True)
    g.sayfa.ata(1, 1, Hucre("a"))
    g.sayfa.ata(1, 2, Hucre("b"))
    g.sec((1, 1), (1, 2))
    g.kopyala()
    g.sec((4, 2))                                             # (4,2)-(4,3): birleşimi kısmen keser
    g.yapistir()
    assert g.sayfa.birlesimler == [A(3, 3, 4, 4)] and g.sayfa.hucre(4, 2) is None


def test_kes_yapistir_birlesimi_tasir(pencere):
    g = pencere.izgara()
    g.sayfa.ata(1, 1, Hucre("t"))
    g.sec((1, 1), (2, 2))
    g.birlestir("birlestir", onayli=True)
    g.kes()
    g.sec((8, 5))
    g.yapistir()
    assert g.sayfa.birlesimler == [A(8, 5, 9, 6)] and g.sayfa.hucre(8, 5) == Hucre("t")
    g.geri_al()
    assert g.sayfa.birlesimler == [A(1, 1, 2, 2)]
