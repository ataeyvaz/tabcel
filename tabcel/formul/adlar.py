"""Fonksiyon adları: kanonik İngilizce ⇄ Türkçe Excel. Qt yok.

CLAUDE.md kural 4: yalnız Microsoft'un tr-tr belgesiyle DOĞRULANMIŞ adlar yazılır.
Dikkat: support.microsoft.com/tr-tr "Excel işlevleri (alfabetik)" sayfası makine çevirisi
hataları içeriyor (ör. PMT için "FAİZ_ORANI", "ADRESİMİZ"); her ad o işlevin kendi tr-tr
sayfasındaki sözdizimi satırından doğrulanmalı. Doğrulanamayan → surec.md §8b-6.
Türkçesi yazılmamış fonksiyon İngilizce adıyla gösterilir ve yazılabilir.
"""
from typing import Dict, Optional

from .yerel import tr_buyuk

# İngilizce → Türkçe. Doğrulama: işlevin tr-tr sayfası (tarih).
EN_TR: Dict[str, str] = {
    # 2026-10-09: her ad, işlevin kendi tr-tr sayfasının başlığı + sözdizimi/örnek satırıyla
    # doğrulandı (support.microsoft.com/tr-tr/excel/functions/<ad>-function; IS* ailesi "E işlevleri"
    # sayfası; EĞERSAY ve BUL: Microsoft tr-tr sayfaları). Alfabetik liste sayfasına güvenilmedi.
    "SUM": "TOPLA", "SUMIF": "ETOPLA", "SUMIFS": "ÇOKETOPLA", "SUMPRODUCT": "TOPLA.ÇARPIM", "PRODUCT": "ÇARPIM", "ROUND": "YUVARLA", "ROUNDUP": "YUKARIYUVARLA", "ROUNDDOWN": "AŞAĞIYUVARLA", "INT": "TAMSAYI", "MOD": "MOD", "ABS": "MUTLAK", "SQRT": "KAREKÖK", "POWER": "KUVVET", "PI": "Pİ", "RAND": "S_SAYI_ÜRET", "RANDBETWEEN": "RASTGELEARADA", "CEILING": "TAVANAYUVARLA", "FLOOR": "TABANAYUVARLA", "TRUNC": "NSAT", "SIGN": "İŞARET", "EXP": "ÜS", "LN": "LN", "LOG": "LOG", "LOG10": "LOG10",
    "AVERAGE": "ORTALAMA", "AVERAGEIF": "EĞERORTALAMA", "AVERAGEIFS": "ÇOKEĞERORTALAMA", "COUNT": "BAĞ_DEĞ_SAY", "COUNTA": "BAĞ_DEĞ_DOLU_SAY", "COUNTBLANK": "BOŞLUKSAY", "COUNTIF": "EĞERSAY", "COUNTIFS": "ÇOKEĞERSAY", "MAX": "MAK", "MIN": "MİN", "MAXIFS": "ÇOKEĞERMAK", "MINIFS": "ÇOKEĞERMİN", "MEDIAN": "ORTANCA", "MODE": "ENÇOK_OLAN", "STDEV": "STDSAPMA", "SUBTOTAL": "ALTTOPLAM", "VAR": "VAR", "LARGE": "BÜYÜK", "SMALL": "KÜÇÜK", "RANK": "RANK",
    "IF": "EĞER", "IFS": "ÇOKEĞER", "AND": "VE", "OR": "YADA", "NOT": "DEĞİL", "XOR": "ÖZELVEYA", "IFERROR": "EĞERHATA", "IFNA": "EĞERYOKSA", "SWITCH": "İLKEŞLEŞEN", "TRUE": "DOĞRU", "FALSE": "YANLIŞ",
    "VLOOKUP": "DÜŞEYARA", "HLOOKUP": "YATAYARA", "XLOOKUP": "ÇAPRAZARA", "INDEX": "İNDİS", "MATCH": "KAÇINCI", "LOOKUP": "ARA", "XMATCH": "ÇAPRAZEŞLEŞTİR", "CHOOSE": "ELEMAN", "ROW": "SATIR", "COLUMN": "SÜTUN", "ROWS": "SATIRSAY", "COLUMNS": "SÜTUNSAY", "INDIRECT": "DOLAYLI", "OFFSET": "KAYDIR",
    "CONCATENATE": "BİRLEŞTİR", "CONCAT": "ARALIKBİRLEŞTİR", "TEXTJOIN": "METİNBİRLEŞTİR", "LEFT": "SOLDAN", "RIGHT": "SAĞDAN", "MID": "PARÇAAL", "LEN": "UZUNLUK", "UPPER": "BÜYÜKHARF", "LOWER": "KÜÇÜKHARF", "PROPER": "YAZIM.DÜZENİ", "TRIM": "KIRP", "FIND": "BUL", "SEARCH": "MBUL", "SUBSTITUTE": "YERİNEKOY", "REPLACE": "DEĞİŞTİR", "TEXT": "METNEÇEVİR", "VALUE": "SAYIYAÇEVİR", "REPT": "YİNELE", "EXACT": "ÖZDEŞ",
    "TODAY": "BUGÜN", "NOW": "ŞİMDİ", "DATE": "TARİH", "TIME": "ZAMAN", "YEAR": "YIL", "MONTH": "AY", "DAY": "GÜN", "HOUR": "SAAT", "MINUTE": "DAKİKA", "SECOND": "SANİYE", "WEEKDAY": "HAFTANINGÜNÜ", "WEEKNUM": "HAFTASAY", "EDATE": "SERİTARİH", "EOMONTH": "SERİAY", "DATEDIF": "ETARİHLİ", "DAYS": "GÜNSAY", "NETWORKDAYS": "TAMİŞGÜNÜ", "WORKDAY": "İŞGÜNÜ",
    "NA": "YOKSAY", "ISNUMBER": "ESAYIYSA", "ISTEXT": "EMETİNSE", "ISBLANK": "EBOŞSA", "ISERROR": "EHATALIYSA", "ISNA": "EYOKSA", "ISLOGICAL": "EMANTIKSALSA",
    "PMT": "DEVRESEL_ÖDEME", "FV": "GD", "PV": "BD", "RATE": "FAİZ_ORANI", "NPV": "NBD", "IRR": "İÇ_VERİM_ORANI",
    # 2026-10-11 (Faz 8e): dinamik dizi işlevleri — Microsoft sayfaları yerine gerçek Excel 365'ten (COM `Formula2Local`,
    # Türkçe bölgesel ayar) doğrulandı; harf harf kod noktasıyla okundu.
    "FILTER": "FİLTRE", "SORT": "SIRALA", "SORTBY": "SIRALAÖLÇÜT", "UNIQUE": "BENZERSİZ", "SEQUENCE": "SIRALI",
    "RANDARRAY": "RASGDİZİ", "TAKE": "AL", "DROP": "BIRAK", "VSTACK": "DÜŞEYYIĞ", "HSTACK": "YATAYYIĞ",
    "TOCOL": "SÜTUNA", "TOROW": "SATIRA", "CHOOSECOLS": "SÜTUNSEÇ", "CHOOSEROWS": "SATIRSEÇ", "EXPAND": "GENİŞLET",
    "TRANSPOSE": "DEVRİK_DÖNÜŞÜM", "LET": "LET",
}

EN_TR["DEC2HEX"] = "DEC2HEX"
EN_TR["DEC2OCT"] = "DEC2OCT"
EN_TR["DEC2BIN"] = "DEC2BIN"
EN_TR["HEX2BIN"] = "HEX2BIN"
EN_TR["HEX2DEC"] = "HEX2DEC"
EN_TR["OCT2BIN"] = "OCT2BIN"
EN_TR["OCT2DEC"] = "OCT2DEC"
EN_TR["BIN2HEX"] = "BIN2HEX"
EN_TR["BIN2OCT"] = "BIN2OCT"
EN_TR["BIN2DEC"] = "BIN2DEC"
EN_TR["FISHER"] = "FISHER"
EN_TR["GAMMA"] = "GAMA"
EN_TR["ERF"] = "HATAİŞLEV"
EN_TR["GESTEP"] = "BESINIR"
EN_TR["DELTA"] = "DELTA"
EN_TR["BITRSHIFT"] = "BİTSAĞAKAYDIR"
EN_TR["BITLSHIFT"] = "BİTSOLAKAYDIR"
EN_TR["BITXOR"] = "BİTÖZELVEYA"
EN_TR["BITOR"] = "BİTVEYA"
EN_TR["BITAND"] = "BİTVE"
EN_TR["BASE"] = "TABAN"
EN_TR["ARABIC"] = "ARAP"
EN_TR["ROMAN"] = "ROMEN"
EN_TR["SERIESSUM"] = "SERİTOPLA"
EN_TR["SUMXMY2"] = "TOPXEY2"
EN_TR["SUMX2PY2"] = "TOPX2AY2"
EN_TR["SUMX2MY2"] = "TOPX2EY2"
EN_TR["SUMSQ"] = "TOPKARE"
EN_TR["FLOOR.MATH"] = "TABANAYUVARLA.MATEMATİK"
EN_TR["CEILING.MATH"] = "TAVANAYUVARLA.MATEMATİK"
EN_TR["MROUND"] = "KYUVARLA"
EN_TR["QUOTIENT"] = "BÖLÜM"
EN_TR["ODD"] = "TEK"
EN_TR["EVEN"] = "ÇİFT"
EN_TR["MULTINOMIAL"] = "ÇOKTERİMLİ"
EN_TR["LCM"] = "OKEK"
EN_TR["GCD"] = "OBEB"
EN_TR["PERMUT"] = "PERMÜTASYON"
EN_TR["COMBINA"] = "KOMBİNASYONA"
EN_TR["COMBIN"] = "KOMBİNASYON"
EN_TR["FACTDOUBLE"] = "ÇİFTFAKTÖR"
EN_TR["FACT"] = "ÇARPINIM"
EN_TR["SQRTPI"] = "KAREKÖKPİ"
EN_TR["RADIANS"] = "RADYAN"
EN_TR["DEGREES"] = "DERECE"
EN_TR["ACOTH"] = "ACOTH"
EN_TR["ACOT"] = "ACOT"
EN_TR["COT"] = "COT"
EN_TR["CSC"] = "CSC"
EN_TR["SEC"] = "SEC"
EN_TR["ATAN2"] = "ATAN2"
EN_TR["ATANH"] = "ATANH"
EN_TR["ACOSH"] = "ACOSH"
EN_TR["ACOS"] = "ACOS"
EN_TR["ASINH"] = "ASİNH"
EN_TR["ASIN"] = "ASİN"
EN_TR["ATAN"] = "ATAN"
EN_TR["TAN"] = "TAN"
EN_TR["TANH"] = "TANH"
EN_TR["COSH"] = "COSH"
EN_TR["SINH"] = "SİNH"
EN_TR["COS"] = "COS"
EN_TR["SIN"] = "SİN"
EN_TR["EXPON.DIST"] = "ÜSTEL.DAĞ"
EN_TR["CONFIDENCE.NORM"] = "GÜVENİLİRLİK.NORM"
EN_TR["Z.TEST"] = "Z.TEST"
EN_TR["WEIBULL.DIST"] = "WEIBULL.DAĞ"
EN_TR["VARP"] = "VARS"
EN_TR["VARA"] = "VARA"
EN_TR["VAR.S"] = "VAR.S"
EN_TR["VAR.P"] = "VAR.P"
EN_TR["TRIMMEAN"] = "KIRPORTALAMA"
EN_TR["STDEVP"] = "STDSAPMAS"
EN_TR["STDEVA"] = "STDSAPMAA"
EN_TR["STDEV.S"] = "STDSAPMA.S"
EN_TR["STDEV.P"] = "STDSAPMA.P"
EN_TR["STANDARDIZE"] = "STANDARTLAŞTIRMA"
EN_TR["SLOPE"] = "EĞİM"
EN_TR["SKEW"] = "ÇARPIKLIK"
EN_TR["RSQ"] = "RKARE"
EN_TR["RANK.EQ"] = "RANK.EŞİT"
EN_TR["RANK.AVG"] = "RANK.ORT"
EN_TR["QUARTILE.INC"] = "DÖRTTEBİRLİK.DHL"
EN_TR["QUARTILE.EXC"] = "DÖRTTEBİRLİK.HRC"
EN_TR["QUARTILE"] = "DÖRTTEBİRLİK"
EN_TR["POISSON.DIST"] = "POISSON.DAĞ"
EN_TR["PERCENTRANK.INC"] = "YÜZDERANK.DHL"
EN_TR["PERCENTRANK.EXC"] = "YÜZDERANK.HRC"
EN_TR["PERCENTRANK"] = "YÜZDERANK"
EN_TR["PERCENTILE.INC"] = "YÜZDEBİRLİK.DHL"
EN_TR["PERCENTILE.EXC"] = "YÜZDEBİRLİK.HRC"
EN_TR["PERCENTILE"] = "YÜZDEBİRLİK"
EN_TR["PEARSON"] = "PEARSON"
EN_TR["NORM.S.INV"] = "NORM.S.TERS"
EN_TR["NORM.S.DIST"] = "NORM.S.DAĞ"
EN_TR["NORM.INV"] = "NORM.TERS"
EN_TR["NORM.DIST"] = "NORM.DAĞ"
EN_TR["MODE.SNGL"] = "ENÇOK_OLAN.TEK"
EN_TR["MODE.MULT"] = "ENÇOK_OLAN.ÇOK"
EN_TR["MINA"] = "MİNA"
EN_TR["MAXA"] = "MAKA"
EN_TR["KURT"] = "BASIKLIK"
EN_TR["INTERCEPT"] = "KESMENOKTASI"
EN_TR["HARMEAN"] = "HARORT"
EN_TR["GEOMEAN"] = "GEOORT"
EN_TR["FORECAST.LINEAR"] = "TAHMİN.DOĞRUSAL"
EN_TR["FORECAST"] = "TAHMİN"
EN_TR["DEVSQ"] = "SAPKARE"
EN_TR["COVARIANCE.S"] = "KOVARYANS.S"
EN_TR["COVARIANCE.P"] = "KOVARYANS.P"
EN_TR["CORREL"] = "KORELASYON"
EN_TR["AVERAGEA"] = "ORTALAMAA"
EN_TR["AVEDEV"] = "ORTSAP"
EN_TR["TEXTBEFORE"] = "ÖNCEKİMETİN"
EN_TR["TEXTAFTER"] = "SONRAKİMETİN"
EN_TR["NUMBERVALUE"] = "SAYIDEĞERİ"
EN_TR["DOLLAR"] = "LİRA"
EN_TR["FIXED"] = "SAYIDÜZENLE"
EN_TR["N"] = "S"
EN_TR["T"] = "M"
EN_TR["ENCODEURL"] = "URLKODLA"
EN_TR["CLEAN"] = "TEMİZ"
EN_TR["UNICODE"] = "UNICODE"
EN_TR["UNICHAR"] = "UNICODEKARAKTERİ"
EN_TR["CODE"] = "KOD"
EN_TR["CHAR"] = "DAMGA"
EN_TR["XIRR"] = "AİÇVERİMORANI"
EN_TR["XNPV"] = "ANBD"
EN_TR["MIRR"] = "D_İÇ_VERİM_ORANI"
EN_TR["DDB"] = "ÇİFTAZALANBAKİYE"
EN_TR["DB"] = "AZALANBAKİYE"
EN_TR["SYD"] = "YAT"
EN_TR["SLN"] = "DA"
EN_TR["RRI"] = "GERÇEKLEŞENYATIRIMGETİRİSİ"
EN_TR["NPER"] = "TAKSİT_SAYISI"
EN_TR["NOMINAL"] = "NOMİNAL"
EN_TR["EFFECT"] = "ETKİN"
EN_TR["CUMPRINC"] = "TOPANAPARA"
EN_TR["CUMIPMT"] = "TOPÖDENENFAİZ"
EN_TR["PPMT"] = "ANA_PARA_ÖDEMESİ"
EN_TR["IPMT"] = "FAİZTUTARI"
EN_TR["ADDRESS"] = "ADRES"
EN_TR["SHEETS"] = "SAYFALAR"
EN_TR["SHEET"] = "SAYFA"
EN_TR["ISFORMULA"] = "EFORMÜLSE"
EN_TR["ISREF"] = "EREFSE"
EN_TR["TYPE"] = "TÜR"
EN_TR["ERROR.TYPE"] = "HATA.TİPİ"
EN_TR["ISODD"] = "TEKMİ"
EN_TR["ISEVEN"] = "ÇİFTMİ"
EN_TR["ISNONTEXT"] = "EMETİNDEĞİLSE"
EN_TR["ISERR"] = "EHATA"
EN_TR["WORKDAY.INTL"] = "İŞGÜNÜ.ULUSL"
EN_TR["NETWORKDAYS.INTL"] = "TAMİŞGÜNÜ.ULUSL"
EN_TR["YEARFRAC"] = "YILORAN"
EN_TR["DAYS360"] = "GÜN360"
EN_TR["ISOWEEKNUM"] = "ISOHAFTASAY"
EN_TR["TIMEVALUE"] = "ZAMANSAYISI"
EN_TR["DATEVALUE"] = "TARİHSAYISI"
EN_TR["DSUM"] = "VSEÇTOPLA"
EN_TR["DMIN"] = "VSEÇMİN"
EN_TR["DMAX"] = "VSEÇMAK"
EN_TR["DGET"] = "VAL"
EN_TR["DCOUNT"] = "VSEÇSAY"
EN_TR["DAVERAGE"] = "VSEÇORT"
EN_TR["MUNIT"] = "BİRİMMATRİS"
EN_TR["MMULT"] = "DÇARP"
EN_TR["MINVERSE"] = "DİZEY_TERS"
EN_TR["MDETERM"] = "DETERMİNANT"
EN_TR["IMAGINARY"] = "SANAL"
EN_TR["WRAPROWS"] = "SATIRSAR"
EN_TR["WRAPCOLS"] = "SÜTUNSAR"
EN_TR["HYPERLINK"] = "KÖPRÜ"
EN_TR["FORMULATEXT"] = "FORMÜLMETNİ"
EN_TR["TEXTSPLIT"] = "METİNBÖL"
EN_TR["TREND"] = "EĞİLİM"
EN_TR["LINEST"] = "DOT"
EN_TR["GROWTH"] = "BÜYÜME"
EN_TR["FREQUENCY"] = "SIKLIK"
EN_TR["DCOUNTA"] = "VSEÇSAYDOLU"
EN_TR["DPRODUCT"] = "VSEÇÇARP"
EN_TR["AGGREGATE"] = "TOPLAMA"
EN_TR["CONVERT"] = "ÇEVİR"
# Tabcel'e özel (Microsoft Excel'de YOK; adlar Microsoft listesinden doğrulanmadı — surec.md §8b). `.xlsx`e
# yazılınca başka programda #AD? verir; kaydederken uyarı gösterilir (`xlsx_io`).
TABCEL_OZEL: Dict[str, str] = {"TR_NUMBERTOWORDS": "YAZIYLA", "TR_VALIDATE_TCKN": "TCKİMLİKDOĞRULA",
                               "TR_VALIDATE_VKN": "VERGİNOGEÇERLİ", "TR_VALIDATE_IBAN": "IBANGEÇERLİ",
                               "TR_VALIDATE_PHONE": "TELEFONGEÇERLİ", "TR_VALIDATE_EMAIL": "EPOSTAGEÇERLİ",
                               "TR_NETWORKDAYS": "TRTAMİŞGÜNÜ", "TR_WORKDAY": "TRİŞGÜNÜ"}   # VKN/IBAN: Faz 9a; telefon/e-posta: 10-ön
EN_TR.update(TABCEL_OZEL)

TR_EN: Dict[str, str] = {tr_buyuk(tr): en for en, tr in EN_TR.items()}


def turkcesi(en: str) -> str:
    return EN_TR.get(en.upper(), en.upper())


def ingilizcesi(yazilan: str) -> Optional[str]:
    """Kullanıcının yazdığı Türkçe adın kanonik karşılığı (yoksa None)."""
    return TR_EN.get(tr_buyuk(yazilan))
