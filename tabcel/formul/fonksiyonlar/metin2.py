"""Metin işlevleri, 2. küme (işlev kitaplığı genişletmesi, 2026-10-15). Qt yok."""
import math
import re
from urllib.parse import quote

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG
from ..donustur import mantiga, metne, sayi_metninden, sayiya
from ..yerel import tr_kucuk
from . import fonksiyon
from .ortak import ham, skaler


@skaler("CHAR", "s")
def _char(b, n):
    n = math.trunc(n)
    if n < 1 or n > 255:
        return D.DEGER_HATASI
    try:
        return bytes([n]).decode("cp1254")
    except UnicodeDecodeError:
        return "?"


@skaler("CODE", "m")
def _code(b, metin):
    if metin == "":
        return D.DEGER_HATASI
    try:
        return float(metin[0].encode("cp1254")[0])
    except UnicodeEncodeError:
        return 63.0


@skaler("UNICHAR", "s")
def _unichar(b, n):
    n = math.trunc(n)
    if n < 1 or n > 0x10FFFF or 0xD800 <= n <= 0xDFFF:
        return D.DEGER_HATASI
    return chr(n)


@skaler("UNICODE", "m")
def _unicode(b, metin):
    return D.DEGER_HATASI if metin == "" else float(ord(metin[0]))


@skaler("CLEAN", "m")
def _clean(b, metin):
    return "".join(c for c in metin if ord(c) >= 32)


@skaler("ENCODEURL", "m")
def _encodeurl(b, metin):
    return quote(metin, safe="-._").replace("~", "%7E")


@skaler("T", "h")
def _t(b, v):
    if isinstance(v, Hata):
        return v
    return v if isinstance(v, str) else ""


@skaler("N", "h")
def _n(b, v):
    if isinstance(v, Hata):
        return v
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    return v if isinstance(v, float) else 0.0


def _grupla(tam: str) -> str:
    ters = tam[::-1]
    return ".".join(ters[i:i + 3] for i in range(0, len(ters), 3))[::-1]


def _sabit(x: float, ondalik: int, gruplu: bool) -> str:
    from decimal import ROUND_HALF_UP, Decimal
    d = Decimal(repr(x))
    if ondalik >= 0:
        d = d.quantize(Decimal(1).scaleb(-ondalik), rounding=ROUND_HALF_UP)
    else:
        d = d.quantize(Decimal(1).scaleb(-ondalik), rounding=ROUND_HALF_UP)
    eksi = d < 0
    s = format(abs(d), "f")
    if "." in s:
        tam, kes = s.split(".")
    else:
        tam, kes = s, ""
    if ondalik < 0:
        kes = ""
    if gruplu:
        tam = _grupla(tam)
    r = tam + ("," + kes if kes else "")
    return ("-" if eksi and float(d) != 0 else "") + r


@skaler("FIXED", "ssb", en_az=1)
def _fixed(b, x, ondalik=2.0, gruplamasiz=False):
    o = math.trunc(ondalik)
    if o > 127:
        return D.DEGER_HATASI
    return _sabit(x, o, not gruplamasiz)


@skaler("DOLLAR", "ss", en_az=1)
def _dollar(b, x, ondalik=2.0):
    o = math.trunc(ondalik)
    if o > 127:
        return D.DEGER_HATASI
    s = _sabit(abs(x), o, True)
    return f"-₺{s}" if x < 0 else f"₺{s}"


@fonksiyon("NUMBERVALUE", en_az=1, en_cok=3)
def _numbervalue(b, metin, ondalik=None, grup=None):
    m = metne(ham(metin))
    if isinstance(m, Hata):
        return m
    od, gr = ",", "."
    if ondalik is not None and ondalik is not BOS_ARG and (grup is None or grup is BOS_ARG):
        gr = "," if metne(ham(ondalik)) == "." else "."
    if ondalik is not None and ondalik is not BOS_ARG:
        od = metne(ham(ondalik))
        if isinstance(od, Hata):
            return od
        od = od[:1] if od else ""
    if grup is not None and grup is not BOS_ARG:
        gr = metne(ham(grup))
        if isinstance(gr, Hata):
            return gr
        gr = gr[:1] if gr else ""
    if od and od == gr:
        return D.DEGER_HATASI
    m = "".join(m.split())
    if m == "":
        return 0.0
    yuzde = 0
    while m.endswith("%"):
        m = m[:-1]
        yuzde += 1
    if gr:
        if od and od in m and gr in m[m.index(od):]:
            return D.DEGER_HATASI
        m = m.replace(gr, "")
    if od and od != ".":
        if m.count(od) > 1:
            return D.DEGER_HATASI
        m = m.replace(od, ".")
    elif not od and "." in m:
        return D.DEGER_HATASI
    try:
        if not re.fullmatch(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", m):
            return D.DEGER_HATASI
        return float(m) / (100 ** yuzde)
    except ValueError:
        return D.DEGER_HATASI


def _once_sonra(sonra: bool):
    def uygula(b, metin, ayrac, sira=None, esle=None, son=None, yok=None):
        m = metne(ham(metin))
        a = metne(ham(ayrac))
        for x in (m, a):
            if isinstance(x, Hata):
                return x
        k = 1
        if sira is not None and sira is not BOS_ARG:
            k = sayiya(ham(sira))
            if isinstance(k, Hata):
                return k
            k = math.trunc(k)
        kucuk = False
        if esle is not None and esle is not BOS_ARG:
            e = sayiya(ham(esle))
            if isinstance(e, Hata):
                return e
            kucuk = math.trunc(e) == 1
        sonu = False
        if son is not None and son is not BOS_ARG:
            e = sayiya(ham(son))
            if isinstance(e, Hata):
                return e
            sonu = math.trunc(e) == 1
        if k == 0 or abs(k) > len(m) + 1 or (a == "" and False):
            return D.DEGER_HATASI
        kaynak = tr_kucuk(m) if kucuk else m
        aranan = tr_kucuk(a) if kucuk else a
        konumlar = []
        i = 0
        if aranan == "":
            konumlar = [0] if k > 0 else [len(m)]
            if abs(k) > 1:
                return D.DEGER_HATASI
        else:
            while True:
                j = kaynak.find(aranan, i)
                if j < 0:
                    break
                konumlar.append(j)
                i = j + len(aranan)
        bulundu = None
        if abs(k) <= len(konumlar):
            bulundu = konumlar[k - 1] if k > 0 else konumlar[k]
        elif sonu and abs(k) == len(konumlar) + 1:
            bulundu = len(m) if k > 0 else 0
            if k > 0 and not sonra:
                return m
            if k > 0 and sonra:
                return ""
            if k < 0 and not sonra:
                return ""
            if k < 0 and sonra:
                return m
        if bulundu is None:
            return D.YOK if yok is None or yok is BOS_ARG else yok
        if sonra:
            return m[bulundu + len(a):]
        return m[:bulundu]
    return uygula


fonksiyon("TEXTAFTER", en_az=2, en_cok=6)(_once_sonra(True))
fonksiyon("TEXTBEFORE", en_az=2, en_cok=6)(_once_sonra(False))
