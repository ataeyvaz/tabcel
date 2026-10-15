"""Mantık fonksiyonları (IF temel.py'de). Qt yok."""
from ...model import deger as D
from ...model.deger import Hata
from ..degerler import BOS_ARG, AralikDeger, Dizi
from ..donustur import karsilastir, mantiga
from . import fonksiyon
from .ortak import ham, matris, skaler
from .temel import cok_hucreli, dizi_sec


def _mantiklar(args):
    """AND/OR/XOR için mantıksal değerler (liste) ya da ilk hata. Aralıktaki de doğrudan yazılan da metin ve boş
    atlanır (Excel COM 2026-10-15: AND(DOĞRU;"a") = DOĞRU, OR("a";YANLIŞ) = YANLIŞ). Hiç değer yoksa #DEĞER!."""
    cikti = []
    for a in args:
        if isinstance(a, (AralikDeger, Dizi)):
            degerler = a.dolu_degerler() if isinstance(a, AralikDeger) else a.degerler()
            for v in degerler:
                if isinstance(v, Hata):
                    return v
                if isinstance(v, bool):
                    cikti.append(v)
                elif isinstance(v, float):
                    cikti.append(v != 0)
        elif a is BOS_ARG:
            continue
        elif isinstance(a, str):
            continue
        else:
            m = mantiga(a)
            if isinstance(m, Hata):
                return m
            cikti.append(m)
    return cikti if cikti else D.DEGER_HATASI


@fonksiyon("AND", en_az=1, en_cok=255)
def _and(b, *args):
    m = _mantiklar(args)
    return m if isinstance(m, Hata) else all(m)


@fonksiyon("OR", en_az=1, en_cok=255)
def _or(b, *args):
    m = _mantiklar(args)
    return m if isinstance(m, Hata) else any(m)


@fonksiyon("XOR", en_az=1, en_cok=255)
def _xor(b, *args):
    m = _mantiklar(args)
    return m if isinstance(m, Hata) else sum(m) % 2 == 1


@skaler("NOT", "b")
def _not(b, x):
    return not x


@fonksiyon("TRUE", en_az=0, en_cok=0)
def _true(b):
    return True


@fonksiyon("FALSE", en_az=0, en_cok=0)
def _false(b):
    return False


@fonksiyon("IFS", en_az=2, en_cok=254, tembel=True)
def _ifs(b, *args):
    if len(args) % 2:
        return D.YOK
    for i in range(0, len(args), 2):
        kv = args[i]()
        if cok_hucreli(kv):                        # dizi koşulu: kalan çiftlerle öğe öğe (Excel 365)
            kosullar, degerler = [kv], [args[i + 1]()]
            for j in range(i + 2, len(args), 2):
                kosullar.append(args[j]())
                degerler.append(args[j + 1]())
            return dizi_sec(kosullar, degerler, D.YOK)
        k = mantiga(ham(kv))
        if isinstance(k, Hata):
            return k
        if k:
            v = args[i + 1]()
            return 0.0 if v is BOS_ARG else v
    return D.YOK


def _hata_degistir(deger, yedek, sadece_yok):
    def hata_mi(v):
        return isinstance(v, Hata) and (v == D.YOK or not sadece_yok)
    v = deger()
    if isinstance(v, (AralikDeger, Dizi)) and matris(v)[:2] != (1, 1):
        R, C, oku = matris(v)
        if not any(hata_mi(oku(i, j)) for i in range(R) for j in range(C)):
            return v
        y = yedek()
        return Dizi([[(y if hata_mi(oku(i, j)) else oku(i, j)) for j in range(C)]
                     for i in range(R)])
    v = ham(v)
    if hata_mi(v):
        y = yedek()
        return 0.0 if y is BOS_ARG else y
    return 0.0 if v is None else v


@fonksiyon("IFERROR", en_az=2, en_cok=2, tembel=True)
def _iferror(b, deger, yedek):
    return _hata_degistir(deger, yedek, False)


@fonksiyon("IFNA", en_az=2, en_cok=2, tembel=True)
def _ifna(b, deger, yedek):
    return _hata_degistir(deger, yedek, True)


@fonksiyon("SWITCH", en_az=3, en_cok=255, tembel=True)
def _switch(b, *args):
    ifade = ham(args[0]())
    if isinstance(ifade, Hata):
        return ifade
    kalan = args[1:]
    for i in range(0, len(kalan) - 1, 2):
        aday = ham(kalan[i]())
        if isinstance(aday, Hata):
            return aday
        if karsilastir(ifade, aday) == 0:
            v = kalan[i + 1]()
            return 0.0 if v is BOS_ARG else v
    if len(kalan) % 2:
        v = kalan[-1]()
        return 0.0 if v is BOS_ARG else v
    return D.YOK
