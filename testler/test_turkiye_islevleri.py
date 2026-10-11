"""T7: YAZIYLA ve TCKIMLIKDOGRULA (Tabcel'e özel; Excel'de yok → referans kendi kurallarımız / bilinen TC örnekleri)."""
import pytest
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from tabcel.formul.fonksiyonlar import turkiye
from tabcel.model.sayfa import CalismaKitabi, Hucre


from _fonk import hesapla as _h
from tabcel.model import deger as D


def _hesapla(formul, veri=None):
    return _h(formul, veri)


@pytest.mark.parametrize("n,yazi", [(0, "sıfır"), (5, "beş"), (10, "on"), (11, "on bir"), (100, "yüz"), (101, "yüz bir"),
                                    (125, "yüz yirmi beş"), (1000, "bin"), (1001, "bin bir"), (2000, "iki bin"),
                                    (12345, "on iki bin üç yüz kırk beş"), (1000000, "bir milyon"),
                                    (1100000, "bir milyon yüz bin"), (999999999999999, None)])
def test_tam_sayi_yazi(n, yazi):
    if yazi is not None:
        assert turkiye.tam_sayi_yazi(n) == yazi
    else:
        assert turkiye.tam_sayi_yazi(n).startswith("dokuz yüz doksan dokuz trilyon")


def test_yaziyla_formulde_normal_eksi_kesir():
    assert _hesapla("=YAZIYLA(125)") == "yüz yirmi beş"
    assert _hesapla("=YAZIYLA(-3)") == "eksi üç"
    assert _hesapla("=YAZIYLA(2.05)") == "iki virgül sıfır beş"


def test_yaziyla_bos_hata_metin():
    assert _hesapla("=YAZIYLA(A1)") == "sıfır"                      # boş hücre = 0
    assert _hesapla("=YAZIYLA(\"abc\")") == D.DEGER_HATASI
    assert _hesapla("=YAZIYLA(10^15)") == D.SAYI
    assert _hesapla("=YAZIYLA(\"12\")") == "on iki"                  # metin sayı: Excel gibi sayıya çevrilir


# Geçerli: algoritma gereği üretilmiş örnek; (d10, d11) hesaplanır
def _gecerli(ilk9):
    d = [int(k) for k in ilk9]
    d10 = (sum(d[0:9:2]) * 7 - sum(d[1:8:2])) % 10
    return ilk9 + str(d10) + str((sum(d) + d10) % 10)


def test_tc_kimlik_algoritma():
    no = _gecerli("123456789")
    assert turkiye.tc_kimlik_gecerli_mi(no)
    yanlis = no[:-1] + str((int(no[-1]) + 1) % 10)
    assert not turkiye.tc_kimlik_gecerli_mi(yanlis)
    assert not turkiye.tc_kimlik_gecerli_mi("01234567890") and not turkiye.tc_kimlik_gecerli_mi("1234567890")
    assert not turkiye.tc_kimlik_gecerli_mi("abcdefghijk")


def test_tc_formulde_metin_sayi_bos_hata():
    no = _gecerli("123456789")
    assert _hesapla(f'=TCKIMLIKDOGRULA("{no}")') is True
    assert _hesapla(f"=TCKIMLIKDOGRULA({no})") is True              # sayı olarak yazılmış
    assert _hesapla("=TCKIMLIKDOGRULA(A1)") is False                # boş
    assert _hesapla('=TCKIMLIKDOGRULA("12a")') is False
    assert _hesapla("=TCKIMLIKDOGRULA(A1)", {"A1": D.YOK}) == D.YOK       # hata girdisi olduğu gibi döner


def test_turkce_ad_ve_goruntu():
    from tabcel.formul import ceviri
    k = CalismaKitabi()
    assert ceviri.girdiden("=TCKİMLİKDOĞRULA(A1)", k) == "=TCKIMLIKDOGRULA(A1)"
    assert "TCKİMLİKDOĞRULA" in ceviri.gosterime("=TCKIMLIKDOGRULA(A1)", k)


def test_xlsx_kaydederken_uyari(tmp_path):
    from tabcel.io import xlsx_io
    k = CalismaKitabi()
    k.sayfalar[0].ata(1, 1, Hucre(None, "=YAZIYLA(5)"))
    r = xlsx_io.kaydet(k, str(tmp_path / "a.xlsx"))
    assert any("YAZIYLA" in u and "Excel" in u for u in r.uyarilar)
    k2 = CalismaKitabi()
    k2.sayfalar[0].ata(1, 1, Hucre(None, "=SUM(1,2)"))
    r2 = xlsx_io.kaydet(k2, str(tmp_path / "b.xlsx"))
    assert not any("YAZIYLA" in u for u in r2.uyarilar)
