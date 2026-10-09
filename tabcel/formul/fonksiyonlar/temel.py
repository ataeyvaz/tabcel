"""Çekirdek fonksiyonlar ve fonksiyon yazarken kullanılan ortak yardımcılar.

Buradaki SUM ve IF motor testleri için örnek kalıptır; geri kalan fonksiyonlar gruplara
(matematik.py, istatistik.py …) eklenir.
"""
from typing import Iterator, Union

from ...model.deger import Hata
from ..degerler import BOS_ARG, AralikDeger, Dizi, skalere
from ..donustur import mantiga, sayiya
from . import fonksiyon


def sayilar(args) -> Iterator[Union[float, Hata]]:
    """TOPLA/ORTALAMA/MAK… kuralı: doğrudan yazılan argümanlar sayıya çevrilir (metin "3" → 3,
    DOĞRU → 1, sayı olmayan metin → #DEĞER!); aralık ve dizilerde yalnız sayılar alınır (metin,
    mantıksal, boş atlanır); hatalar her durumda yayılır. Atlanmış argüman atlanır."""
    for a in args:
        if isinstance(a, AralikDeger):
            liste, hata = a.sayilar()
            if hata is not None:
                yield hata
            yield from liste
        elif isinstance(a, Dizi):
            for v in a.degerler():
                if isinstance(v, float) and not isinstance(v, bool):
                    yield v
                elif isinstance(v, Hata):
                    yield v
        elif a is BOS_ARG or a is None:
            continue
        else:
            yield sayiya(a)


@fonksiyon("SUM", en_az=1, en_cok=255)
def _sum(b, *args):
    if len(args) == 1 and isinstance(args[0], AralikDeger):     # sıcak yol: =TOPLA(A1:A100)
        toplam, _, hata = args[0].toplam()
        return hata if hata is not None else toplam
    toplam = 0.0
    for v in sayilar(args):
        if isinstance(v, Hata):
            return v
        toplam += v
    return toplam


@fonksiyon("IF", en_az=2, en_cok=3, tembel=True)
def _if(b, kosul, dogruysa, yanlissa=None):
    k = mantiga(skalere(kosul(), b.satir, b.sutun))
    if isinstance(k, Hata):
        return k
    if k:
        v = dogruysa()
        return 0.0 if v is BOS_ARG else v
    if yanlissa is None:
        return False
    v = yanlissa()
    return 0.0 if v is BOS_ARG else v
