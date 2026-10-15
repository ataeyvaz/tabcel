"""Finans işlevleri, 2. küme (işlev kitaplığı genişletmesi, 2026-10-15). Qt yok."""
import math

from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG
from ..donustur import sayi_sonucu, sayiya
from . import fonksiyon
from .finans import _ek
from .ortak import duz, ham, skaler
from .temel import sayilar


def _pmt(r, n, pv, fv, tur):
    if r == 0:
        return -(pv + fv) / n
    return -(pv * (1 + r) ** n + fv) / _ek(r, n, tur)


def _bakiye(r, k, pmt, pv, tur):
    """k ödemeden sonraki 'FV' (Excel FV işaretiyle)."""
    return -(pv * (1 + r) ** k + pmt * _ek(r, k, tur))


def _faiz(r, per, n, pv, fv, tur):
    pmt = _pmt(r, n, pv, fv, tur)
    if tur == 1:
        if per == 1:
            return 0.0, pmt
        return (_bakiye(r, per - 2, pmt, pv, 1) - pmt) * r, pmt
    return _bakiye(r, per - 1, pmt, pv, 0) * r, pmt


@skaler("IPMT", "ssssss", en_az=4)
def _ipmt(b, r, per, n, pv, fv=0.0, tur=0.0):
    if per < 1 or per > n or n <= 0:
        return D.SAYI
    try:
        return sayi_sonucu(_faiz(r, math.floor(per), n, pv, fv, 1 if tur else 0)[0])
    except (OverflowError, ZeroDivisionError):
        return D.SAYI


@skaler("PPMT", "ssssss", en_az=4)
def _ppmt(b, r, per, n, pv, fv=0.0, tur=0.0):
    if per < 1 or per > n or n <= 0:
        return D.SAYI
    try:
        ip, pmt = _faiz(r, math.floor(per), n, pv, fv, 1 if tur else 0)
        return sayi_sonucu(pmt - ip)
    except (OverflowError, ZeroDivisionError):
        return D.SAYI


def _kum(b, r, n, pv, bas, son, tur, anapara):
    if r <= 0 or n <= 0 or pv <= 0 or bas < 1 or son < bas or son > n or tur not in (0, 1):
        return D.SAYI
    try:
        t = 0.0
        for per in range(int(math.floor(bas)), int(math.floor(son)) + 1):
            ip, pmt = _faiz(r, per, n, pv, 0.0, int(tur))
            t += (pmt - ip) if anapara else ip
        return sayi_sonucu(t)
    except (OverflowError, ZeroDivisionError):
        return D.SAYI


skaler("CUMIPMT", "ssssss")(lambda b, r, n, pv, bas, son, tur: _kum(b, r, n, pv, bas, son, tur, False))
skaler("CUMPRINC", "ssssss")(lambda b, r, n, pv, bas, son, tur: _kum(b, r, n, pv, bas, son, tur, True))


@skaler("EFFECT", "ss")
def _effect(b, nominal, k):
    k = math.trunc(k)
    if nominal <= 0 or k < 1:
        return D.SAYI
    return sayi_sonucu((1 + nominal / k) ** k - 1)


@skaler("NOMINAL", "ss")
def _nominal(b, etkin, k):
    k = math.trunc(k)
    if etkin <= 0 or k < 1:
        return D.SAYI
    return sayi_sonucu(k * ((1 + etkin) ** (1 / k) - 1))


@skaler("NPER", "ssssss", en_az=3)
def _nper(b, r, odeme, pv, fv=0.0, tur=0.0):
    try:
        if r == 0:
            return D.BOL0 if odeme == 0 else sayi_sonucu(-(pv + fv) / odeme)
        t = 1 + r * (1 if tur else 0)
        pay = odeme * t - fv * r
        payda = odeme * t + pv * r
        if payda == 0 or pay / payda <= 0:
            return D.SAYI
        return sayi_sonucu(math.log(pay / payda) / math.log(1 + r))
    except (ValueError, OverflowError, ZeroDivisionError):
        return D.SAYI


@skaler("RRI", "sss")
def _rri(b, n, pv, fv):
    if n <= 0:
        return D.SAYI
    if pv == 0:
        return D.SAYI
    if fv / pv < 0:
        return D.SAYI
    return sayi_sonucu((fv / pv) ** (1 / n) - 1)


@skaler("SLN", "sss")
def _sln(b, maliyet, hurda, omur):
    return D.BOL0 if omur == 0 else (maliyet - hurda) / omur


@skaler("SYD", "ssss")
def _syd(b, maliyet, hurda, omur, donem):
    if omur <= 0 or donem <= 0 or donem > omur or hurda < 0 or maliyet < 0:
        return D.SAYI
    return (maliyet - hurda) * (omur - donem + 1) * 2 / (omur * (omur + 1))


@skaler("DB", "sssss", en_az=4)
def _db(b, maliyet, hurda, omur, donem, ay=12.0):
    ay = math.trunc(ay)
    donem = math.trunc(donem) if donem == math.floor(donem) else donem
    if maliyet < 0 or hurda < 0 or omur <= 0 or donem <= 0 or ay < 1 or ay > 12 or donem > omur + (1 if ay < 12 else 0):
        return D.SAYI
    if maliyet == 0:
        return 0.0
    oran = round(1 - (hurda / maliyet) ** (1 / omur), 3)
    top = 0.0
    d = 0.0
    for i in range(1, int(donem) + 1):
        if i == 1:
            d = maliyet * oran * ay / 12
        elif i == omur + 1:
            d = (maliyet - top) * oran * (12 - ay) / 12
        else:
            d = (maliyet - top) * oran
        top += d
    return sayi_sonucu(d)


@skaler("DDB", "sssss", en_az=4)
def _ddb(b, maliyet, hurda, omur, donem, carpan=2.0):
    if maliyet < 0 or hurda < 0 or omur <= 0 or donem <= 0 or donem > omur or carpan <= 0:
        return D.SAYI
    oran = carpan / omur
    if donem != math.floor(donem):                # kesirli dönem: Excel kapalı biçimle hesaplar
        onceki = maliyet * (1 - (1 - oran) ** (donem - 1))
        return sayi_sonucu(max(0.0, min(maliyet * oran * (1 - oran) ** (donem - 1), maliyet - hurda - onceki)))
    top = 0.0
    d = 0.0
    for i in range(1, int(donem) + 1):
        d = max(0.0, min((maliyet - top) * oran, maliyet - hurda - top))
        top += d
    return sayi_sonucu(d)


@fonksiyon("MIRR", en_az=3, en_cok=3)
def _mirr(b, degerler, finans, yatirim):
    f, y = sayiya(ham(finans)), sayiya(ham(yatirim))
    for x in (f, y):
        if isinstance(x, Hata):
            return x
    liste = []
    for v in sayilar([degerler]):
        if isinstance(v, Hata):
            return v
        liste.append(v)
    n = len(liste)
    if n < 2 or not (any(v > 0 for v in liste) and any(v < 0 for v in liste)):
        return D.BOL0
    pozitif = sum(v / (1 + y) ** (i + 1) for i, v in enumerate(liste) if v > 0)
    negatif = sum(v / (1 + f) ** (i + 1) for i, v in enumerate(liste) if v < 0)
    try:
        return sayi_sonucu((-pozitif * (1 + y) ** n / (negatif * (1 + f))) ** (1 / (n - 1)) - 1)
    except (ValueError, OverflowError, ZeroDivisionError):
        return D.SAYI


def _deger_tarih(degerler, tarihler):
    v, t = duz(degerler), duz(tarihler)
    if len(v) != len(t):
        return None, D.SAYI
    cv, ct = [], []
    for a, c in zip(v, t):
        for x in (a, c):
            if isinstance(x, Hata):
                return None, x
        a, c = sayiya(a), sayiya(c)
        for x in (a, c):
            if isinstance(x, Hata):
                return None, x
        if c < 0:
            return None, D.SAYI
        cv.append(a)
        ct.append(math.floor(c))
    if any(x < ct[0] for x in ct):
        return None, D.SAYI
    return (cv, ct), None


@fonksiyon("XNPV", en_az=3, en_cok=3)
def _xnpv(b, oran, degerler, tarihler):
    r = sayiya(ham(oran))
    if isinstance(r, Hata):
        return r
    veri, h = _deger_tarih(degerler, tarihler)
    if h is not None:
        return h
    if r <= 0:                                  # Excel (COM 2026-10-15): oran 0 ve negatifte #SAYI!
        return D.SAYI
    cv, ct = veri
    try:
        return sayi_sonucu(sum(v / (1 + r) ** ((t - ct[0]) / 365) for v, t in zip(cv, ct)))
    except (OverflowError, ZeroDivisionError):
        return D.SAYI


@fonksiyon("XIRR", en_az=2, en_cok=3)
def _xirr(b, degerler, tarihler, tahmin=None):
    r = 0.1
    if tahmin is not None and tahmin is not BOS_ARG:
        r = sayiya(ham(tahmin))
        if isinstance(r, Hata):
            return r
    veri, h = _deger_tarih(degerler, tarihler)
    if h is not None:
        return h
    cv, ct = veri
    if not (any(v > 0 for v in cv) and any(v < 0 for v in cv)):
        return D.SAYI

    def f(x):
        return sum(v / (1 + x) ** ((t - ct[0]) / 365) for v, t in zip(cv, ct))

    def df(x):
        return sum(-((t - ct[0]) / 365) * v / (1 + x) ** ((t - ct[0]) / 365 + 1) for v, t in zip(cv, ct))
    try:
        for _ in range(200):
            d = df(r)
            if d == 0:
                return D.SAYI
            yeni = r - f(r) / d
            if yeni <= -1:
                yeni = (r - 1) / 2
            if abs(yeni - r) < 1e-10:
                return sayi_sonucu(yeni)
            r = yeni
    except (OverflowError, ZeroDivisionError):
        return D.SAYI
    return D.SAYI
