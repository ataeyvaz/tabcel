"""Metin fonksiyonları (TEXT = METNEÇEVİR sayı biçimi çözümleyicisiyle). Qt yok."""
import math
import re

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import skalere
from ..donustur import mantiga, metne, sayi_metninden
from ...model.sayi_bicimi import BicimHatasi, bicimle, kanonige
from ..yerel import tr_buyuk, tr_kucuk
from . import fonksiyon
from .ortak import _joker_regex, duz, ham, skaler

MAKS_METIN = 32767


def _sinir(s):
    return D.DEGER_HATASI if len(s) > MAKS_METIN else s


@fonksiyon("CONCATENATE", en_az=1, en_cok=255)
def _concatenate(b, *args):
    parca = []
    for a in args:
        m = metne(skalere(a, b.satir, b.sutun))
        if isinstance(m, Hata):
            return m
        parca.append(m)
    return _sinir("".join(parca))


@fonksiyon("CONCAT", en_az=1, en_cok=255)
def _concat(b, *args):
    parca = []
    for a in args:
        for v in duz(a):
            m = metne(v)
            if isinstance(m, Hata):
                return m
            parca.append(m)
    return _sinir("".join(parca))


@fonksiyon("TEXTJOIN", en_az=3, en_cok=255)
def _textjoin(b, ayrac, bosla, *args):
    ay = metne(ham(skalere(ayrac, b.satir, b.sutun)))
    if isinstance(ay, Hata):
        return ay
    yoksay = mantiga(ham(skalere(bosla, b.satir, b.sutun)))
    if isinstance(yoksay, Hata):
        return yoksay
    parca = []
    for a in args:
        for v in duz(a):
            m = metne(v)
            if isinstance(m, Hata):
                return m
            if yoksay and m == "":
                continue
            parca.append(m)
    return _sinir(ay.join(parca))


@skaler("LEFT", "ms", en_az=1)
def _left(b, s, n=1.0):
    n = math.floor(n)
    return D.DEGER_HATASI if n < 0 else s[:n]


@skaler("RIGHT", "ms", en_az=1)
def _right(b, s, n=1.0):
    n = math.floor(n)
    if n < 0:
        return D.DEGER_HATASI
    return s[len(s) - n:] if n < len(s) else s


@skaler("MID", "mss")
def _mid(b, s, bas, n):
    bas, n = math.floor(bas), math.floor(n)
    if bas < 1 or n < 0:
        return D.DEGER_HATASI
    return s[bas - 1:bas - 1 + n]


@skaler("LEN", "m")
def _len(b, s):
    return float(len(s))


@skaler("UPPER", "m")
def _upper(b, s):
    return tr_buyuk(s)


@skaler("LOWER", "m")
def _lower(b, s):
    return tr_kucuk(s)


@skaler("PROPER", "m")
def _proper(b, s):
    cikti, onceki_harf = [], False
    for c in s:
        if c.isalpha():
            cikti.append(tr_kucuk(c) if onceki_harf else tr_buyuk(c))
            onceki_harf = True
        else:
            cikti.append(c)
            onceki_harf = False
    return "".join(cikti)


@skaler("TRIM", "m")
def _trim(b, s):
    return re.sub(" +", " ", s).strip(" ")


@skaler("FIND", "mms", en_az=2)
def _find(b, ara, icinde, bas=1.0):
    bas = math.floor(bas)
    if bas < 1 or bas > len(icinde) + 1:
        return D.DEGER_HATASI
    i = icinde.find(ara, bas - 1)
    return float(i + 1) if i >= 0 else D.DEGER_HATASI


@skaler("SEARCH", "mms", en_az=2)
def _search(b, ara, icinde, bas=1.0):
    bas = math.floor(bas)
    if bas < 1 or bas > len(icinde) + 1:
        return D.DEGER_HATASI
    desen = re.compile(_joker_regex(tr_kucuk(ara)).pattern[1:-1], re.S)
    m = desen.search(tr_kucuk(icinde), bas - 1)
    return float(m.start() + 1) if m else D.DEGER_HATASI


@skaler("SUBSTITUTE", "mmms", en_az=3)
def _substitute(b, s, eski, yeni, kacinci=None):
    if eski == "":
        return s
    if kacinci is None:
        return _sinir(s.replace(eski, yeni))
    k = math.floor(kacinci)
    if k < 1:
        return D.DEGER_HATASI
    konum = -1
    for _ in range(k):
        konum = s.find(eski, konum + 1)
        if konum < 0:
            return s
    return _sinir(s[:konum] + yeni + s[konum + len(eski):])


@skaler("REPLACE", "mssm")
def _replace(b, s, bas, n, yeni):
    bas, n = math.floor(bas), math.floor(n)
    if bas < 1 or n < 0:
        return D.DEGER_HATASI
    return _sinir(s[:bas - 1] + yeni + s[bas - 1 + n:])


@skaler("VALUE", "h")
def _value(b, v):
    if isinstance(v, Hata):
        return v
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return D.DEGER_HATASI
    if isinstance(v, float):
        return v
    n = sayi_metninden(v)
    return D.DEGER_HATASI if n is None else n


@skaler("TEXT", "hm")
def _text(b, v, kod):
    """METNEÇEVİR: sayıyı biçim koduyla metne çevirir. Biçim Türkçe yazımla verilir (`"gg.aa.yyyy"`,
    `"#.##0,00"`); çözülemezse kanonik yazım denenir (surec.md §8b-41). Metin sayıya benziyorsa
    çevrilir, benzemiyorsa olduğu gibi döner (Excel)."""
    if isinstance(v, Hata):
        return v
    if kod.strip() == "":
        return ""
    if v is None:
        v = 0.0
    if isinstance(v, bool):
        return "DOĞRU" if v else "YANLIŞ"
    if isinstance(v, str):
        n = sayi_metninden(v)
        if n is None:
            return v
        v = n
    try:
        kanonik = kanonige(kod)
    except BicimHatasi:
        kanonik = kod
    try:
        s = bicimle(float(v), kanonik)
    except BicimHatasi:
        return D.DEGER_HATASI
    return D.DEGER_HATASI if s.diyez else s.metin


@skaler("REPT", "ms")
def _rept(b, s, n):
    n = math.floor(n)
    if n < 0 or len(s) * n > MAKS_METIN:
        return D.DEGER_HATASI
    return s * n


@skaler("EXACT", "mm")
def _exact(b, x, y):
    return x == y
