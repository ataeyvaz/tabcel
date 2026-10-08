import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tabcel import APP_NAME
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    for r in range(1, 6):
        s.ata(r, 1, Hucre(float(r)))
    s.ata(1, 2, Hucre("metin"))
    p = Pencere(k)
    p.show()
    return p


def test_baslik_ad_sabitinden(pencere):
    assert APP_NAME in pencere.windowTitle()
    assert pencere.windowTitle().startswith("Adsız")


def test_ad_kutusu_aktif_hucre(pencere):
    assert pencere.ad_kutusu.text() == "A1"
    pencere.izgara().sec((7, 3))
    assert pencere.ad_kutusu.text() == "C7"


def test_ad_kutusundan_git(pencere):
    pencere.ad_kutusu.setText("c7")
    pencere.ad_kutusu.returnPressed.emit()
    assert pencere.izgara().aktif == (7, 3)
    pencere.ad_kutusu.setText("A1:B3")
    pencere.ad_kutusu.returnPressed.emit()
    g = pencere.izgara()
    assert g.aktif == (1, 1) and (g.secim.son_satir, g.secim.son_sutun) == (3, 2)


def test_formul_cubugu_icerigi_gosterir(pencere):
    pencere.izgara().sec((2, 1))
    assert pencere.formul.text() == "2"
    pencere.izgara().sec((1, 2))
    assert pencere.formul.text() == "metin"
    pencere.izgara().sec((9, 9))
    assert pencere.formul.text() == ""


def test_formul_cubugundan_giris(pencere):
    g = pencere.izgara()
    g.sec((8, 1))
    pencere.formul.setText("=A1+A2")
    pencere.formul.onayla.emit(pencere.formul.text())
    assert g.sayfa.hucre(8, 1).formul == "=A1+A2"
    assert g.aktif == (9, 1)


def test_formul_cubugu_vazgec(pencere):
    g = pencere.izgara()
    g.sec((2, 1))
    pencere.formul.setText("zzz")
    pencere.formul.vazgec.emit()
    assert pencere.formul.text() == "2" and g.sayfa.deger(2, 1) == 2.0


def test_hucre_ici_duzenleme_formul_cubugunda_aynalanir(pencere):
    g = pencere.izgara()
    g.sec((8, 2))
    QTest.keyClicks(g, "a")
    QTest.keyClicks(g.focusWidget(), "bc")
    assert pencere.formul.text() == "abc"
    assert pencere.mod_etiketi.text() == "Gir"
    QTest.keyClick(g.focusWidget(), Qt.Key_Return)
    assert pencere.mod_etiketi.text() == "Hazır"
    assert pencere.formul.text() == ""          # aktif hücre artık (9,2)
    assert g.sayfa.deger(8, 2) == "abc"


def test_f2_modu(pencere):
    g = pencere.izgara()
    g.sec((1, 2))
    QTest.keyClick(g, Qt.Key_F2)
    assert pencere.mod_etiketi.text() == "Düzenle"
    g.duzenlemeyi_bitir(False)
    assert pencere.mod_etiketi.text() == "Hazır"


def test_durum_ozeti(pencere):
    g = pencere.izgara()
    assert pencere.ozet_etiketi.text() == ""           # tek hücre
    g.sec((1, 1), (5, 1))
    t = pencere.ozet_etiketi.text()
    assert "Ortalama: 3" in t and "Sayım: 5" in t and "Toplam: 15" in t
    g.sec((1, 1), (1, 2))                              # sayı + metin
    t = pencere.ozet_etiketi.text()
    assert "Sayım: 2" in t and "Toplam: 1" in t
    g.sec((20, 5), (21, 6))
    assert pencere.ozet_etiketi.text() == ""


def test_secim_boyutu_surukleme_sirasinda(pencere):
    g = pencere.izgara()
    g._surukleme = "hucre"
    g.sec((1, 1), (3, 2))
    assert pencere.ad_kutusu.text() == "3S x 2Sü"
    g._surukleme = None
    g.suruklemeBitti.emit()
    assert pencere.ad_kutusu.text() == "A1"


def test_sayfa_ekle_ve_gecis(pencere):
    pencere.sayfa_ekle()
    assert [s.ad for s in pencere.kitap.sayfalar] == ["Sayfa1", "Sayfa2"]
    assert pencere.sekmeler.count() == 2 and pencere.sekmeler.currentIndex() == 1
    assert pencere.izgara().sayfa.ad == "Sayfa2"
    pencere._sekme_git(1)                               # döngüsel
    assert pencere.sekmeler.currentIndex() == 0
    assert pencere.formul.text() == "1"


def test_yeniden_adlandir(pencere, monkeypatch):
    pencere.sayfa_yeniden_adlandir(0, "Bütçe")
    assert pencere.kitap.sayfalar[0].ad == "Bütçe"
    assert pencere.sekmeler.tabText(0) == "Bütçe"
    uyarilar = []
    from tabcel.ui import window
    monkeypatch.setattr(window.QMessageBox, "warning", lambda *a: uyarilar.append(a[2]))
    pencere.sayfa_yeniden_adlandir(0, "a/b")
    assert pencere.kitap.sayfalar[0].ad == "Bütçe" and uyarilar


def test_sayfa_sil(pencere, monkeypatch):
    from tabcel.ui import window
    pencere.sayfa_ekle()
    monkeypatch.setattr(window.QMessageBox, "question", lambda *a: window.QMessageBox.Yes)
    pencere.sayfa_sil(0)                                # dolu sayfa, onaylandı
    assert [s.ad for s in pencere.kitap.sayfalar] == ["Sayfa2"]
    assert pencere.sekmeler.count() == 1 and pencere.izgara().sayfa.ad == "Sayfa2"
    bilgi = []
    monkeypatch.setattr(window.QMessageBox, "information", lambda *a: bilgi.append(1))
    pencere.sayfa_sil(0)                                # son sayfa silinmez
    assert bilgi and len(pencere.kitap.sayfalar) == 1


def test_sayfa_sil_onay_reddedilirse(pencere, monkeypatch):
    from tabcel.ui import window
    pencere.sayfa_ekle()
    monkeypatch.setattr(window.QMessageBox, "question", lambda *a: window.QMessageBox.No)
    pencere.sayfa_sil(0)
    assert len(pencere.kitap.sayfalar) == 2


def test_sekme_surukleme_modeli_gunceller(pencere):
    pencere.sayfa_ekle()
    a, b = pencere.kitap.sayfalar
    pencere.sekmeler.moveTab(0, 1)
    assert pencere.kitap.sayfalar == [b, a]


def test_ortak_geri_al(pencere):
    pencere.sayfa_ekle()
    g2 = pencere.izgara()
    g2.sec((1, 1))
    g2.hucre_gir(1, 1, "x")
    assert g2.sayfa.deger(1, 1) == "x"
    pencere._sekme_git(1)
    pencere.izgara().geri_al()                          # ortak yığın
    assert g2.sayfa.deger(1, 1) is None


def test_yakinlastirma(pencere):
    g = pencere.izgara()
    pencere.yakin_kaydirici.setValue(150)
    assert g.yakinlastirma == 1.5 and pencere.yakin_etiketi.text() == "150%"
    g.yakinlastir(0.5)
    assert pencere.yakin_kaydirici.value() == 50 and pencere.yakin_etiketi.text() == "50%"
    g.yakinlastir(99)                                   # sınır
    assert g.yakinlastirma == 4.0
    r = g.hucre_dikdortgeni(1, 1)
    assert r is not None and r.height() >= 20 * 4 - 1


def test_ctrl_tekerlek_yakinlastirir(pencere):
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent
    g = pencere.izgara()
    olay = QWheelEvent(QPointF(100, 100), QPointF(100, 100), QPoint(0, 0), QPoint(0, 120),
                       Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(g.viewport(), olay)
    g.wheelEvent(olay)
    assert g.yakinlastirma > 1.0


def test_sekme_rengi(pencere):
    pencere.sekme_rengi_ata(0, "#ff0000")
    assert pencere.kitap.sayfalar[0].sekme_rengi == "#ff0000"
    assert pencere.sekmeler.tabData(0) == "#ff0000"
    assert not pencere.sekmeler.grab().isNull()                  # renkli şeritle çizim
    pencere.sekme_rengi_ata(0, None)
    assert pencere.kitap.sayfalar[0].sekme_rengi is None


def test_sekme_rengi_tasinan_sekmeyle_gider(pencere):
    pencere.sayfa_ekle()
    pencere.sekme_rengi_ata(0, "#00ff00")
    pencere.sekmeler.moveTab(0, 1)
    assert pencere.kitap.sayfalar[1].sekme_rengi == "#00ff00"
    assert pencere.sekmeler.tabData(1) == "#00ff00"


def test_sekme_menusu_rengi_kaldir_yalniz_renkliyse(pencere):
    d = pencere.sekmeler.tabRect(0).center()
    metinler = [a.text() for a in pencere.sekme_menusu_olustur(d).actions()]
    assert "Sekme rengini kaldır" not in metinler and "Sekme rengi…" in metinler
    pencere.sekme_rengi_ata(0, "#123456")
    metinler = [a.text() for a in pencere.sekme_menusu_olustur(d).actions()]
    assert "Sekme rengini kaldır" in metinler
