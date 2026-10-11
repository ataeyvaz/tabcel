"""Türkçe harmanlama ve Excel sıralama düzeni (faz5_tasarim.md §1.4). Qt yok; `formul/` içe aktarılmaz.

- `metin_anahtari`: Türkçe alfabe sırası (a b c ç d e f g ğ h ı i j k l m n o ö p q r s ş t u ü v w x y z).
  Birincil düzey: noktalama/simge < rakam < harf. Kısa çizgi ve kesme işareti birincil düzeyde yok
  sayılır (Windows "word sort"), eşitlikte ikincil düzeyde karşılaştırılır; aksanlı yabancı harf
  (â î û é …) temel harfle aynı birincil ağırlıktadır, ikincil düzeyde sonra gelir.
- `deger_anahtari`: Excel sıralama düzeni (sayı < metin < YANLIŞ < DOĞRU < hata < boş; azalanda
  boş yine en sonda).
"""
import unicodedata
from typing import Any, Tuple

from ..metin_tr import tr_buyuk, tr_kucuk  # noqa: F401  (tek kaynak; eski içe aktarma yolu korunur)
from .deger import Hata

_ALFABE = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"
_SIRA = {h: i for i, h in enumerate(_ALFABE)}
_YOK_SAYILAN = "-'’‘‐‑"          # birincil düzeyde atlanan karakterler


def _taban(c: str) -> Tuple[str, bool]:
    """Küçük harf `c` için (birincil harf, aksanlı mı). Türkçe harfler (ç ğ ı ö ş ü) kendi başınadır."""
    if c in _SIRA or c.isascii():
        return c, False
    ayrik = unicodedata.normalize("NFD", c)
    if len(ayrik) > 1 and ayrik[0] in _SIRA:
        return ayrik[0], True
    return c, False


def metin_anahtari(s: str, buyuk_kucuk: bool = False) -> tuple:
    """Metin sıralama anahtarı: `(birincil, ikincil, üçüncül)`. `buyuk_kucuk=True`: eşit anahtarda
    küçük harf önce gelir (Excel "Büyük/küçük harfe duyarlı")."""
    birincil = []
    ikincil = []
    ucuncul = []
    for orijinal in s:
        c = tr_kucuk(orijinal)
        if len(c) != 1:                       # nadir: küçük harfi birden çok karakter olan harf
            c = orijinal
        if c in _YOK_SAYILAN:
            ikincil.append(ord(c))
            ucuncul.append(0)
            continue
        taban, aksanli = _taban(c)
        if taban in _SIRA:
            birincil.append((2, _SIRA[taban]))
        elif taban.isdigit():
            birincil.append((1, int(unicodedata.digit(taban, 0))))
        elif taban.isalpha():
            birincil.append((3, ord(taban)))
        else:                                 # boşluk, noktalama, simge
            birincil.append((0, ord(taban)))
        ikincil.append(ord(c) if aksanli else 0)
        ucuncul.append(1 if orijinal != c else 0)
    return (tuple(birincil), tuple(ikincil), tuple(ucuncul) if buyuk_kucuk else ())


class _Ters:
    """Karşılaştırması ters çevrilmiş sarmalayıcı (azalan sıralamada anahtar içi için)."""
    __slots__ = ("x",)

    def __init__(self, x):
        self.x = x

    def __lt__(self, diger):
        return diger.x < self.x

    def __eq__(self, diger):
        return self.x == diger.x


def _onbes(x: float) -> float:
    if x == 0 or x != x or x in (float("inf"), float("-inf")):
        return x
    return float(f"{x:.15g}")


def deger_anahtari(v: Any, artan: bool = True, buyuk_kucuk: bool = False) -> tuple:
    """Hücre değerinin Excel sıralama anahtarı; `sorted(key=...)` artan düzende yeterlidir (azalan
    için de aynı çağrı, `artan=False`). Artan: sayı < metin < YANLIŞ < DOĞRU < hata < boş. Azalan:
    hata, DOĞRU, YANLIŞ, metin, sayı; boş her iki yönde en sonda. Hatalar birbirine eşit sayılır
    (kararlı sıralama sırayı korur)."""
    if v is None:
        return (9, 0)
    if isinstance(v, Hata):
        sinif, ic = 4, 0
    elif isinstance(v, bool):
        sinif, ic = 2, int(v)
    elif isinstance(v, (int, float)):
        sinif, ic = 0, _onbes(float(v))
    else:
        sinif, ic = 1, metin_anahtari(str(v), buyuk_kucuk)
    if artan:
        return (sinif, ic)
    return (4 - sinif, _Ters(ic))
