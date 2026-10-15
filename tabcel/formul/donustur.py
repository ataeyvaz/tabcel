"""Excel tür dönüşümleri ve karşılaştırma. Qt yok.

Çalışma zamanı dönüşümleri (metin → sayı, sayı → metin) Excel'de sistemin yerel ayarına bağlıdır;
uygulama Türkçe olduğundan burada Türkçe kurallar kullanılır (`="2,5"+1` = 3,5).
Doğrulanmamış ayrıntılar surec.md §8b'dedir.
"""
import math
from typing import Union

from ..model import deger as D
from ..model.deger import Hata
from ..model.harmanla import metin_anahtari
from ..model.girdi import sayi_coz, sayisal_akilli
from .yerel import tr_kucuk

Sayi = Union[float, Hata]


def sayi_metninden(metin: str):
    """Metni sayıya çevirmeyi dener (Türkçe yazım; sonda % varsa yüzde; tarih, saat, para ve kesir
    yazımı hücreye yazılmış gibi çözülür: `="1.1.2026"+1` tarih + 1). Olmazsa None."""
    m = metin.strip()
    if not m:
        return None
    yuzde = m.endswith("%")
    if yuzde:
        m = m[:-1].rstrip()
    n = sayi_coz(m)
    if n is None:
        a = sayisal_akilli(metin)
        return None if a is None else a[0]
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
    """Sayının metin hali (`&`, METNEÇEVİR olmadan birleştirme): en çok 15 anlamlı basamak, ondalık virgül.
    Gerçek Excel 16'da (COM, 2026-10-15) ölçülen kural: 15 basamağa yuvarlanıp sondaki sıfırlar atılır;
    ondalık gösterim, tamsayı kısmı ≤ 20 basamak ve ondalık basamak sayısı ≤ 18 ise kullanılır
    (0,00001; 123456789012345000), aksi halde bilimsel (1,5E+20; 1,23456789012345E-05)."""
    if x == 0:
        return "0"
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    isaret = "-" if x < 0 else ""
    mantis, us = f"{abs(x):.14e}".split("e")
    basamaklar = mantis.replace(".", "").rstrip("0") or "0"
    e = int(us)
    if e >= 0:
        sigar = e + 1 <= 20
    else:
        sigar = (-e - 1) + len(basamaklar) <= 18
    if not sigar:
        govde = basamaklar[0] + ("," + basamaklar[1:] if len(basamaklar) > 1 else "")
        return f"{isaret}{govde}E{'-' if e < 0 else '+'}{abs(e):02d}"
    if e >= 0:
        tam = basamaklar[:e + 1].ljust(e + 1, "0")
        kesir = basamaklar[e + 1:]
        return isaret + tam + ("," + kesir if kesir else "")
    return isaret + "0," + "0" * (-e - 1) + basamaklar


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
        # Türkçe Excel (COM, 2026-10-15): yalnız yerel ad çevrilir; "TRUE"/"FALSE"/"1"/"0" metni #DEĞER! verir
        if k == "doğru":
            return True
        if k in ("yanliş", "yanlış"):
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
        # eşitlik: Türkçe büyük/küçük harf duyarsız tam eşitlik; sıra: Türkçe alfabe (ç, ğ, ı, ö, ş, ü
        # kendi yerinde — `"ç" < "d"` DOĞRU; surec.md §8b-55)
        ka, kb = tr_kucuk(a), tr_kucuk(b)
        if ka == kb:
            return 0
        ma, mb = metin_anahtari(a), metin_anahtari(b)
        if ma == mb:
            return (ka > kb) - (ka < kb)
        return (ma > mb) - (ma < mb)
    elif ta == 0:
        a, b = onbes_basamak(float(a)), onbes_basamak(float(b))
    return (a > b) - (a < b)
