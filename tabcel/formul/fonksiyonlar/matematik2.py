"""Matematik/trigonometri/mühendislik işlevleri, 2. küme (işlev kitaplığı genişletmesi, 2026-10-15). Qt yok.
Davranışlar gerçek Excel'de (COM) `araclar/excel_vaka.py` ile karşılaştırılır."""
import math

from ...model import deger as D
from ...model.deger import Hata
from ..donustur import onbes_basamak, sayi_sonucu
from . import fonksiyon
from .ortak import duz, skaler
from .temel import sayilar

_ROMEN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def _guvenli(f, *a):
    try:
        return sayi_sonucu(f(*a))
    except (ValueError, OverflowError, ZeroDivisionError):
        return D.SAYI


# --- trigonometri ---
for _ad, _f in (("SIN", math.sin), ("COS", math.cos), ("SINH", math.sinh), ("COSH", math.cosh),
                ("TANH", math.tanh), ("ATAN", math.atan), ("ASINH", math.asinh)):
    skaler(_ad, "s")(lambda b, x, _f=_f: _guvenli(_f, x))


@skaler("TAN", "s")
def _tan(b, x):
    return _guvenli(math.tan, x)


@skaler("ASIN", "s")
def _asin(b, x):
    return _guvenli(math.asin, x)


@skaler("ACOS", "s")
def _acos(b, x):
    return _guvenli(math.acos, x)


@skaler("ACOSH", "s")
def _acosh(b, x):
    return _guvenli(math.acosh, x)


@skaler("ATANH", "s")
def _atanh(b, x):
    return _guvenli(math.atanh, x)


@skaler("ATAN2", "ss")
def _atan2(b, x, y):
    if x == 0 and y == 0:
        return D.BOL0
    return math.atan2(y, x)


@skaler("SEC", "s")
def _sec(b, x):
    return _guvenli(lambda v: 1 / math.cos(v), x)


@skaler("CSC", "s")
def _csc(b, x):
    return D.BOL0 if x == 0 else _guvenli(lambda v: 1 / math.sin(v), x)


@skaler("COT", "s")
def _cot(b, x):
    return D.BOL0 if x == 0 else _guvenli(lambda v: 1 / math.tan(v), x)


@skaler("ACOT", "s")
def _acot(b, x):
    return math.pi / 2 - math.atan(x)


@skaler("ACOTH", "s")
def _acoth(b, x):
    return D.SAYI if abs(x) <= 1 else _guvenli(lambda v: 0.5 * math.log((v + 1) / (v - 1)), x)


@skaler("DEGREES", "s")
def _degrees(b, x):
    return math.degrees(x)


@skaler("RADIANS", "s")
def _radians(b, x):
    return math.radians(x)


@skaler("SQRTPI", "s")
def _sqrtpi(b, x):
    return D.SAYI if x < 0 else math.sqrt(x * math.pi)


# --- sayı kuramı / birleşim ---
def _tamsayi(x):
    return int(math.floor(x))


@skaler("FACT", "s")
def _fact(b, x):
    n = _tamsayi(x)
    if n < 0 or n > 170:
        return D.SAYI
    return float(math.factorial(n))


@skaler("FACTDOUBLE", "s")
def _factdouble(b, x):
    n = _tamsayi(x)
    if n < -1 or n > 300:
        return D.SAYI
    r = 1
    while n > 1:
        r *= n
        n -= 2
    return _guvenli(float, r)


@skaler("COMBIN", "ss")
def _combin(b, n, k):
    n, k = _tamsayi(n), _tamsayi(k)
    if n < 0 or k < 0 or k > n:
        return D.SAYI
    return _guvenli(float, math.comb(n, k))


@skaler("COMBINA", "ss")
def _combina(b, n, k):
    n, k = _tamsayi(n), _tamsayi(k)
    if n < 0 or k < 0 or (n == 0 and k > 0):
        return D.SAYI
    return 1.0 if n == 0 else _guvenli(float, math.comb(n + k - 1, k))


@skaler("PERMUT", "ss")
def _permut(b, n, k):
    n, k = _tamsayi(n), _tamsayi(k)
    if n < 0 or k < 0 or k > n or (n == 0 and k != 0):
        return D.SAYI
    return _guvenli(float, math.perm(n, k))


def _tamlar(args):
    """GCD/LCM/MULTINOMIAL argümanları (Excel COM 2026-10-15): mantıksal → #DEĞER!, sayı gibi metin → sayı,
    sayı olmayan metin → #DEĞER!, çok hücreli aralıkta boş hücre 0 sayılır (tek başvuruda atlanır)."""
    from ..degerler import BOS_ARG, AralikDeger
    from ..donustur import sayi_metninden
    for a in args:
        if a is BOS_ARG:
            continue
        coklu = isinstance(a, AralikDeger) and not a.tek_hucre()
        for v in duz(a):
            if isinstance(v, Hata):
                yield v
            elif isinstance(v, bool):
                yield D.DEGER_HATASI
            elif isinstance(v, str):
                n = sayi_metninden(v)
                yield D.DEGER_HATASI if n is None else n
            elif v is None:
                if coklu:
                    yield 0.0
            else:
                yield v


@fonksiyon("GCD", en_az=1, en_cok=255)
def _gcd(b, *args):
    r = 0
    for v in _tamlar(args):
        if isinstance(v, Hata):
            return v
        if v < 0:
            return D.SAYI
        r = math.gcd(r, int(v))
    return float(r)


@fonksiyon("LCM", en_az=1, en_cok=255)
def _lcm(b, *args):
    r = 1
    for v in _tamlar(args):
        if isinstance(v, Hata):
            return v
        if v < 0:
            return D.SAYI
        if int(v) == 0:
            return 0.0
        r = r * int(v) // math.gcd(r, int(v))
    return _guvenli(float, r)


@fonksiyon("MULTINOMIAL", en_az=1, en_cok=255)
def _multinomial(b, *args):
    liste = []
    for v in _tamlar(args):
        if isinstance(v, Hata):
            return v
        if v < 0:
            return D.SAYI
        liste.append(int(v))
    if not liste:
        return D.SAYI
    r = math.factorial(sum(liste))
    for k in liste:
        r //= math.factorial(k)
    return _guvenli(float, r)


@skaler("EVEN", "s")
def _even(b, x):
    s = math.ceil(abs(onbes_basamak(x)) / 2) * 2
    return float(-s if x < 0 else s)


@skaler("ODD", "s")
def _odd(b, x):
    a = math.ceil(abs(onbes_basamak(x)))
    s = a if a % 2 == 1 else a + 1
    return float(-s if x < 0 else s)


@skaler("QUOTIENT", "ss")
def _quotient(b, x, y):
    return D.BOL0 if y == 0 else float(math.trunc(onbes_basamak(x / y)))


@skaler("MROUND", "ss")
def _mround(b, x, m):
    if m == 0:
        return 0.0
    if x * m < 0:
        return D.SAYI
    return sayi_sonucu(math.floor(abs(onbes_basamak(x / m)) + 0.5) * abs(m) * (1 if x >= 0 else -1))


@skaler("CEILING.MATH", "sss", en_az=1)
def _ceiling_math(b, x, anlam=1.0, kip=0.0):
    anlam = abs(anlam)
    if anlam == 0:
        return 0.0
    if x < 0 and kip != 0:
        return sayi_sonucu(math.floor(onbes_basamak(x / anlam)) * anlam)
    return sayi_sonucu(math.ceil(onbes_basamak(x / anlam)) * anlam)


@skaler("FLOOR.MATH", "sss", en_az=1)
def _floor_math(b, x, anlam=1.0, kip=0.0):
    anlam = abs(anlam)
    if anlam == 0:
        return 0.0
    if x < 0 and kip != 0:
        return sayi_sonucu(math.ceil(onbes_basamak(x / anlam)) * anlam)
    return sayi_sonucu(math.floor(onbes_basamak(x / anlam)) * anlam)


# --- toplam ailesi ---
@fonksiyon("SUMSQ", en_az=1, en_cok=255)
def _sumsq(b, *args):
    t = 0.0
    for v in sayilar(args):
        if isinstance(v, Hata):
            return v
        t += v * v
    return sayi_sonucu(t)


def _cift(a1, a2):
    x, y = duz(a1), duz(a2)
    if len(x) != len(y):
        return None, None
    ciftler = []
    for p, q in zip(x, y):
        if isinstance(p, Hata):
            return p, None
        if isinstance(q, Hata):
            return q, None
        if isinstance(p, float) and not isinstance(p, bool) and isinstance(q, float) and not isinstance(q, bool):
            ciftler.append((p, q))
    return None, ciftler


def _sumx(f):
    def uygula(b, a1, a2):
        hata, c = _cift(a1, a2)
        if hata is not None:
            return hata
        if c is None:
            return D.YOK
        return sayi_sonucu(math.fsum(f(p, q) for p, q in c))
    return uygula


fonksiyon("SUMX2MY2", en_az=2, en_cok=2)(_sumx(lambda p, q: p * p - q * q))
fonksiyon("SUMX2PY2", en_az=2, en_cok=2)(_sumx(lambda p, q: p * p + q * q))
fonksiyon("SUMXMY2", en_az=2, en_cok=2)(_sumx(lambda p, q: (p - q) ** 2))


@fonksiyon("SERIESSUM", en_az=4, en_cok=4)
def _seriessum(b, x, n, m, katsayilar):
    from ..donustur import sayiya
    x, n, m = sayiya(x), sayiya(n), sayiya(m)
    for v in (x, n, m):
        if isinstance(v, Hata):
            return v
    t = 0.0
    for i, a in enumerate(duz(katsayilar)):
        if isinstance(a, Hata):
            return a
        if not isinstance(a, float) or isinstance(a, bool):
            return D.DEGER_HATASI
        try:
            t += a * x ** (n + i * m)
        except (ZeroDivisionError, OverflowError, ValueError):
            return D.SAYI
    return sayi_sonucu(t)


# --- Roma rakamı / taban ---
@skaler("ROMAN", "sh", en_az=1)
def _roman(b, x, bicim=None):
    n = _tamsayi(x)
    if n < 0 or n > 3999:
        return D.DEGER_HATASI
    if n == 0:
        return ""
    s = ""
    for d, r in _ROMEN:
        while n >= d:
            s += r
            n -= d
    return s


@skaler("ARABIC", "m")
def _arabic(b, metin):
    metin = metin.strip().upper()
    if metin == "":
        return 0.0
    deger = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    isaret = 1
    if metin.startswith("-"):
        isaret, metin = -1, metin[1:]
    if not metin or any(c not in deger for c in metin):
        return D.DEGER_HATASI
    t = 0
    for i, c in enumerate(metin):
        v = deger[c]
        t += -v if i + 1 < len(metin) and deger[metin[i + 1]] > v else v
    return float(isaret * t)


_RAKAM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@skaler("BASE", "sss", en_az=2)
def _base(b, x, taban, min_uzunluk=0.0):
    x, taban, u = _tamsayi(x), _tamsayi(taban), _tamsayi(min_uzunluk)
    if x < 0 or taban < 2 or taban > 36 or u < 0 or u > 255 or x >= 2 ** 53:
        return D.SAYI
    s = ""
    while x:
        s = _RAKAM[x % taban] + s
        x //= taban
    return (s or "0").rjust(max(u, 1), "0")


# --- bit işlemleri ---
def _bit(f, ad):
    def uygula(b, x, y):
        if x < 0 or y < 0 or x != math.floor(x) or y != math.floor(y) or x >= 2 ** 48 or y >= 2 ** 48:
            return D.SAYI
        return float(f(int(x), int(y)))
    skaler(ad, "ss")(uygula)


_bit(lambda a, c: a & c, "BITAND")
_bit(lambda a, c: a | c, "BITOR")
_bit(lambda a, c: a ^ c, "BITXOR")


@skaler("BITLSHIFT", "ss")
def _bitlshift(b, x, k):
    if x < 0 or x != math.floor(x) or x >= 2 ** 48 or abs(k) > 53:
        return D.SAYI
    r = int(x) << int(k) if k >= 0 else int(x) >> int(-k)
    return D.SAYI if r >= 2 ** 48 else float(r)


@skaler("BITRSHIFT", "ss")
def _bitrshift(b, x, k):
    return _bitlshift(b, x, -k)


@skaler("DELTA", "ss", en_az=1)
def _delta(b, x, y=0.0):
    return 1.0 if x == y else 0.0


@skaler("GESTEP", "ss", en_az=1)
def _gestep(b, x, e=0.0):
    return 1.0 if x >= e else 0.0


@skaler("ERF", "ss", en_az=1)
def _erf(b, a, ust=None):
    if ust is None:
        return math.erf(a)
    return math.erf(ust) - math.erf(a)


@skaler("GAMMA", "s")
def _gamma(b, x):
    if x == math.floor(x) and x <= 0:
        return D.SAYI
    return _guvenli(math.gamma, x)


@skaler("FISHER", "s")
def _fisher(b, x):
    return D.SAYI if abs(x) >= 1 else math.atanh(x)


def _taban_cevir(ad, kaynak, hedef, basamak=True):
    """BIN2DEC gibi: kaynak tabandaki metin → hedef tabana. İkili/sekizli/onaltılı negatif = 2'ye tümleyen (10 hane)."""
    bit = {2: 10, 8: 10, 16: 10}.get(kaynak, 10)

    def uygula(b, deger, yer=None):
        if isinstance(deger, float):
            deger = str(int(deger)) if deger == int(deger) else str(deger)
        s = str(deger).strip()
        if len(s) > 10:
            return D.SAYI
        if s == "":
            s = "0"
        try:
            n = int(s, kaynak)
        except ValueError:
            return D.SAYI
        toplam_bit = {2: 10, 8: 30, 16: 40}[kaynak]
        if len(s) == 10 and n >= 1 << (toplam_bit - 1):
            n -= 1 << toplam_bit
        if hedef == 10:
            return float(n)
        hedef_bit = {2: 10, 8: 30, 16: 40}[hedef]
        sinir = 1 << (hedef_bit - 1)
        if n < -sinir or n >= sinir:
            return D.SAYI
        if n < 0:
            n += 1 << hedef_bit
            gosterim = _yaz(n, hedef)
            return gosterim.rjust(10, "0")[-10:]
        gosterim = _yaz(n, hedef)
        if yer is not None:
            if yer < len(gosterim) or yer > 10 or yer < 0:
                return D.SAYI
            return gosterim.rjust(int(yer), "0")
        return gosterim
    return uygula


def _yaz(n, taban):
    if n == 0:
        return "0"
    s = ""
    while n:
        s = "0123456789ABCDEF"[n % taban] + s
        n //= taban
    return s


def _dec_cevir(hedef):
    def uygula(b, x, yer=None):
        n = _tamsayi(x)
        hedef_bit = {2: 10, 8: 30, 16: 40}[hedef]
        sinir = 1 << (hedef_bit - 1)
        if n < -sinir or n >= sinir:
            return D.SAYI
        if n < 0:
            return _yaz(n + (1 << hedef_bit), hedef).rjust(10, "0")[-10:]
        g = _yaz(n, hedef)
        if yer is not None:
            if yer < len(g) or yer > 10 or yer < 0:
                return D.SAYI
            return g.rjust(int(yer), "0")
        return g
    return uygula


for _ad, _k, _h in (("BIN2DEC", 2, 10), ("BIN2OCT", 2, 8), ("BIN2HEX", 2, 16), ("OCT2DEC", 8, 10),
                    ("OCT2BIN", 8, 2), ("HEX2DEC", 16, 10), ("HEX2BIN", 16, 2)):
    skaler(_ad, "hs", en_az=1)(_taban_cevir(_ad, _k, _h))
for _ad, _h in (("DEC2BIN", 2), ("DEC2OCT", 8), ("DEC2HEX", 16)):
    skaler(_ad, "ss", en_az=1)(_dec_cevir(_h))
