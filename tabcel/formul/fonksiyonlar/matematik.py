"""Matematik fonksiyonları (SUM temel.py'de). Qt yok."""
import math
import random
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Context, Decimal

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG, AralikDeger, _boyut
from ..donustur import onbes_basamak, sayi_sonucu
from . import fonksiyon
from .ortak import hizala, kriter, matris, olcut_yayar, skaler
from .temel import sayilar

_BAGLAM = Context(prec=80)


def yuvarla(x: float, basamak: int, kip) -> float:
    """Ondalık gösterim üzerinden yuvarlar (Excel 2,675 → 2,68 verir; ikili kesir değil)."""
    if math.isinf(x) or math.isnan(x):
        return x
    d = Decimal(repr(x))
    if basamak > 340:
        return x
    q = Decimal(1).scaleb(-basamak)
    try:
        return float(d.quantize(q, rounding=kip, context=_BAGLAM)) + 0.0
    except Exception:
        return x


def _tam(x: float) -> int:
    return int(math.trunc(x))


@skaler("ROUND", "ss")
def _round(b, x, n):
    return yuvarla(x, _tam(n), ROUND_HALF_UP)


@skaler("ROUNDUP", "ss")
def _roundup(b, x, n):
    return yuvarla(x, _tam(n), ROUND_UP)


@skaler("ROUNDDOWN", "ss")
def _rounddown(b, x, n):
    return yuvarla(x, _tam(n), ROUND_DOWN)


@skaler("TRUNC", "ss", en_az=1)
def _trunc(b, x, n=0.0):
    return yuvarla(x, _tam(n), ROUND_DOWN)


@skaler("INT", "s")
def _int(b, x):
    return float(math.floor(onbes_basamak(x)))


@skaler("MOD", "ss")
def _mod(b, x, y):
    if y == 0:
        return D.BOL0
    r = math.fmod(x, y)
    if r != 0 and (r < 0) != (y < 0):
        r += y
    return sayi_sonucu(r)


@skaler("ABS", "s")
def _abs(b, x):
    return abs(x)


@skaler("SQRT", "s")
def _sqrt(b, x):
    return math.sqrt(x) if x >= 0 else D.SAYI


@skaler("POWER", "ss")
def _power(b, x, y):
    from ..degerlendir import _us
    return _us(x, y)


@fonksiyon("PI", en_az=0, en_cok=0)
def _pi(b):
    return math.pi


@fonksiyon("RAND", en_az=0, en_cok=0, degisken=True)
def _rand(b):
    return random.random()


@skaler("RANDBETWEEN", "ss", degisken=True)
def _randbetween(b, alt, ust):
    alt, ust = math.ceil(alt), math.floor(ust)
    if alt > ust:
        return D.SAYI
    return float(random.randint(alt, ust))


@skaler("CEILING", "ss")
def _ceiling(b, x, anlam):
    if anlam == 0 or x == 0:
        return 0.0
    if x > 0 and anlam < 0:
        return D.SAYI
    return sayi_sonucu(math.ceil(onbes_basamak(x / anlam)) * anlam)


@skaler("FLOOR", "ss")
def _floor(b, x, anlam):
    if anlam == 0:
        return D.BOL0 if x != 0 else 0.0
    if x > 0 and anlam < 0:
        return D.SAYI
    return sayi_sonucu(math.floor(onbes_basamak(x / anlam)) * anlam)


@skaler("SIGN", "s")
def _sign(b, x):
    return 1.0 if x > 0 else -1.0 if x < 0 else 0.0


@skaler("EXP", "s")
def _exp(b, x):
    try:
        return sayi_sonucu(math.exp(x))
    except OverflowError:
        return D.SAYI


@skaler("LN", "s")
def _ln(b, x):
    return math.log(x) if x > 0 else D.SAYI


@skaler("LOG10", "s")
def _log10(b, x):
    return math.log10(x) if x > 0 else D.SAYI


@skaler("LOG", "ss", en_az=1)
def _log(b, x, taban=10.0):
    if x <= 0 or taban <= 0:
        return D.SAYI
    if taban == 1:
        return D.BOL0
    return math.log(x) / math.log(taban)


@fonksiyon("PRODUCT", en_az=1, en_cok=255)
def _product(b, *args):
    t, var = 1.0, False
    for v in sayilar(args):
        if isinstance(v, Hata):
            return v
        t *= v
        var = True
    return sayi_sonucu(t) if var else 0.0


# --- ölçütlü toplama ---
def eslesen_konumlar(araliklar, olcutler, hedef=None):
    """Tüm ölçütleri sağlayan göreli (i, j) konumları. Boyut uyuşmazlığı → Hata döner.
    `hedef`: toplanacak/ortalanacak aralık (ölçüt aralıklarıyla aynı boyutta olmalı)."""
    if hizala(list(araliklar) + ([hedef] if hedef is not None else [])) is None:
        return D.DEGER_HATASI
    R, C = _boyut(araliklar[0])
    sinamalar = [kriter(o) for o in olcutler]
    cikti = []
    for i in range(R):
        for j in range(C):
            if all(s(a.hucre_degeri(a.r1 + i, a.c1 + j)) for a, s in zip(araliklar, sinamalar)):
                cikti.append((i, j))
    return cikti


def _deger_oku(a: AralikDeger, i: int, j: int):
    r, c = a.r1 + i, a.c1 + j
    if r > 1048576 or c > 16384:
        return None
    return a.hucre_degeri(r, c)


def sayilari_topla(aralik, konumlar):
    """Konumlardaki sayılar (liste) ya da ilk hata."""
    cikti = []
    for i, j in konumlar:
        v = _deger_oku(aralik, i, j)
        if isinstance(v, Hata):
            return v
        if isinstance(v, float) and not isinstance(v, bool):
            cikti.append(v)
    return cikti


def _tek_olcut_konumlari(aralik, olcut, toplam_araligi):
    if not isinstance(aralik, AralikDeger):
        return D.DEGER_HATASI
    if toplam_araligi is not None and not isinstance(toplam_araligi, AralikDeger):
        return D.DEGER_HATASI
    return eslesen_konumlar([aralik], [olcut])


@fonksiyon("SUMIF", en_az=2, en_cok=3)
@olcut_yayar(lambda n: range(1, 2))
def _sumif(b, aralik, olcut, toplam=None):
    if toplam is BOS_ARG:
        toplam = None
    konum = _tek_olcut_konumlari(aralik, olcut, toplam)
    if isinstance(konum, Hata):
        return konum
    sayilar_ = sayilari_topla(toplam or aralik, konum)
    return sayilar_ if isinstance(sayilar_, Hata) else float(sum(sayilar_))


@fonksiyon("SUMIFS", en_az=3, en_cok=255)
@olcut_yayar(lambda n: range(2, n, 2))
def _sumifs(b, toplam, *cift):
    if len(cift) % 2:
        return D.DEGER_HATASI
    konum = eslesen_konumlar(list(cift[0::2]), list(cift[1::2]), toplam)
    if isinstance(konum, Hata):
        return konum
    s = sayilari_topla(toplam, konum)
    return s if isinstance(s, Hata) else float(sum(s))


@fonksiyon("SUMPRODUCT", en_az=1, en_cok=255)
def _sumproduct(b, *args):
    mat = [matris(a) for a in args]
    R, C = mat[0][0], mat[0][1]
    if any((m[0], m[1]) != (R, C) for m in mat):
        return D.DEGER_HATASI
    toplam = 0.0
    for i in range(R):
        for j in range(C):
            carpim = 1.0
            for _, _, oku in mat:
                v = oku(i, j)
                if isinstance(v, Hata):
                    return v
                carpim *= v if isinstance(v, float) and not isinstance(v, bool) else 0.0
            toplam += carpim
    return sayi_sonucu(toplam)
