"""Faz 7: özelleştirilebilir Hızlı Erişim çubuğu — ekle/kaldır, kalıcılık, sağ tık menüsü."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QToolButton

from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui import hizli_erisim
from tabcel.ui.window import Pencere


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, monkeypatch, tmp_path):
    monkeypatch.setenv("TABCEL_VERI_KLASORU", str(tmp_path))
    p = Pencere(CalismaKitabi())
    p.show()
    yield p
    p.degisti_mi = lambda: False
    p.close()


def _dugmeler(p):
    return [b for b in p._hizli_kutu.findChildren(QToolButton)]


def test_ekle_kaldir_ve_kalicilik(pencere, tmp_path):
    assert _dugmeler(pencere) == []
    assert pencere.hizli_ekle("bul", "find32") and not pencere.hizli_ekle("bul")        # yinelenmez
    assert not pencere.hizli_ekle("olmayan_eylem")
    assert [b.property("hizliEylem") for b in _dugmeler(pencere)] == ["bul"]
    assert _dugmeler(pencere)[0].defaultAction() is pencere.eylemler["bul"]
    assert hizli_erisim.dosya_yolu() == tmp_path / "hizli_erisim.json" and hizli_erisim.dosya_yolu().exists()
    ikinci = Pencere(CalismaKitabi())                                                    # yeni pencere listeyi okur
    assert [b.property("hizliEylem") for b in _dugmeler(ikinci)] == ["bul"]
    ikinci.degisti_mi = lambda: False
    ikinci.close()
    assert pencere.hizli_kaldir("bul") and not pencere.hizli_kaldir("bul")
    assert _dugmeler(pencere) == [] and hizli_erisim.oku() == []


def test_bozuk_dosya_bos_liste(pencere):
    hizli_erisim.dosya_yolu().write_text("{bozuk", encoding="utf-8")
    assert hizli_erisim.oku() == []
    hizli_erisim.dosya_yolu().write_text('[{"eylem": 5}, "x", {"eylem": "bul", "ikon": "find32"}]', encoding="utf-8")
    assert hizli_erisim.oku() == [{"eylem": "bul", "ikon": "find32"}]


def test_bilinmeyen_eylem_acilista_atlanir(app, monkeypatch, tmp_path):
    monkeypatch.setenv("TABCEL_VERI_KLASORU", str(tmp_path))
    hizli_erisim.yaz([{"eylem": "yok_boyle_bir_sey", "ikon": None}, {"eylem": "git", "ikon": None}])
    p = Pencere(CalismaKitabi())
    assert [b.property("hizliEylem") for b in _dugmeler(p)] == ["git"]
    p.degisti_mi = lambda: False
    p.close()


def test_sinir(pencere):
    anahtarlar = [k for k in pencere.eylemler][:hizli_erisim.SINIR + 3]
    eklenen = sum(pencere.hizli_ekle(k) for k in anahtarlar)
    assert eklenen == hizli_erisim.SINIR and len(_dugmeler(pencere)) == hizli_erisim.SINIR


def test_sag_tik_menusu_ekler_ve_kaldirir(pencere, monkeypatch):
    sunulan = []
    monkeypatch.setattr(type(pencere), "_hizli_menu_goster",
                        lambda self, menu, konum: sunulan.append([a.text() for a in menu.actions()]) or menu.actions()[0].trigger())
    serit_dugmesi = next(b for b in pencere.serit.findChildren(QToolButton)
                         if b.objectName() == "seritDugme" and pencere.hizli_anahtar(b))
    anahtar = pencere.hizli_anahtar(serit_dugmesi)
    olay = QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(3, 3), QPoint(3, 3))
    assert QApplication.sendEvent(serit_dugmesi, olay) or True
    assert sunulan[-1] == [hizli_erisim.EKLE] and pencere.hizli_var_mi(anahtar)
    QApplication.sendEvent(serit_dugmesi, QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(3, 3), QPoint(3, 3)))
    assert sunulan[-1] == [hizli_erisim.KALDIR] and not pencere.hizli_var_mi(anahtar)       # varsa menüde Kaldır çıkar


def test_hizli_dugmeye_sag_tik_kaldir(pencere, monkeypatch):
    pencere.hizli_ekle("bul", "find32")
    sunulan = []
    monkeypatch.setattr(type(pencere), "_hizli_menu_goster",
                        lambda self, menu, konum: sunulan.append([a.text() for a in menu.actions()]) or menu.actions()[0].trigger())
    QApplication.sendEvent(_dugmeler(pencere)[0], QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(2, 2), QPoint(2, 2)))
    assert sunulan == [[hizli_erisim.KALDIR]] and _dugmeler(pencere) == []


def test_ilgisiz_dugme_menu_acmaz(pencere, monkeypatch):
    sunulan = []
    monkeypatch.setattr(type(pencere), "_hizli_menu_goster", lambda self, m, k: sunulan.append(1))
    pencere.kaydet_dugmesi and QApplication.sendEvent(
        pencere.kaydet_dugmesi, QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(2, 2), QPoint(2, 2)))
    assert sunulan == []
