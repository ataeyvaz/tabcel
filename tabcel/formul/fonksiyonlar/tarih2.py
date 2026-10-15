"""Tarih işlevleri, 2. küme (işlev kitaplığı genişletmesi, 2026-10-15). Qt yok."""
import math
import re

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG
from ..donustur import mantiga, sayi_metninden, sayiya
from . import fonksiyon
from .ortak import ham, skaler
from .tarih import MAKS_SERI, _seri_kontrol, _tarih_nesnesi, _tatiller, haftanin_gunu0, seri_ymd


def _seri(v):
    n = sayiya(ham(v))
    if isinstance(n, Hata):
        return n
    return _seri_kontrol(n)


@skaler("DATEVALUE", "m")
def _datevalue(b, metin):
    n = sayi_metninden(metin.strip())
    if n is None or (not any(c in metin for c in "./-:") and not any(c.isalpha() for c in metin)):
        return D.DEGER_HATASI
    if n < 0 or n >= MAKS_SERI + 1:
        return D.DEGER_HATASI
    return float(math.floor(n))


@skaler("TIMEVALUE", "m")
def _timevalue(b, metin):
    if ":" not in metin:
        return D.DEGER_HATASI
    n = sayi_metninden(metin.strip())
    if n is None:
        e = re.fullmatch(r"\s*(\d+):(\d+)(?::(\d+(?:[.,]\d+)?))?\s*", metin)      # 25:00 → 01:00 (Excel)
        if e is None:
            return D.DEGER_HATASI
        n = (int(e.group(1)) * 3600 + int(e.group(2)) * 60 + float((e.group(3) or "0").replace(",", "."))) / 86400
    return n - math.floor(n)


@skaler("ISOWEEKNUM", "s")
def _isoweeknum(b, x):
    n = _seri_kontrol(x)
    if isinstance(n, Hata):
        return n
    return float(_tarih_nesnesi(n).isocalendar()[1])


def _artik(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _gun360(n1, n2, avrupa):
    y1, m1, d1 = seri_ymd(n1)
    y2, m2, d2 = seri_ymd(n2)
    if avrupa:
        d1 = min(d1, 30)
        d2 = min(d2, 30)
    else:
        def son_subat(y, m, d):
            return m == 2 and d == (29 if _artik(y) else 28)
        if son_subat(y1, m1, d1):
            d1 = 30
        if d2 == 31 and d1 >= 30:
            d2 = 30
        if d1 == 31:
            d1 = 30
    return (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)


@fonksiyon("DAYS360", en_az=2, en_cok=3)
def _days360(b, bas, son, yontem=None):
    n1, n2 = _seri(bas), _seri(son)
    for x in (n1, n2):
        if isinstance(x, Hata):
            return x
    avrupa = False
    if yontem is not None and yontem is not BOS_ARG:
        avrupa = mantiga(ham(yontem))
        if isinstance(avrupa, Hata):
            return avrupa
    return float(_gun360(n1, n2, avrupa))


@fonksiyon("YEARFRAC", en_az=2, en_cok=3)
def _yearfrac(b, bas, son, esas=None):
    n1, n2 = _seri(bas), _seri(son)
    for x in (n1, n2):
        if isinstance(x, Hata):
            return x
    e = 0
    if esas is not None and esas is not BOS_ARG:
        e = sayiya(ham(esas))
        if isinstance(e, Hata):
            return e
        e = math.trunc(e)
    if e < 0 or e > 4:
        return D.SAYI
    if n1 > n2:
        n1, n2 = n2, n1
    if e == 0:
        return abs(_gun360(n1, n2, False)) / 360
    if e == 4:
        return abs(_gun360(n1, n2, True)) / 360
    if e == 2:
        return (n2 - n1) / 360
    if e == 3:
        return (n2 - n1) / 365
    y1, m1, d1 = seri_ymd(n1)
    y2, m2, d2 = seri_ymd(n2)
    gun = n2 - n1
    if y1 == y2:
        yil = 366 if _artik(y1) else 365
    elif y2 == y1 + 1 and (m2, d2) <= (m1, d1):
        yil = 366 if ((_artik(y1) and (m1, d1) <= (2, 29)) or (_artik(y2) and (m2, d2) >= (2, 29))) else 365
    else:
        toplam = sum(366 if _artik(y) else 365 for y in range(y1, y2 + 1))
        yil = toplam / (y2 - y1 + 1)
    return gun / yil


def _haftasonu(w):
    """Hafta sonu kümesi (Pzt=0 … Paz=6) ya da hata."""
    if w is None or w is BOS_ARG:
        return {5, 6}
    w = ham(w)
    if isinstance(w, Hata):
        return w
    if isinstance(w, str):
        if len(w) == 7 and set(w) <= {"0", "1"}:
            return {i for i, c in enumerate(w) if c == "1"}
        n = sayi_metninden(w)
        if n is None:
            return D.DEGER_HATASI
        w = n
    if isinstance(w, bool):
        return D.DEGER_HATASI
    k = math.trunc(w)
    if 1 <= k <= 7:
        return {((k - 1 + 5) % 7), ((k + 5) % 7)}
    if 11 <= k <= 17:
        return {(k - 11 + 6) % 7}
    return D.SAYI


def _is(n, hs, tatil):
    return ((haftanin_gunu0(n) - 1) % 7) not in hs and n not in tatil


@fonksiyon("NETWORKDAYS.INTL", en_az=2, en_cok=4)
def _networkdays_intl(b, bas, son, hafta_sonu=None, tatil=None):
    n1, n2 = _seri(bas), _seri(son)
    for x in (n1, n2):
        if isinstance(x, Hata):
            return x
    hs = _haftasonu(hafta_sonu)
    if isinstance(hs, Hata):
        return hs
    t = _tatiller(tatil) if tatil is not None else set()
    if isinstance(t, Hata):
        return t
    isaret, a, z = (1, n1, n2) if n1 <= n2 else (-1, n2, n1)
    return float(isaret * sum(1 for n in range(a, z + 1) if _is(n, hs, t)))


@fonksiyon("WORKDAY.INTL", en_az=2, en_cok=4)
def _workday_intl(b, bas, gun, hafta_sonu=None, tatil=None):
    n = _seri(bas)
    k = sayiya(ham(gun))
    for x in (n, k):
        if isinstance(x, Hata):
            return x
    hs = _haftasonu(hafta_sonu)
    if isinstance(hs, Hata):
        return hs
    if len(hs) == 7:
        return D.DEGER_HATASI
    t = _tatiller(tatil) if tatil is not None else set()
    if isinstance(t, Hata):
        return t
    k = math.trunc(k)
    adim = 1 if k >= 0 else -1
    kalan = abs(k)
    while kalan:
        n += adim
        if n < 0 or n > MAKS_SERI:
            return D.SAYI
        if _is(n, hs, t):
            kalan -= 1
    return float(n)
