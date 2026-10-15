"""Matematik, istatistik, mantık, bilgi fonksiyonları — her biri 4 vaka (CLAUDE.md kural 11):
normal · boş hücre/argüman · hata girdisi · metin/sayı karışımı. Formüller kanonik (İngilizce)."""
import pytest

from _fonk import kontrol
from tabcel.model import deger as D

Y, B0, V, N, R = D.YOK, D.BOL0, D.DEGER_HATASI, D.SAYI, D.BASV
V1 = {"A1": 10, "A2": 20, "A3": 30, "A4": "x", "A6": True}          # A5 boş
VH = {"A1": 10, "A2": D.YOK, "A3": 30}                              # aralıkta hata
AC = {"A1": "a", "A2": "b", "A3": "a", "C1": 1, "C2": 2, "C3": 3}  # ölçüt aralığı + toplam
CC = {"A1": 10, "A2": 20, "A3": 30, "C1": 1, "C2": 2, "C3": 3}
BH = {"A1": 10, "A2": 20, "A3": 30, "B1": 1, "B2": D.YOK, "B3": 3}

MATEMATIK = [
    # SUM
    ("=SUM(A1:A3)", 60.0, V1), ("=SUM(B1:B3)", 0.0, V1), ("=SUM(A1:A3)", Y, VH),
    ('=SUM(A1:A4,"5",TRUE)', 66.0, V1),
    # ROUND
    ("=ROUND(2.675,2)", 2.68, None), ("=ROUND(-2.5,0)", -3.0, None), ("=ROUND(1234.567,-2)", 1200.0, None),
    ("=ROUND(B1,0)", 0.0, None), ("=ROUND(#N/A,1)", Y, None), ('=ROUND("2,567",1)', 2.6, None),
    ("=ROUND(TRUE,0)", 1.0, None),
    # ROUNDUP / ROUNDDOWN
    ("=ROUNDUP(3.2,0)", 4.0, None), ("=ROUNDUP(-3.2,0)", -4.0, None), ("=ROUNDUP(31415.92654,-2)", 31500.0, None),
    ("=ROUNDUP(B1,0)", 0.0, None), ("=ROUNDUP(#N/A,0)", Y, None), ('=ROUNDUP("3,14159",3)', 3.142, None),
    ("=ROUNDDOWN(3.14159,3)", 3.141, None), ("=ROUNDDOWN(-3.14159,1)", -3.1, None),
    ("=ROUNDDOWN(31415.92654,-2)", 31400.0, None), ("=ROUNDDOWN(B1,0)", 0.0, None),
    ("=ROUNDDOWN(#N/A,0)", Y, None), ('=ROUNDDOWN("9,99",1)', 9.9, None),
    # TRUNC / INT
    ("=TRUNC(8.9)", 8.0, None), ("=TRUNC(-8.9)", -8.0, None), ("=TRUNC(PI(),3)", 3.141, None),
    ("=TRUNC(B1)", 0.0, None), ("=TRUNC(#N/A)", Y, None), ('=TRUNC("4,56",1)', 4.5, None),
    ("=INT(8.9)", 8.0, None), ("=INT(-8.9)", -9.0, None), ("=INT(B1)", 0.0, None),
    ("=INT(#N/A)", Y, None), ('=INT("3,7")', 3.0, None),
    # MOD
    ("=MOD(3,2)", 1.0, None), ("=MOD(-3,2)", 1.0, None), ("=MOD(3,-2)", -1.0, None),
    ("=MOD(3,0)", B0, None), ("=MOD(B1,3)", 0.0, None), ("=MOD(#N/A,2)", Y, None), ('=MOD("10",3)', 1.0, None),
    # ABS / SQRT / POWER
    ("=ABS(-4)", 4.0, None), ("=ABS(B1)", 0.0, None), ("=ABS(#N/A)", Y, None), ('=ABS("-2,5")', 2.5, None),
    ("=ABS(TRUE)", 1.0, None),
    ("=SQRT(16)", 4.0, None), ("=SQRT(-1)", N, None), ("=SQRT(B1)", 0.0, None), ("=SQRT(#N/A)", Y, None),
    ('=SQRT("9")', 3.0, None),
    ("=POWER(5,2)", 25.0, None), ("=POWER(0,0)", N, None), ("=POWER(B1,2)", 0.0, None),
    ("=POWER(#N/A,2)", Y, None), ('=POWER("2","3")', 8.0, None),
    # PI / RAND / RANDBETWEEN
    ("=PI()", 3.141592653589793, None), ("=PI()+B1", 3.141592653589793, None), ("=PI()+#N/A", Y, None),
    ('=PI()+"1"', 4.141592653589793, None),
    ("=RAND()<1", True, None), ("=RAND()>=0", True, None), ("=RAND()+#N/A", Y, None), ('=RAND()*0+"2"', 2.0, None),
    ("=RANDBETWEEN(5,5)", 5.0, None), ("=RANDBETWEEN(1,10)>=1", True, None), ("=RANDBETWEEN(B1,B1)", 0.0, None),
    ("=RANDBETWEEN(#N/A,1)", Y, None), ('=RANDBETWEEN("3",3)', 3.0, None), ("=RANDBETWEEN(5,1)", N, None),
    # CEILING / FLOOR
    ("=CEILING(2.5,1)", 3.0, None), ("=CEILING(-2.5,-2)", -4.0, None), ("=CEILING(-2.5,2)", -2.0, None),
    ("=CEILING(2.5,-1)", N, None), ("=CEILING(1.5,0)", 0.0, None), ("=CEILING(0.234,0.01)", 0.24, None),
    ("=CEILING(B1,1)", 0.0, None), ("=CEILING(#N/A,1)", Y, None), ('=CEILING("1,5","1")', 2.0, None),
    ("=FLOOR(3.7,2)", 2.0, None), ("=FLOOR(-2.5,2)", -4.0, None), ("=FLOOR(-2.5,-2)", -2.0, None),
    ("=FLOOR(2.5,-1)", N, None), ("=FLOOR(1,0)", B0, None), ("=FLOOR(0,0)", 0.0, None),
    ("=FLOOR(B1,1)", 0.0, None), ("=FLOOR(#N/A,1)", Y, None), ('=FLOOR("3,7","2")', 2.0, None),
    # SIGN / EXP / LN / LOG / LOG10
    ("=SIGN(10)", 1.0, None), ("=SIGN(-0.1)", -1.0, None), ("=SIGN(B1)", 0.0, None), ("=SIGN(#N/A)", Y, None),
    ('=SIGN("-3")', -1.0, None),
    ("=EXP(1)", 2.718281828459045, None), ("=EXP(0)", 1.0, None), ("=EXP(B1)", 1.0, None),
    ("=EXP(#N/A)", Y, None), ('=EXP("1")', 2.718281828459045, None), ("=EXP(1000)", N, None),
    ("=LN(86)", 4.454347296253507, None), ("=LN(1)", 0.0, None), ("=LN(0)", N, None), ("=LN(B1)", N, None),
    ("=LN(#N/A)", Y, None), ('=LN("2,718281828459045")', 1.0, None),
    ("=LOG(10)", 1.0, None), ("=LOG(8,2)", 3.0, None), ("=LOG(0)", N, None), ("=LOG(10,1)", B0, None),
    ("=LOG(B1)", N, None), ("=LOG(#N/A)", Y, None), ('=LOG("100","10")', 2.0, None),
    ("=LOG10(100)", 2.0, None), ("=LOG10(0)", N, None), ("=LOG10(#N/A)", Y, None), ('=LOG10("1000")', 3.0, None),
    ("=LOG10(B1)", N, None),
    # PRODUCT
    ("=PRODUCT(A1:A3)", 6000.0, V1), ("=PRODUCT(A1:A4)", 6000.0, V1), ("=PRODUCT(B1:B3)", 0.0, V1),
    ("=PRODUCT(A1:A3)", Y, VH), ('=PRODUCT(A1:A2,"2",TRUE)', 400.0, V1),
    # SUMIF / SUMIFS / SUMPRODUCT
    ('=SUMIF(A1:A4,">15")', 50.0, V1), ('=SUMIF(A1:A3,">15",C1:C3)', 0.0, {"A1": 10, "A2": 20, "A3": 30}),
    ('=SUMIF(B1:B3,">1")', 0.0, V1), ('=SUMIF(A1:A3,">5",B1:B3)', Y, BH),
    ('=SUMIF(A1:A3,"a",C1:C3)', 4.0, AC), ('=SUMIF(A1:A3,"A*",C1:C3)', 4.0, AC), ("=SUMIF(A1:A3,20)", 20.0, CC),
    ('=SUMIF(A1:A4,"<>x")', 60.0, V1),
    ('=SUMIFS(C1:C3,A1:A3,"a",C1:C3,">1")', 3.0, AC), ('=SUMIFS(E1:E3,F1:F3,">1")', 0.0, None),
    ('=SUMIFS(B1:B3,A1:A3,">5")', Y, BH), ('=SUMIFS(C1:C3,A1:A2,"a")', V, AC),
    ("=SUMPRODUCT(A1:A3,C1:C3)", 140.0, CC), ("=SUMPRODUCT(A1:A3)", 60.0, CC),
    ("=SUMPRODUCT(A1:A3,C1:C3)", 14.0, {"A1": 1, "A2": 2, "A3": "x", "C1": 4, "C2": 5, "C3": 6}),
    ("=SUMPRODUCT(E1:E3,F1:F3)", 0.0, None),
    ("=SUMPRODUCT(A1:A3,C1:C3)", Y, {"A1": 1, "A2": 2, "A3": 3, "C1": 4, "C2": D.YOK, "C3": 6}),
    ("=SUMPRODUCT(A1:A3,C1:C2)", V, CC), ("=SUMPRODUCT(--(A1:A3>1))", 2.0, {"A1": 1, "A2": 2, "A3": "x"}),
]

ISTATISTIK = [
    ("=AVERAGE(A1:A3)", 20.0, V1), ("=AVERAGE(B1:B3)", B0, V1), ("=AVERAGE(A1:A3)", Y, VH),
    ('=AVERAGE(A1:A4,"5",TRUE)', 13.2, V1),
    ("=COUNT(A1:A4)", 3.0, V1), ("=COUNT(B1:B3)", 0.0, V1), ("=COUNT(A1:A3)", 2.0, VH),
    ('=COUNT(A1:A6,"5","x",TRUE,1)', 6.0, V1),
    ("=COUNTA(A1:A5)", 4.0, V1), ("=COUNTA(B1:B3)", 0.0, V1), ("=COUNTA(A1:A3)", 3.0, VH),
    ('=COUNTA(A1:A6,"")', 6.0, V1),
    ("=COUNTBLANK(A1:A6)", 1.0, V1), ("=COUNTBLANK(B1:B3)", 3.0, V1), ("=COUNTBLANK(A1:A3)", 0.0, VH),
    ("=COUNTBLANK(A1:A5)", 1.0, V1),
    ('=COUNTIF(A1:A4,">15")', 2.0, V1), ('=COUNTIF(B1:B3,">0")', 0.0, V1), ('=COUNTIF(B1:B3,"")', 3.0, V1),
    ('=COUNTIF(A1:A3,">5")', 2.0, VH), ('=COUNTIF(A1:A3,"#N/A")', 1.0, VH),
    ('=COUNTIF(A1:A6,"x")', 1.0, V1), ("=COUNTIF(A1:A6,TRUE)", 1.0, V1), ('=COUNTIF(A1:A4,"<>x")', 3.0, V1),
    ('=COUNTIF(A1:A4,"?")', 1.0, V1), ("=COUNTIF(A1:A4,10)", 1.0, V1),
    ('=COUNTIFS(A1:A3,">5",C1:C3,"<3")', 2.0, CC), ('=COUNTIFS(E1:E3,">5")', 0.0, None),
    ('=COUNTIFS(A1:A3,">5")', 2.0, VH), ('=COUNTIFS(A1:A3,">5",C1:C2,"<3")', V, CC),
    ("=MAX(A1:A4)", 30.0, V1), ("=MAX(B1:B3)", 0.0, V1), ("=MAX(A1:A3)", Y, VH), ('=MAX(A1:A4,"50")', 50.0, V1),
    ("=MAX(A1:A4,TRUE)", 30.0, V1),
    ("=MIN(A1:A4)", 10.0, V1), ("=MIN(B1:B3)", 0.0, V1), ("=MIN(A1:A3)", Y, VH), ('=MIN(A1:A4,"5")', 5.0, V1),
    ("=MIN(A1:A4,TRUE)", 1.0, V1),
    ('=MAXIFS(C1:C3,A1:A3,">10")', 3.0, CC), ('=MAXIFS(E1:E3,F1:F3,">1")', 0.0, None),
    ('=MAXIFS(B1:B3,A1:A3,">5")', Y, BH), ('=MAXIFS(C1:C3,A1:A2,">5")', V, CC),
    ('=MINIFS(C1:C3,A1:A3,">10")', 2.0, CC), ('=MINIFS(E1:E3,F1:F3,">1")', 0.0, None),
    ('=MINIFS(B1:B3,A1:A3,">5")', Y, BH), ('=MINIFS(C1:C3,A1:A3,"x")', 0.0, CC),
    ("=MEDIAN(A1:A3)", 20.0, V1), ("=MEDIAN(1,2,3,4)", 2.5, None), ("=MEDIAN(B1:B3)", N, V1),
    ("=MEDIAN(A1:A3)", Y, VH), ('=MEDIAN(A1:A4,"100")', 25.0, V1),
    ("=MODE(1,2,2,3)", 2.0, None), ("=MODE(1,2,3)", Y, None), ("=MODE(B1:B3)", Y, V1),
    ("=MODE(A1:A3)", Y, VH), ('=MODE(A1:A4,"20")', 20.0, V1),
    ("=STDEV(2,4,4,4,5,5,7,9)", 2.138089935299395, None), ("=STDEV(5)", B0, None), ("=STDEV(B1:B3)", B0, V1),
    ("=STDEV(A1:A3)", Y, VH), ("=STDEV(A1:A4)", 10.0, V1),
    ("=VAR(2,4,4,4,5,5,7,9)", 4.571428571428571, None), ("=VAR(1)", B0, None), ("=VAR(B1:B3)", B0, V1),
    ("=VAR(A1:A3)", Y, VH), ("=VAR(A1:A4)", 100.0, V1),
    ("=LARGE(A1:A3,1)", 30.0, V1), ("=LARGE(A1:A3,2)", 20.0, V1), ("=LARGE(A1:A3,4)", N, V1),
    ("=LARGE(B1:B3,1)", N, V1), ("=LARGE(A1:A3,1)", Y, VH), ("=LARGE(A1:A4,2)", 20.0, V1),
    ("=SMALL(A1:A3,1)", 10.0, V1), ("=SMALL(A1:A3,3)", 30.0, V1), ("=SMALL(A1:A3,0)", N, V1),
    ("=SMALL(B1:B3,1)", N, V1), ("=SMALL(A1:A3,1)", Y, VH), ("=SMALL(A1:A4,2)", 20.0, V1),
    ("=RANK(20,A1:A3)", 2.0, V1), ("=RANK(20,A1:A3,1)", 2.0, V1), ("=RANK(10,A1:A3,1)", 1.0, V1),
    ("=RANK(99,A1:A3)", Y, V1), ("=RANK(20,B1:B3)", Y, V1), ("=RANK(20,A1:A3)", Y, VH),
    ('=RANK("20",A1:A4)', 2.0, V1),
]

MANTIK_BILGI = [
    ("=IFS(FALSE,1,TRUE,2)", 2.0, None), ("=IFS(FALSE,1)", Y, None), ("=IFS(B1,1,TRUE,2)", 2.0, None),
    ("=IFS(#N/A,1)", Y, None), ('=IFS("TRUE",1)', V, None), ('=IFS("DOĞRU",1)', 1.0, None),   # Excel-tr: yalnız yerel ad çevrilir (COM)
    ("=AND(TRUE,TRUE)", True, None), ("=AND(TRUE,FALSE)", False, None), ("=AND(B1:B3)", V, None),
    ("=AND(TRUE,#N/A)", Y, None), ("=AND(A1:A4)", True, V1), ('=AND(1,"x")', True, None), ('=AND("x")', V, None),   # metin argüman atlanır (Excel COM 2026-10-15)
    ("=OR(FALSE,TRUE)", True, None), ("=OR(FALSE,0)", False, None), ("=OR(B1:B3)", V, None),
    ("=OR(FALSE,#N/A)", Y, None), ("=OR(A1:A4)", True, V1), ('=OR(0,"x")', False, None),
    ("=XOR(TRUE,FALSE)", True, None), ("=XOR(TRUE,TRUE)", False, None), ("=XOR(B1:B3)", V, None),
    ("=XOR(TRUE,#N/A)", Y, None), ("=XOR(A1:A4)", True, {"A1": 1, "A2": 0, "A3": 0, "A4": "x"}),
    ("=NOT(TRUE)", False, None), ("=NOT(0)", True, None), ("=NOT(B1)", True, None), ("=NOT(#N/A)", Y, None),
    ('=NOT("x")', V, None), ('=NOT("TRUE")', V, None), ('=NOT("DOĞRU")', False, None),
    ("=TRUE()", True, None), ("=FALSE()", False, None), ("=TRUE()+1", 2.0, None), ("=FALSE()+#N/A", Y, None),
    ('=TRUE()&""', "DOĞRU", None),
    ('=IFERROR(1/0,"h")', "h", None), ('=IFERROR(5,"h")', 5.0, None), ('=IFERROR(B1,"h")', 0.0, None),
    ("=IFERROR(#N/A,B2)", 0.0, None), ('=IFERROR("a"+1,"bad")', "bad", None),
    ("=IFNA(#N/A,1)", 1.0, None), ("=IFNA(1/0,1)", B0, None), ("=IFNA(B1,5)", 0.0, None), ("=IFNA(2,3)", 2.0, None),
    ('=SWITCH(2,1,"a",2,"b","z")', "b", None), ('=SWITCH(9,1,"a","z")', "z", None), ('=SWITCH(9,1,"a")', Y, None),
    ('=SWITCH(B1,0,"zero","x")', "zero", None), ("=SWITCH(#N/A,1,2)", Y, None), ('=SWITCH("A","a",1)', 1.0, None),
    # bilgi
    ("=ISNUMBER(1)", True, None), ('=ISNUMBER("1")', False, None), ("=ISNUMBER(B1)", False, None),
    ("=ISNUMBER(#N/A)", False, None), ("=ISNUMBER(TRUE)", False, None),
    ('=ISTEXT("a")', True, None), ("=ISTEXT(1)", False, None), ("=ISTEXT(B1)", False, None),
    ("=ISTEXT(#N/A)", False, None),
    ("=ISBLANK(B1)", True, None), ("=ISBLANK(A1)", False, V1), ('=ISBLANK("")', False, None),
    ("=ISBLANK(#N/A)", False, None),
    ("=ISERROR(1/0)", True, None), ("=ISERROR(1)", False, None), ("=ISERROR(B1)", False, None),
    ('=ISERROR("a"+1)', True, None), ("=ISERROR(#N/A)", True, None),
    ("=ISNA(#N/A)", True, None), ("=ISNA(1/0)", False, None), ("=ISNA(1)", False, None), ("=ISNA(B1)", False, None),
    ("=ISLOGICAL(TRUE)", True, None), ("=ISLOGICAL(1)", False, None), ("=ISLOGICAL(B1)", False, None),
    ("=ISLOGICAL(#N/A)", False, None), ('=ISLOGICAL("TRUE")', False, None),
    ("=SUMPRODUCT(--ISNUMBER(A1:A4))", 3.0, V1),
]


@pytest.mark.parametrize("formul,beklenen,veri", MATEMATIK)
def test_matematik(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


@pytest.mark.parametrize("formul,beklenen,veri", ISTATISTIK)
def test_istatistik(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


@pytest.mark.parametrize("formul,beklenen,veri", MANTIK_BILGI)
def test_mantik_bilgi(formul, beklenen, veri):
    kontrol(formul, beklenen, veri)


def test_olcut_sozdizimi():
    kontrol('=COUNTIF(A1:A4,">=20")', 2.0, V1)
    kontrol('=COUNTIF(A1:A4,"<=20")', 2.0, V1)
    kontrol('=COUNTIF(A1:A4,"=10")', 1.0, V1)
    kontrol('=COUNTIF(A1:A3,"a*")', 2.0, AC)
    kontrol('=COUNTIF(A1:A3,"~*")', 0.0, AC)
    kontrol('=COUNTIF(A1:A3,"B")', 1.0, AC)                 # büyük/küçük harf duyarsız


def test_vektor_yayma():
    kontrol("=SUM(ROUND(A1:A3/3,1))", 20.0, {"A1": 10, "A2": 20, "A3": 30})   # 3,3+6,7+10
    kontrol("=SUM(ABS(A1:A3))", 6.0, {"A1": -1, "A2": -2, "A3": 3})
