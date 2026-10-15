"""Excel karşılaştırma vakaları üreticisi (293 işlev vakası): python araclar/excel_vaka_uret.py → araclar/vaka_fonk.json;
sonra .venv/Scripts/python araclar/excel_vaka.py araclar/vaka_fonk.json (gerçek Excel gerekir)."""
import json, os
SP = os.path.dirname(os.path.abspath(__file__))
V = []
n = [0]
def f(formul, h=None, **k):
    n[0] += 1
    V.append(dict(id=f"F{n[0]:03d}", formul=formul, hucreler=h, **k))

NUM = {"A1": 1, "A2": 4, "A3": 9, "A4": 16, "A5": 25}
MIX = {"A1": 3, "A2": "x", "A3": 7, "A4": True, "A5": None, "A6": "=1/0", "A7": 2.5}
TXT = {"A1": "Ali", "A2": "veli", "A3": "İstanbul", "A4": "ıspanak", "A5": "Çorum"}

# matematik
for fm in ["=SUM(A1:A5)", "=AVERAGE(A1:A5)", "=MEDIAN(A1:A5)", "=MIN(A1:A5)", "=MAX(A1:A5)", "=LARGE(A1:A5,2)", "=SMALL(A1:A5,2)",
           "=STDEV(A1:A5)", "=VAR(A1:A5)", "=PRODUCT(A1:A5)", "=SUMPRODUCT(A1:A5,A1:A5)", "=ROUND(A3/7,2)", "=ROUNDUP(2.341,2)", "=ROUNDDOWN(-2.349,2)",
           "=ROUND(-2.5,0)", "=ROUND(2.5,0)", "=ROUND(1234.567,-2)", "=INT(-2.5)", "=TRUNC(-2.567,1)", "=MOD(-7,3)", "=MOD(7,-3)", "=MOD(5.5,2)", "=ABS(-3)", "=SIGN(-2)",
           "=POWER(2,10)", "=POWER(-8,1/3)", "=SQRT(16)", "=SQRT(-1)", "=EXP(1)", "=LN(10)", "=LOG(100,10)", "=LOG10(1000)", "=LOG(8,2)", "=PI()", "=CEILING(2.1,0.5)", "=FLOOR(2.9,0.5)", "=CEILING(-2.1,2)", "=FLOOR(-2.1,2)",
           "=SIN(1)", "=COS(1)", "=TAN(1)", "=ATAN(1)", "=DEGREES(PI())", "=RADIANS(180)", "=RAND()>=0", "=RANDBETWEEN(1,1)", "=SUMIF(A1:A5,\">4\")", "=SUMIF(A1:A5,\">4\",A1:A5)",
           "=SUMIFS(A1:A5,A1:A5,\">1\",A1:A5,\"<20\")", "=COUNTIF(A1:A5,\">4\")", "=COUNTIFS(A1:A5,\">1\",A1:A5,\"<20\")", "=AVERAGEIF(A1:A5,\">4\")", "=MAXIFS(A1:A5,A1:A5,\"<20\")", "=MINIFS(A1:A5,A1:A5,\">1\")",
           "=SUBTOTAL(9,A1:A5)", "=SUBTOTAL(1,A1:A5)", "=RANK(9,A1:A5)", "=RANK(9,A1:A5,1)", "=MODE(1,2,2,3)", "=COUNT(A1:A5)", "=COUNTA(A1:A5)", "=COUNTBLANK(A1:A7)"]:
    f(fm, NUM)
for fm in ["=SUM(A1:A7)", "=AVERAGE(A1:A5)", "=COUNT(A1:A7)", "=COUNTA(A1:A7)", "=MAX(A1:A5)", "=MIN(A1:A4)", "=SUM(A1,A2,A4)", "=SUM(A2:A3)", "=AVERAGE(A1,A2)", "=A1+A2", "=A1+A4", "=A1&A2", "=SUM(A1:A3,A4)", "=SUMPRODUCT(A1:A3,A1:A3)",
           "=IFERROR(A6,\"hata\")", "=ISERROR(A6)", "=ISNUMBER(A1)", "=ISNUMBER(A2)", "=ISTEXT(A2)", "=ISBLANK(A5)", "=ISLOGICAL(A4)", "=ISNA(NA())", "=ISERR(A6)", "=N(A4)", "=N(A2)", "=T(A2)", "=T(A1)", "=TYPE(A2)", "=TYPE(A4)", "=TYPE(A6)", "=ERROR.TYPE(A6)", "=COUNTIF(A1:A7,TRUE)", "=COUNTIF(A1:A7,\"x\")"]:
    f(fm, MIX)
# metin
for fm in ["=UPPER(A1)", "=LOWER(A1)", "=UPPER(A3)", "=LOWER(A3)", "=UPPER(A4)", "=LOWER(A5)", "=PROPER(\"istanbul ıspanak\")", "=PROPER(\"ali veli-ahmet\")", "=LEN(A3)", "=LEFT(A3,3)", "=RIGHT(A3,3)", "=MID(A3,2,4)",
           "=FIND(\"a\",A1)", "=FIND(\"I\",A4)", "=SEARCH(\"I\",A4)", "=SEARCH(\"i\",A3)", "=SEARCH(\"İ\",A3)", "=FIND(\"A\",\"banana\")", "=SEARCH(\"A\",\"banana\")", "=SEARCH(\"a?a\",\"banana\")", "=SEARCH(\"n*a\",\"banana\")",
           "=SUBSTITUTE(\"a-b-c\",\"-\",\"+\")", "=SUBSTITUTE(\"a-b-c\",\"-\",\"+\",2)", "=REPLACE(\"abcdef\",2,3,\"X\")", "=TRIM(\"  a   b  \")", "=CLEAN(\"a\"&CHAR(10)&\"b\")", "=CONCATENATE(A1,\"-\",A2)", "=CONCAT(A1:A2)", "=TEXTJOIN(\",\",TRUE,A1:A5)",
           "=REPT(\"ab\",3)", "=EXACT(A1,\"ali\")", "=EXACT(A1,\"Ali\")", "=A1=\"ALI\"", "=A3=\"istanbul\"", "=A3=\"ISTANBUL\"", "=CHAR(65)", "=CODE(\"A\")", "=UNICHAR(305)", "=UNICODE(\"ı\")", "=VALUE(\"1.234,5\")", "=VALUE(\"12%\")", "=VALUE(\"1e3\")", "=VALUE(\"abc\")",
           "=NUMBERVALUE(\"1.234,5\",\",\",\".\")", "=TEXT(1234.5,\"#,##0.00\")", "=TEXT(0.256,\"0.0%\")", "=TEXT(45000,\"dd.mm.yyyy\")", "=TEXT(45000,\"dddd\")", "=TEXT(45000,\"mmmm\")", "=TEXT(1.5,\"0.00\")", "=TEXT(-1.5,\"0\")", "=TEXT(0.5,\"# ?/?\")",
           "=TEXT(5,\"00\")", "=TEXT(TRUE,\"0\")", "=TEXT(\"abc\",\"@\")", "=TEXT(1234567,\"#,##0,\")", "=T(\"a\")", "=LEN(\"\")", "=LEFT(\"abc\",0)", "=LEFT(\"abc\",10)", "=MID(\"abc\",0,1)", "=MID(\"abc\",5,1)", "=LEFT(\"abc\",-1)", "=FIXED(1234.567,1)", "=DOLLAR(1234.5)", "=ROMAN(1999)", "=ARABIC(\"MCMXCIX\")"]:
    f(fm, TXT)
# tarih
for fm in ["=DATE(2026,10,15)", "=DATE(2026,13,1)", "=DATE(2026,0,1)", "=DATE(2026,1,0)", "=DATE(2026,2,30)", "=DATE(26,1,1)", "=DATE(1899,1,1)", "=DATE(2026,-1,1)", "=YEAR(45000)", "=MONTH(45000)", "=DAY(45000)", "=WEEKDAY(45000)", "=WEEKDAY(45000,2)", "=WEEKDAY(45000,3)", "=WEEKNUM(45000)", "=WEEKNUM(45000,2)",
           "=ISOWEEKNUM(45000)", "=EDATE(45000,1)", "=EDATE(45000,-13)", "=EOMONTH(45000,0)", "=EOMONTH(45000,5)", "=DATEDIF(44000,45000,\"d\")", "=DATEDIF(44000,45000,\"m\")", "=DATEDIF(44000,45000,\"y\")", "=DATEDIF(44000,45000,\"ym\")", "=DATEDIF(44000,45000,\"md\")", "=DATEDIF(45000,44000,\"d\")",
           "=DAYS(45000,44000)", "=DAYS360(44000,45000)", "=NETWORKDAYS(45000,45030)", "=NETWORKDAYS(45000,45030,45005)", "=WORKDAY(45000,10)", "=WORKDAY(45000,-10)", "=WORKDAY(45000,10,45001)", "=NETWORKDAYS.INTL(45000,45030)", "=YEARFRAC(44000,45000)", "=YEARFRAC(44000,45000,1)",
           "=TIME(12,30,45)", "=TIME(25,0,0)", "=TIME(0,0,86400)", "=HOUR(0.75)", "=MINUTE(0.7525)", "=SECOND(0.7525)", "=HOUR(45000.999999)", "=TIMEVALUE(\"12:30\")", "=DATEVALUE(\"15.10.2026\")", "=DATEVALUE(\"2026-10-15\")", "=DATEVALUE(\"15/10/2026\")", "=DATEVALUE(\"1 Mart 2026\")", "=DATEVALUE(\"1.3.2026\")",
           "=VALUE(\"15.10.2026\")", "=VALUE(\"12:30\")", "=DATE(2026,10,15)-DATE(2026,1,1)", "=DATE(2026,1,31)+30", "=TEXT(DATE(2026,10,15),\"dddd d mmmm yyyy\")", "=TEXT(0.5,\"hh:mm\")", "=TEXT(1.5,\"[h]:mm\")"]:
    f(fm)
# mantık/arama
for fm in ["=IF(1>2,\"a\",\"b\")", "=IF(A1>0,A1)", "=IF(FALSE,1)", "=IFS(A1>5,\"a\",A1>0,\"b\")", "=IFS(A1>5,\"a\")", "=AND(TRUE,1)", "=AND(TRUE,\"a\")", "=OR(FALSE,0)", "=NOT(0)", "=XOR(TRUE,TRUE)", "=IFERROR(1/0,\"x\")", "=IFNA(NA(),\"y\")", "=IFNA(1/0,\"y\")",
           "=SWITCH(2,1,\"a\",2,\"b\",\"c\")", "=SWITCH(9,1,\"a\",2,\"b\",\"c\")", "=SWITCH(9,1,\"a\")", "=CHOOSE(2,\"a\",\"b\",\"c\")", "=CHOOSE(4,\"a\",\"b\")", "=INDEX(A1:B3,2,2)", "=INDEX(A1:B3,0,2)", "=INDEX(A1:B3,4,1)", "=MATCH(\"b\",B1:B3,0)", "=MATCH(\"B\",B1:B3,0)", "=MATCH(5,A1:A3,1)",
           "=VLOOKUP(2,A1:B3,2,FALSE)", "=VLOOKUP(2,A1:B3,3,FALSE)", "=VLOOKUP(5,A1:B3,2,FALSE)", "=VLOOKUP(5,A1:B3,2,TRUE)", "=VLOOKUP(0,A1:B3,2,TRUE)", "=HLOOKUP(2,A1:B3,2,FALSE)", "=XLOOKUP(2,A1:A3,B1:B3)", "=XLOOKUP(5,A1:A3,B1:B3,\"yok\")", "=XLOOKUP(5,A1:A3,B1:B3,,1)", "=XLOOKUP(5,A1:A3,B1:B3,,-1)", "=XMATCH(2,A1:A3)",
           "=ROW(A5)", "=COLUMN(C1)", "=ROWS(A1:B3)", "=COLUMNS(A1:B3)", "=ADDRESS(2,3)", "=ADDRESS(2,3,4)", "=OFFSET(A1,1,1)", "=INDIRECT(\"A2\")", "=SUM(INDIRECT(\"A1:A3\"))", "=TRANSPOSE(A1:A3)", "=SORT(A1:A3,1,-1)", "=UNIQUE(A1:A3)", "=FILTER(A1:A3,A1:A3>1)", "=SEQUENCE(3)", "=SEQUENCE(2,2)", "=TOCOL(A1:B2)",
           "=ROWS(SORT(A1:A3))", "=SUM(SEQUENCE(5))", "=COUNTA(UNIQUE(A1:A3))", "=LET(x,5,x*2)", "=TEXT(A1,\"0.00\")&\"x\""]:
    f(fm, {"A1": 1, "A2": 2, "A3": 3, "B1": "a", "B2": "b", "B3": "c"})
# finans
for fm in ["=PMT(0.01,12,-1000)", "=PMT(0.01,12,-1000,0,1)", "=FV(0.01,12,-100)", "=PV(0.01,12,-100)", "=NPV(0.1,100,200,300)", "=IRR(A1:A4)", "=RATE(12,-100,1000)", "=NPER(0.01,-100,1000)", "=IPMT(0.01,1,12,-1000)", "=PPMT(0.01,1,12,-1000)", "=SLN(1000,100,5)", "=DB(1000,100,5,1)", "=DDB(1000,100,5,1)", "=SYD(1000,100,5,1)", "=EFFECT(0.1,4)", "=NOMINAL(0.1,4)", "=XNPV(0.1,A1:A3,B1:B3)", "=MIRR(A1:A4,0.1,0.12)"]:
    f(fm, {"A1": -1000, "A2": 300, "A3": 400, "A4": 500, "B1": 44000, "B2": 44200, "B3": 44400})
json.dump(V, open(os.path.join(SP, "vaka_fonk.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(V))
