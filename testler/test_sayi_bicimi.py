"""Sayı biçimi kodu çözümleyici/biçimleyici (model/sayi_bicimi.py). Qt'siz.

Kural 11: her biçim ailesi için en az dört vaka — normal, boş (None), hata/metin girdisi,
metin/sayı karışımı — ve Microsoft belge örneklerinden ("Review guidelines for customizing a number
format", en-US/tr-tr) altın değerler. Kodlar kanonik (en-US) yazılır, çıktı Türkçe yerel ayardadır.
Emin olunmayan Excel davranışları burada TEST EDİLMEZ (test.md / surec.md §8b'de listelenir).
"""
import dataclasses
import datetime as dt
import random
import time

import pytest

from tabcel.model import deger as D
from tabcel.model import sayi_bicimi as S
from tabcel.model.gosterim import goster, sayiyi_sigdir
from tabcel.model.sayi_bicimi import (AYLAR, GUNLER, HAZIR, ORTA, SAG, SOL, BicimHatasi,
                                      ad_kodu, bicimle, doldur, kanonige, kod_coz,
                                      ondalik_degistir, sigdir, yerele)


def m(deger, kod, yerel=False):
    return bicimle(deger, kod, yerel).metin


def seri(y, a, g):
    return float((dt.date(y, a, g) - dt.date(1899, 12, 30)).days)


# ------------------------------------------------------------------ kural 11: dört vaka, her aile
AILELER = {
    "genel": "General",
    "sayi": "#,##0.00",
    "yuzde": "0.0%",
    "bilimsel": "0.00E+00",
    "kesir": "# ?/?",
    "tarih": "dd.mm.yyyy",
    "saat": "hh:mm:ss",
    "para": '"₺"#,##0.00',
    "renkli": "[Red]0;[Blue]-0",
    "kosullu": "[>100]0;0.0",
    "metin_bolumlu": '0.00;-0.00;0;"Ad: "@',
}


@pytest.mark.parametrize("kod", AILELER.values(), ids=AILELER.keys())
def test_bos_hucre_bos_metin(kod):
    s = bicimle(None, kod)
    assert s.metin == "" and s.renk is None


@pytest.mark.parametrize("kod", AILELER.values(), ids=AILELER.keys())
def test_hata_degeri_bicimlenmez_ortalanir(kod):
    s = bicimle(D.BOL0, kod)
    assert (s.metin, s.hizalama, s.renk) == ("#BÖL/0!", ORTA, None)


@pytest.mark.parametrize("kod", AILELER.values(), ids=AILELER.keys())
def test_mantiksal_bicimlenmez(kod):
    assert (m(True, kod), bicimle(False, kod).hizalama) == ("DOĞRU", ORTA)


@pytest.mark.parametrize("kod", [k for a, k in AILELER.items() if a != "metin_bolumlu"])
def test_sayi_gibi_metin_oldugu_gibi_sola(kod):
    # metin hücresi ("12") sayı biçiminden etkilenmez (metin bölümü yoksa), sola yaslanır
    s = bicimle("12", kod)
    assert (s.metin, s.hizalama) == ("12", SOL)


@pytest.mark.parametrize("kod,deger,beklenen", [
    ("General", 1234.5, "1234,5"),
    ("#,##0.00", 1234.567, "1.234,57"),
    ("0.0%", 0.1234, "12,3%"),
    ("0.00E+00", 12200000.0, "1,22E+07"),
    ("# ?/?", 1.25, "1 1/4"),
    ("dd.mm.yyyy", seri(2026, 10, 12), "12.10.2026"),
    ("hh:mm:ss", 0.5, "12:00:00"),
    ('"₺"#,##0.00', 1234.5, "₺1.234,50"),
    ("[Red]0;[Blue]-0", 5.0, "5"),
    ("[>100]0;0.0", 150.0, "150"),
    ('0.00;-0.00;0;"Ad: "@', 2.0, "2,00"),
])
def test_normal_durum_sayi_saga(kod, deger, beklenen):
    s = bicimle(deger, kod)
    assert (s.metin, s.hizalama) == (beklenen, SAG)


# ------------------------------------------------------------------ Genel
def test_genel_gosterim_ile_ayni():
    for v in (0.0, 1.0, -3.0, 2.5, 1 / 3, 1e11, 1e-7, 123456789.0, -0.001):
        assert m(v, "General") == goster(v)
        assert m(v, "") == goster(v)
        assert m(v, None) == goster(v)


def test_genel_yerel_adi_ve_sabitle():
    assert m(5.0, "Genel", yerel=True) == "5"
    assert m(5.0, 'General" kg"') == "5 kg"
    assert m(-5.0, 'General;"eksi "General') == "eksi 5"


def test_genel_sigdir_gosterim_ile_tutarli():
    for v in (1234567.891, 0.000123456, 98765432101.0, 3.14159):
        for gen in range(1, 14):
            def sigar(t, gen=gen):
                return len(t) <= gen
            assert sigdir(v, "General", sigar) == sayiyi_sigdir(v, sigar)


# ------------------------------------------------------------------ sayı yer tutucuları (MS örnekleri)
@pytest.mark.parametrize("kod,deger,beklenen", [
    ("####.#", 1234.59, "1234,6"),
    ("#.000", 8.9, "8,900"),
    ("0.#", 0.631, "0,6"),
    ("#.0#", 12.0, "12,0"),
    ("#.0#", 1234.568, "1234,57"),
    ("#,###", 12000.0, "12.000"),
    ("#,", 12000.0, "12"),
    ("0.0,,", 12200000.0, "12,2"),
    ("#,##0", 1234567.0, "1.234.567"),
    ("0", 2.5, "3"),                 # yarım değer sıfırdan uzağa
    ("0", -2.5, "-3"),
    ("0", 0.0, "0"),
    ("00000", 123.0, "00123"),
    ("000-00-0000", 123456789.0, "123-45-6789"),
])
def test_sayi_ms_ornekleri(kod, deger, beklenen):
    assert m(deger, kod) == beklenen


@pytest.mark.parametrize("deger,beklenen", [
    (44.398, " 44,398"), (102.65, "102,65 "), (2.8, "  2,8  ")])
def test_soru_isareti_hizalama(deger, beklenen):
    # MS: "???.???" ondalık noktaları hizalar (anlamsız sıfırlar yerine boşluk)
    assert m(deger, "???.???") == beklenen


def test_sayi_hata_ve_karisik():
    assert m(D.YOK, "0.00") == "#YOK"
    assert m("metin", "#,##0") == "metin"
    assert m(None, "0") == ""
    assert m(7.0, "0.00") == "7,00"


def test_yuzde():
    assert m(0.5, "0%") == "50%"
    assert m(0.1234, "0.00%") == "12,34%"
    assert m(None, "0%") == ""
    assert m("%5", "0%") == "%5"


def test_bilimsel():
    assert m(0.000123, "0.00E+00") == "1,23E-04"
    assert m(12345.0, "0.00E-00") == "1,23E04"
    assert m(0.0, "0.00E+00") == "0,00E+00"
    assert m(D.SAYI, "0.00E+00") == "#SAYI!"
    assert m("1E5", "0.00E+00") == "1E5"


@pytest.mark.parametrize("kod,deger,beklenen", [
    ("# ?/?", 1.25, "1 1/4"),
    ("# ???/???", 5.25, "5 1/4"),
    ("# ???/???", 5.3, "5 3/10"),
    ("# ?/8", 1.3, "1 2/8"),          # sabit payda
    ("?/?", 5.25, "21/4"),            # tam kısım yok: bileşik kesir
    ("# ??/100", 0.37, "37/100"),
])
def test_kesir(kod, deger, beklenen):
    assert " ".join(m(deger, kod).split()) == beklenen


def test_kesir_dort_vaka():
    assert m(None, "# ?/?") == ""
    assert m(D.DEGER_HATASI, "# ?/?") == "#DEĞER!"
    assert m("1/2", "# ?/?") == "1/2"
    assert m(-1.5, "# ?/?") == "-1 1/2"


# ------------------------------------------------------------------ bölümler, renk, koşul, metin
MS_DORT = '[Blue]#,##0.00_);[Red](#,##0.00);0.00;"sales "@'


def test_dort_bolum_ms_ornegi():
    s = bicimle(1234.5, MS_DORT)
    assert (s.metin, s.renk) == ("1.234,50 ", "#0000FF")
    s = bicimle(-1234.5, MS_DORT)
    assert (s.metin, s.renk) == ("(1.234,50)", "#FF0000")
    assert m(0.0, MS_DORT) == "0,00"
    s = bicimle("abc", MS_DORT)
    assert (s.metin, s.hizalama) == ("sales abc", SOL)


def test_iki_bolum_negatif_isaretsiz():
    assert m(-5.0, "0;(0)") == "(5)"
    assert m(5.0, "0;(0)") == "5"
    assert m(0.0, "0;(0)") == "0"           # iki bölümde sıfır ilk bölümde


def test_bos_bolum_gizler():
    assert m(-5.0, "0;") == ""
    assert m(0.0, "0;-0;") == ""
    assert m(3.0, ";;;") == ""


def test_metin_bolumu_tek_basina():
    assert m("abc", "@") == "abc"
    assert m("abc", '"<"@">"') == "<abc>"
    assert m(5.0, "@") == "5"               # sayı Genel kalır
    assert m("x", '0;0;0;"sabit"') == "sabit"


def test_renk_ms_ornegi_ve_kosul():
    # MS: "[Red][<=100];[Blue][>100]"
    k = "[Red][<=100];[Blue][>100]"
    assert bicimle(50.0, k) == S.BicimSonucu("50", "#FF0000", SAG)
    assert bicimle(150.0, k).renk == "#0000FF"


def test_kosullu_bolumler():
    k = '[>100]"büyük";[<=5]0.0;0.00'
    assert m(150.0, k) == "büyük"
    assert m(3.0, k) == "3,0"
    assert m(50.0, k) == "50,00"
    assert m("t", k) == "t"


@pytest.mark.parametrize("tr,en,hx", [
    ("Siyah", "Black", "#000000"), ("Yeşil", "Green", "#00FF00"), ("Beyaz", "White", "#FFFFFF"),
    ("Mavi", "Blue", "#0000FF"), ("Eflatun", "Magenta", "#FF00FF"), ("Sarı", "Yellow", "#FFFF00"),
    ("Camgöbeği", "Cyan", "#00FFFF"), ("Kırmızı", "Red", "#FF0000")])
def test_renk_adlari_tr_en(tr, en, hx):
    assert bicimle(1.0, f"[{tr}]0", yerel=True).renk == hx
    assert bicimle(1.0, f"[{en}]0").renk == hx
    assert bicimle(1.0, f"[{en.upper()}]0").renk == hx
    assert yerele(f"[{en}]0") == f"[{tr}]0"
    assert kanonige(f"[{tr}]0") == f"[{en}]0"


def test_renk_numarasi_palet_openpyxl_ile_ayni():
    from openpyxl.styles.colors import COLOR_INDEX
    for n in range(1, 57):
        assert bicimle(1.0, f"[Color{n}]0").renk[1:] == COLOR_INDEX[7 + n][2:]
    with pytest.raises(BicimHatasi):
        kod_coz("[Color57]0")


# ------------------------------------------------------------------ sabit metin
def test_sabitler():
    assert m(5.0, '0" adet"') == "5 adet"
    assert m(5.0, "0\\x") == "5x"
    assert m(5.0, "$0") == "$5"
    assert m(5.0, "0 €") == "5 €"
    assert m(5.0, "0_)") == "5 "
    assert m(1234.5, "#,##0.00 [$₺-41F]") == "1.234,50 ₺"
    assert m(5.0, '"\\"0') == "\\5"


def test_dolgu_yildiz():
    s = bicimle(5.0, "*-0")
    assert s.metin == "5" and s.dolgu == (0, "-")
    assert doldur(s, lambda t: len(t) <= 6) == "-----5"
    s = bicimle(1234.5, '_-"₺"* #,##0.00_-')
    assert s.metin == " ₺1.234,50 " and s.dolgu == (2, " ")
    assert doldur(bicimle(5.0, "0"), lambda t: True) == "5"


# ------------------------------------------------------------------ tarih / saat
def test_tarih_ms_kodlari():
    n = seri(2026, 1, 5)                   # 5 Ocak 2026 Pazartesi
    gun = GUNLER[(dt.date(2026, 1, 5).weekday() + 1) % 7]
    assert gun == "Pazartesi"
    assert m(n, "m") == "1" and m(n, "mm") == "01" and m(n, "mmmm") == "Ocak"
    assert m(n, "mmmmm") == "O"
    assert m(n, "d") == "5" and m(n, "dd") == "05" and m(n, "dddd") == gun
    assert m(n, "yy") == "26" and m(n, "yyyy") == "2026"
    assert m(n, "dd.mm.yyyy") == "05.01.2026"
    assert m(n, "d mmmm yyyy dddd") == "5 Ocak 2026 Pazartesi"


@pytest.mark.parametrize("ay", range(1, 13))
def test_ay_adlari(ay):
    assert m(seri(2025, ay, 15), "mmmm") == AYLAR[ay - 1]


def test_tarih_dort_vaka_ve_1900():
    assert m(None, "dd.mm.yyyy") == ""
    assert m(D.YOK, "dd.mm.yyyy") == "#YOK"
    assert m("12.10.2026", "dd.mm.yyyy") == "12.10.2026"     # metin dokunulmaz
    assert m(1.0, "dd.mm.yyyy") == "01.01.1900"
    assert m(60.0, "dd.mm.yyyy") == "29.02.1900"               # Excel'in 1900 hatası (bilerek)
    assert m(61.0, "dd.mm.yyyy") == "01.03.1900"
    assert m(2958465.0, "dd.mm.yyyy") == "31.12.9999"


def test_negatif_ya_da_cok_buyuk_tarih_diyez():
    assert bicimle(-1.0, "dd.mm.yyyy").diyez
    assert bicimle(2958466.0, "dd.mm.yyyy").diyez
    assert sigdir(-1.0, "dd.mm.yyyy", lambda t: True) is None


def test_saat_ve_dakika_ay_ayrimi():
    t = 16 / 24 + 36 / 1440 + 3 / 86400      # 16:36:03
    assert m(t, "h:mm") == "16:36"
    assert m(t, "h:mm:ss") == "16:36:03"
    assert m(t, "h:mm:ss A/P") == "4:36:03 P"
    assert m(t, "h:mm AM/PM").startswith("4:36 ")
    assert m(t, "m:ss") == "36:03"            # saniyeden önce: dakika
    assert m(t, "h:m") == "16:36"             # saatten sonra: dakika
    assert m(seri(2026, 3, 1) + t, "m") == "3"   # tek başına: ay


def test_gecen_sure():
    assert m(1.5, "[h]:mm") == "36:00"
    assert m(1.5, "[h]:mm:ss") == "36:00:00"
    assert m(1 / 16, "[mm]:ss") == "90:00"
    assert m(1 / 1440, "[ss]") == "60"
    assert m(0.5 + 0.25 / 86400, "hh:mm:ss.00") == "12:00:00,25"


# ------------------------------------------------------------------ kanonik ⇄ yerel
@pytest.mark.parametrize("kanonik,yerel", [
    ("#,##0.00", "#.##0,00"),
    ("dd.mm.yyyy", "gg.aa.yyyy"),
    ("d mmmm yyyy dddd", "g aaaa yyyy gggg"),
    ("[Red]0.0%;[Blue]-0.0%", "[Kırmızı]0,0%;[Mavi]-0,0%"),
    ("General", "Genel"),
    ("0.00E+00", "0,00E+00"),
    ("[>1.5]0.0;0", "[>1,5]0,0;0"),
    ("hh:mm:ss.00", "hh:mm:ss,00"),
    ("[h]:mm", "[h]:mm"),
    ('#,##0.00 "₺"', '#.##0,00 "₺"'),
    ("# ?/?", "# ?/?"),
    ("@", "@"),
])
def test_kanonik_yerel_gidis_donus(kanonik, yerel):
    assert yerele(kanonik) == yerel
    assert kanonige(yerel) == kanonik
    assert kanonige(yerele(kanonik)) == kanonik


@pytest.mark.parametrize("kod", list(HAZIR.values()) + [MS_DORT, "000-00-0000", "0\\-0", "*-0"])
def test_hazir_ve_ornek_kodlar_gidis_donus(kod):
    assert kanonige(yerele(kod)) == kod
    # yerel yazımla biçimleme kanonikle aynı sonucu verir
    for v in (1234.5, -2.25, 0.0, "x"):
        assert bicimle(v, yerele(kod), yerel=True) == bicimle(v, kod)


def test_yerel_tarih_harfleri():
    n = seri(2026, 10, 12)
    assert m(n, "gg.aa.yyyy", yerel=True) == "12.10.2026"
    assert m(n, "dd.mm.yyyy", yerel=True) == "12.10.2026"      # d de gün; m bağlamla ay


@pytest.mark.parametrize("kod", ['"abc', "[Foo]0", "0;0;0;0;0", "0x", "[Color0]0", "0_", "[>a]0",
                                 "0;@;0", "# ?/"])
def test_gecersiz_kod(kod):
    with pytest.raises(BicimHatasi):
        kod_coz(kod)


# ------------------------------------------------------------------ sığdırma, hazır biçimler, ondalık
def test_sigdir_sayi_bicimi_kisaltilmaz():
    assert sigdir(1234.5, "#,##0.00", lambda t: len(t) <= 8) == "1.234,50"
    assert sigdir(1234.5, "#,##0.00", lambda t: len(t) <= 7) is None
    assert sigdir("uzun metin", "0", lambda t: False) == "uzun metin"
    assert sigdir(None, "0", lambda t: False) == ""


def test_hazir_bicimler():
    for ad, kod in HAZIR.items():
        assert ad_kodu(ad) == kod
        kod_coz(kod)
    assert m(0.256, ad_kodu("Yüzde")) == "25,60%"
    assert m(12345.678, ad_kodu("Bilimsel")) == "1,23E+04"
    assert m("abc", ad_kodu("Metin")) == "abc"
    assert kod_coz(ad_kodu("Kısa Tarih")).tarih_mi
    with pytest.raises(KeyError):
        ad_kodu("Yok böyle")


@pytest.mark.parametrize("kod,fark,beklenen", [
    ("0", 1, "0.0"), ("#,##0.00", 1, "#,##0.000"), ("0.00", -1, "0.0"), ("0.0", -1, "0"),
    ("0%", 1, "0.0%"), ('"₺"#,##0.00', -2, '"₺"#,##0'), ("0.00;(0.00)", 1, "0.000;(0.000)")])
def test_ondalik_artir_azalt(kod, fark, beklenen):
    assert ondalik_degistir(kod, fark) == beklenen


def test_ondalik_genel_degerden_baslar():
    assert ondalik_degistir("General", 1, 1.25) == "0.000"
    assert ondalik_degistir("General", -1, 1.25) == "0.0"
    assert ondalik_degistir("General", 1, 7.0) == "0.0"


# ------------------------------------------------------------------ hızlı yol = genel yol, başarım
@pytest.mark.parametrize("kod", ["0", "#,##0.00", "0.0%", '"₺"#,##0.00', "#,##0,", "0.000", "#",
                                 ".00", "00000", "_-* #,##0.00_-"])
def test_hizli_yol_genel_yolla_ayni(kod):
    b = kod_coz(kod).sayi_bolumleri[0]
    assert b.duzen.hizli is not None
    yavas = dataclasses.replace(b, duzen=dataclasses.replace(b.duzen, hizli=None))
    rnd = random.Random(7)
    degerler = [rnd.uniform(-1e7, 1e7) for _ in range(2000)] + [
        0.0, 0.5, 2.5, -2.5, 1.005, 999.995, 1e14, 0.0049, 123456789.987]
    for v in degerler:
        assert S._sayi_bicimle(b, v, v < 0) == S._sayi_bicimle(yavas, v, v < 0), (kod, v)


def test_basarim_kaba():
    # sıcak yol: 20.000 biçimleme 1 sn'nin çok altında olmalı (ölçüm: ~7 µs/hücre sayı, ~10 µs tarih)
    degerler = [i * 1.37 for i in range(20000)]
    t = time.perf_counter()
    for v in degerler:
        bicimle(v, "#,##0.00")
    assert time.perf_counter() - t < 1.0
    assert kod_coz("#,##0.00") is kod_coz("#,##0.00")          # önbellek
