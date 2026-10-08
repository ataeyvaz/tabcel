"""Kullanıcının yazdığı metni hücre değerine çevirir (Excel, Türkçe yerel ayar). Qt yok.

Kurallar:
- Boş metin → hücre silinir.
- Başta kesme işareti (') → kalan kısım metindir.
- '=' ile başlayıp devamı olan → formül. Şimdilik yazıldığı gibi saklanır; kanonik
  İngilizce biçime çeviri Faz 2'de formul/ yerelleştirme katmanında yapılacak.
- DOĞRU/YANLIŞ (TRUE/FALSE de) → mantıksal.
- Sayı: ondalık ayırıcı virgül, binlik ayırıcı nokta (yalnızca 3'lü gruplarla).
  "1.5" gibi noktalı ondalık Excel'de tarih olabilir; tarih çözümü Faz 3'te,
  şimdilik metin kalır.
- Yüzde, para birimi, tarih/saat: Faz 3.
"""
import re
from typing import Optional

from .sayfa import Hucre

_SAYI_RE = re.compile(
    r"^[+-]?(?:\d{1,3}(?:\.\d{3})+|\d*)(?:,\d*)?(?:[eE][+-]?\d+)?$")

_MANTIKSAL = {"DOĞRU": True, "YANLIŞ": False, "TRUE": True, "FALSE": False}


def sayi_coz(metin: str) -> Optional[float]:
    m = metin.strip()
    if not _SAYI_RE.match(m) or not any(ch.isdigit() for ch in m):
        return None
    try:
        return float(m.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _mantiksal_coz(metin: str) -> Optional[bool]:
    m = metin.strip()
    # Türkçe büyük harf: 'i' → 'İ' için önce kendi dönüşümümüzü yapıyoruz
    return _MANTIKSAL.get(m.replace("i", "İ").replace("ı", "I").upper())


def girdi_coz(metin: str) -> Optional[Hucre]:
    if metin == "":
        return None
    if metin.startswith("'"):
        return Hucre(metin[1:]) if len(metin) > 1 else None
    if metin.startswith("=") and len(metin) > 1:
        return Hucre(None, metin)
    b = _mantiksal_coz(metin)
    if b is not None:
        return Hucre(b)
    n = sayi_coz(metin)
    if n is not None:
        return Hucre(n)
    return Hucre(metin)


def sayi_yaz(n: float) -> str:
    """Düzenleme kutusu için sayı metni (binlik ayırıcısız, ondalık virgül)."""
    if n == int(n) and abs(n) < 1e15:
        return str(int(n))
    return repr(n).replace(".", ",").replace("e", "E")


def duzenleme_metni(hucre: Optional[Hucre]) -> str:
    """Hücreyi düzenlerken görünen metin; girdi_coz ile gidiş-dönüş yapar."""
    if hucre is None:
        return ""
    if hucre.formul is not None:
        return hucre.formul
    v = hucre.deger
    if v is None:
        return ""
    if isinstance(v, bool):
        return "DOĞRU" if v else "YANLIŞ"
    if isinstance(v, float):
        return sayi_yaz(v)
    if isinstance(v, str):
        # Metin başka türe çözülecekse (sayı gibi görünen metin) başına ' konur.
        yeni = girdi_coz(v)
        if v == "" or v.startswith(("'", "=")) or yeni is None or yeni.deger != v:
            return "'" + v
        return v
    return str(v)
