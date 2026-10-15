"""Gerçek Excel 16'da (COM, Türkçe arayüz, 2026-10-15) ölçülen davranışlar — oturumdaki farklılık taramasından çıkan
düzeltmelerin regresyon testleri. Referans değerler Excel'in kendi çıktısıdır (tahmin değil); ayrıntı surec.md günlüğü."""
import pytest

from _fonk import kontrol
from tabcel.formul.adlar import turkcesi, ingilizcesi
from tabcel.formul.donustur import sayi_metni
from tabcel.model import deger as D
from tabcel.model.gosterim import HATA_TR, goster
from tabcel.model.sayi_bicimi import bicimle, kanonige, yerele

Y = D.YOK
TAB = {"A1": 1, "A2": 3, "A3": 5, "A4": 7, "B1": "a", "B2": "b", "B3": "c", "B4": "d"}


# ---- hata değerleri (Excel Türkçe: #DIV/0! → #SAYI/0!, #NUM! → #SAYI!)
def test_hata_adlari_excel_gibi():
    assert HATA_TR["#DIV/0!"] == "#SAYI/0!" and HATA_TR["#NUM!"] == "#SAYI!" and HATA_TR["#N/A"] == "#YOK"
    assert HATA_TR["#NAME?"] == "#AD?" and HATA_TR["#REF!"] == "#BAŞV!" and HATA_TR["#VALUE!"] == "#DEĞER!"
    assert HATA_TR["#NULL!"] == "#BOŞ!"


def test_adlar_excelden_olculdu():
    assert turkcesi("SWITCH") == "İLKEŞLEŞEN" and ingilizcesi("İLKEŞLEŞEN") == "SWITCH"
    assert turkcesi("LOOKUP") == "ARA" and turkcesi("MAXIFS") == "ÇOKEĞERMAK" and turkcesi("COUNTIF") == "EĞERSAY"


# ---- sayının metne dönüşümü (& ile birleştirme): 15 basamak, ondalık ≤ 18 hane, tamsayı ≤ 20 hane
@pytest.mark.parametrize("x,beklenen", [
    (1 / 3, "0,333333333333333"), (0.00001, "0,00001"), (1e-17 * 1.5, "0,000000000000000015"), (1.5e-18, "1,5E-18"),
    (1.234567890123456e-5, "1,23456789012346E-05"), (123456789012345678.0, "123456789012346000"), (1.5e19, "15000000000000000000"),
    (1.5e20, "1,5E+20"), (1e20, "1E+20"), (-0.00001, "-0,00001"), (0.000123456789012345678, "0,000123456789012346"),
    (2 / 3, "0,666666666666667"), (1234567.5, "1234567,5"),
])
def test_sayi_metni(x, beklenen):
    assert sayi_metni(x) == beklenen


# ---- Genel biçim: işaretsiz en çok 11 karakter
@pytest.mark.parametrize("x,beklenen", [
    (123456789012.0, "1,23457E+11"), (12345678901.2345, "12345678901"), (1e-5, "0,00001"), (1e-9, "0,000000001"),
    (1e-10, "1E-10"), (1.234e-6, "0,000001234"), (1.2345678e-6, "1,23457E-06"), (1 / 3, "0,333333333"), (-1 / 3, "-0,333333333"),
    (-123456789012.0, "-1,23457E+11"), (123456789.123456, "123456789,1"), (0.99999999999999, "1"),
])
def test_genel_11_karakter(x, beklenen):
    assert goster(x) == beklenen


# ---- sayı biçimi
def test_eksi_sifir_isaretsiz():
    assert bicimle(-0.4, "0").metin == "0" and bicimle(-1e-10, "0.00").metin == "0,00" and bicimle(-0.6, "0").metin == "-1"


def test_buyuk_sayi_15_basamak_yuvarlama():
    assert bicimle(5691075034743.234, "0.00").metin == "5691075034743,23"
    assert bicimle(5691075034743.234, "#,##0.00").metin == "5.691.075.034.743,23"


@pytest.mark.parametrize("x,kod,beklenen", [
    (3.14159, "# ??/??", "3  1/7 "), (0.37, "# ??/??", " 10/27"), (0.1, "# ?/?", "0    "), (0.01, "# ??/??", "0      "),
    (0.333, "# ???/???", "   1/3  "),
])
def test_kesir_son_yakinsak(x, kod, beklenen):
    assert bicimle(x, kod).metin.strip() == beklenen.strip()


def test_tarihte_bolu_nokta_olur():
    assert bicimle(45000, "dd/mm/yy").metin == "15.03.23" and bicimle(45000, "d/m/yyyy").metin == "15.3.2023"


@pytest.mark.parametrize("kanonik,yerel", [
    ("hh:mm:ss", "ss:dd:nn"), ("h:mm", "s:dd"), ("[h]:mm", "[s]:dd"), ("[mm]:ss", "[dd]:nn"), ("dd.mm.yyyy hh:mm", "gg.aa.yyyy ss:dd"),
    ("mm:ss", "dd:nn"), ("[Color10]0", "[Renk10]0"), ("d mmmm yyyy dddd", "g aaaa yyyy gggg"),
])
def test_yerel_kod_excel_gibi(kanonik, yerel):
    assert yerele(kanonik) == yerel and kanonige(yerel) == kanonik


# ---- EĞERSAY ölçütleri
def test_egersay_bos_olcutler():
    veri = {"A1": "x", "A2": "", "A3": 1}         # A2: boş metin (="" sonucu gibi)
    kontrol('=COUNTIF(A1:A3,"")', 1.0, veri)             # boş + boş metin: yalnız A2 (A4 boş değil)
    kontrol('=COUNTIF(A1:A4,"")', 2.0, veri)             # A4 gerçekten boş
    kontrol('=COUNTIF(A1:A4,"=")', 1.0, veri)            # "=": yalnız gerçekten boş hücre (A2 boş metin sayılmaz)
    kontrol('=COUNTIF(A1:A4,"<>")', 3.0, veri)           # "<>": boş olmayan her şey (boş metin dahil)
    kontrol('=COUNTIF(A1:A3,"=")', 0.0, veri)
    kontrol('=COUNTIF(A1:A3,"<>")', 3.0, veri)


def test_egersay_bos_olcut_hucresi_sifir_sayilir():
    kontrol("=COUNTIF(A1:A3,B1)", 1.0, {"A1": 0, "A2": 5})          # B1 boş → ölçüt 0
    kontrol("=COUNTIF(A1:A3,B1)", 0.0, {"A1": 5, "A2": 6})


def test_egersay_15_basamak_esitlik():
    kontrol("=COUNTIF(C1,0.3)", 1.0, {"C1": 0.1 + 0.2})           # 0,1+0,2 ile 0,3: 15 basamakta eşit
    kontrol("=C1=0.3", True, {"C1": 0.1 + 0.2})


# ---- yaklaşık eşleşme İKİLİ ARAMA (sırasız veride Excel'in verdiği sonuç)
@pytest.mark.parametrize("formul,beklenen,veri", [
    ("=VLOOKUP(6,A1:B3,2)", "b", {"A1": 10, "B1": "a", "A2": 5, "B2": "b", "A3": 7, "B3": "c"}),
    ("=VLOOKUP(5,A1:B5,2)", "c", {"A1": 1, "B1": "a", "A2": 9, "B2": "b", "A3": 2, "B3": "c", "A4": 8, "B4": "d", "A5": 3, "B5": "e"}),
    ("=VLOOKUP(3,A1:B4,2)", "c", {"A1": 3, "B1": "a", "A2": 3, "B2": "b", "A3": 3, "B3": "c", "A4": 4, "B4": "d"}),   # eşitlerde sonuncu
    ("=VLOOKUP(8,A1:B4,2)", "a", {"A1": 3, "B1": "a", "A2": 9, "B2": "b", "A3": 2, "B3": "c", "A4": 4, "B4": "d"}),
    ("=MATCH(6,A1:A4)", 2.0, {"A1": 10, "A2": 5, "A3": 7, "A4": 1}),
    ("=MATCH(6,A1:A4,1)", 1.0, {"A1": 1, "A2": 9, "A3": 2, "A4": 8}),
    ("=MATCH(2,A1:A3,-1)", Y, {"A1": 1, "A2": 2, "A3": 3}),        # azalan: doğrusal (artan veri → #YOK)
    ("=MATCH(6,A1:A4,-1)", Y, {"A1": 1, "A2": 9, "A3": 3, "A4": 8}),
    ("=MATCH(4,A1:A4,-1)", 1.0, {"A1": 9, "A2": 1, "A3": 5, "A4": 3}),
])
def test_yaklasik_eslesme_ikili_arama(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


# ---- LOOKUP (ARA): vektör ve dizi biçimi
@pytest.mark.parametrize("formul,beklenen", [
    ("=LOOKUP(4,A1:A4,B1:B4)", "b"), ("=LOOKUP(4,A1:B4)", "b"), ("=LOOKUP(0,A1:A4,B1:B4)", Y), ("=LOOKUP(99,A1:A4)", 7.0),
    ("=LOOKUP(3,A1:A4,B1:B4)", "b"),
])
def test_lookup(formul, beklenen):
    kontrol(formul, beklenen, TAB)


def test_lookup_yatay_dizi_ve_metin():
    kontrol("=LOOKUP(2,A1:C2)", "x", {"A1": 1, "B1": 3, "C1": 5, "A2": "x", "B2": "y", "C2": "z"})
    kontrol('=LOOKUP("b",A1:A3,B1:B3)', 20.0, {"A1": "a", "A2": "b", "A3": "c", "B1": 10, "B2": 20, "B3": 30})
    kontrol("=LOOKUP(1,A1:A3)", D.YOK, {"A1": 5, "A2": 6, "A3": 7})


# ---- tarih/saat
@pytest.mark.parametrize("formul,beklenen", [
    ("=EOMONTH(40,0)", 59.0), ("=EOMONTH(DATE(1900,1,15),1)", 59.0), ("=EOMONTH(61,-1)", 59.0), ("=EDATE(DATE(1900,1,31),1)", 59.0),
    ("=EDATE(31,1)", 59.0), ("=EDATE(0,1)", 31.0), ("=EDATE(0,2)", 60.0), ("=EDATE(60,1)", 89.0), ("=EOMONTH(0,0)", 31.0),
    ("=TIME(1,-30,0)", 0.5 / 24), ("=TIME(0,-1,70)", 10 / 86400), ("=TIME(0,0,-1)", D.SAYI), ("=TIME(-1,30,0)", D.SAYI),
    ("=DATEDIF(DATE(2020,2,29),DATE(2021,2,28),\"YD\")", 365.0), ("=DATEDIF(DATE(2020,2,29),DATE(2021,3,1),\"YD\")", 0.0),
    ("=DATEDIF(DATE(2020,2,29),DATE(2021,3,2),\"YD\")", 1.0),
])
def test_tarih_saat_excel_gibi(formul, beklenen):
    kontrol(formul, beklenen)


# ---- POWER: negatif taban, kesirli üs yalnız 1/tek-sayı ise gerçek kök (Excel COM)
@pytest.mark.parametrize("formul,beklenen", [
    ("=POWER(-8,1/3)", -2.0), ("=POWER(-27,1/3)", -3.0), ("=(-8)^(1/3)", -2.0), ("=POWER(-32,0.2)", -2.0), ("=POWER(-8,-1/3)", -0.5),
    ("=POWER(-512,1/9)", -2.0), ("=POWER(-1,1/3)", -1.0), ("=POWER(-8,0.5)", D.SAYI), ("=POWER(-8,2/3)", D.SAYI),
    ("=POWER(-16,0.25)", D.SAYI), ("=POWER(-4,1.5)", D.SAYI), ("=POWER(-8,0.3333)", D.SAYI), ("=POWER(0,-1)", D.BOL0),
])
def test_power_negatif_taban(formul, beklenen):
    kontrol(formul, beklenen)


# ---- AND/OR/XOR: metin argüman atlanır; metin→mantık yalnız DOĞRU/YANLIŞ (Excel-tr COM)
@pytest.mark.parametrize("formul,beklenen", [
    ('=AND(TRUE,"a")', True), ('=AND("a")', D.DEGER_HATASI), ('=AND(TRUE,"FALSE")', True), ('=OR("a",TRUE)', True),
    ('=OR("a",FALSE)', False), ('=AND(1,"2")', True), ('=XOR(TRUE,"a")', True), ('=NOT("a")', D.DEGER_HATASI),
    ('=NOT("TRUE")', D.DEGER_HATASI), ('=NOT("DOĞRU")', False), ('=IF("TRUE",1,2)', D.DEGER_HATASI), ('=IF("DOĞRU",1,2)', 1.0),
    ('=IF("YANLIŞ",1,2)', 2.0), ('=IF("1",1,2)', D.DEGER_HATASI), ('=IF("",1,2)', D.DEGER_HATASI), ('=IF(2,1,2)', 1.0),
])
def test_mantik_metin_argumanlari(formul, beklenen):
    kontrol(formul, beklenen)
