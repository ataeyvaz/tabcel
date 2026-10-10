"""Faz 5 / 5c: Sırala arayüzü (menü, A→Z/Z→A, uyarı, özel sıralama penceresi) — ekransız."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from tabcel.model.adres import Aralik
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.grid import Izgara
from tabcel.ui.sirala_penceresi import SiralaPenceresi
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    Izgara._pano_durumu = None
    k = CalismaKitabi()
    s = k.sayfalar[0]
    veri = [("Ad", "Puan"), ("Zeynep", 70.0), ("Çağla", 90.0), ("Ali", 80.0), ("Ömer", 90.0)]
    for r, (a, b) in enumerate(veri, start=1):
        s.ata(r, 1, Hucre(a))
        s.ata(r, 2, Hucre(b))
    p = Pencere(k)
    p.show()
    yield p
    p.hide()


def sutun(p, c, n=5):
    s = p.kitap.sayfalar[0]
    return [s.deger(r, c) for r in range(1, n + 1)]


def test_menu_eylemleri_acik(pencere):
    for ad in ("artan", "azalan", "ozel_sirala"):
        assert pencere.veri_eylemleri[ad].isEnabled()


def test_tek_hucre_artan_baslik_tahmini_ve_geri_al(pencere):
    g = pencere.izgara()
    g.sec((3, 1))
    assert pencere.sirala_hizli(True)
    assert sutun(pencere, 1) == ["Ad", "Ali", "Çağla", "Ömer", "Zeynep"]
    assert sutun(pencere, 2) == ["Puan", 80.0, 90.0, 90.0, 70.0]            # satırlar birlikte taşındı
    g.geri_al()
    assert sutun(pencere, 1) == ["Ad", "Zeynep", "Çağla", "Ali", "Ömer"]


def test_azalan_sayi_sutunu(pencere):
    g = pencere.izgara()
    g.sec((2, 2))
    assert pencere.sirala_hizli(False)
    assert sutun(pencere, 2) == ["Puan", 90.0, 90.0, 80.0, 70.0]
    assert sutun(pencere, 1) == ["Ad", "Çağla", "Ömer", "Ali", "Zeynep"]    # eşitlerde özgün sıra (kararlı)


def test_sutun_secimi_yaninda_veri_uyarisi(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((2, 2), (5, 2))                                  # yalnız Puan sütunu; yanında Ad var
    sorular = []
    monkeypatch.setattr(pencere, "_siralama_uyarisi", lambda: sorular.append(1) or False)
    assert pencere.sirala_hizli(True)
    assert sorular == [1]
    assert sutun(pencere, 2) == ["Puan", 70.0, 80.0, 90.0, 90.0]            # yalnız seçim sıralandı
    assert sutun(pencere, 1) == ["Ad", "Zeynep", "Çağla", "Ali", "Ömer"]    # Ad yerinde (uyarının nedeni)


def test_uyari_genislet_ve_iptal(pencere, monkeypatch):
    g = pencere.izgara()
    g.sec((2, 2), (5, 2))
    monkeypatch.setattr(pencere, "_siralama_uyarisi", lambda: None)
    assert pencere.sirala_hizli(True) is False
    assert sutun(pencere, 2) == ["Puan", 70.0, 90.0, 80.0, 90.0]            # değişmedi
    assert pencere.sirala_hizli(True, genislet=True)
    assert sutun(pencere, 1) == ["Ad", "Zeynep", "Ali", "Çağla", "Ömer"]


def test_birlesim_varsa_reddedilir(pencere, monkeypatch):
    s = pencere.kitap.sayfalar[0]
    s.birlesimleri_yaz([Aralik(3, 3, 4, 3)], [])
    s.ata(3, 3, Hucre("x"))
    g = pencere.izgara()
    g.sec((2, 2))
    ileti = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: ileti.append(a[2]))
    assert pencere.sirala_hizli(True) is False
    assert ileti and "aynı boyutta" in ileti[0]


def test_coklu_secim_reddedilir(pencere, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    ileti = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: ileti.append(a[2]))
    g = pencere.izgara()
    g.sec((1, 1), (2, 1))
    g._ekler.append(Aralik(4, 2, 5, 2))
    assert pencere.sirala_hizli(True) is False and "çoklu" in ileti[0]


def test_ozel_siralama_penceresi_duzeyler(pencere):
    s = pencere.kitap.sayfalar[0]
    pen = SiralaPenceresi(s, Aralik(1, 1, 5, 2), 2, None, baslik=True)
    assert pen.baslik() is True
    ilk = pen.anahtarlar()
    assert len(ilk) == 1 and ilk[0].sutun == 2 and ilk[0].artan
    assert pen.tablo.cellWidget(0, 0).currentText() == "Puan"               # başlık metni
    assert pen.tablo.cellWidget(0, 3).itemText(0) == "Küçükten Büyüğe"      # sayı sütunu
    pen.duzey_ekle()                                                       # kullanılmayan sütun: Ad
    assert [a.sutun for a in pen.anahtarlar()] == [2, 1]
    assert pen.tablo.cellWidget(1, 3).itemText(0) == "A'dan Z'ye"
    pen.tablo.cellWidget(0, 3).setCurrentIndex(1)                          # Puan azalan
    assert pen.anahtarlar()[0].artan is False
    pen.tablo.selectRow(1)
    pen.tasi(-1)
    assert [a.sutun for a in pen.anahtarlar()] == [1, 2] and pen.anahtarlar()[1].artan is False
    pen.tablo.selectRow(0)
    pen.duzey_kopyala()
    assert len(pen.anahtarlar()) == 3
    pen.duzey_sil()
    assert len(pen.anahtarlar()) == 2
    pen.baslik_kutusu.setChecked(False)
    assert pen.tablo.cellWidget(0, 0).currentText() == "Sütun A"


def test_ozel_siralama_en_cok_64_duzey(pencere):
    pen = SiralaPenceresi(pencere.kitap.sayfalar[0], Aralik(1, 1, 5, 2), 1, None, baslik=True)
    for _ in range(80):
        pen.duzey_ekle()
    assert pen.tablo.rowCount() == 64


def test_ozel_siralama_uygula_cok_duzey(pencere):
    s = pencere.kitap.sayfalar[0]
    pen = SiralaPenceresi(s, Aralik(1, 1, 5, 2), 2, None, baslik=True)
    pen.tablo.cellWidget(0, 3).setCurrentIndex(1)                          # Puan azalan
    pen.duzey_ekle(1)                                                      # sonra Ad artan
    pencere.izgara().sec((2, 2))
    assert pencere.sirala_ozel((pen.anahtarlar(), pen.baslik(), pen.buyuk_kucuk(), pen.yon()))
    assert sutun(pencere, 1) == ["Ad", "Çağla", "Ömer", "Ali", "Zeynep"]
    assert sutun(pencere, 2) == ["Puan", 90.0, 90.0, 80.0, 70.0]


def test_ozel_siralama_renk_secenekleri(pencere):
    from tabcel.model.komutlar import bicim_komutu
    from tabcel.model.stil import StilYama
    s = pencere.kitap.sayfalar[0]
    bicim_komutu(s, [Aralik(3, 2, 3, 2)], StilYama(dolgu="#FF0000")).yap()
    pen = SiralaPenceresi(s, Aralik(1, 1, 5, 2), 2, None, baslik=True)
    pen.tablo.cellWidget(0, 1).setCurrentIndex(1)                          # Hücre Rengi
    assert pen.tablo.cellWidget(0, 2).isEnabled() and pen.tablo.cellWidget(0, 2).itemData(0) == "#FF0000"
    assert pen.tablo.cellWidget(0, 3).itemText(0) == "Üstte"
    a = pen.anahtarlar()[0]
    assert a.olcut == "dolgu" and a.renk == "#FF0000" and a.artan


def test_sag_tik_menusunde_sirala(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    from PySide6.QtCore import QPoint
    r = g.hucre_dikdortgeni(2, 1)
    m = g.hucre_menusu(r.center())
    basliklar = [a.text() for a in m.actions()]
    assert "Sırala" in basliklar
