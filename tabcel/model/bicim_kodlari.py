"""Hücreleri Biçimlendir ▸ Sayı sekmesinin Qt'siz mantığı (Faz 3 / 3e): kategori + seçenek ⇄ kanonik kod.

Saklanan kod hep kanoniktir (`sayi_bicimi.py`); ekranda `yerele` ile Türkçe gösterilir. Hazır kodlar
Windows tr-TR varsayımıdır (surec.md §8b-35, doğrulanacak).
"""
from typing import Dict, Optional, Tuple

from .sayi_bicimi import BicimHatasi, bicimle, kanonige, kod_coz

KATEGORILER = ("Genel", "Sayı", "Para Birimi", "Muhasebe", "Tarih", "Saat", "Yüzde", "Kesir",
               "Bilimsel", "Metin", "Özel")
SEMBOLLER = ("₺", "$", "€", "Yok")
TARIH_TIPLERI = ("d.mm.yyyy", "dd.mm.yyyy", "d.m.yy", "d mmmm yyyy", "d mmmm yyyy dddd",
                 "dd mmm yyyy", "mmmm yyyy", "d.mm.yyyy hh:mm")
SAAT_TIPLERI = ("hh:mm:ss", "hh:mm", "h:mm AM/PM", "h:mm:ss AM/PM", "[h]:mm:ss", "mm:ss")
KESIR_TIPLERI = ("# ?/?", "# ??/??", "# ???/???", "# ?/2", "# ?/4", "# ?/8", "# ?/16")
ORNEK = {"Genel": 1234.5678, "Tarih": 46000.0, "Saat": 0.7534, "Metin": "örnek"}


def _ondalik(n: int) -> str:
    return "." + "0" * n if n else ""


def _para(n: int, binlik: bool, sembol: str) -> str:
    sayi = "#,##0" + _ondalik(n)
    if sembol == "€":
        return sayi + ' "€"'
    return (f'"{sembol}"' if sembol in ("₺", "$") else "") + sayi


def _muhasebe(n: int, sembol: str) -> str:
    s = f'"{sembol}"' if sembol in ("₺", "$", "€") else ""
    sayi = "#,##0" + _ondalik(n)
    sifir = '"-"' + "?" * max(n, 2)
    return f'_-{s}* {sayi}_-;-{s}* {sayi}_-;_-{s}* {sifir}_-;_-@_-'


def kod_olustur(kategori: str, ondalik: int = 2, binlik: bool = False, sembol: str = "₺",
                tip: Optional[str] = None) -> str:
    """Kategori + seçeneklerden kanonik kod. `tip`: Tarih/Saat/Kesir için listeden bir kod."""
    if not 0 <= ondalik <= 30:
        raise ValueError("ondalık 0–30 olmalı")
    if kategori == "Genel":
        return "General"
    if kategori == "Sayı":
        return ("#,##0" if binlik else "0") + _ondalik(ondalik)
    if kategori == "Para Birimi":
        return _para(ondalik, binlik, sembol)
    if kategori == "Muhasebe":
        return _muhasebe(ondalik, sembol)
    if kategori == "Yüzde":
        return "0" + _ondalik(ondalik) + "%"
    if kategori == "Bilimsel":
        return "0" + _ondalik(ondalik) + "E+00"
    if kategori == "Metin":
        return "@"
    if kategori == "Tarih":
        return tip or TARIH_TIPLERI[0]
    if kategori == "Saat":
        return tip or SAAT_TIPLERI[0]
    if kategori == "Kesir":
        return tip or KESIR_TIPLERI[0]
    raise ValueError(f"Kategori kod üretmez: {kategori!r}")


def kategori_coz(kod: str) -> Dict[str, object]:
    """Kanonik kodu kategoriye ayırır: `{kategori, ondalik, binlik, sembol, tip}`. Tanınmayan → "Özel"
    (kod olduğu gibi kullanılır)."""
    kod = kod or "General"
    if kod == "General":
        return {"kategori": "Genel", "ondalik": 2, "binlik": False, "sembol": "₺", "tip": None}
    for kat, liste in (("Tarih", TARIH_TIPLERI), ("Saat", SAAT_TIPLERI), ("Kesir", KESIR_TIPLERI)):
        if kod in liste:
            return {"kategori": kat, "ondalik": 2, "binlik": False, "sembol": "₺", "tip": kod}
    if kod == "@":
        return {"kategori": "Metin", "ondalik": 2, "binlik": False, "sembol": "₺", "tip": None}
    for kat in ("Sayı", "Para Birimi", "Muhasebe", "Yüzde", "Bilimsel"):
        for n in range(0, 31):
            for binlik in (False, True):
                for sembol in SEMBOLLER:
                    if kat in ("Yüzde", "Bilimsel") and (binlik or sembol != "₺"):
                        continue
                    if kat == "Sayı" and sembol != "₺":
                        continue
                    if kat == "Muhasebe" and binlik:
                        continue
                    if kod_olustur(kat, n, binlik, sembol) == kod:
                        return {"kategori": kat, "ondalik": n, "binlik": binlik, "sembol": sembol,
                                "tip": None}
    return {"kategori": "Özel", "ondalik": 2, "binlik": False, "sembol": "₺", "tip": None}


def ozel_kodu_coz(yerel_metin: str) -> str:
    """Özel alana Türkçe yazımla girilen kod → kanonik; geçersizse `BicimHatasi` (uyarı metni için)."""
    kod = kanonige(yerel_metin)
    kod_coz(kod)                          # ayrıştırılabildiğini doğrula
    return kod


def onizleme(kod: str, deger=None) -> str:
    """Önizleme metni (yerel gösterim). Geçersiz kodda "" döner."""
    if deger is None:
        deger = 1234.5678
    try:
        return bicimle(deger, kod).metin
    except BicimHatasi:
        return ""
