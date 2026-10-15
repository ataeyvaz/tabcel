"""Bilgi işlevleri, 2. küme (işlev kitaplığı genişletmesi, 2026-10-15). Qt yok."""
import math

from ...model import deger as D
from ...model.adres import sutun_harfe
from ...model.deger import Hata
from ..degerler import BOS_ARG, AralikDeger, Dizi
from ..donustur import mantiga, metne, sayi_metninden, sayiya
from . import fonksiyon
from .ortak import skaler


@skaler("ISERR", "h")
def _iserr(b, v):
    return isinstance(v, Hata) and v != D.YOK


@skaler("ISNONTEXT", "h")
def _isnontext(b, v):
    return not isinstance(v, str)


def _tek_cift(ad, cift):
    @skaler(ad, "h")
    def uygula(b, v):
        if isinstance(v, Hata):
            return v
        if v is None:
            v = 0.0
        if isinstance(v, str):
            v = sayi_metninden(v)
        if isinstance(v, bool) or v is None:
            return D.DEGER_HATASI
        return (math.floor(abs(v)) % 2 == 0) == cift


_tek_cift("ISEVEN", True)
_tek_cift("ISODD", False)

_HATA_NO = {"#NULL!": 1.0, "#DIV/0!": 2.0, "#VALUE!": 3.0, "#REF!": 4.0, "#NAME?": 5.0, "#NUM!": 6.0, "#N/A": 7.0}


@skaler("ERROR.TYPE", "h")
def _error_type(b, v):
    if isinstance(v, Hata):
        for kod, n in _HATA_NO.items():
            if D.hata_bul(kod) == v:
                return n
    return D.YOK


@fonksiyon("TYPE", en_az=1, en_cok=1)
def _type(b, v):
    if isinstance(v, Dizi):
        return 64.0
    if isinstance(v, AralikDeger):
        v = v.hucre_degeri(v.r1, v.c1)
    if v is BOS_ARG or v is None:
        return 1.0
    if isinstance(v, Hata):
        return 16.0
    if isinstance(v, bool):
        return 4.0
    return 2.0 if isinstance(v, str) else 1.0


@fonksiyon("ISREF", en_az=1, en_cok=1)
def _isref(b, v):
    return isinstance(v, AralikDeger)


@fonksiyon("ISFORMULA", en_az=1, en_cok=1)
def _isformula(b, v):
    if not isinstance(v, AralikDeger):
        return D.DEGER_HATASI
    h = v.sayfa.hucre(v.r1, v.c1)
    return bool(h is not None and h.formul)


@fonksiyon("SHEETS", en_az=0, en_cok=1)
def _sheets(b, v=None):
    if isinstance(v, AralikDeger):
        return 1.0
    return float(len(b.kitap.sayfalar)) if b.kitap is not None else 1.0


@fonksiyon("SHEET", en_az=0, en_cok=1)
def _sheet(b, v=None):
    sayfa = b.sayfa
    if isinstance(v, AralikDeger):
        sayfa = v.sayfa
    elif v is not None and v is not BOS_ARG:
        return D.YOK
    if b.kitap is None:
        return 1.0
    for i, s in enumerate(b.kitap.sayfalar):
        if s is sayfa:
            return float(i + 1)
    return D.YOK


@fonksiyon("ADDRESS", en_az=2, en_cok=5)
def _address(b, satir, sutun, mutlak=None, a1=None, sayfa=None):
    r, c = sayiya(satir), sayiya(sutun)
    for x in (r, c):
        if isinstance(x, Hata):
            return x
    tur = 1.0
    if mutlak is not None and mutlak is not BOS_ARG:
        tur = sayiya(mutlak)
        if isinstance(tur, Hata):
            return tur
    r, c, tur = math.trunc(r), math.trunc(c), math.trunc(tur)
    if r < 1 or c < 1 or tur < 1 or tur > 4 or c > 16384 or r > 1048576:
        return D.DEGER_HATASI
    a1_stil = True
    if a1 is not None and a1 is not BOS_ARG:
        a1_stil = mantiga(a1)
        if isinstance(a1_stil, Hata):
            return a1_stil
    if a1_stil:
        metin = ("$" if tur in (1, 3) else "") + sutun_harfe(c) + ("$" if tur in (1, 2) else "") + str(r)
    else:
        metin = "R" + (str(r) if tur in (1, 2) else f"[{r}]") + "C" + (str(c) if tur in (1, 3) else f"[{c}]")
    if sayfa is not None and sayfa is not BOS_ARG:
        ad = metne(sayfa)
        if isinstance(ad, Hata):
            return ad
        ad = ad if (ad == "" or ad.isalnum()) else "'" + ad.replace("'", "''") + "'"
        metin = ad + "!" + metin
    return metin
