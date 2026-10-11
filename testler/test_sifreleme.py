"""Faz 8b: parolayla şifreli .xlsx — açma (parola sorma, yanlış parola), parolayla kaydetme, Parola Belirle/Kaldır,
otomatik kurtarma kopyasının şifreli belgeyi düz yazmaması."""
import io
import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication, QMessageBox

from tabcel.io import kurtarma, sifreleme, xlsx_io
from tabcel.io.xlsx_io import XlsxHatasi
from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere


def _paket(deger=5):
    wb = Workbook()
    wb.active["A1"] = deger
    wb.active["B1"] = "gizli metin"
    t = io.BytesIO()
    wb.save(t)
    return t.getvalue()


def _sifreli_dosya(yol, parola="p4rola", deger=5):
    yol.write_bytes(sifreleme.sifrele(_paket(deger), parola))
    return str(yol)


# ---------------------------------------------------------------- Qt'siz
def test_sifrele_coz_gidis_donus_ve_tanima(tmp_path):
    paket = _paket()
    veri = sifreleme.sifrele(paket, "şifre-ğüş")                   # Türkçe karakterli parola
    assert veri[:4] == b"\xd0\xcf\x11\xe0" and b"gizli metin" not in veri
    assert sifreleme.coz(veri, "şifre-ğüş").getvalue() == paket
    assert sifreleme.dogrula(veri, "şifre-ğüş", paket) and not sifreleme.dogrula(veri, "baska", paket)
    d = tmp_path / "a.xlsx"
    d.write_bytes(veri)
    assert sifreleme.sifreli_mi(str(d))
    d.write_bytes(paket)
    assert not sifreleme.sifreli_mi(str(d)) and not sifreleme.sifreli_mi(str(tmp_path / "yok.xlsx"))


def test_yanlis_parola_ve_bozuk_veri():
    veri = sifreleme.sifrele(_paket(), "dogru")
    with pytest.raises(sifreleme.YanlisParola):
        sifreleme.coz(veri, "yanlis")
    with pytest.raises(sifreleme.SifrelemeHatasi):
        sifreleme.coz(veri[:300], "dogru")


def test_xlsx_io_parolali_ac_kaydet(tmp_path):
    y = _sifreli_dosya(tmp_path / "s.xlsx", deger=7)
    with pytest.raises(XlsxHatasi, match="parola gerekir"):
        xlsx_io.ac(y)
    with pytest.raises(sifreleme.YanlisParola):
        xlsx_io.ac(y, "yanlis")
    k, r = xlsx_io.ac(y, "p4rola")
    assert k.sayfalar[0].deger(1, 1) == 7.0 and k.sayfalar[0].deger(1, 2) == "gizli metin"
    hedef = str(tmp_path / "yeni.xlsx")
    xlsx_io.kaydet(k, hedef, parola="yeni-parola")
    assert sifreleme.sifreli_mi(hedef) and b"gizli metin" not in open(hedef, "rb").read()
    k2, _ = xlsx_io.ac(hedef, "yeni-parola")
    assert k2.sayfalar[0].deger(1, 2) == "gizli metin"
    assert not [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]                  # geçici dosya kalmaz


def test_parolasiz_kayit_duz_xlsx(tmp_path):
    k, _ = xlsx_io.ac(os.path.join(os.path.dirname(__file__), "ornekler", "butce.xlsx"))
    hedef = str(tmp_path / "duz.xlsx")
    xlsx_io.kaydet(k, hedef)
    assert not sifreleme.sifreli_mi(hedef) and zipfile.is_zipfile(hedef)


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


def _yeni():
    p = Pencere(CalismaKitabi())
    p.show()
    return p


def test_acarken_parola_sorulur_yanlista_yeniden(tmp_path, monkeypatch):
    y = _sifreli_dosya(tmp_path / "s.xlsx", deger=9)
    cevaplar = iter(["yanlis", "p4rola"])
    sorular = []
    monkeypatch.setattr(DosyaIslemleri, "_parola_sor", lambda self, yol, yanlis=False: sorular.append(yanlis) or next(cevaplar))
    q = _yeni().dosya_ac(y)
    assert q.izgara().sayfa.deger(1, 1) == 9.0 and q.parola == "p4rola" and q.yol == os.path.abspath(y)
    assert sorular == [False, True]                                    # ikincisi "yanlış" ipucuyla


def test_parola_iptal_dosya_acilmaz(tmp_path, monkeypatch):
    y = _sifreli_dosya(tmp_path / "s.xlsx")
    monkeypatch.setattr(DosyaIslemleri, "_parola_sor", lambda self, yol, yanlis=False: None)
    p = _yeni()
    assert p.dosya_ac(y) is None and p.isVisible()


def test_kaydet_yeniden_sifreler_ve_kurtarma_yazilmaz(tmp_path, monkeypatch):
    y = _sifreli_dosya(tmp_path / "s.xlsx", deger=1)
    monkeypatch.setattr(DosyaIslemleri, "_parola_sor", lambda self, yol, yanlis=False: "p4rola")
    q = _yeni().dosya_ac(y)
    q.izgara().hucre_gir(2, 1, "yeni veri")
    assert q.degisti_mi() and q.otokayit_yap() is False                 # düz kurtarma kopyası yok
    assert not kurtarma.bekleyenler()
    assert q.kaydet()
    assert sifreleme.sifreli_mi(y) and b"yeni veri" not in open(y, "rb").read()
    k, _ = xlsx_io.ac(y, "p4rola")
    assert k.sayfalar[0].deger(2, 1) == "yeni veri"


def test_parola_belirle_ve_kaldir(tmp_path, monkeypatch):
    y = str(tmp_path / "d.xlsx")
    p = _yeni()
    p.izgara().hucre_gir(1, 1, "42")
    monkeypatch.setattr(DosyaIslemleri, "_parola_belirle_sorusu", lambda self: "yeni")
    assert p.parola_belirle() and p.parola == "yeni" and p.degisti_mi()
    assert not p.parola_belirle()                                      # aynı parola: değişiklik yok
    assert p._kaydet_yola(y) and sifreleme.sifreli_mi(y) and not p.degisti_mi()
    monkeypatch.setattr(DosyaIslemleri, "_parola_belirle_sorusu", lambda self: "")
    assert p.parola_belirle() and p.parola is None
    assert p._kaydet_yola(y) and not sifreleme.sifreli_mi(y) and zipfile.is_zipfile(y)
    monkeypatch.setattr(DosyaIslemleri, "_parola_belirle_sorusu", lambda self: None)
    assert not p.parola_belirle()


def test_parola_belirle_sorusu_eslesmeyen(monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    cevap = iter([("a", True), ("b", True)])
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: next(cevap))
    iletiler = []
    monkeypatch.setattr(QMessageBox, "warning", lambda w, b, m, *a: iletiler.append(m))
    assert _yeni()._parola_belirle_sorusu() is None and "eşleşmiyor" in iletiler[0]


def test_menude_parola_eylemi():
    p = _yeni()
    assert p.eylemler["dosya.parola"].text() == "Parola Belirle…" and p.eylemler["dosya.parola"] in p.dosya_menusu.actions()
