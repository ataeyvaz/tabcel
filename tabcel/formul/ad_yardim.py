"""Tanımlı adlar için arayüzün kullandığı yardımcılar (Qt yok): adın hedef aralığı, seçimin adı,
Başvurur metni üretme/çözme, adın değeri. Kurallar: faz5_tasarim.md §4.5."""
from typing import List, Optional, Tuple

from ..model import deger as D
from ..model.adres import Aralik, sutun_harfe
from ..model.ad import TanimliAd
from ..model.gosterim import goster
from . import ceviri
from .agac import Ad
from .degerlendir import Baglam, degerlendir, hucre_sonucu
from .degerler import AralikDeger
from .kaydir import sayfaya_bagla
from .sozcuk import sayfa_oneki

Hedef = Tuple[object, Aralik]           # (Sayfa, Aralik)


def _degerle(kitap, tanim: TanimliAd, sayfa):
    """Adın formülünü A1'e göre (sayfa = kullanıldığı sayfa) değerlendirir: Ad düğümü üzerinden."""
    b = Baglam(sayfa, 1, 1, kitap)
    try:
        return degerlendir(Ad(tanim.ad), b), b
    except Exception:
        return D.DEGER_HATASI, b


def hedef_aralik(kitap, tanim: TanimliAd, sayfa=None) -> Optional[Hedef]:
    """Ad bir hücre/aralığa başvuruyorsa (Sayfa, Aralik); değilse (sabit, formül, hata) None.
    `sayfa`: adın kullanıldığı sayfa (kapsamlı adda kapsam sayfası); göreli adlar A1'e göre çözülür."""
    if sayfa is None:
        sayfa = (kitap.sayfa_kimlikle(tanim.kapsam) if tanim.kapsam is not None else None) or kitap.sayfalar[0]
    v, _ = _degerle(kitap, tanim, sayfa)
    if isinstance(v, AralikDeger) and v.sayfa is not None:
        return v.sayfa, Aralik(v.r1, v.c1, v.r2, v.c2)
    return None


def deger_metni(kitap, tanim: TanimliAd) -> str:
    """Ad Yöneticisi "Değer" sütunu: tek değer görünen metin, çok hücreli aralık/dizi `{…}`."""
    sayfa = (kitap.sayfa_kimlikle(tanim.kapsam) if tanim.kapsam is not None else None) or kitap.sayfalar[0]
    v, b = _degerle(kitap, tanim, sayfa)
    if isinstance(v, AralikDeger):
        if (v.r1, v.c1) == (v.r2, v.c2):
            return goster(v.hucre_degeri(v.r1, v.c1))
        return "{…}"
    if hasattr(v, "satirlar") or type(v).__name__ == "Dizi":
        return "{…}"
    return goster(v)


def secimin_adi(kitap, sayfa, aralik: Aralik) -> Optional[str]:
    """Seçim tam olarak bir adın aralığıysa o ad (Ad Kutusu bunu gösterir). Sayfa kapsamlı ad önce."""
    if not kitap.adlar or len(kitap.adlar) > 500:
        return None
    adaylar = sorted((t for t in kitap.adlar.values() if not t.gizli and t.kapsam in (None, sayfa.kimlik)),
                     key=lambda t: (t.kapsam is None, t.ad.casefold()))
    for t in adaylar:
        h = hedef_aralik(kitap, t, sayfa)
        if h is not None and h[0] is sayfa and h[1] == aralik:
            return t.ad
    return None


def gorunur_adlar(kitap, sayfa=None) -> List[TanimliAd]:
    """Listede gösterilecek (gizli olmayan) adlar; `sayfa` verilirse yalnız o sayfada görünenler."""
    sonuc = [t for t in kitap.adlar.values() if not t.gizli
             and (t.kapsam is None or kitap.sayfa_kimlikle(t.kapsam) is not None)
             and (sayfa is None or t.kapsam in (None, sayfa.kimlik))]
    return sorted(sonuc, key=lambda t: (t.ad.casefold(), t.kapsam is not None))


# ------------------------------------------------------------------ Başvurur metni
def aralik_basvurusu(sayfa, aralik: Aralik) -> str:
    """Seçimin Başvurur için mutlak biçimi: `=Sayfa1!$A$1:$B$5` (sayfa adı gerekirse tırnaklı)."""
    a = f"${sutun_harfe(aralik.ilk_sutun)}${aralik.ilk_satir}"
    if (aralik.ilk_satir, aralik.ilk_sutun) != (aralik.son_satir, aralik.son_sutun):
        a += f":${sutun_harfe(aralik.son_sutun)}${aralik.son_satir}"
    return "=" + sayfa_oneki(sayfa.ad) + a


def basvurur_saklanan(kitap, metin: str, sayfa) -> str:
    """Kullanıcının yazdığı Türkçe Başvurur metni → saklanan biçim. Sayfasız hücre başvuruları `sayfa`ya
    bağlanır (Excel: ad tanımlanırken etkin sayfa). Hata → `FormulHatasi`."""
    metin = metin.strip()
    if not metin.startswith("="):
        metin = "=" + metin
    return sayfaya_bagla(ceviri.girdiden(metin, kitap), sayfa.kimlik)


def basvurur_gosterim(kitap, tanim: TanimliAd) -> str:
    return ceviri.gosterime(tanim.formul, kitap)
