"""Faz 4 / 4c: CSV'nin Dosya menüsüne bağlanması (aç, önizleme penceresi, kaydet)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere


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


def yeni_pencere():
    p = Pencere(CalismaKitabi())
    p.show()
    return p


def _csv(yol, icerik="Ad;Tutar\nçay;12,5\n", kodlama="utf-8-sig"):
    yol.write_bytes(icerik.encode(kodlama))
    return str(yol)


def test_csv_ac_yeni_pencerede_xlsx_onerir(tmp_path, monkeypatch):
    yol = _csv(tmp_path / "satis.csv")
    p = yeni_pencere()
    monkeypatch.setattr(DosyaIslemleri, "_csv_ayarlari",
                        lambda self, y: ([["Ad", "Tutar"], ["çay", "12,5"]], False))
    q = p.dosya_ac(yol)
    assert q.kitap.sayfalar[0].ad == "satis" and q.izgara().sayfa.deger(2, 2) == 12.5
    assert q.yol is None and q.belge_adi == "satis.csv" and not q.degisti_mi()
    gorulen = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a, **k: gorulen.append(a[2]) or ("", ""))
    assert not q.kaydet()                                  # yol yok → Farklı Kaydet; öneri .xlsx
    assert gorulen[0].endswith("satis.xlsx")


def test_csv_iptal(tmp_path, monkeypatch):
    yol = _csv(tmp_path / "a.csv")
    p = yeni_pencere()
    monkeypatch.setattr(DosyaIslemleri, "_csv_ayarlari", lambda self, y: None)
    assert p.dosya_ac(yol) is None and p.isVisible()


def test_csv_penceresi_gercek_onizleme():
    from tabcel.ui.csv_penceresi import CsvAlmaPenceresi
    veri = "Şehir;Not\nİzmir;5\nAğrı;7\n".encode("cp1254")
    d = CsvAlmaPenceresi("x.csv", veri)
    assert d.secili_kodlama() == "cp1254" and d.secili_ayrac() == ";"
    assert d.tablo.rowCount() == 3 and d.tablo.item(1, 0).text() == "İzmir"
    d.ayrac.setCurrentIndex(d.ayrac.findData(","))          # yanlış ayraç: tek sütun
    assert d.tablo.columnCount() == 1
    d.ayrac.setCurrentIndex(d.ayrac.findData(";"))
    d.metin_olarak.setChecked(True)
    assert d.satirlar()[2] == ["Ağrı", "7"] and d.metin_olarak_mi()
    d.kodlama.setCurrentIndex(d.kodlama.findData("utf-8"))  # yanlış kodlama bozuk karakter gösterir, çökmez
    assert d.tablo.rowCount() == 3


def test_csv_olarak_kaydet(tmp_path, monkeypatch):
    p = yeni_pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "Ali; Veli")
    g.hucre_gir(2, 1, "1,5")
    hedef = str(tmp_path / "cikti.csv")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    assert p.kaydet() and p.yol == hedef and not p.degisti_mi()
    assert open(hedef, encoding="utf-8-sig", newline="").read() == '"Ali; Veli"\r\n1,5\r\n'
    g.hucre_gir(3, 1, "x")
    assert p.kaydet() and open(hedef, encoding="utf-8-sig", newline="").read().endswith("x\r\n")   # yol var: tekrar csv


def test_csv_filtresiyle_uzantisiz_kaydet(tmp_path, monkeypatch):
    p = yeni_pencere()
    p.izgara().hucre_gir(1, 1, "a")
    hedef = str(tmp_path / "isimsiz")
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a, **k: (hedef, "CSV (Noktalı virgülle ayrılmış) (*.csv)"))
    assert p.kaydet() and p.yol.endswith("isimsiz.csv") and os.path.exists(hedef + ".csv")


def test_csv_cok_sayfa_uyarisi(tmp_path, monkeypatch):
    p = yeni_pencere()
    p.izgara().hucre_gir(1, 1, "a")
    p.sayfa_ekle()
    hedef = str(tmp_path / "c.csv")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    monkeypatch.setattr(DosyaIslemleri, "_csv_cok_sayfa_sorusu", lambda self: False)
    assert not p.kaydet() and not os.path.exists(hedef) and p.degisti_mi()
    monkeypatch.setattr(DosyaIslemleri, "_csv_cok_sayfa_sorusu", lambda self: True)
    assert p.kaydet() and os.path.exists(hedef)


def test_ayni_csv_iki_kez_acilmaz(tmp_path, monkeypatch):
    yol = _csv(tmp_path / "a.csv")
    monkeypatch.setattr(DosyaIslemleri, "_csv_ayarlari", lambda self, y: ([["x"]], False))
    q = yeni_pencere().dosya_ac(yol)
    assert q.dosya_ac(yol) is q


def test_gercek_csv_penceresi_yolu(tmp_path, monkeypatch):
    """Önizleme penceresi `exec` yamalanıp Tamam'a basılmış gibi: dosya → kitap tüm zinciri."""
    from PySide6.QtWidgets import QDialog
    from tabcel.ui import csv_penceresi
    yol = _csv(tmp_path / "t.csv", "Ürün;Fiyat\nŞeker;8,25\n", "cp1254")
    monkeypatch.setattr(csv_penceresi.CsvAlmaPenceresi, "exec", lambda self: QDialog.Accepted)
    q = yeni_pencere().dosya_ac(yol)
    s = q.izgara().sayfa
    assert s.deger(2, 1) == "Şeker" and s.deger(2, 2) == 8.25
