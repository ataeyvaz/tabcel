"""Metin, tarih/saat, arama, finans fonksiyonları — her biri 4 vaka (CLAUDE.md kural 11)."""
import pytest

from _fonk import hesapla, kontrol
from tabcel.model import deger as D

Y, B0, V, N, R = D.YOK, D.BOL0, D.DEGER_HATASI, D.SAYI, D.BASV
V1 = {"A1": 10, "A2": 20, "A3": 30, "A4": "x", "A6": True}
VH = {"A1": 10, "A2": D.YOK, "A3": 30}
AC = {"A1": "a", "A2": "b", "A3": "a", "C1": 1, "C2": 2, "C3": 3}
CC = {"A1": 10, "A2": 20, "A3": 30, "C1": 1, "C2": 2, "C3": 3}
BH = {"A1": 10, "A2": 20, "A3": 30, "B1": 1, "B2": D.YOK, "B3": 3}
TAB = {"A1": 1, "B1": "a", "A2": 2, "B2": "b", "A3": 3, "B3": "c"}      # dikey tablo
YAT = {"A1": 1, "B1": 2, "C1": 3, "A2": "a", "B2": "b", "C2": "c"}      # yatay tablo

AVERAGEIF = [
    ('=AVERAGEIF(A1:A3,">15")', 25.0, CC), ('=AVERAGEIF(A1:A3,">15",C1:C3)', 2.5, CC),
    ('=AVERAGEIF(E1:E3,">1")', B0, None), ('=AVERAGEIF(A1:A3,">5",B1:B3)', Y, BH),
    ('=AVERAGEIF(A1:A3,"a",C1:C3)', 2.0, AC), ('=AVERAGEIF(A1:A3,"z",C1:C3)', B0, AC),
    ('=AVERAGEIFS(C1:C3,A1:A3,"a",C1:C3,">1")', 3.0, AC), ('=AVERAGEIFS(E1:E3,F1:F3,">1")', B0, None),
    ('=AVERAGEIFS(B1:B3,A1:A3,">5")', Y, BH), ('=AVERAGEIFS(C1:C3,A1:A2,"a")', V, AC),
]

METIN = [
    ('=CONCATENATE("a","b",1)', "ab1", None), ('=CONCATENATE(B1,"x")', "x", None),
    ('=CONCATENATE(#N/A,"x")', Y, None), ('=CONCATENATE(1,TRUE,"a")', "1DOĞRUa", None),
    ('=CONCATENATE(1.5,"")', "1,5", None),
    ("=CONCAT(A1:A4)", "102030x", V1), ("=CONCAT(B1:B3)", "", V1), ("=CONCAT(A1:A3)", Y, VH),
    ('=CONCAT("a",A6)', "aDOĞRU", V1),
    ('=TEXTJOIN(",",TRUE,"a","","b")', "a,b", None), ('=TEXTJOIN(",",FALSE,"a","","b")', "a,,b", None),
    ('=TEXTJOIN("-",TRUE,B1:B3)', "", None), ('=TEXTJOIN("-",TRUE,A1:A3)', Y, VH),
    ('=TEXTJOIN("-",TRUE,A1:A4)', "10-20-30-x", V1),
    ('=LEFT("abc")', "a", None), ('=LEFT("abc",2)', "ab", None), ("=LEFT(B1)", "", None), ("=LEFT(#N/A)", Y, None),
    ("=LEFT(12345,2)", "12", None), ('=LEFT("abc",-1)', V, None), ('=LEFT("abc",10)', "abc", None),
    ('=RIGHT("abc",2)', "bc", None), ('=RIGHT("abc")', "c", None), ('=RIGHT("abc",0)', "", None),
    ("=RIGHT(123,2)", "23", None), ('=RIGHT("abc",10)', "abc", None), ("=RIGHT(B1,2)", "", None),
    ("=RIGHT(#N/A,2)", Y, None),
    ('=MID("abcdef",2,3)', "bcd", None), ('=MID("abc",5,2)', "", None), ('=MID("abc",0,1)', V, None),
    ("=MID(B1,1,1)", "", None), ("=MID(#N/A,1,1)", Y, None), ("=MID(12345,2,2)", "23", None),
    ('=LEN("abc")', 3.0, None), ("=LEN(B1)", 0.0, None), ("=LEN(12.5)", 4.0, None), ("=LEN(#N/A)", Y, None),
    ("=LEN(TRUE)", 5.0, None),
    ('=UPPER("abc i")', "ABC İ", None), ('=UPPER("ı")', "I", None), ("=UPPER(B1)", "", None),
    ("=UPPER(#N/A)", Y, None), ("=UPPER(1)", "1", None),
    ('=LOWER("ABC I")', "abc ı", None), ('=LOWER("İ")', "i", None), ("=LOWER(B1)", "", None),
    ("=LOWER(#N/A)", Y, None),
    ('=PROPER("hello wORLD")', "Hello World", None), ('=PROPER("ilk işlem")', "İlk İşlem", None),
    ('=PROPER("2cats")', "2Cats", None), ("=PROPER(B1)", "", None), ("=PROPER(#N/A)", Y, None),
    ('=TRIM("  a   b  ")', "a b", None), ("=TRIM(B1)", "", None), ("=TRIM(#N/A)", Y, None), ("=TRIM(12)", "12", None),
    ('=FIND("b","abc")', 2.0, None), ('=FIND("B","abc")', V, None), ('=FIND("","abc")', 1.0, None),
    ('=FIND("a","abca",2)', 4.0, None), ('=FIND("a",B1)', V, None), ('=FIND("a",#N/A)', Y, None),
    ('=SEARCH("B","abc")', 2.0, None), ('=SEARCH("a*c","xabc")', 2.0, None), ('=SEARCH("?b","abc")', 1.0, None),
    ('=SEARCH("z","abc")', V, None), ('=SEARCH("a",#N/A)', Y, None), ('=SEARCH("1",123)', 1.0, None),
    ('=SUBSTITUTE("a-b-c","-","+")', "a+b+c", None), ('=SUBSTITUTE("a-b-c","-","+",2)', "a-b+c", None),
    ('=SUBSTITUTE(B1,"a","b")', "", None), ('=SUBSTITUTE(#N/A,"a","b")', Y, None),
    ("=SUBSTITUTE(123,2,9)", "193", None), ('=SUBSTITUTE("abc","","x")', "abc", None),
    ('=SUBSTITUTE("Aa","a","x")', "Ax", None),
    ('=REPLACE("abcdef",2,3,"X")', "aXef", None), ('=REPLACE("abc",5,1,"Z")', "abcZ", None),
    ('=REPLACE("abc",0,1,"Z")', V, None), ('=REPLACE(#N/A,1,1,"x")', Y, None),
    ('=REPLACE(12345,2,2,"")', "145", None), ('=REPLACE(B1,1,1,"x")', "x", None),
    ('=VALUE("12")', 12.0, None), ('=VALUE("1,5")', 1.5, None), ('=VALUE("abc")', V, None), ("=VALUE(B1)", 0.0, None),
    ("=VALUE(#N/A)", Y, None), ("=VALUE(TRUE)", V, None), ('=VALUE("50%")', 0.5, None),
    ('=REPT("ab",3)', "ababab", None), ('=REPT("a",0)', "", None), ('=REPT("a",-1)', V, None),
    ("=REPT(B1,3)", "", None), ("=REPT(#N/A,3)", Y, None), ("=REPT(1,3)", "111", None),
    ('=EXACT("a","a")', True, None), ('=EXACT("a","A")', False, None), ('=EXACT(1,"1")', True, None),
    ('=EXACT(B1,"")', True, None), ('=EXACT(#N/A,"a")', Y, None),
]

# Seri numaraları bağımsız hesaplandı (1899-12-30 temelli): 2000-01-01=36526, 2024-01-01=45292,
# 2024-02-29=45351, 2023-12-31=45291, 2023-02-28=44985, 2024-03-29=45380, 2024-01-08=45299
TARIH = [
    ("=DATE(2024,2,29)", 45351.0, None), ("=DATE(2000,1,1)", 36526.0, None), ("=DATE(2024,14,1)", 45689.0, None),
    ("=DATE(2024,1,0)", 45291.0, None), ("=DATE(B1,1,1)", 1.0, None), ("=DATE(#N/A,1,1)", Y, None),
    ('=DATE("2024","2","29")', 45351.0, None), ("=DATE(-1,1,1)", N, None), ("=DATE(1900,2,29)", 60.0, None),
    ("=DATE(1900,3,0)", 60.0, None), ("=DATE(10000,1,1)", N, None),
    ("=TODAY()>=46304", True, None), ("=TODAY()=INT(TODAY())", True, None), ("=TODAY()+#N/A", Y, None),
    ("=TODAY()-B1>46000", True, None),
    ("=NOW()>=TODAY()", True, None), ("=INT(NOW())=TODAY()", True, None), ("=NOW()+#N/A", Y, None),
    ('=NOW()*0+"2"', 2.0, None),
    ("=TIME(12,0,0)", 0.5, None), ("=TIME(24,0,0)", 0.0, None), ("=TIME(B1,B1,B1)", 0.0, None),
    ("=TIME(#N/A,0,0)", Y, None), ('=TIME("6","0","0")', 0.25, None), ("=TIME(-1,0,0)", N, None),
    ("=TIME(0,90,0)", 0.0625, None),
    ("=YEAR(45351)", 2024.0, None), ("=MONTH(45351)", 2.0, None), ("=DAY(45351)", 29.0, None),
    ("=YEAR(B1)", 1900.0, None), ("=MONTH(B1)", 1.0, None), ("=DAY(B1)", 0.0, None),
    ("=YEAR(#N/A)", Y, None), ("=MONTH(#N/A)", Y, None), ("=DAY(#N/A)", Y, None),
    ('=YEAR("45351")', 2024.0, None), ("=YEAR(-1)", N, None), ("=YEAR(60)", 1900.0, None),
    ("=MONTH(60)", 2.0, None), ("=DAY(60)", 29.0, None), ("=MONTH(61)", 3.0, None),
    ("=HOUR(0.75)", 18.0, None), ("=HOUR(B1)", 0.0, None), ("=HOUR(#N/A)", Y, None), ('=HOUR("0,5")', 12.0, None),
    ("=HOUR(45351.5)", 12.0, None), ("=MINUTE(0.0625)", 30.0, None), ("=MINUTE(B1)", 0.0, None),
    ("=MINUTE(#N/A)", Y, None), ('=MINUTE("0,0625")', 30.0, None), ("=SECOND(TIME(0,0,45))", 45.0, None),
    ("=SECOND(B1)", 0.0, None), ("=SECOND(#N/A)", Y, None), ('=SECOND("0,5")', 0.0, None),
    ("=WEEKDAY(45351)", 5.0, None), ("=WEEKDAY(45351,2)", 4.0, None), ("=WEEKDAY(45351,3)", 3.0, None),
    ("=WEEKDAY(45351,11)", 4.0, None), ("=WEEKDAY(45352)", 6.0, None), ("=WEEKDAY(1)", 1.0, None),
    ("=WEEKDAY(B1)", 7.0, None), ("=WEEKDAY(#N/A)", Y, None), ("=WEEKDAY(45351,99)", N, None),
    ('=WEEKDAY("45351")', 5.0, None),
    ("=WEEKNUM(45292)", 1.0, None), ("=WEEKNUM(45657)", 53.0, None), ("=WEEKNUM(45657,2)", 53.0, None),
    ("=WEEKNUM(45298,1)", 2.0, None), ("=WEEKNUM(45656,21)", 1.0, None), ("=WEEKNUM(#N/A)", Y, None),
    ('=WEEKNUM("45292")', 1.0, None), ("=WEEKNUM(45292,5)", N, None),
    ("=EDATE(45322,1)", 45351.0, None), ("=EDATE(45351,-12)", 44985.0, None), ("=EDATE(#N/A,1)", Y, None),
    ('=EDATE("45351","1")', 45380.0, None), ("=EDATE(45351,B1)", 45351.0, None),
    ("=EOMONTH(45351,0)", 45351.0, None), ("=EOMONTH(45306,1)", 45351.0, None), ("=EOMONTH(45306,2)", 45382.0, None),
    ("=EOMONTH(45351,-1)", 45322.0, None), ("=EOMONTH(#N/A,0)", Y, None), ('=EOMONTH("45351","0")', 45351.0, None),
    ('=DATEDIF(43845,45361,"Y")', 4.0, None), ('=DATEDIF(43845,45361,"M")', 49.0, None),
    ('=DATEDIF(43845,45361,"D")', 1516.0, None), ('=DATEDIF(43845,45361,"MD")', 24.0, None),
    ('=DATEDIF(43845,45361,"YM")', 1.0, None), ('=DATEDIF(43845,45361,"YD")', 55.0, None),
    ('=DATEDIF(45361,43845,"Y")', N, None), ('=DATEDIF(#N/A,45361,"Y")', Y, None),
    ('=DATEDIF(43845,45361,"Q")', N, None), ('=DATEDIF("43845","45361","y")', 4.0, None),
    ("=DAYS(45381,45351)", 30.0, None), ("=DAYS(B1,B1)", 0.0, None), ("=DAYS(#N/A,1)", Y, None),
    ('=DAYS("45352","45351")', 1.0, None),
    ("=NETWORKDAYS(45292,45298)", 5.0, None), ("=NETWORKDAYS(45292,45298,45292)", 4.0, None),
    ("=NETWORKDAYS(45298,45292)", -5.0, None), ("=NETWORKDAYS(45292,45298,B1:B3)", 5.0, None),
    ("=NETWORKDAYS(#N/A,45298)", Y, None), ('=NETWORKDAYS("45292","45298")', 5.0, None),
    ("=WORKDAY(45296,1)", 45299.0, None), ("=WORKDAY(45292,5)", 45299.0, None),
    ("=WORKDAY(45296,1,45299)", 45300.0, None), ("=WORKDAY(45299,-1)", 45296.0, None),
    ("=WORKDAY(#N/A,1)", Y, None), ('=WORKDAY("45296","1")', 45299.0, None),
]

ARAMA = [
    ("=VLOOKUP(2,A1:B3,2,FALSE)", "b", TAB), ("=VLOOKUP(2.5,A1:B3,2)", "b", TAB),
    ("=VLOOKUP(9,A1:B3,2,FALSE)", Y, TAB), ("=VLOOKUP(2,A1:B3,3,FALSE)", R, TAB),
    ("=VLOOKUP(2,A1:B3,0,FALSE)", V, TAB), ("=VLOOKUP(#N/A,A1:B3,2,FALSE)", Y, TAB),
    ('=VLOOKUP("B",B1:B3,1,FALSE)', "b", TAB), ('=VLOOKUP("2",A1:B3,2,FALSE)', Y, TAB),
    ("=VLOOKUP(0.5,A1:B3,2)", Y, TAB), ("=VLOOKUP(E1,A1:B3,2,FALSE)", Y, TAB),
    ('=VLOOKUP("a*",B1:B3,1,FALSE)', "a", TAB), ("=VLOOKUP(2,A1:B3,2,0)", "b", TAB),
    ("=HLOOKUP(2,A1:C2,2,FALSE)", "b", YAT), ("=HLOOKUP(2.5,A1:C2,2)", "b", YAT),
    ("=HLOOKUP(9,A1:C2,2,FALSE)", Y, YAT), ("=HLOOKUP(2,A1:C2,3,FALSE)", R, YAT),
    ("=HLOOKUP(#N/A,A1:C2,2,FALSE)", Y, YAT), ("=HLOOKUP(E1,A1:C2,2,FALSE)", Y, YAT),
    ("=MATCH(2,A1:A3,0)", 2.0, TAB), ("=MATCH(2.5,A1:A3,1)", 2.0, TAB), ("=MATCH(2.5,A1:A3,0)", Y, TAB),
    ('=MATCH("b",B1:B3,0)', 2.0, TAB), ("=MATCH(#N/A,A1:A3,0)", Y, TAB), ("=MATCH(5,E1:E3,0)", Y, TAB),
    ('=MATCH("B*",B1:B3,0)', 2.0, TAB), ("=MATCH(2,A1:B3,0)", Y, TAB), ("=MATCH(2,C1:C3,-1)", Y, TAB),
    ("=MATCH(2,A3:A1,-1)", Y, TAB),
    ("=XMATCH(2,A1:A3)", 2.0, TAB), ("=XMATCH(2.5,A1:A3,-1)", 2.0, TAB), ("=XMATCH(2.5,A1:A3,1)", 3.0, TAB),
    ('=XMATCH("b*",B1:B3,2)', 2.0, TAB), ("=XMATCH(9,A1:A3)", Y, TAB), ("=XMATCH(#N/A,A1:A3)", Y, TAB),
    ("=XMATCH(1,A1:A3,0,-1)", 1.0, TAB), ("=XMATCH(1,E1:E3)", Y, TAB),
    ("=XLOOKUP(2,A1:A3,B1:B3)", "b", TAB), ('=XLOOKUP(9,A1:A3,B1:B3,"yok")', "yok", TAB),
    ("=XLOOKUP(9,A1:A3,B1:B3)", Y, TAB), ("=XLOOKUP(2.5,A1:A3,B1:B3,,-1)", "b", TAB),
    ("=XLOOKUP(2,A1:A3,B1:B2)", V, TAB), ("=XLOOKUP(#N/A,A1:A3,B1:B3)", Y, TAB),
    ('=XLOOKUP("B",B1:B3,A1:A3)', 2.0, TAB), ("=XLOOKUP(2,A1:C1,A2:C2)", "b", YAT),
    ("=INDEX(A1:A3,2)", 2.0, TAB), ("=INDEX(A1:B3,3,2)", "c", TAB), ("=SUM(INDEX(A1:B3,0,1))", 6.0, TAB),
    ("=INDEX(A1:A3,5)", R, TAB), ("=INDEX(A1:C1,2)", 2.0, YAT), ("=INDEX(A1:A3,#N/A)", Y, TAB),
    ('=INDEX(A1:A3,"2")', 2.0, TAB), ("=INDEX(A1:A3,-1)", V, TAB), ("=INDEX(E1:E3,2)", 0.0, TAB),
    ('=CHOOSE(2,"a","b","c")', "b", None), ('=CHOOSE(4,"a","b","c")', V, None), ('=CHOOSE(B1,"a","b")', V, None),
    ("=CHOOSE(#N/A,1)", Y, None), ('=CHOOSE("2",10,20)', 20.0, None), ("=SUM(CHOOSE(1,A1:A3))", 6.0, TAB),
    ("=ROW()", 20.0, None), ("=ROW(A5)", 5.0, None), ("=ROW(A2:A3)", 2.0, None), ("=ROW(B9)", 9.0, None),
    ('=ROW("a")', V, None), ("=ROW(#N/A)", Y, None), ("=SUM(ROW(A1:A3))", 6.0, None),
    ("=COLUMN()", 20.0, None), ("=COLUMN(C1)", 3.0, None), ("=COLUMN(B1:D1)", 2.0, None), ("=COLUMN(E9)", 5.0, None),
    ('=COLUMN("a")', V, None), ("=COLUMN(#N/A)", Y, None), ("=SUM(COLUMN(A1:C1))", 6.0, None),
    ("=ROWS(A1:A3)", 3.0, None), ("=ROWS(A1:C1)", 1.0, None), ("=ROWS(B1:B9)", 9.0, None), ("=ROWS(5)", 1.0, None),
    ("=ROWS({1;2;3})", 3.0, None), ("=ROWS(#N/A)", Y, None),
    ("=COLUMNS(A1:C1)", 3.0, None), ("=COLUMNS(A1:A3)", 1.0, None), ("=COLUMNS(B1:D9)", 3.0, None),
    ("=COLUMNS(5)", 1.0, None), ("=COLUMNS({1,2,3})", 3.0, None), ("=COLUMNS(#N/A)", Y, None),
    ('=INDIRECT("A2")', 2.0, TAB), ('=INDIRECT("A"&3)', 3.0, TAB), ('=SUM(INDIRECT("A1:A3"))', 6.0, TAB),
    ('=INDIRECT("zzz")', R, TAB), ("=INDIRECT(B9)", R, TAB), ("=INDIRECT(#N/A)", Y, TAB),
    ('=INDIRECT("A1",FALSE)', R, TAB), ('=INDIRECT("$A$2")', 2.0, TAB), ('=INDIRECT("Yok!A1")', R, TAB),
    ("=OFFSET(A1,1,0)", 2.0, TAB), ("=SUM(OFFSET(A1,0,0,3,1))", 6.0, TAB), ("=OFFSET(A1,-1,0)", R, TAB),
    ("=OFFSET(A1,0,1)", "a", TAB), ("=OFFSET(A1,#N/A,0)", Y, TAB), ('=OFFSET("a",1,1)', V, TAB),
    ("=OFFSET(E9,0,0)", 0.0, TAB), ("=SUM(OFFSET(A1:A2,1,0))", 5.0, TAB),
]

FINANS = [
    ("=PMT(0.08/12,10,10000)", -1037.0320893591636, None), ("=PMT(0,10,1000)", -100.0, None),
    ("=PMT(0.1,0,100)", N, None), ("=PMT(B1,12,1200)", -100.0, None), ("=PMT(#N/A,12,1000)", Y, None),
    ('=PMT("0,01","12","1000")', -88.84878867834166, None),
    ("=FV(0.06/12,10,-200,-500,1)", 2581.4033740601362, None), ("=FV(0,10,-100)", 1000.0, None),
    ("=FV(B1,10,-100)", 1000.0, None), ("=FV(#N/A,10,-100)", Y, None),
    ('=FV("0,01","12","-100")', 1268.2503013196979, None),
    ("=PV(0.08/12,240,500,0,0)", -59777.14585118777, None), ("=PV(0,10,100)", -1000.0, None),
    ("=PV(B1,10,100)", -1000.0, None), ("=PV(#N/A,10,100)", Y, None), ('=PV("0","10","100")', -1000.0, None),
    ("=RATE(48,-200,8000)", 0.00770147248820207, None), ("=RATE(10,0,-100,200)", 0.07177346253629313, None),
    ("=RATE(#N/A,-200,8000)", Y, None), ('=RATE("48","-200","8000")', 0.00770147248820207, None),
    ("=RATE(10,100,100)", N, None),
    ("=NPV(0.1,-10000,3000,4200,6800)", 1188.4434123352216, None), ("=NPV(0.1,A1:A4)", 1188.4434123352216,
                                                                      {"A1": -10000, "A2": 3000, "A3": 4200, "A4": 6800}),
    ("=NPV(0.1,B1:B3)", 0.0, None), ("=NPV(0.1,A1:A3)", Y, VH), ('=NPV(0.1,"100",A1:A2)', 100 / 1.1 + 10 / 1.21 + 20 / 1.331, V1),
    ("=NPV(-1,100)", B0, None),
    ("=IRR(A1:A6)", 0.0866309480365316, {"A1": -70000, "A2": 12000, "A3": 15000, "A4": 18000, "A5": 21000, "A6": 26000}),
    ("=IRR(A1:A5)", -0.021244848273410947, {"A1": -70000, "A2": 12000, "A3": 15000, "A4": 18000, "A5": 21000}),
    ("=IRR(A1:A3)", N, {"A1": 1, "A2": 2, "A3": 3}), ("=IRR(B1:B3)", N, None), ("=IRR(A1:A3)", Y, VH),
    ("=IRR(A1:A3,0.5)", 1.0, {"A1": -100, "A2": 0, "A3": 400}),
]


@pytest.mark.parametrize("formul,beklenen,veri", AVERAGEIF)
def test_averageif(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


@pytest.mark.parametrize("formul,beklenen,veri", METIN)
def test_metin(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


@pytest.mark.parametrize("formul,beklenen,veri", TARIH)
def test_tarih(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


@pytest.mark.parametrize("formul,beklenen,veri", ARAMA)
def test_arama(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


@pytest.mark.parametrize("formul,beklenen,veri", FINANS)
def test_finans(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


def test_kayitli_her_fonksiyonun_turkce_adi_var():
    from tabcel.formul import fonksiyonlar
    from tabcel.formul.adlar import EN_TR
    eksik = sorted(ad for ad in fonksiyonlar.KAYIT if ad not in EN_TR)
    assert eksik == []


def test_dolayli_baska_sayfa():
    from _fonk import kitap_kur
    from tabcel.formul.agac import formul_ayristir
    from tabcel.formul.degerlendir import Baglam, hucre_sonucu
    from tabcel.formul.yerel import EN
    from tabcel.model.sayfa import Hucre
    k = kitap_kur({"A1": 1})
    s2 = k.sayfa_ekle("Gelir Gider") if hasattr(k, "sayfa_ekle") else None
    s2.ata(1, 1, Hucre(42.0))
    b = Baglam(k.sayfalar[0], 20, 20, k)
    assert hucre_sonucu(formul_ayristir("=INDIRECT(\"'Gelir Gider'!A1\")", EN), b) == 42.0
