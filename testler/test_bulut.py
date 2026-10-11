"""Faz 7a: Google Drive / OneDrive (eşitleme klasörü üzerinden) — bulut klasörü tanıma, dışarıdan değişiklik
izleme, Google biçimli dosya, Dosya menüsü girişleri, açık dosya başka yerde değişince yeniden yükleme."""
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tabcel.io import bulut
from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.bulut_islemleri import BulutIslemleri
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere


# ---------------------------------------------------------------- Qt'siz: io/bulut.py
@pytest.fixture
def onedrive(tmp_path, monkeypatch):
    kok = tmp_path / "OneDrive"
    kok.mkdir()
    monkeypatch.setenv("OneDrive", str(kok))
    monkeypatch.delenv("OneDriveConsumer", raising=False)
    monkeypatch.delenv("OneDriveCommercial", raising=False)
    monkeypatch.setattr(bulut, "_google_drive_folders", lambda: [])
    bulut.cloud_folders(refresh=True)
    yield kok
    monkeypatch.undo()
    bulut.cloud_folders(refresh=True)


def test_onedrive_klasoru_taninir(onedrive):
    assert [(k.provider, k.path) for k in bulut.cloud_folders()] == [(bulut.ONEDRIVE, onedrive)]
    assert bulut.provider_for(onedrive / "alt" / "a.xlsx") == bulut.ONEDRIVE
    assert bulut.provider_for(onedrive.parent / "baska" / "a.xlsx") is None
    assert bulut.provider_for(None) is None


def test_olmayan_klasor_yok_sayilir(tmp_path, monkeypatch):
    monkeypatch.setenv("OneDrive", str(tmp_path / "yok"))
    monkeypatch.delenv("OneDriveConsumer", raising=False)
    monkeypatch.delenv("OneDriveCommercial", raising=False)
    monkeypatch.setattr(bulut, "_google_drive_folders", lambda: [])
    assert bulut.cloud_folders(refresh=True) == []
    monkeypatch.undo()
    bulut.cloud_folders(refresh=True)


def test_google_bicimi():
    assert bulut.is_google_format("x/Butce.gsheet") and bulut.is_google_format("a.GDOC")
    assert not bulut.is_google_format("a.xlsx")
    assert bulut.google_search_url("x/Bütçe 2026.gsheet").endswith("q=B%C3%BCt%C3%A7e%202026")


def test_izleyici_dis_degisiklik(tmp_path):
    d = tmp_path / "a.xlsx"
    d.write_bytes(b"bir")
    t = bulut.ChangeTracker()
    t.track(d)
    assert not t.changed()
    d.write_bytes(b"iki!")
    assert t.changed() and t.conflict
    assert not t.changed()                                   # karar verilene dek yeniden bildirmez
    t.remember()
    assert not t.conflict and not t.changed()


def test_izleyici_ayni_icerik_degisiklik_sayilmaz(tmp_path):
    d = tmp_path / "a.xlsx"
    d.write_bytes(b"ayni")
    t = bulut.ChangeTracker()
    t.track(d)
    os.utime(d, ns=(time.time_ns() + 5_000_000_000,) * 2)    # eşitleme uygulaması yalnız tarihi değiştirdi
    assert not t.changed()


def test_izleyici_dosya_gecici_yoksa_silinme_sayilmaz(tmp_path):
    d = tmp_path / "a.xlsx"
    d.write_bytes(b"x")
    t = bulut.ChangeTracker()
    t.track(d)
    d.unlink()
    assert not t.changed()
    assert not bulut.ChangeTracker().changed()               # izlenen dosya yok


# ---------------------------------------------------------------- arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _temiz(app, monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: QMessageBox.Ok)
    yield
    for p in list(DosyaIslemleri._tutulan):
        p.degisti_mi = lambda: False
        p.close()
    DosyaIslemleri._tutulan.clear()


def _xlsx(yol, deger=5):
    wb = Workbook()
    wb.active["A1"] = deger
    wb.save(yol)
    return str(yol)


def _yeni():
    p = Pencere(CalismaKitabi())
    p.show()
    return p


def test_menude_bulut_girisleri_klasore_gore_gorunur(onedrive):
    p = _yeni()
    p._bulut_eylemlerini_guncelle(True)
    durum = {(s, t): e.isVisible() for s, t, e in p._bulut_eylem_listesi}
    assert durum[(bulut.ONEDRIVE, "ac")] and durum[(bulut.ONEDRIVE, "kaydet")]
    assert not durum[(bulut.GOOGLE, "ac")] and not durum[(bulut.GOOGLE, "kaydet")]
    assert "dosya.bulut_ac_onedrive" in p.eylemler


def test_bulut_klasorune_kaydet_ve_izle(onedrive, monkeypatch):
    hedef = str(onedrive / "kitap.xlsx")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    p = _yeni()
    p.izgara().hucre_gir(1, 1, "7")
    assert p._bulutta(bulut.ONEDRIVE, "kaydet") is True
    assert p.yol == os.path.abspath(hedef) and os.path.exists(hedef)
    assert p._izleyici.path is not None and not p._izleyici.changed()


def test_bulut_klasorunden_ac(onedrive, monkeypatch):
    yol = _xlsx(onedrive / "a.xlsx", 9)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (yol, ""))
    q = _yeni()._bulutta(bulut.ONEDRIVE, "ac")
    assert q.izgara().sayfa.deger(1, 1) == 9.0 and q._izleyici.path is not None


def test_klasor_yoksa_iletisi(onedrive, monkeypatch):
    iletiler = []
    monkeypatch.setattr(QMessageBox, "information", lambda w, b, m, *a: iletiler.append(m))
    assert _yeni()._bulutta(bulut.GOOGLE, "ac") is None
    assert iletiler and "Google Drive" in iletiler[0]


def test_dis_degisiklik_degisiklik_yoksa_sessiz_yeniden_yukler(tmp_path):
    yol = _xlsx(tmp_path / "a.xlsx", 1)
    q = _yeni().dosya_ac(yol)
    time.sleep(0.02)
    _xlsx(tmp_path / "a.xlsx", 2)                            # başka yerde değişti
    q._dis_degisiklik_denetle()
    yeniler = [p for p in DosyaIslemleri._acik_pencereler if p is not q and p.yol == q.yol]
    assert len(yeniler) == 1 and yeniler[0].izgara().sayfa.deger(1, 1) == 2.0
    assert not q.isVisible()


def test_dis_degisiklik_yerel_degisiklik_varsa_sorar(tmp_path, monkeypatch):
    yol = _xlsx(tmp_path / "a.xlsx", 1)
    q = _yeni().dosya_ac(yol)
    q.izgara().hucre_gir(2, 2, "benim")
    time.sleep(0.02)
    _xlsx(tmp_path / "a.xlsx", 3)
    sorular = []
    monkeypatch.setattr(BulutIslemleri, "_dis_degisiklik_sorusu", lambda self: sorular.append(1) or "koru")
    q._dis_degisiklik_denetle()
    assert sorular == [1] and q.isVisible() and q.izgara().sayfa.deger(1, 1) == 1.0
    q._dis_degisiklik_denetle()                              # "koru" dedi: aynı değişiklik için yeniden sormaz
    assert sorular == [1]


def test_dis_degisiklik_onlarin_surumunu_yukle(tmp_path, monkeypatch):
    yol = _xlsx(tmp_path / "a.xlsx", 1)
    q = _yeni().dosya_ac(yol)
    q.izgara().hucre_gir(2, 2, "benim")
    time.sleep(0.02)
    _xlsx(tmp_path / "a.xlsx", 4)
    monkeypatch.setattr(BulutIslemleri, "_dis_degisiklik_sorusu", lambda self: "yukle")
    q._dis_degisiklik_denetle()
    yeni = next(p for p in DosyaIslemleri._acik_pencereler if p is not q and p.yol == q.yol)
    assert yeni.izgara().sayfa.deger(1, 1) == 4.0 and not q.isVisible()


def test_gsheet_acilmaz_tarayicida_aranir(tmp_path, monkeypatch):
    d = tmp_path / "Butce.gsheet"
    d.write_text("{}")
    acilan = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: acilan.append(self.text()) or 0)
    p = _yeni()
    assert p.dosya_ac(str(d)) is None and acilan and "Google" in acilan[0]
