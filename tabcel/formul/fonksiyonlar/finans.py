"""Temel finans fonksiyonları. Qt yok.

Denklem (Excel): bd·(1+r)^n + ö·(1+r·tür)·((1+r)^n − 1)/r + gd = 0   (r = 0 iken bd + ö·n + gd = 0)
"""

from ...model import deger as D
from ...model.deger import Hata
from ..donustur import sayi_sonucu
from . import fonksiyon
from .ortak import skaler
from .temel import sayilar


def _ek(r: float, n: float, tur: float) -> float:
    """((1+r·tür)·((1+r)^n − 1)/r) çarpanı (ödeme çarpanı)."""
    if r == 0:
        return n
    return (1 + r * tur) * ((1 + r) ** n - 1) / r


@skaler("PMT", "sssss", en_az=3)
def _pmt(b, r, n, bd, gd=0.0, tur=0.0):
    if n == 0:
        return D.SAYI
    try:
        if r == 0:
            return sayi_sonucu(-(bd + gd) / n)
        return sayi_sonucu(-(bd * (1 + r) ** n + gd) / _ek(r, n, tur))
    except (OverflowError, ZeroDivisionError):
        return D.SAYI


@skaler("FV", "sssss", en_az=3)
def _fv(b, r, n, odeme, bd=0.0, tur=0.0):
    try:
        return sayi_sonucu(-(bd * (1 + r) ** n + odeme * _ek(r, n, tur)))
    except OverflowError:
        return D.SAYI


@skaler("PV", "sssss", en_az=3)
def _pv(b, r, n, odeme, gd=0.0, tur=0.0):
    try:
        return sayi_sonucu(-(gd + odeme * _ek(r, n, tur)) / (1 + r) ** n)
    except (OverflowError, ZeroDivisionError):
        return D.SAYI


@skaler("RATE", "ssssss", en_az=3)
def _rate(b, n, odeme, bd, gd=0.0, tur=0.0, tahmin=0.1):
    def f(r):
        if abs(r) < 1e-12:
            return bd + odeme * n + gd
        return bd * (1 + r) ** n + odeme * (1 + r * tur) * ((1 + r) ** n - 1) / r + gd
    r = tahmin
    try:
        for _ in range(100):
            y = f(r)
            h = 1e-7 * max(1.0, abs(r))
            tur_ = (f(r + h) - f(r - h)) / (2 * h)
            if tur_ == 0:
                return D.SAYI
            yeni = r - y / tur_
            if yeni <= -1:
                yeni = (r - 1) / 2
            if abs(yeni - r) < 1e-12:
                return D.SAYI if yeni < -0.999999 else sayi_sonucu(yeni)
            r = yeni
    except (OverflowError, ZeroDivisionError):
        return D.SAYI
    return D.SAYI


@fonksiyon("NPV", en_az=2, en_cok=255)
def _npv(b, oran, *degerler):
    from ..donustur import sayiya
    from .ortak import ham
    r = sayiya(ham(oran))
    if isinstance(r, Hata):
        return r
    if r == -1:
        return D.BOL0
    toplam = 0.0
    i = 0
    for v in sayilar(degerler):
        if isinstance(v, Hata):
            return v
        i += 1
        toplam += v / (1 + r) ** i
    return sayi_sonucu(toplam)


@fonksiyon("IRR", en_az=1, en_cok=2)
def _irr(b, degerler, tahmin=None):
    from ..donustur import sayiya
    from .ortak import ham
    liste = []
    for v in sayilar([degerler]):
        if isinstance(v, Hata):
            return v
        liste.append(v)
    if not (any(v > 0 for v in liste) and any(v < 0 for v in liste)):
        return D.SAYI
    r = 0.1
    if tahmin is not None:
        r = sayiya(ham(tahmin))
        if isinstance(r, Hata):
            return r

    def f(x):
        return sum(v / (1 + x) ** i for i, v in enumerate(liste))

    def df(x):
        return sum(-i * v / (1 + x) ** (i + 1) for i, v in enumerate(liste))
    try:
        for _ in range(100):
            d = df(r)
            if d == 0:
                return D.SAYI
            yeni = r - f(r) / d
            if yeni <= -1:
                yeni = (r - 1) / 2
            if abs(yeni - r) < 1e-12:
                return sayi_sonucu(yeni)
            r = yeni
    except (OverflowError, ZeroDivisionError):
        return D.SAYI
    return D.SAYI
