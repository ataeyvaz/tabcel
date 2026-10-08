"""Hücre adresleme: A1 ⇄ (satır, sütun). Satır ve sütun 1 tabanlıdır (Excel gibi).

Qt içe aktarmaz (CLAUDE.md kural 2).
"""
import re
from typing import NamedTuple, Optional

MAX_ROW = 1_048_576   # Excel sınırı
MAX_COL = 16_384      # XFD

_HUCRE_RE = re.compile(r"^(\$?)([A-Za-z]{1,3})(\$?)(\d+)$")
_SUTUN_RE = re.compile(r"^(\$?)([A-Za-z]{1,3})$")
_SATIR_RE = re.compile(r"^(\$?)(\d+)$")


class AdresHatasi(ValueError):
    pass


class Hucre(NamedTuple):
    satir: int
    sutun: int
    satir_mutlak: bool = False
    sutun_mutlak: bool = False


class Aralik(NamedTuple):
    """Normalize edilmiş dikdörtgen: ilk <= son. Tam sütun/satır aralıkları sınırlara uzanır."""
    ilk_satir: int
    ilk_sutun: int
    son_satir: int
    son_sutun: int


def sutun_harfe(sutun: int) -> str:
    """1 -> 'A', 27 -> 'AA', 16384 -> 'XFD'."""
    if not 1 <= sutun <= MAX_COL:
        raise AdresHatasi(f"Sütun aralık dışı: {sutun}")
    harfler = ""
    while sutun:
        sutun, kalan = divmod(sutun - 1, 26)
        harfler = chr(65 + kalan) + harfler
    return harfler


def harften_sutun(harfler: str) -> int:
    """'A' -> 1, 'XFD' -> 16384 (büyük/küçük harf fark etmez)."""
    h = harfler.upper()
    if not h or not h.isascii() or not h.isalpha():
        raise AdresHatasi(f"Geçersiz sütun: {harfler!r}")
    sayi = 0
    for c in h:
        sayi = sayi * 26 + (ord(c) - 64)
    if not 1 <= sayi <= MAX_COL:
        raise AdresHatasi(f"Sütun aralık dışı: {harfler!r}")
    return sayi


def hucre_coz(metin: str) -> Hucre:
    """'$B$3' -> Hucre(3, 2, True, True)."""
    m = _HUCRE_RE.match(metin.strip())
    if not m:
        raise AdresHatasi(f"Geçersiz hücre adresi: {metin!r}")
    sm, harf, rm, satir = m.groups()
    satir = int(satir)
    if not 1 <= satir <= MAX_ROW:
        raise AdresHatasi(f"Satır aralık dışı: {metin!r}")
    return Hucre(satir, harften_sutun(harf), bool(rm), bool(sm))


def hucre_yaz(satir: int, sutun: int, satir_mutlak: bool = False,
              sutun_mutlak: bool = False) -> str:
    if not 1 <= satir <= MAX_ROW:
        raise AdresHatasi(f"Satır aralık dışı: {satir}")
    return (("$" if sutun_mutlak else "") + sutun_harfe(sutun)
            + ("$" if satir_mutlak else "") + str(satir))


def aralik_coz(metin: str) -> Aralik:
    """'B2:A1', 'A:C' (tam sütun), '2:5' (tam satır) veya tek hücre 'C3' -> normalize Aralik."""
    parcalar = metin.strip().split(":")
    if len(parcalar) == 1:
        h = hucre_coz(parcalar[0])
        return Aralik(h.satir, h.sutun, h.satir, h.sutun)
    if len(parcalar) != 2:
        raise AdresHatasi(f"Geçersiz aralık: {metin!r}")
    a, b = (p.strip() for p in parcalar)
    ma, mb = _SUTUN_RE.match(a), _SUTUN_RE.match(b)
    if ma and mb:
        c1, c2 = sorted((harften_sutun(ma.group(2)), harften_sutun(mb.group(2))))
        return Aralik(1, c1, MAX_ROW, c2)
    ra, rb = _SATIR_RE.match(a), _SATIR_RE.match(b)
    if ra and rb:
        r1, r2 = sorted((int(ra.group(2)), int(rb.group(2))))
        if r1 < 1 or r2 > MAX_ROW:
            raise AdresHatasi(f"Satır aralık dışı: {metin!r}")
        return Aralik(r1, 1, r2, MAX_COL)
    h1, h2 = hucre_coz(a), hucre_coz(b)
    return Aralik(min(h1.satir, h2.satir), min(h1.sutun, h2.sutun),
                  max(h1.satir, h2.satir), max(h1.sutun, h2.sutun))


def aralik_yaz(ar: Aralik) -> str:
    """Tek hücre ise 'A1', tam sütun/satır ise 'A:C' / '2:5', değilse 'A1:B2'."""
    tam_sutun = ar.ilk_satir == 1 and ar.son_satir == MAX_ROW
    tam_satir = ar.ilk_sutun == 1 and ar.son_sutun == MAX_COL
    if tam_sutun and not tam_satir:
        return f"{sutun_harfe(ar.ilk_sutun)}:{sutun_harfe(ar.son_sutun)}"
    if tam_satir and not tam_sutun:
        return f"{ar.ilk_satir}:{ar.son_satir}"
    ilk = hucre_yaz(ar.ilk_satir, ar.ilk_sutun)
    if (ar.ilk_satir, ar.ilk_sutun) == (ar.son_satir, ar.son_sutun):
        return ilk
    return f"{ilk}:{hucre_yaz(ar.son_satir, ar.son_sutun)}"


def aralik_icinde(ar: Aralik, satir: int, sutun: int) -> bool:
    return (ar.ilk_satir <= satir <= ar.son_satir
            and ar.ilk_sutun <= sutun <= ar.son_sutun)
