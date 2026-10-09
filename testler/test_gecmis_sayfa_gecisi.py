"""6f: geri al/yinele yalnız asıl değişikliğin sayfasına geçer; başka sayfalardaki formül
düzeltmeleri (yan etki) geçiş yaptırmaz."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.model.komutlar import (Grup, HucrelerDegis, HucreTasi, SatirEkleSil, ana_sayfa)
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import window
from tabcel.ui.grid import Izgara
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch):
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: None)
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    k.sayfa_ekle()
    k.sayfa_ekle()
    s1, s2, s3 = k.sayfalar[:3]
    for r in range(1, 6):
        s1.ata(r, 1, Hucre(float(r)))
    s2.ata(1, 1, Hucre(None, f"=[{s1.kimlik}]!A5"))          # Sayfa2 formülü Sayfa1'e başvurur
    p = Pencere(k)
    p.show()
    p.sekmeler.setCurrentIndex(0)
    return p


def sayfa_no(p):
    return p.kitap.sayfalar.index(p._secili_sayfa)


def test_satir_ekle_geri_al_asil_sayfaya_gider(pencere):
    k = pencere.kitap
    pencere.yigin.calistir(SatirEkleSil(k.sayfalar[0], 2, 1, True))
    assert k.sayfalar[1].hucre(1, 1).formul == f"=[{k.sayfalar[0].kimlik}]!A6"
    pencere.sekmeler.setCurrentIndex(2)                       # kullanıcı Sayfa3'e geçti
    pencere.izgara().geri_al()
    assert sayfa_no(pencere) == 0                             # değişikliğin yapıldığı sayfaya
    pencere.sekmeler.setCurrentIndex(2)
    pencere.izgara().yinele()
    assert sayfa_no(pencere) == 0


def test_yan_etki_baska_sayfaya_gecirmez(pencere):
    """Sayfa1'deyken satır eklemeyi geri al: Sayfa2'deki formül düzeltmesi pencereyi Sayfa2'ye götürmez."""
    k = pencere.kitap
    pencere.yigin.calistir(SatirEkleSil(k.sayfalar[0], 2, 1, True))
    assert sayfa_no(pencere) == 0
    pencere.izgara().geri_al()
    assert sayfa_no(pencere) == 0
    pencere.izgara().yinele()
    assert sayfa_no(pencere) == 0


def test_kes_yapistir_geri_al_kaynak_yinele_hedef(pencere):
    k = pencere.kitap
    s1, s2, s3 = k.sayfalar[:3]
    pencere.yigin.calistir(HucreTasi(s1, (1, 1, 2, 1), s3, (1, 1)))     # Sayfa1 → Sayfa3
    pencere.sekmeler.setCurrentIndex(1)
    pencere.izgara().geri_al()
    assert sayfa_no(pencere) == 0                              # geri alırken kaynak
    pencere.izgara().yinele()
    assert sayfa_no(pencere) == 2                              # yinelerken hedef


def test_ana_sayfa_komut_turleri(pencere):
    s1, s2 = pencere.kitap.sayfalar[:2]
    assert ana_sayfa(HucrelerDegis(s2, {})) is s2
    assert ana_sayfa(Grup([HucrelerDegis(s1, {}), HucrelerDegis(s2, {})])) is s1
    assert ana_sayfa(None) is None
