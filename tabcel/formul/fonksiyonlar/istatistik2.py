"""İstatistik işlevleri, 2. küme (işlev kitaplığı genişletmesi, 2026-10-15). Qt yok.
Davranışlar gerçek Excel'de (COM) `araclar/excel_vaka.py` ile karşılaştırılır."""
import math
from collections import Counter
from statistics import NormalDist

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG, AralikDeger, Dizi
from ..donustur import sayi_metninden, sayi_sonucu, sayiya, mantiga
from . import fonksiyon
from .istatistik import _liste, _mode, _rank, _varyans, ham_sayi
from .matematik2 import _cift
from .ortak import duz, ham

_N = NormalDist()


def _say(v):
    return sayiya(ham(v))


def _sayilar_a(args):
    """MAXA/AVERAGEA ailesi: başvuruda metin 0, DOĞRU 1, YANLIŞ 0, boş atlanır; doğrudan yazılan
    metin sayıya çevrilir (olmazsa #DEĞER!), mantıksal 1/0."""
    cikti = []
    for a in args:
        if a is BOS_ARG:
            continue
        if isinstance(a, (AralikDeger, Dizi)):
            for v in duz(a):
                if isinstance(v, Hata):
                    return None, v
                if v is None:
                    continue
                cikti.append(float(v) if isinstance(v, bool) else (v if isinstance(v, float) else 0.0))
        else:
            v = sayiya(a)
            if isinstance(v, Hata):
                return None, v
            cikti.append(v)
    return cikti, None


@fonksiyon("AVERAGEA", en_az=1, en_cok=255)
def _averagea(b, *args):
    l, h = _sayilar_a(args)
    return h if h is not None else (math.fsum(l) / len(l) if l else D.BOL0)


@fonksiyon("MAXA", en_az=1, en_cok=255)
def _maxa(b, *args):
    l, h = _sayilar_a(args)
    return h if h is not None else (max(l) if l else 0.0)


@fonksiyon("MINA", en_az=1, en_cok=255)
def _mina(b, *args):
    l, h = _sayilar_a(args)
    return h if h is not None else (min(l) if l else 0.0)


def _var_a(args, ornek):
    l, h = _sayilar_a(args)
    if h is not None:
        return h
    n = len(l)
    if n < (2 if ornek else 1):
        return D.BOL0
    m = math.fsum(l) / n
    return math.fsum((x - m) ** 2 for x in l) / (n - 1 if ornek else n)


@fonksiyon("VARA", en_az=1, en_cok=255)
def _vara(b, *args):
    return _var_a(args, True)


@fonksiyon("STDEVA", en_az=1, en_cok=255)
def _stdeva(b, *args):
    v = _var_a(args, True)
    return v if isinstance(v, Hata) else math.sqrt(v)


for _ad in ("VAR.S",):
    fonksiyon(_ad, en_az=1, en_cok=255)(lambda b, *a: _varyans(a, True))
for _ad in ("VAR.P", "VARP"):
    fonksiyon(_ad, en_az=1, en_cok=255)(lambda b, *a: _varyans(a, False))


def _std(ornek):
    def uygula(b, *a):
        v = _varyans(a, ornek)
        return v if isinstance(v, Hata) else math.sqrt(v)
    return uygula


fonksiyon("STDEV.S", en_az=1, en_cok=255)(_std(True))
for _ad in ("STDEV.P", "STDEVP"):
    fonksiyon(_ad, en_az=1, en_cok=255)(_std(False))
fonksiyon("MODE.SNGL", en_az=1, en_cok=255)(_mode)


@fonksiyon("MODE.MULT", en_az=1, en_cok=255)
def _mode_mult(b, *args):
    l, h = _liste(args)
    if h is not None:
        return h
    s = Counter(l)
    en = max(s.values()) if s else 0
    if en < 2:
        return D.YOK
    gor = []
    for x in l:
        if s[x] == en and x not in gor:
            gor.append(x)
    return Dizi([[x] for x in gor])


# --- ortalama/sapma ---
@fonksiyon("AVEDEV", en_az=1, en_cok=255)
def _avedev(b, *args):
    l, h = _liste(args)
    if h is not None:
        return h
    if not l:
        return D.SAYI
    m = math.fsum(l) / len(l)
    return math.fsum(abs(x - m) for x in l) / len(l)


@fonksiyon("DEVSQ", en_az=1, en_cok=255)
def _devsq(b, *args):
    l, h = _liste(args)
    if h is not None:
        return h
    if not l:
        return D.SAYI
    m = math.fsum(l) / len(l)
    return math.fsum((x - m) ** 2 for x in l)


@fonksiyon("GEOMEAN", en_az=1, en_cok=255)
def _geomean(b, *args):
    l, h = _liste(args)
    if h is not None:
        return h
    if not l or any(x <= 0 for x in l):
        return D.SAYI
    return sayi_sonucu(math.exp(math.fsum(math.log(x) for x in l) / len(l)))


@fonksiyon("HARMEAN", en_az=1, en_cok=255)
def _harmean(b, *args):
    l, h = _liste(args)
    if h is not None:
        return h
    if not l or any(x <= 0 for x in l):
        return D.SAYI
    return len(l) / math.fsum(1 / x for x in l)


@fonksiyon("SKEW", en_az=1, en_cok=255)
def _skew(b, *args):
    l, h = _liste(args)
    if h is not None:
        return h
    n = len(l)
    if n < 3:
        return D.BOL0
    m = math.fsum(l) / n
    s = math.sqrt(math.fsum((x - m) ** 2 for x in l) / (n - 1))
    if s == 0:
        return D.BOL0
    return n / ((n - 1) * (n - 2)) * math.fsum(((x - m) / s) ** 3 for x in l)


@fonksiyon("KURT", en_az=1, en_cok=255)
def _kurt(b, *args):
    l, h = _liste(args)
    if h is not None:
        return h
    n = len(l)
    if n < 4:
        return D.BOL0
    m = math.fsum(l) / n
    s = math.sqrt(math.fsum((x - m) ** 2 for x in l) / (n - 1))
    if s == 0:
        return D.BOL0
    return (n * (n + 1) / ((n - 1) * (n - 2) * (n - 3)) * math.fsum(((x - m) / s) ** 4 for x in l)
            - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))


@fonksiyon("TRIMMEAN", en_az=2, en_cok=2)
def _trimmean(b, dizi, oran):
    p = _say(oran)
    if isinstance(p, Hata):
        return p
    l, h = _liste([dizi])
    if h is not None:
        return h
    if p < 0 or p >= 1 or not l:
        return D.SAYI
    k = int(len(l) * p / 2)
    l.sort()
    kes = l[k:len(l) - k]
    return math.fsum(kes) / len(kes)


@fonksiyon("STANDARDIZE", en_az=3, en_cok=3)
def _standardize(b, x, ort, sapma):
    x, ort, sapma = _say(x), _say(ort), _say(sapma)
    for v in (x, ort, sapma):
        if isinstance(v, Hata):
            return v
    return D.SAYI if sapma <= 0 else (x - ort) / sapma


# --- yüzdelikler / sıra ---
def _yuzdelik(liste, k, haric):
    n = len(liste)
    if n == 0:
        return D.SAYI
    liste = sorted(liste)
    if haric:
        if k <= 0 or k >= 1 or k < 1 / (n + 1) - 1e-15 or k > n / (n + 1) + 1e-15:
            return D.SAYI
        pos = k * (n + 1) - 1
    else:
        if k < 0 or k > 1:
            return D.SAYI
        pos = k * (n - 1)
    pos = min(max(pos, 0), n - 1)
    alt = int(math.floor(pos))
    ust = min(alt + 1, n - 1)
    return liste[alt] + (pos - alt) * (liste[ust] - liste[alt])


def _yuzdelik_uygula(haric):
    def uygula(b, dizi, k):
        kk = _say(k)
        if isinstance(kk, Hata):
            return kk
        l, h = _liste([dizi])
        return h if h is not None else _yuzdelik(l, kk, haric)
    return uygula


for _ad, _h in (("PERCENTILE", False), ("PERCENTILE.INC", False), ("PERCENTILE.EXC", True)):
    fonksiyon(_ad, en_az=2, en_cok=2)(_yuzdelik_uygula(_h))


def _dortte(haric):
    def uygula(b, dizi, kuartil):
        q = _say(kuartil)
        if isinstance(q, Hata):
            return q
        q = math.trunc(q)
        if q < (1 if haric else 0) or q > (3 if haric else 4):
            return D.SAYI
        l, h = _liste([dizi])
        return h if h is not None else _yuzdelik(l, q / 4, haric)
    return uygula


for _ad, _h in (("QUARTILE", False), ("QUARTILE.INC", False), ("QUARTILE.EXC", True)):
    fonksiyon(_ad, en_az=2, en_cok=2)(_dortte(_h))


def _yuzderank(haric):
    def uygula(b, dizi, x, anlam=None):
        x = _say(x)
        if isinstance(x, Hata):
            return x
        a = 3.0
        if anlam is not None and anlam is not BOS_ARG:
            a = _say(anlam)
            if isinstance(a, Hata):
                return a
        a = math.trunc(a)
        l, h = _liste([dizi])
        if h is not None:
            return h
        if a < 1:
            return D.SAYI
        if not l:
            return D.SAYI if False else D.YOK
        l.sort()
        n = len(l)
        if x < l[0] or x > l[-1]:
            return D.YOK
        payda = (n + 1) if haric else (n - 1)
        if payda == 0:
            return D.BOL0
        ofs = 1 if haric else 0
        alt = sum(1 for v in l if v < x)
        if x in l:
            r = (alt + ofs) / payda
        else:
            lo = max(v for v in l if v < x)
            hi = min(v for v in l if v > x)
            i = sum(1 for v in l if v <= lo) - 1
            r = ((i + ofs) + (x - lo) / (hi - lo)) / payda
        kat = 10 ** a
        return math.floor(r * kat + 1e-9) / kat
    return uygula


for _ad, _h in (("PERCENTRANK", False), ("PERCENTRANK.INC", False), ("PERCENTRANK.EXC", True)):
    fonksiyon(_ad, en_az=2, en_cok=3)(_yuzderank(_h))
fonksiyon("RANK.EQ", en_az=2, en_cok=3)(_rank)


@fonksiyon("RANK.AVG", en_az=2, en_cok=3)
def _rank_avg(b, sayi, baslik, sira=None):
    r = _rank(b, sayi, baslik, sira)
    if isinstance(r, Hata):
        return r
    x = _say(sayi)
    l, _ = _liste([baslik])
    artan = sira is not None and sira is not BOS_ARG and _say(sira) != 0
    esit = sum(1 for v in l if v == x)
    return r + (esit - 1) / 2


# --- iki değişkenli ---
def _iki(a1, a2):
    hata, c = _cift(a1, a2)
    if hata is not None:
        return None, hata
    if c is None:
        return None, D.YOK
    return c, None


def _momentler(c):
    n = len(c)
    mx = math.fsum(p for p, _ in c) / n
    my = math.fsum(q for _, q in c) / n
    sxx = math.fsum((p - mx) ** 2 for p, _ in c)
    syy = math.fsum((q - my) ** 2 for _, q in c)
    sxy = math.fsum((p - mx) * (q - my) for p, q in c)
    return n, mx, my, sxx, syy, sxy


def _iki_fonk(f, en_az_n=2):
    def uygula(b, a1, a2):
        c, h = _iki(a1, a2)
        if h is not None:
            return h
        if len(c) < en_az_n:
            return D.BOL0
        return f(*_momentler(c))
    return uygula


def _bol(a, c):
    return D.BOL0 if c == 0 else a / c


for _ad in ("CORREL", "PEARSON"):
    fonksiyon(_ad, en_az=2, en_cok=2)(_iki_fonk(
        lambda n, mx, my, sxx, syy, sxy: D.BOL0 if sxx == 0 or syy == 0 else sxy / math.sqrt(sxx * syy)))
fonksiyon("RSQ", en_az=2, en_cok=2)(_iki_fonk(
    lambda n, mx, my, sxx, syy, sxy: D.BOL0 if sxx == 0 or syy == 0 else sxy * sxy / (sxx * syy)))
fonksiyon("COVARIANCE.P", en_az=2, en_cok=2)(_iki_fonk(lambda n, mx, my, sxx, syy, sxy: sxy / n, 1))
fonksiyon("COVARIANCE.S", en_az=2, en_cok=2)(_iki_fonk(lambda n, mx, my, sxx, syy, sxy: sxy / (n - 1)))


def _egim(a1, a2):                      # SLOPE(bilinen_y, bilinen_x)
    c, h = _iki(a2, a1)
    if h is not None:
        return None, h
    if len(c) < 2:
        return None, D.BOL0
    n, mx, my, sxx, syy, sxy = _momentler(c)
    if sxx == 0:
        return None, D.BOL0
    return (sxy / sxx, my - sxy / sxx * mx), None


@fonksiyon("SLOPE", en_az=2, en_cok=2)
def _slope(b, y, x):
    r, h = _egim(y, x)
    return h if h is not None else r[0]


@fonksiyon("INTERCEPT", en_az=2, en_cok=2)
def _intercept(b, y, x):
    r, h = _egim(y, x)
    return h if h is not None else r[1]


def _tahmin(b, x, y, bx):
    x0 = _say(x)
    if isinstance(x0, Hata):
        return x0
    r, h = _egim(y, bx)
    return h if h is not None else r[1] + r[0] * x0


fonksiyon("FORECAST", en_az=3, en_cok=3)(_tahmin)
fonksiyon("FORECAST.LINEAR", en_az=3, en_cok=3)(_tahmin)


# --- dağılımlar ---
def _uc(b, args, f):
    v = [_say(a) for a in args]
    for x in v:
        if isinstance(x, Hata):
            return x
    return f(*v)


def _kum(c):
    r = mantiga(ham(c))
    return r


@fonksiyon("NORM.S.DIST", en_az=2, en_cok=2)
def _norm_s_dist(b, z, kum):
    z = _say(z)
    k = _kum(kum)
    for v in (z, k):
        if isinstance(v, Hata):
            return v
    return _N.cdf(z) if k else math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


@fonksiyon("NORM.DIST", en_az=4, en_cok=4)
def _norm_dist(b, x, ort, sd, kum):
    x, ort, sd = _say(x), _say(ort), _say(sd)
    k = _kum(kum)
    for v in (x, ort, sd, k):
        if isinstance(v, Hata):
            return v
    if sd <= 0:
        return D.SAYI
    z = (x - ort) / sd
    return _N.cdf(z) if k else math.exp(-z * z / 2) / (math.sqrt(2 * math.pi) * sd)


@fonksiyon("NORM.S.INV", en_az=1, en_cok=1)
def _norm_s_inv(b, p):
    p = _say(p)
    if isinstance(p, Hata):
        return p
    return D.SAYI if p <= 0 or p >= 1 else _N.inv_cdf(p)


@fonksiyon("NORM.INV", en_az=3, en_cok=3)
def _norm_inv(b, p, ort, sd):
    p, ort, sd = _say(p), _say(ort), _say(sd)
    for v in (p, ort, sd):
        if isinstance(v, Hata):
            return v
    if p <= 0 or p >= 1 or sd <= 0:
        return D.SAYI
    return ort + sd * _N.inv_cdf(p)


@fonksiyon("POISSON.DIST", en_az=3, en_cok=3)
def _poisson(b, x, ort, kum):
    x, ort = _say(x), _say(ort)
    k = _kum(kum)
    for v in (x, ort, k):
        if isinstance(v, Hata):
            return v
    x = math.trunc(x)
    if x < 0 or ort < 0:
        return D.SAYI
    try:
        if k:
            return sayi_sonucu(math.fsum(math.exp(-ort + i * math.log(ort) - math.lgamma(i + 1)) if ort > 0
                                         else (1.0 if i == 0 else 0.0) for i in range(x + 1)))
        return sayi_sonucu(math.exp(-ort + x * math.log(ort) - math.lgamma(x + 1)) if ort > 0
                           else (1.0 if x == 0 else 0.0))
    except (OverflowError, ValueError):
        return D.SAYI


@fonksiyon("WEIBULL.DIST", en_az=4, en_cok=4)
def _weibull(b, x, alfa, beta, kum):
    x, alfa, beta = _say(x), _say(alfa), _say(beta)
    k = _kum(kum)
    for v in (x, alfa, beta, k):
        if isinstance(v, Hata):
            return v
    if x < 0 or alfa <= 0 or beta <= 0:
        return D.SAYI
    if k:
        return 1 - math.exp(-((x / beta) ** alfa))
    return sayi_sonucu(alfa / beta ** alfa * x ** (alfa - 1) * math.exp(-((x / beta) ** alfa)))


@fonksiyon("EXPON.DIST", en_az=3, en_cok=3)
def _expon(b, x, lam, kum):
    x, lam = _say(x), _say(lam)
    k = _kum(kum)
    for v in (x, lam, k):
        if isinstance(v, Hata):
            return v
    if x < 0 or lam <= 0:
        return D.SAYI
    return 1 - math.exp(-lam * x) if k else lam * math.exp(-lam * x)


@fonksiyon("CONFIDENCE.NORM", en_az=3, en_cok=3)
def _confidence(b, alfa, sd, boyut):
    alfa, sd, n = _say(alfa), _say(sd), _say(boyut)
    for v in (alfa, sd, n):
        if isinstance(v, Hata):
            return v
    n = math.trunc(n)
    if alfa <= 0 or alfa >= 1 or sd <= 0 or n < 1:
        return D.SAYI
    return _N.inv_cdf(1 - alfa / 2) * sd / math.sqrt(n)


@fonksiyon("Z.TEST", en_az=2, en_cok=3)
def _ztest(b, dizi, x, sigma=None):
    x = _say(x)
    if isinstance(x, Hata):
        return x
    l, h = _liste([dizi])
    if h is not None:
        return h
    n = len(l)
    if n == 0:
        return D.YOK
    s = None
    if sigma is not None and sigma is not BOS_ARG:
        s = _say(sigma)
        if isinstance(s, Hata):
            return s
        if s <= 0:
            return D.SAYI
    if s is None:
        if n < 2:
            return D.BOL0
        m = math.fsum(l) / n
        s = math.sqrt(math.fsum((v - m) ** 2 for v in l) / (n - 1))
    if s == 0:
        return D.BOL0
    return 1 - _N.cdf((math.fsum(l) / n - x) / (s / math.sqrt(n)))
