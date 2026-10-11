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
    "IF": "EĞER", "IFS": "ÇOKEĞER", "AND": "VE", "OR": "YADA", "NOT": "DEĞİL", "XOR": "ÖZELVEYA", "IFERROR": "EĞERHATA", "IFNA": "EĞERYOKSA", "SWITCH": "İLKEŞLENEN", "TRUE": "DOĞRU", "FALSE": "YANLIŞ",
    "VLOOKUP": "DÜŞEYARA", "HLOOKUP": "YATAYARA", "XLOOKUP": "ÇAPRAZARA", "INDEX": "İNDİS", "MATCH": "KAÇINCI", "XMATCH": "ÇAPRAZEŞLEŞTİR", "CHOOSE": "ELEMAN", "ROW": "SATIR", "COLUMN": "SÜTUN", "ROWS": "SATIRSAY", "COLUMNS": "SÜTUNSAY", "INDIRECT": "DOLAYLI", "OFFSET": "KAYDIR",
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

# Tabcel'e özel (Microsoft Excel'de YOK; adlar Microsoft listesinden doğrulanmadı — surec.md §8b). `.xlsx`e
# yazılınca başka programda #AD? verir; kaydederken uyarı gösterilir (`xlsx_io`).
TABCEL_OZEL: Dict[str, str] = {"TR_NUMBERTOWORDS": "YAZIYLA", "TR_VALIDATE_TCKN": "TCKİMLİKDOĞRULA",
                               "TR_VALIDATE_VKN": "VERGİNOGEÇERLİ", "TR_VALIDATE_IBAN": "IBANGEÇERLİ"}          # VKN/IBAN: Faz 9a
EN_TR.update(TABCEL_OZEL)

TR_EN: Dict[str, str] = {tr_buyuk(tr): en for en, tr in EN_TR.items()}


def turkcesi(en: str) -> str:
    return EN_TR.get(en.upper(), en.upper())


def ingilizcesi(yazilan: str) -> Optional[str]:
    """Kullanıcının yazdığı Türkçe adın kanonik karşılığı (yoksa None)."""
    return TR_EN.get(tr_buyuk(yazilan))
