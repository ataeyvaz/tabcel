"""Hücre değerinin ekrandaki/panodaki metni. Qt yok.

Geçici 'Genel' biçim; sayı biçimleri (Para, Tarih, Yüzde…) Faz 3'te gelecek.
"""
from decimal import ROUND_HALF_UP, Decimal


def goster(deger) -> str:
    if deger is None:
        return ""
    if isinstance(deger, bool):
        return "DOĞRU" if deger else "YANLIŞ"
    if isinstance(deger, float):
        if deger == int(deger) and abs(deger) < 1e11:
            return str(int(deger))
        return f"{deger:.10g}".replace(".", ",").replace("e", "E")
    return str(deger)


def _sabit(v: float, k: int) -> str:
    # Excel yarım değerleri sıfırdan uzağa yuvarlar (2,5 → 3); Python'un yuvarlaması çifte yuvarlar
    s = f"{Decimal(repr(v)).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP):f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",")


def _bilimsel(v: float, d: int) -> str:
    mantis, us = f"{v:.{d}E}".split("E")
    if "." in mantis:
        mantis = mantis.rstrip("0").rstrip(".")
    return f"{mantis.replace('.', ',')}E{us[0]}{us[1:].lstrip('0').rjust(2, '0')}"


def sayiyi_sigdir(deger: float, sigar) -> "str | None":
    """Genel biçimde sayıyı sütuna sığana dek kısaltır (Excel gibi: önce ondalıkları yuvarlar,
    olmazsa bilimsel gösterime geçer). `sigar(metin)` metin sığıyorsa True döner.
    Hiçbiri sığmazsa None — çağıran `####` çizer."""
    t = goster(deger)
    if sigar(t):
        return t
    if 0.01 <= abs(deger) < 1e11:          # küçük sayılarda yuvarlama basamak kaybettirir → bilimsel
        for k in range(9, -1, -1):
            t = _sabit(deger, k)
            if t.lstrip("-") == "0":
                break
            if sigar(t):
                return t
    for d in range(8, -1, -1):
        t = _bilimsel(deger, d)
        if sigar(t):
            return t
    return None
