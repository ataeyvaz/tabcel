import pytest

from tabcel.model.girdi import duzenleme_metni, girdi_coz, sayi_coz
from tabcel.model.sayfa import Hucre


@pytest.mark.parametrize("metin,beklenen", [
    ("12", 12.0), ("-3", -3.0), ("+4", 4.0), ("1,5", 1.5), (",5", 0.5), ("5,", 5.0),
    ("1.500", 1500.0), ("1.234.567,89", 1234567.89), ("1E3", 1000.0),
    ("1,5E-2", 0.015), ("  7  ", 7.0),
])
def test_sayilar(metin, beklenen):
    assert sayi_coz(metin) == beklenen


@pytest.mark.parametrize("metin", ["", ",", "-", "1.5", "1.50", "12.34.56", "abc", "1,2,3",
                                   "E3", "1e", "0x10", "inf", "nan", "1 000"])
def test_sayi_degil(metin):
    assert sayi_coz(metin) is None


def test_girdi_turleri():
    assert girdi_coz("") is None
    assert girdi_coz("merhaba") == Hucre("merhaba")
    assert girdi_coz("42") == Hucre(42.0)
    assert girdi_coz("doğru") == Hucre(True)
    assert girdi_coz("YANLIŞ") == Hucre(False)
    assert girdi_coz("true") == Hucre(True)
    assert girdi_coz("=TOPLA(A1:A3)") == Hucre(None, "=TOPLA(A1:A3)")
    assert girdi_coz("=") == Hucre("=")
    assert girdi_coz("'123") == Hucre("123")
    assert girdi_coz("'") is None
    assert girdi_coz("1.5") == Hucre("1.5")       # tarih çözümü Faz 3


@pytest.mark.parametrize("hucre", [
    None, Hucre("abc"), Hucre(3.0), Hucre(1500.0), Hucre(0.1), Hucre(1e20), Hucre(-2.5e-7),
    Hucre(True), Hucre(False), Hucre("123"), Hucre("=x"), Hucre("'q"), Hucre("DOĞRU"),
    Hucre(None, "=SUM(A1:A3)"), Hucre("1,5"),
])
def test_duzenleme_gidis_donus(hucre):
    geri = girdi_coz(duzenleme_metni(hucre))
    if hucre is not None and hucre.formul is not None:
        assert geri == Hucre(None, hucre.formul)
    else:
        assert geri == hucre


def test_duzenleme_metni_bicimi():
    assert duzenleme_metni(Hucre(2.5)) == "2,5"
    assert duzenleme_metni(Hucre(1500.0)) == "1500"
    assert duzenleme_metni(Hucre("123")) == "'123"
    assert duzenleme_metni(Hucre(True)) == "DOĞRU"
