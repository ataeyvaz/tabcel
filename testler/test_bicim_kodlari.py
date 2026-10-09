"""Faz 3 / 3e: sayı biçimi kategorileri ⇄ kanonik kod (Qt'siz)."""
import pytest

from tabcel.model import bicim_kodlari as bk
from tabcel.model.sayi_bicimi import HAZIR, BicimHatasi, yerele


def test_kod_olustur_temel():
    assert bk.kod_olustur("Genel") == "General"
    assert bk.kod_olustur("Sayı", 2) == "0.00" and bk.kod_olustur("Sayı", 0) == "0"
    assert bk.kod_olustur("Sayı", 3, True) == "#,##0.000"
    assert bk.kod_olustur("Yüzde", 1) == "0.0%" and bk.kod_olustur("Yüzde", 0) == "0%"
    assert bk.kod_olustur("Bilimsel", 2) == "0.00E+00"
    assert bk.kod_olustur("Metin") == "@"
    assert bk.kod_olustur("Para Birimi", 2, sembol="₺") == '"₺"#,##0.00'
    assert bk.kod_olustur("Para Birimi", 2, sembol="€") == '#,##0.00 "€"'
    assert bk.kod_olustur("Para Birimi", 0, sembol="Yok") == "#,##0"
    assert bk.kod_olustur("Tarih") == "d.mm.yyyy" and bk.kod_olustur("Saat") == "hh:mm:ss"
    with pytest.raises(ValueError):
        bk.kod_olustur("Sayı", 31)
    with pytest.raises(ValueError):
        bk.kod_olustur("Özel")


def test_hazir_kodlar_kategoriye_gidis_donus():
    for ad, kod in HAZIR.items():
        c = bk.kategori_coz(kod)
        assert c["kategori"] != "Özel", ad
        yeni = bk.kod_olustur(c["kategori"], c["ondalik"], c["binlik"], c["sembol"], c["tip"])
        assert yeni == kod, ad


def test_bilinmeyen_kod_ozel():
    assert bk.kategori_coz('0.0" kg"')["kategori"] == "Özel"
    assert bk.kategori_coz("[Red]0")["kategori"] == "Özel"
    assert bk.kategori_coz(None)["kategori"] == "Genel"


def test_muhasebe_ondalik():
    kod = bk.kod_olustur("Muhasebe", 0)
    assert bk.kategori_coz(kod)["ondalik"] == 0 and bk.kategori_coz(kod)["kategori"] == "Muhasebe"
    assert bk.onizleme(kod, 1234.5) != ""


def test_ozel_kod_yerel_yazim():
    assert bk.ozel_kodu_coz("#.##0,00") == "#,##0.00"
    assert bk.ozel_kodu_coz("gg.aa.yyyy") == "dd.mm.yyyy"
    assert bk.ozel_kodu_coz("Genel") == "General"
    assert yerele(bk.ozel_kodu_coz("0,0%")) == "0,0%"
    with pytest.raises(BicimHatasi):
        bk.ozel_kodu_coz("[>x]0")


def test_onizleme():
    assert bk.onizleme("0.00", 1234.5678) == "1234,57"
    assert bk.onizleme("#,##0.00", 1234.5678) == "1.234,57"
    assert bk.onizleme("0%", 0.256) == "26%"
    assert bk.onizleme("[>x]0", 1) == ""
    assert bk.onizleme("0.00", "metin") == "metin"
