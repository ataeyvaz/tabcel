"""İşlev kitaplığı genişletmesi — Excel'in birebir yakalanamayan ya da dizi dönen işlevleri (2026-10-15)."""
import pytest

from _fonk import hesapla, kitap_kur, kontrol
from tabcel.formul.agac import formul_ayristir
from tabcel.formul.degerlendir import Baglam, degerlendir
from tabcel.formul.yerel import EN
from tabcel.model import deger as D
from tabcel.formul.degerler import Dizi


def _ham(formul, veri):
    k = kitap_kur(veri)
    return degerlendir(formul_ayristir(formul, EN), Baglam(k.sayfalar[0], 20, 20, k))


def test_mode_mult_dizi_ve_yok():
    s = _ham("=MODE.MULT(A1:A6)", {"A1": 1, "A2": 2, "A3": 2, "A4": 3, "A5": 3, "A6": 4})
    assert isinstance(s, Dizi) and [r[0] for r in s.satirlar] == [2.0, 3.0]
    assert hesapla("=MODE.MULT(A1:A3)", {"A1": 1, "A2": 2, "A3": 3}) == D.YOK
    assert hesapla("=MODE.MULT(A1:A3)", {"A1": "a", "A2": "b"}) == D.YOK            # boş/metin
    assert hesapla("=MODE.MULT(A1:A3)", {"A1": 1, "A2": D.YOK, "A3": 1}) == D.YOK   # hata girdisi


def test_char_satir_sonu():
    kontrol("=CHAR(10)", "\n")
    kontrol('=CLEAN("a"&CHAR(10)&"b")', "ab")
    kontrol("=CLEAN(A1)", "", {"A1": None})
    kontrol("=CLEAN(A1)", "5", {"A1": 5})


G = {"A1": -120000, "A2": 39000, "A3": 30000, "A4": 21000, "A5": 37000, "A6": 46000,
     "B1": 39448, "B2": 39508, "B3": 39751, "B4": 39859, "B5": 39904, "B6": 39911}


def test_xirr_excel_yakin():
    # Excel 0,51511926054954538 verir (yineleme 1e-8'de durur); Tabcel kökü daha sıkı bulur
    assert hesapla("=XIRR(A1:A6,B1:B6)", G) == pytest.approx(0.5151192605, abs=1e-7)
    assert hesapla("=XIRR(A1:A6,B1:B6,0.2)", G) == pytest.approx(0.5151192605, abs=1e-7)
    assert hesapla("=XIRR(A1:A3,B1:B3)", G) == pytest.approx(-0.6598584600, abs=1e-7)
    assert hesapla("=XIRR(A1:A3,B1:B2)", G) == D.SAYI
    assert hesapla("=XIRR(A2:A6,B2:B6)", G) == D.SAYI


def test_isformula_ve_sheet():
    veri = {"A1": 5, "A2": "=A1*2"}
    kontrol("=ISFORMULA(A2)", True, veri)
    kontrol("=ISFORMULA(A1)", False, veri)
    kontrol("=ISFORMULA(A9)", False, veri)
    assert hesapla("=ISFORMULA(5)", veri) == D.DEGER_HATASI
    kontrol("=SHEET()", 1.0, veri)
    kontrol("=SHEETS()", 1.0, veri)
