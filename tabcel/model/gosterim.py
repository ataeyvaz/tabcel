"""Hücre değerinin ekrandaki/panodaki metni. Qt yok.

Geçici 'Genel' biçim; sayı biçimleri (Para, Tarih, Yüzde…) Faz 3'te gelecek.
"""
from decimal import ROUND_HALF_UP, Decimal

from .deger import Hata

# Türkçe hata gösterimi. 2026-10-15: gerçek Excel 16'da (COM, Türkçe arayüz) doğrulandı — #DIV/0! → "#SAYI/0!"
# (önceki "#BÖL/0!" yanlıştı); #NUM! = "#SAYI!" ayrıdır. Eski "#BÖL/0!" yazımı girişte takma ad olarak okunur.
HATA_TR = {
    "#DIV/0!": "#SAYI/0!", "#N/A": "#YOK", "#NAME?": "#AD?", "#NULL!": "#BOŞ!",
    "#NUM!": "#SAYI!", "#REF!": "#BAŞV!", "#VALUE!": "#DEĞER!",
    "#SPILL!": "#TAŞMA!", "#CALC!": "#HESAPLA!",       # 2026-10-11 Excel 365 (COM) ile doğrulandı
}


def goster(deger) -> str:
    if deger is None:
        return ""
    if isinstance(deger, Hata):
        return HATA_TR.get(deger.kod, deger.kod)
    if isinstance(deger, bool):
        return "DOĞRU" if deger else "YANLIŞ"
    if isinstance(deger, float):
        if deger == int(deger) and abs(deger) < 1e11:
            return str(int(deger))
        return _genel(deger)
    return str(deger)


def _genel(x: float) -> str:
    """Genel biçim (geniş sütunda): Excel işareti saymadan en çok 11 karakter gösterir (gerçek Excel'de, COM ile
    2026-10-15'te ölçüldü). Önce 15 anlamlı basamağa yuvarlanır; ondalık gösterim sığıyorsa ve bilimselden
    az anlamlı basamak göstermiyorsa o, değilse bilimsel (1,23457E+11) kullanılır."""
    if x != x or x in (float("inf"), float("-inf")):
        return str(x)
    isaret = "-" if x < 0 else ""
    d15 = Decimal(f"{abs(x):.14e}")                      # 15 anlamlı basamak
    e = d15.adjusted()
    sig = d15.as_tuple().digits
    sig = "".join(map(str, sig)).rstrip("0") or "0"
    ARALIK = 11

    def sade(d: Decimal) -> str:
        s = f"{d:f}"
        return s.rstrip("0").rstrip(".") if "." in s else s

    def bilimsel() -> str:
        ee = e
        son_uz = 4 if abs(ee) < 100 else 5               # "E+11" / "E+100"
        n = max(1, min(len(sig), ARALIK - son_uz - 1))   # mantis: bir basamak + virgül + kalanlar
        m = d15.scaleb(-e).quantize(Decimal(1).scaleb(-(n - 1)), rounding=ROUND_HALF_UP)
        if m >= 10:                                      # 9,99999 → 10,0000 yuvarlaması
            m, ee = m / 10, ee + 1
        return f"{isaret}{sade(m).replace('.', ',')}E{'-' if ee < 0 else '+'}{abs(ee):02d}"

    if e >= 0:
        if e + 1 > ARALIK:
            return bilimsel()
        ondalik = max(0, ARALIK - (e + 1) - 1)
        s = sade(d15.quantize(Decimal(1).scaleb(-ondalik), rounding=ROUND_HALF_UP))
        if len(s.split(".")[0]) > ARALIK:                # yuvarlama basamak ekledi (99999999999,9 → 100000000000)
            return bilimsel()
        return isaret + s.replace(".", ",")
    s = sade(d15.quantize(Decimal(1).scaleb(-(ARALIK - 2)), rounding=ROUND_HALF_UP))   # "0," sonrası en çok 9 basamak
    if s == "0":
        return bilimsel()
    if s == "1":
        return isaret + "1"
    pos_sig = len(s.split(".")[1].lstrip("0"))
    if pos_sig >= len(sig) or pos_sig >= min(len(sig), ARALIK - 4 - 1):
        return isaret + s.replace(".", ",")
    # bilimsel yazım ondalıktan fazla anlamlı basamak göstermiyorsa ondalık yazılır (0,0899999999999999 → 0,09; Excel COM)
    n = min(len(sig), ARALIK - 4 - 1)
    m = d15.scaleb(-e).quantize(Decimal(1).scaleb(-(n - 1)), rounding=ROUND_HALF_UP)
    bil_sig = len(sade(min(m, Decimal(10))).replace(".", "").lstrip("0")) if m < 10 else 1
    if pos_sig >= bil_sig:
        return isaret + s.replace(".", ",")
    return bilimsel()


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
