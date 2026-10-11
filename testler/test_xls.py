"""Faz 8a: eski .xls okuma (xlrd). Örnek dosya gerçek Excel'de üretildi (araclar/xls_ornek_uret.ps1)."""
import os
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from tabcel.io import xls_io, xlsx_io
from tabcel.io.xlsx_io import XlsxHatasi
from tabcel.model.deger import Hata
from tabcel.model.sayfa import CalismaKitabi
from tabcel.ui.dosya_islemleri import DosyaIslemleri
from tabcel.ui.window import Pencere

ORNEK = os.path.join(os.path.dirname(__file__), "ornekler", "ornek.xls")


@pytest.fixture(scope="module")
def kitap():
    return xls_io.ac(ORNEK)


def test_sayfalar_ve_degerler(kitap):
    k, r = kitap
    assert [s.ad for s in k.sayfalar] == ["Satış", "İkinci"]
    s = k.sayfalar[0]
    assert [s.deger(1, c) for c in range(1, 5)] == ["Ürün", "Adet", "Fiyat", "Tarih"]
    assert [s.deger(2, c) for c in range(1, 4)] == ["Çay", 3.0, 12.5]
    assert s.deger(3, 1) == "Şeker" and s.deger(3, 2) == 10.0 and s.deger(3, 3) == 8.25
    assert s.deger(2, 4) == 46307.0                                    # 12.10.2026 seri sayısı
    assert s.deger(4, 1) is True
    assert s.deger(4, 2) == Hata("#DIV/0!") or getattr(s.deger(4, 2), "kod", None) == "#DIV/0!"
    assert s.deger(4, 3) == 37.5                                       # formül → son hesaplanan değer
    assert s.hucre(4, 3).formul is None
    assert s.deger(5, 1) is None


def test_bicim_birlesim_dondurma_not(kitap):
    k, _ = kitap
    s = k.sayfalar[0]
    b = s.stil(1, 1)
    assert b.kalin and b.dolgu and b.kenar.ust is not None and b.yazi_rengi is None      # siyah yazı varsayılan
    assert s.stil(2, 3).sayi_bicimi == "0.00" and s.stil(2, 4).sayi_bicimi.lower().startswith("dd")
    a = s.birlesim(6, 1)
    assert (a.ilk_satir, a.ilk_sutun, a.son_satir, a.son_sutun) == (6, 1, 6, 3)
    assert s.stil(6, 1).yatay == "orta"
    assert s.sutun_genislik[1] > s.sutun_genislik.get(2, 0) or 1 in s.sutun_genislik
    assert s.dondur == (2, 1)
    assert s.notlar[(2, 1)].metin == "Not metni"
    s2 = k.sayfalar[1]
    assert s2.stil(1, 1).italik and s2.stil(1, 1).yazi_rengi == "#FF0000"
    assert s2.deger(2, 1) == 0.15 and s2.stil(2, 1).sayi_bicimi == "0%"


def test_rapor_okunamayanlari_soyler(kitap):
    _, r = kitap
    assert len(r.uyarilar) == 1 and "formüller okunamaz" in r.uyarilar[0] and ".xlsx" in r.uyarilar[0]
    assert not r.veri_kaybi


def test_xlsx_ve_xls_ayni_veri(tmp_path, kitap):
    """.xls'den okunan kitap .xlsx'e kaydedilip açılınca değerler aynı kalır."""
    k, _ = kitap
    hedef = str(tmp_path / "cikti.xlsx")
    xlsx_io.kaydet(k, hedef)
    k2, _ = xlsx_io.ac(hedef)
    for ad in ("Satış", "İkinci"):
        a = next(s for s in k.sayfalar if s.ad == ad)
        b = next(s for s in k2.sayfalar if s.ad == ad)
        for r in range(1, 8):
            for c in range(1, 5):
                assert a.deger(r, c) == b.deger(r, c), (ad, r, c)


def test_uzantisi_xls_ama_xlsx_ise_yonlenir(tmp_path):
    src = os.path.join(os.path.dirname(__file__), "ornekler", "butce.xlsx")
    hedef = str(tmp_path / "gercekte_xlsx.xls")
    shutil.copy(src, hedef)
    k, _ = xls_io.ac(hedef)
    assert k.sayfalar[0].kullanilan_aralik() is not None


def test_bozuk_ve_eksik_dosya(tmp_path):
    kotu = tmp_path / "bozuk.xls"
    kotu.write_bytes(b"bu bir xls degil")
    with pytest.raises(XlsxHatasi, match="geçerli bir .xls değil"):
        xls_io.ac(str(kotu))
    kesik = tmp_path / "kesik.xls"
    kesik.write_bytes(open(ORNEK, "rb").read()[:700])
    with pytest.raises(XlsxHatasi):
        xls_io.ac(str(kesik))
    with pytest.raises(XlsxHatasi, match="açılamadı"):
        xls_io.ac(str(tmp_path / "yok.xls"))


# ---------------------------------------------------------------- arayüz
@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _temiz(app, monkeypatch):
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.Ok)
    yield
    for p in list(DosyaIslemleri._tutulan):
        p.degisti_mi = lambda: False
        p.close()
    DosyaIslemleri._tutulan.clear()


def test_pencerede_acilir_ve_xlsx_olarak_kaydedilir(monkeypatch, tmp_path):
    p = Pencere(CalismaKitabi())
    p.show()
    q = p.dosya_ac(ORNEK)
    assert q.izgara().sayfa.deger(2, 1) == "Çay"
    assert q.yol is None and q.kaynak_yol == os.path.abspath(ORNEK) and q.belge_adi == "ornek.xls"
    assert q.bilgi_etiketi.text() and "formüller okunamaz" in q.bilgi_etiketi.text()
    onerilen = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: onerilen.append(a[2]) or ("", ""))
    assert not q.kaydet()                                              # yol yok → Farklı Kaydet; öneri .xlsx
    assert onerilen[0].endswith("ornek.xlsx")


def test_ayni_xls_iki_kez_acilmaz():
    p = Pencere(CalismaKitabi())
    p.show()
    q = p.dosya_ac(ORNEK)
    assert q.dosya_ac(ORNEK) is q
