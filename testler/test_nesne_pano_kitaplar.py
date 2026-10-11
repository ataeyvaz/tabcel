"""Opus gözden geçirmesi (Faz 6): nesne panosu iki çalışma kitabı arasında yanlış veri / karışık geri al üretmez."""
import io
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.model.adres import Aralik
from tabcel.model.grafik import Grafik, Konum, Referans, Resim, Seri
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _kitap_penceresi(deger):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre(float(deger)))
    p = Pencere(k)
    p.resize(900, 700)
    p.show()
    QApplication.processEvents()
    return p


@pytest.fixture
def iki(app, monkeypatch):
    for ad in ("warning", "information", "critical"):          # `Pencere._uyari` modal kutu açar
        monkeypatch.setattr(QMessageBox, ad, lambda *a, **k: QMessageBox.Ok)
    Izgara._nesne_panosu = None
    a, b = _kitap_penceresi(1), _kitap_penceresi(999)
    yield a, b
    Izgara._nesne_panosu = None
    for p in (a, b):
        p.degisti_mi = lambda: False
        p.close()


def _grafik(sayfa):
    return Grafik(seriler=(Seri(deger=Referans(sayfa.kimlik, Aralik(1, 1, 1, 1))),), konum=Konum(3, 3))


def _png():
    b = io.BytesIO()
    Image.new("RGB", (40, 30), (255, 0, 0)).save(b, "PNG")
    return b.getvalue()


def _uyarilar(g):
    l = []
    g.uyari.connect(l.append)                                  # pencerenin kutusundan bağımsız, sinyali yakalar
    return l


@pytest.mark.parametrize("kes", [False, True])
def test_grafik_baska_kitaba_yapistirilmaz(iki, kes):
    a, b = iki
    ga, gb = a.izgara(), b.izgara()
    kimlik = ga.nesne_ekle(_grafik(ga.sayfa))
    ga.nesne_sec(kimlik)
    assert ga.nesne_kopyala(kes)
    uy = _uyarilar(gb)
    assert gb.nesne_yapistir() is False
    assert gb.sayfa.nesneler == [] and uy and "başka bir çalışma kitabına" in uy[0]
    assert len(ga.sayfa.nesneler) == 1                         # kaynak yerinde
    assert not b.yigin.geri_alinabilir()                       # B'nin geri al yığınına bir şey girmedi
    assert Izgara._nesne_panosu is not None                    # pano korunur: aynı kitaba yapıştırılabilir


def test_grafik_ayni_kitapta_baska_sayfaya_yine_yapisir(iki):
    a, _ = iki
    ga = a.izgara()
    kimlik = ga.nesne_ekle(_grafik(ga.sayfa))
    ga.nesne_sec(kimlik)
    ga.nesne_kopyala(False)
    a.kitap.sayfa_ekle()
    assert ga.nesne_yapistir() is True and len(ga.sayfa.nesneler) == 2


@pytest.mark.parametrize("kes", [False, True])
def test_resim_baska_kitaba_kopya_olarak_yapisir_kaynak_degismez(iki, kes):
    a, b = iki
    ga, gb = a.izgara(), b.izgara()
    kimlik = ga.nesne_ekle(Resim(veri=_png(), konum=Konum(2, 2)))
    ga.nesne_sec(kimlik)
    a_geri_al_once = a.yigin.geri_alinabilir()
    assert ga.nesne_kopyala(kes)
    assert gb.nesne_yapistir() is True
    assert len(gb.sayfa.nesneler) == 1 and isinstance(gb.sayfa.nesneler[0], Resim)
    assert len(ga.sayfa.nesneler) == 1                         # kes bile olsa kaynak silinmez (iki yığın karışmaz)
    assert a.yigin.geri_alinabilir() == a_geri_al_once
    b.yigin.geri_al()                                          # B'deki yapıştırma B'de geri alınır
    assert gb.sayfa.nesneler == []
