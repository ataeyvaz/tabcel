"""Excel tür dönüşümleri ve karşılaştırma. Qt yok.

Çalışma zamanı dönüşümleri (metin → sayı, sayı → metin) Excel'de sistemin yerel ayarına bağlıdır;
uygulama Türkçe olduğundan burada Türkçe kurallar kullanılır (`="2,5"+1` = 3,5).
Doğrulanmamış ayrıntılar surec.md §8b'dedir.
"""
import math
from typing import Union

from ..model import deger as D
from ..model.deger import Hata
from ..model.girdi import sayi_coz
from .yerel import tr_kucuk

Sayi = Union[float, Hata]


def sayi_metninden(metin: str):
    """Metni sayıya çevirmeyi dener (Türkçe yazım; sonda % varsa yüzde). Olmazsa None.
    Tarih/saat metinleri Faz 3 (sayı biçimleriyle) — şimdilik dönüşmez."""
    m = metin.strip()
    if not m:
        return None
    yuzde = m.endswith("%")
    if yuzde:
        m = m[:-1].rstrip()
    n = sayi_coz(m)
    if n is None:
        return None
    return n / 100 if yuzde else n


def sayiya(v) -> Sayi:
    """Aritmetik için: boş → 0, DOĞRU → 1, sayı gibi metin → sayı, diğer metin → #DEĞER!."""
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, float):
        return v
    if isinstance(v, int):
        return float(v)
    if isinstance(v, Hata):
        return v
    if isinstance(v, str):
        n = sayi_metninden(v)
        return D.DEGER_HATASI if n is None else n
    return D.DEGER_HATASI


def sayi_metni(x: float) -> str:
    """Sayının metin hali (`&`, METNEÇEVİR olmadan birleştirme): en çok 15 anlamlı basamak,
    ondalık virgül. Bilimsel gösterime geçiş eşiği Excel'de doğrulanmadı (surec.md §8b)."""
    if x == 0:
        return "0"
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    t = f"{x:.15g}"
    if "e" in t:
        mantis, us = t.split("e")
        isaret = us[0]
        us = us[1:].lstrip("0").rjust(2, "0")
        t = f"{mantis}E{isaret}{us}"
    return t.replace(".", ",")


def metne(v) -> Union[str, Hata]:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "DOĞRU" if v else "YANLIŞ"
    if isinstance(v, float):
        return sayi_metni(v)
    if isinstance(v, Hata):
        return v
    return str(v)


def mantiga(v) -> Union[bool, Hata]:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, float):
        return v != 0
    if isinstance(v, Hata):
        return v
    if isinstance(v, str):
        k = tr_kucuk(v.strip())
        if k in ("doğru", "true"):
            return True
        if k in ("yanliş", "yanlış", "false"):
            return False
    return D.DEGER_HATASI


def sayi_sonucu(x: float) -> Sayi:
    """Hesaplanan sayıyı denetler: sonsuz/NaN → #SAYI!; -0 → 0."""
    if math.isnan(x) or math.isinf(x):
        return D.SAYI
    return x + 0.0


def onbes_basamak(x: float) -> float:
    """15 anlamlı basamağa yuvarlar (Excel'in karşılaştırma/gösterim duyarlığı)."""
    if x == 0 or math.isinf(x) or math.isnan(x):
        return x
    return float(f"{x:.15g}")


def _tur_sirasi(v) -> int:
    if isinstance(v, bool):
        return 2
    if isinstance(v, str):
        return 1
    return 0


def karsilastir(a, b) -> Union[int, Hata]:
    """Excel karşılaştırması: −1 / 0 / 1. Sayı < metin < mantıksal; metin büyük/küçük harf
    duyarsız; boş, karşısındakinin türünde boş değer gibi davranır (0, "", YANLIŞ)."""
    if isinstance(a, Hata):
        return a
    if isinstance(b, Hata):
        return b
    if a is None and b is None:
        return 0
    if a is None:
        a = False if isinstance(b, bool) else "" if isinstance(b, str) else 0.0
    if b is None:
        b = False if isinstance(a, bool) else "" if isinstance(a, str) else 0.0
    ta, tb = _tur_sirasi(a), _tur_sirasi(b)
    if ta != tb:
        return -1 if ta < tb else 1
    if ta == 1:
        a, b = tr_kucuk(a), tr_kucuk(b)
    elif ta == 0:
        a, b = onbes_basamak(float(a)), onbes_basamak(float(b))
    return (a > b) - (a < b)
