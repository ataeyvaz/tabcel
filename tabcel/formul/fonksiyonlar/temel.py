"""Çekirdek fonksiyonlar ve fonksiyon yazarken kullanılan ortak yardımcılar.

Buradaki SUM ve IF motor testleri için örnek kalıptır; geri kalan fonksiyonlar gruplara
(matematik.py, istatistik.py …) eklenir.
"""
from typing import Iterator, Union

from ...model.deger import Hata
from ...model import deger as D
from ..degerler import BOS_ARG, AralikDeger, Dizi, _boyut, _okuyucu, _yay, skalere
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


def cok_hucreli(v) -> bool:
    bt = _boyut(v)
    return bt is not None and bt != (1, 1)


def dizi_sec(kosullar, degerler, yoksa) -> Dizi:
    """Excel 365: koşul(lar) çok hücreliyse öğe öğe seçim. `kosullar[i]` doğruysa `degerler[i]`
    (boş → 0); hiçbiri doğru değilse `yoksa` (ölçülerin hepsi aynı yayma kuralıyla: 1 satırlı/sütunlu
    taraf genişler, yetmeyen yerde #YOK). Koşul öğesi hatalıysa o öğe hata olur."""
    ogeler = list(kosullar) + list(degerler) + [yoksa]
    R = max([bt[0] for bt in map(_boyut, ogeler) if bt] or [1])
    C = max([bt[1] for bt in map(_boyut, ogeler) if bt] or [1])
    kok = [_yay(_okuyucu(x), _boyut(x), R, C) for x in kosullar]
    dok = [_yay(_okuyucu(x), _boyut(x), R, C) for x in degerler]
    yok = _yay(_okuyucu(yoksa), _boyut(yoksa), R, C)
    satirlar = []
    for i in range(R):
        satir = []
        for j in range(C):
            sonuc = None
            for ko, do in zip(kok, dok):
                k = mantiga(ko(i, j))
                if isinstance(k, Hata):
                    sonuc = k
                    break
                if k:
                    sonuc = do(i, j)
                    break
            else:
                sonuc = yok(i, j)
            satir.append(0.0 if sonuc is None else sonuc)
        satirlar.append(satir)
    return Dizi(satirlar)


@fonksiyon("IF", en_az=2, en_cok=3, tembel=True)
def _if(b, kosul, dogruysa, yanlissa=None):
    kv = kosul()
    if cok_hucreli(kv):                            # dizi/aralık koşulu: öğe öğe (Excel 365)
        return dizi_sec([kv], [dogruysa()], yanlissa() if yanlissa is not None else False)
    k = mantiga(skalere(kv, b.satir, b.sutun))
    if isinstance(k, Hata):
        return k
    if k:
        v = dogruysa()
        return 0.0 if v is BOS_ARG else v
    if yanlissa is None:
        return False
    v = yanlissa()
    return 0.0 if v is BOS_ARG else v
