"""Faz 9d: Paylaşım Temizleyici penceresi (ui/temizleyici_penceresi.py): donmadan tarama, tür eylemleri, tek tek işaretleme,
etkilenen formüller, özgün dosyaya yazma engeli, doğrulama. Yalnız sentetik veri (kural 19)."""
import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from sentetik import iban_uret, tc_uret
from tabcel.io import xlsx_io
from tabcel.model import kimlik, temizle
from tabcel.model.sayfa import CalismaKitabi, Hucre
from tabcel.ui import temizleyici_penceresi as tp
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere

TC = tc_uret()
IBAN = iban_uret()
EPOSTA = "ornek.kisi@ornek-sirket.com"


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pencere(app, tmp_path):
    k = CalismaKitabi()
    s = k.sayfalar[0]
    s.ata(1, 1, Hucre("Ad Soyad"))
    s.ata(2, 1, Hucre("Ayşe Örnek"))
    s.ata(2, 2, Hucre(TC))
    s.ata(3, 2, Hucre(IBAN))
    s.ata(4, 2, Hucre(f"mail: {EPOSTA}"))
    s.ata(5, 3, Hucre(None, "=SUM(C1:C2)"))
    s.ata(1, 3, Hucre(float(TC)))
    s.ata(6, 1, Hucre("tamamen temiz metin"))
    xlsx_io.kaydet(k, str(tmp_path / "ozgun.xlsx"))
    k2, _ = xlsx_io.ac(str(tmp_path / "ozgun.xlsx"))
    p = Pencere(k2)
    p.yol = str(tmp_path / "ozgun.xlsx")
    p.resize(1200, 700)
    p.show()
    yield p
    p.degisti_mi = lambda: False
    p.close()
    DosyaIslemleri._tutulan.clear()


def tara_bitir(d):
    d.tara()
    for _ in range(2000):
        if d._uretec is None:
            break
        QTest.qWait(5)
    assert d._uretec is None


def test_tarama_ve_tur_satirlari(pencere):
    d = tp.TemizleyiciPenceresi(pencere)
    tara_bitir(d)
    turler = {d.turler.topLevelItem(i).text(0): int(d.turler.topLevelItem(i).text(1)) for i in range(d.turler.topLevelItemCount())}
    assert turler["T.C. kimlik no"] == 2 and turler["IBAN"] == 1 and turler["E-posta"] == 1 and turler["Ad-soyad"] == 1
    assert d.olustur_dugmesi.isEnabled()
    assert "yasal" in tp.BASLIK_NOTU and "bilgisayarınızdan çıkmaz" in tp.BASLIK_NOTU
    # bulgu listesinde özgün değer gösterilmez, maskeli gösterilir
    tum = []
    for i in range(d.agac.topLevelItemCount()):
        ust = d.agac.topLevelItem(i)
        tum += [ust.child(j).text(1) for j in range(ust.childCount())]
    assert tum and all(TC not in t and IBAN not in t for t in tum)


def test_olustur_yazar_ve_ozgunu_bozmaz(pencere, tmp_path, monkeypatch):
    d = tp.TemizleyiciPenceresi(pencere)
    tara_bitir(d)
    d.plan.eylem[kimlik.AD] = temizle.BIRAK
    hedef = str(tmp_path / "temiz.xlsx")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (hedef, "")))
    mesajlar = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: mesajlar.append(a[2])))
    monkeypatch.setattr(tp.EtkilenenFormuller, "exec", lambda self: QDialog.Accepted)
    ozgun = open(pencere.yol, "rb").read()
    assert d.olustur() is True
    assert mesajlar and "Doğrulandı" in mesajlar[0]
    with zipfile.ZipFile(hedef) as z:
        butun = b"".join(z.read(a) for a in z.namelist()).decode("utf-8", "ignore")
    assert TC not in butun and IBAN not in butun and EPOSTA not in butun
    assert "Ayşe Örnek" in butun                                    # Ad için Bırak seçilmişti
    assert open(pencere.yol, "rb").read() == ozgun                  # özgün dosya baytı baytına aynı
    assert pencere.kitap.sayfalar[0].deger(2, 2) == TC               # açık kitap değişmedi


def test_ozgun_yola_yazma_engellenir(pencere, monkeypatch):
    d = tp.TemizleyiciPenceresi(pencere)
    tara_bitir(d)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (pencere.yol, "")))
    uyarilar = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: uyarilar.append(a[2])))
    monkeypatch.setattr(tp.EtkilenenFormuller, "exec", lambda self: QDialog.Accepted)
    ozgun = open(pencere.yol, "rb").read()
    assert d.olustur() is False
    assert uyarilar and "özgün" in uyarilar[0]
    assert open(pencere.yol, "rb").read() == ozgun


def test_tek_tek_isaret_kaldirma_haric_tutar(pencere):
    d = tp.TemizleyiciPenceresi(pencere)
    tara_bitir(d)
    ust = next(d.agac.topLevelItem(i) for i in range(d.agac.topLevelItemCount()) if d.agac.topLevelItem(i).text(0).startswith("E-posta"))
    ust.child(0).setCheckState(0, Qt.Unchecked)
    assert len(d.plan.haric) == 1
    ust.child(0).setCheckState(0, Qt.Checked)
    assert d.plan.haric == set()


def test_formul_etkisi_listesi_degere_cevir(pencere, app):
    k = pencere.kitap
    k.sayfalar[0].ata(7, 3, Hucre(None, "=C1+1"))                   # TC sayı → maskelenince #DEĞER!
    d = tp.TemizleyiciPenceresi(pencere)
    tara_bitir(d)
    tk = temizle.temiz_kopya(pencere.kitap, d.kayitlar, d.plan)
    try:
        e = tp.EtkilenenFormuller(tk.etkiler, tk.kitap)
        assert e.agac.topLevelItemCount() == len(tk.etkiler) >= 1
        satir = next(i for i, x in enumerate(tk.etkiler) if x.adres == "C7")
        assert e.agac.topLevelItem(satir).flags() & Qt.ItemIsUserCheckable
        e.agac.topLevelItem(satir).setCheckState(0, Qt.Checked)
        assert [x.adres for x in e.secilenler()] == ["C7"]
    finally:
        tk.kapat()


def test_maske_ayari_penceresi_onizleme(app):
    m = tp.MaskeAyariPenceresi(kimlik.TC, kimlik.MaskeAyari(3, 1, "#"))
    assert m.ayar() == kimlik.MaskeAyari(3, 1, "#") and m.onizleme.text().startswith("123#")


def test_serit_dugmesi_ve_eylem(pencere):
    assert "temizleyici" in pencere.eylemler
