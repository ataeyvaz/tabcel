"""Faz 4 / 4b: Dosya menüsü — Yeni/Aç/Kaydet/Farklı Kaydet, değişti işareti, kapatırken sorma, veri kaybı
uyarısı, son dosyalar, komut satırı. Diyaloglar yamalanır (ekransız)."""
import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from openpyxl import Workbook, load_workbook
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tabcel.io import son_dosyalar
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


def _xlsx(yol, deger=5, ek=None):
    wb = Workbook()
    wb.active["A1"] = deger
    wb.active.title = "Veri"
    wb.save(yol)
    if ek:
        gecici = str(yol) + ".z"
        with zipfile.ZipFile(yol) as z, zipfile.ZipFile(gecici, "w") as o:
            for ad in z.namelist():
                o.writestr(ad, z.read(ad))
            o.writestr(ek, "<c/>")
        os.replace(gecici, yol)
    return str(yol)


def test_degisti_isareti_ve_baslik(tmp_path):
    p = yeni_pencere()
    assert not p.degisti_mi() and p.windowTitle() == "Adsız - Tabcel"
    p.izgara().hucre_gir(1, 1, "x")
    assert p.degisti_mi() and p.windowTitle() == "Adsız * - Tabcel"
    p.izgara().geri_al()                                   # kayıt noktasına dönüldü
    assert not p.degisti_mi() and p.windowTitle() == "Adsız - Tabcel"


def test_farkli_kaydet_ve_kaydet(tmp_path, monkeypatch):
    p = yeni_pencere()
    p.izgara().hucre_gir(1, 1, "42")
    hedef = str(tmp_path / "defter")                       # uzantısız: .xlsx eklenmeli
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    assert p.kaydet()                                      # yol yok → Farklı Kaydet
    assert p.yol == str(tmp_path / "defter.xlsx") and os.path.exists(p.yol)
    assert not p.degisti_mi() and p.belge_adi == "defter.xlsx"
    assert p.windowTitle() == "defter.xlsx - Tabcel"
    assert load_workbook(p.yol).active["A1"].value == 42
    p.izgara().hucre_gir(2, 1, "7")
    assert p.degisti_mi()
    assert p.kaydet() and not p.degisti_mi()               # yol var: diyalog yok
    assert load_workbook(p.yol).active["A2"].value == 7
    assert son_dosyalar.oku()[0] == p.yol


def test_farkli_kaydet_iptal(tmp_path, monkeypatch):
    p = yeni_pencere()
    p.izgara().hucre_gir(1, 1, "x")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    assert not p.kaydet() and p.yol is None and p.degisti_mi()


def test_ac_yeni_pencerede_ve_bos_pencere_kapanir(tmp_path):
    yol = _xlsx(tmp_path / "a.xlsx", 5)
    p = yeni_pencere()
    q = p.dosya_ac(yol)
    assert q is not p and q.yol == os.path.abspath(yol)
    assert q.izgara().sayfa.deger(1, 1) == 5.0 and q.kitap.sayfalar[0].ad == "Veri"
    assert not q.degisti_mi() and not p.isVisible()        # boş, değişmemiş pencere yerine açıldı


def test_dolu_pencere_kapanmaz(tmp_path):
    yol = _xlsx(tmp_path / "a.xlsx")
    p = yeni_pencere()
    p.izgara().hucre_gir(1, 1, "benim")
    q = p.dosya_ac(yol)
    assert p.isVisible() and q.isVisible() and q is not p


def test_ayni_dosya_iki_kez_acilmaz(tmp_path):
    yol = _xlsx(tmp_path / "a.xlsx")
    p = yeni_pencere()
    q = p.dosya_ac(yol)
    assert q.dosya_ac(yol) is q
    assert sum(1 for x in DosyaIslemleri._acik_pencereler if x.yol == q.yol) == 1


def test_ac_penceresi_diyalogdan(tmp_path, monkeypatch):
    yol = _xlsx(tmp_path / "a.xlsx", 9)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (yol, ""))
    q = yeni_pencere().ac_penceresi()
    assert q.izgara().sayfa.deger(1, 1) == 9.0
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
    assert yeni_pencere().ac_penceresi() is None


def test_bozuk_ve_eksik_dosya_iletisi(tmp_path, monkeypatch):
    iletiler = []
    monkeypatch.setattr(QMessageBox, "critical", lambda w, b, m, *a: iletiler.append(m))
    bozuk = tmp_path / "b.xlsx"
    bozuk.write_bytes(b"zip degil")
    p = yeni_pencere()
    assert p.dosya_ac(str(bozuk)) is None and p.dosya_ac(str(tmp_path / "yok.xlsx")) is None
    assert len(iletiler) == 2 and "bulunamadı" in iletiler[1]
    assert p.isVisible()                                   # hatada pencere kapanmaz


def test_veri_kaybi_bilgi_cubugu_ve_onay(tmp_path, monkeypatch):
    yol = _xlsx(tmp_path / "g.xlsx", ek="xl/charts/chart1.xml")
    p = yeni_pencere()
    q = p.dosya_ac(yol)
    assert q.rapor.veri_kaybi and q.bilgi_cubugu.isVisible() and "grafik" in q.bilgi_etiketi.text()
    q.izgara().hucre_gir(2, 1, "x")
    # İptal: dosya değişmez
    monkeypatch.setattr(DosyaIslemleri, "_veri_kaybi_sorusu", lambda self: "iptal")
    onceki = open(yol, "rb").read()
    assert not q.kaydet() and open(yol, "rb").read() == onceki
    # Farklı kaydet seçilirse özgün dosya yerinde kalır
    yeni = str(tmp_path / "kopya.xlsx")
    monkeypatch.setattr(DosyaIslemleri, "_veri_kaybi_sorusu", lambda self: "farkli")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (yeni, ""))
    assert q.kaydet() and open(yol, "rb").read() == onceki and os.path.exists(yeni)
    assert not q.rapor.veri_kaybi and not q.bilgi_cubugu.isVisible()
    assert q.yol == yeni


def test_yine_de_kaydet(tmp_path, monkeypatch):
    yol = _xlsx(tmp_path / "g.xlsx", ek="xl/charts/chart1.xml")
    q = yeni_pencere().dosya_ac(yol)
    q.izgara().hucre_gir(1, 1, "9")
    monkeypatch.setattr(DosyaIslemleri, "_veri_kaybi_sorusu", lambda self: "kaydet")
    assert q.kaydet()
    with zipfile.ZipFile(yol) as z:
        assert not any("charts" in n for n in z.namelist())   # grafik gerçekten çıktı (uyarılmıştı)
    assert load_workbook(yol).active["A1"].value == 9


@pytest.mark.parametrize("cevap,kapanir,kayit", [("kaydetme", True, False), ("iptal", False, False),
                                                  ("kaydet", True, True)])
def test_kapatirken_sorma(tmp_path, monkeypatch, cevap, kapanir, kayit):
    hedef = str(tmp_path / "k.xlsx")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    monkeypatch.setattr(DosyaIslemleri, "_kapatma_sorusu", lambda self: cevap)
    p = yeni_pencere()
    p.izgara().hucre_gir(1, 1, "x")
    olay = QCloseEvent()
    p.closeEvent(olay)
    assert olay.isAccepted() is kapanir
    assert os.path.exists(hedef) is kayit


def test_degismemis_pencere_sormadan_kapanir(monkeypatch):
    monkeypatch.setattr(DosyaIslemleri, "_kapatma_sorusu", lambda self: pytest.fail("sorulmamalıydı"))
    p = yeni_pencere()
    olay = QCloseEvent()
    p.closeEvent(olay)
    assert olay.isAccepted()


def test_son_dosyalar(tmp_path):
    a, b = _xlsx(tmp_path / "a.xlsx"), _xlsx(tmp_path / "b.xlsx")
    p = yeni_pencere()
    p.dosya_ac(a)
    p.dosya_ac(b)
    p.dosya_ac(a)                                          # öne çıkar, yinelenmez
    assert [os.path.basename(y) for y in son_dosyalar.oku()] == ["a.xlsx", "b.xlsx"]
    p.son_menusu.aboutToShow.emit()
    assert [x.text() for x in p.son_menusu.actions()] == ["a.xlsx", "b.xlsx"]
    for i in range(12):
        son_dosyalar.ekle(str(tmp_path / f"x{i}.xlsx"))
    assert len(son_dosyalar.oku()) == son_dosyalar.SINIR


def test_son_dosyalar_bozuk_json(tmp_path):
    from tabcel import veri_klasoru
    veri_klasoru().mkdir(parents=True, exist_ok=True)
    (veri_klasoru() / "son_dosyalar.json").write_text("{bozuk", encoding="utf-8")
    assert son_dosyalar.oku() == []


def test_sayfa_yapisi_gidis_donus_pencereden(tmp_path, monkeypatch):
    """Pencereden kaydedilen dosya yeniden açılınca aynı: biçim + formül + ikinci sayfa."""
    hedef = str(tmp_path / "t.xlsx")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (hedef, ""))
    p = yeni_pencere()
    g = p.izgara()
    g.hucre_gir(1, 1, "10")
    g.hucre_gir(2, 1, "=A1*3")
    p.sayfa_ekle()
    assert p.kaydet()
    q = p.dosya_ac(hedef)
    assert q is p                                          # aynı dosya zaten açık: o pencere
    assert [s.ad for s in p.kitap.sayfalar] == ["Sayfa1", "Sayfa2"]
